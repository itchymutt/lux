use crate::ast::*;
use crate::effects::Effect;
use crate::token::{Span, Token, TokenKind};

pub struct Parser {
    tokens: Vec<Token>,
    pos: usize,
}

#[derive(Debug)]
pub struct ParseError {
    pub message: String,
    pub offset: u32,
}

impl Parser {
    pub fn new(tokens: Vec<Token>) -> Self {
        Parser { tokens, pos: 0 }
    }

    pub fn parse_module(&mut self) -> Result<Module, ParseError> {
        let mut items = Vec::new();
        while !self.at_eof() {
            // Skip optional `pub` keyword
            if self.check(&TokenKind::Pub) {
                self.advance();
            }
            items.push(self.parse_item()?);
        }
        Ok(Module { items })
    }

    fn parse_item(&mut self) -> Result<Item, ParseError> {
        if self.check(&TokenKind::Fn) {
            Ok(Item::Function(self.parse_function()?))
        } else if self.check(&TokenKind::Struct) {
            Ok(Item::Struct(self.parse_struct_def()?))
        } else if self.check(&TokenKind::Enum) {
            Ok(Item::Enum(self.parse_enum_def()?))
        } else {
            Err(self.error("expected `fn`, `struct`, or `enum`"))
        }
    }

    fn parse_struct_def(&mut self) -> Result<StructDef, ParseError> {
        let start = self.current_span();
        self.expect(&TokenKind::Struct)?;
        let name = self.expect_ident()?;
        self.expect(&TokenKind::LBrace)?;

        let mut fields = Vec::new();
        while !self.check(&TokenKind::RBrace) && !self.at_eof() {
            let field_span = self.current_span();
            let field_name = self.expect_ident()?;
            self.expect(&TokenKind::Colon)?;
            let ty_span = self.current_span();
            let ty_name = self.expect_ident()?;
            fields.push(FieldDef {
                name: field_name,
                ty: TypeExpr {
                    name: ty_name,
                    span: ty_span,
                },
                span: field_span,
            });
            // Optional trailing comma
            if self.check(&TokenKind::Comma) {
                self.advance();
            }
        }
        let end = self.current_span();
        self.expect(&TokenKind::RBrace)?;

        Ok(StructDef {
            name,
            fields,
            span: Span::new(start.start as usize, end.end as usize),
        })
    }

    fn parse_enum_def(&mut self) -> Result<EnumDef, ParseError> {
        let start = self.current_span();
        self.expect(&TokenKind::Enum)?;
        let name = self.expect_ident()?;
        self.expect(&TokenKind::LBrace)?;

        let mut variants = Vec::new();
        while !self.check(&TokenKind::RBrace) && !self.at_eof() {
            let var_span = self.current_span();
            let var_name = self.expect_ident()?;
            let mut fields = Vec::new();
            if self.check(&TokenKind::LParen) {
                self.advance();
                while !self.check(&TokenKind::RParen) && !self.at_eof() {
                    let ty_span = self.current_span();
                    let ty_name = self.expect_ident()?;
                    fields.push(TypeExpr {
                        name: ty_name,
                        span: ty_span,
                    });
                    if !self.check(&TokenKind::RParen) {
                        self.expect(&TokenKind::Comma)?;
                    }
                }
                self.expect(&TokenKind::RParen)?;
            }
            variants.push(VariantDef {
                name: var_name,
                fields,
                span: var_span,
            });
            if self.check(&TokenKind::Comma) {
                self.advance();
            }
        }
        let end = self.current_span();
        self.expect(&TokenKind::RBrace)?;

        Ok(EnumDef {
            name,
            variants,
            span: Span::new(start.start as usize, end.end as usize),
        })
    }

    fn parse_function(&mut self) -> Result<Function, ParseError> {
        let start = self.current_span();
        self.expect(&TokenKind::Fn)?;

        let name = self.expect_ident()?;
        self.expect(&TokenKind::LParen)?;

        // Parse params (for Demo 1: always empty)
        let mut params = Vec::new();
        while !self.check(&TokenKind::RParen) && !self.at_eof() {
            let param = self.parse_param()?;
            params.push(param);
            if !self.check(&TokenKind::RParen) {
                self.expect(&TokenKind::Comma)?;
            }
        }
        self.expect(&TokenKind::RParen)?;

        // Parse optional return type: -> Type
        let return_type = if self.check(&TokenKind::Arrow) {
            self.advance();
            let ty_span = self.current_span();
            let ty_name = self.expect_ident()?;
            Some(TypeExpr {
                name: ty_name,
                span: ty_span,
            })
        } else {
            None
        };

        // Parse optional effects: can Effect1, Effect2
        let effects = if self.check(&TokenKind::Can) {
            self.advance();
            self.parse_effect_list()?
        } else {
            vec![]
        };

        // Parse body
        self.expect(&TokenKind::LBrace)?;
        let body = self.parse_body()?;
        let end = self.current_span();
        self.expect(&TokenKind::RBrace)?;

        Ok(Function {
            name,
            params,
            return_type,
            effects,
            body,
            span: Span::new(start.start as usize, end.end as usize),
        })
    }

    fn parse_param(&mut self) -> Result<Param, ParseError> {
        let span = self.current_span();
        let name = self.expect_ident()?;
        self.expect(&TokenKind::Colon)?;
        let ty_span = self.current_span();
        let ty_name = self.expect_ident()?;
        Ok(Param {
            name,
            ty: TypeExpr {
                name: ty_name,
                span: ty_span,
            },
            span,
        })
    }

    fn parse_effect_list(&mut self) -> Result<Vec<Effect>, ParseError> {
        let mut effects = Vec::new();
        loop {
            let span = self.current_span();
            let name = self.expect_ident()?;
            match Effect::from_str(&name) {
                Some(e) => effects.push(e),
                None => {
                    return Err(ParseError {
                        message: format!("unknown effect `{name}`"),
                        offset: span.start,
                    });
                }
            }
            if self.check(&TokenKind::Comma) {
                self.advance();
            } else {
                break;
            }
        }
        Ok(effects)
    }

    fn parse_body(&mut self) -> Result<Vec<Stmt>, ParseError> {
        let mut stmts = Vec::new();
        while !self.check(&TokenKind::RBrace) && !self.at_eof() {
            stmts.push(self.parse_stmt()?);
        }
        Ok(stmts)
    }

    fn parse_stmt(&mut self) -> Result<Stmt, ParseError> {
        if self.check(&TokenKind::Let) {
            self.parse_let()
        } else {
            Ok(Stmt::Expr(self.parse_expr()?))
        }
    }

    fn parse_let(&mut self) -> Result<Stmt, ParseError> {
        let span = self.current_span();
        self.expect(&TokenKind::Let)?;
        let name = self.expect_ident()?;
        self.expect(&TokenKind::Eq)?;
        let value = self.parse_expr()?;
        Ok(Stmt::Let(LetStmt { name, value, span }))
    }

    fn parse_expr(&mut self) -> Result<Expr, ParseError> {
        self.parse_comparison()
    }

    // Precedence climbing: comparison < additive < multiplicative < call < primary
    fn parse_comparison(&mut self) -> Result<Expr, ParseError> {
        let mut left = self.parse_additive()?;
        loop {
            let op = match &self.tokens[self.pos].kind {
                TokenKind::EqEq => BinOp::Eq,
                TokenKind::BangEq => BinOp::NotEq,
                TokenKind::Lt => BinOp::Lt,
                TokenKind::Gt => BinOp::Gt,
                TokenKind::LtEq => BinOp::LtEq,
                TokenKind::GtEq => BinOp::GtEq,
                _ => break,
            };
            self.advance();
            let right = self.parse_additive()?;
            let span = Span::new(left.span().start as usize, right.span().end as usize);
            left = Expr::BinOp {
                op,
                left: Box::new(left),
                right: Box::new(right),
                span,
            };
        }
        Ok(left)
    }

    fn parse_additive(&mut self) -> Result<Expr, ParseError> {
        let mut left = self.parse_multiplicative()?;
        loop {
            let op = match &self.tokens[self.pos].kind {
                TokenKind::Plus => BinOp::Add,
                TokenKind::Minus => BinOp::Sub,
                _ => break,
            };
            self.advance();
            let right = self.parse_multiplicative()?;
            let span = Span::new(left.span().start as usize, right.span().end as usize);
            left = Expr::BinOp {
                op,
                left: Box::new(left),
                right: Box::new(right),
                span,
            };
        }
        Ok(left)
    }

    fn parse_multiplicative(&mut self) -> Result<Expr, ParseError> {
        let mut left = self.parse_call()?;
        loop {
            let op = match &self.tokens[self.pos].kind {
                TokenKind::Star => BinOp::Mul,
                TokenKind::Slash => BinOp::Div,
                _ => break,
            };
            self.advance();
            let right = self.parse_call()?;
            let span = Span::new(left.span().start as usize, right.span().end as usize);
            left = Expr::BinOp {
                op,
                left: Box::new(left),
                right: Box::new(right),
                span,
            };
        }
        Ok(left)
    }

    fn parse_call(&mut self) -> Result<Expr, ParseError> {
        let mut expr = self.parse_primary()?;

        loop {
            if self.check(&TokenKind::LParen) {
                // Call syntax: expr(args...)
                let call_start = expr.span();
                self.advance();
                let mut args = Vec::new();
                while !self.check(&TokenKind::RParen) && !self.at_eof() {
                    args.push(self.parse_expr()?);
                    if !self.check(&TokenKind::RParen) {
                        self.expect(&TokenKind::Comma)?;
                    }
                }
                let end = self.current_span();
                self.expect(&TokenKind::RParen)?;
                expr = Expr::Call {
                    callee: Box::new(expr),
                    args,
                    span: Span::new(call_start.start as usize, end.end as usize),
                };
            } else if self.check(&TokenKind::Dot) {
                // Field access: expr.field
                self.advance();
                let field_span = self.current_span();
                let field = self.expect_ident()?;
                let span = Span::new(expr.span().start as usize, field_span.end as usize);
                expr = Expr::FieldAccess {
                    object: Box::new(expr),
                    field,
                    span,
                };
            } else {
                break;
            }
        }

        Ok(expr)
    }

    fn parse_match(&mut self) -> Result<Expr, ParseError> {
        let start = self.current_span();
        self.expect(&TokenKind::Match)?;
        let subject = self.parse_expr()?;
        self.expect(&TokenKind::LBrace)?;

        let mut arms = Vec::new();
        while !self.check(&TokenKind::RBrace) && !self.at_eof() {
            let arm_span = self.current_span();
            let pattern = self.parse_pattern()?;
            self.expect(&TokenKind::FatArrow)?;
            let body = self.parse_expr()?;
            arms.push(MatchArm {
                pattern,
                body,
                span: arm_span,
            });
            // Optional comma between arms
            if self.check(&TokenKind::Comma) {
                self.advance();
            }
        }
        let end = self.current_span();
        self.expect(&TokenKind::RBrace)?;

        Ok(Expr::Match {
            subject: Box::new(subject),
            arms,
            span: Span::new(start.start as usize, end.end as usize),
        })
    }

    fn parse_pattern(&mut self) -> Result<Pattern, ParseError> {
        let span = self.current_span();
        match &self.tokens[self.pos].kind {
            TokenKind::IntLit(n) => {
                let n = *n;
                self.advance();
                Ok(Pattern::IntLit(n, span))
            }
            TokenKind::Ident(name) if name == "_" => {
                self.advance();
                Ok(Pattern::Wildcard(span))
            }
            TokenKind::Ident(name) => {
                let name = name.clone();
                self.advance();
                // Check for variant pattern: Name(binding1, binding2)
                if self.check(&TokenKind::LParen) {
                    self.advance();
                    let mut bindings = Vec::new();
                    while !self.check(&TokenKind::RParen) && !self.at_eof() {
                        bindings.push(self.expect_ident()?);
                        if !self.check(&TokenKind::RParen) {
                            self.expect(&TokenKind::Comma)?;
                        }
                    }
                    self.expect(&TokenKind::RParen)?;
                    Ok(Pattern::Variant {
                        name,
                        bindings,
                        span,
                    })
                } else {
                    Ok(Pattern::Ident(name, span))
                }
            }
            _ => Err(self.error("expected pattern")),
        }
    }

    fn parse_primary(&mut self) -> Result<Expr, ParseError> {
        let span = self.current_span();
        match &self.tokens[self.pos].kind {
            TokenKind::Match => return self.parse_match(),
            TokenKind::StringLit(s) => {
                let s = s.clone();
                self.advance();
                Ok(Expr::StringLit(s, span))
            }
            TokenKind::IntLit(n) => {
                let n = *n;
                self.advance();
                Ok(Expr::IntLit(n, span))
            }
            TokenKind::FloatLit(n) => {
                let n = *n;
                self.advance();
                Ok(Expr::FloatLit(n, span))
            }
            TokenKind::Ident(name) if name == "true" => {
                self.advance();
                Ok(Expr::BoolLit(true, span))
            }
            TokenKind::Ident(name) if name == "false" => {
                self.advance();
                Ok(Expr::BoolLit(false, span))
            }
            TokenKind::Ident(name) => {
                let name = name.clone();
                self.advance();
                // Check for struct literal: Name { field: value, ... }
                // Convention: type names start with uppercase
                if self.check(&TokenKind::LBrace) && name.starts_with(char::is_uppercase) {
                    self.advance(); // consume {
                    let mut fields = Vec::new();
                    while !self.check(&TokenKind::RBrace) && !self.at_eof() {
                        let field_span = self.current_span();
                        let field_name = self.expect_ident()?;
                        self.expect(&TokenKind::Colon)?;
                        let value = self.parse_expr()?;
                        fields.push(FieldInit {
                            name: field_name,
                            value,
                            span: field_span,
                        });
                        if !self.check(&TokenKind::RBrace) {
                            self.expect(&TokenKind::Comma)?;
                        }
                    }
                    let end = self.current_span();
                    self.expect(&TokenKind::RBrace)?;
                    Ok(Expr::StructLit {
                        name,
                        fields,
                        span: Span::new(span.start as usize, end.end as usize),
                    })
                } else {
                    Ok(Expr::Ident(name, span))
                }
            }
            TokenKind::LParen => {
                self.advance();
                let expr = self.parse_expr()?;
                self.expect(&TokenKind::RParen)?;
                Ok(expr)
            }
            _ => Err(self.error("expected expression")),
        }
    }

    // --- Utilities ---

    fn check(&self, kind: &TokenKind) -> bool {
        std::mem::discriminant(&self.tokens[self.pos].kind) == std::mem::discriminant(kind)
    }

    fn advance(&mut self) -> &Token {
        let t = &self.tokens[self.pos];
        if self.pos < self.tokens.len() - 1 {
            self.pos += 1;
        }
        t
    }

    fn expect(&mut self, kind: &TokenKind) -> Result<&Token, ParseError> {
        if self.check(kind) {
            Ok(self.advance())
        } else {
            Err(self.error(&format!("expected {kind:?}, got {:?}", self.tokens[self.pos].kind)))
        }
    }

    fn expect_ident(&mut self) -> Result<String, ParseError> {
        if let TokenKind::Ident(name) = &self.tokens[self.pos].kind {
            let name = name.clone();
            self.advance();
            Ok(name)
        } else {
            Err(self.error(&format!(
                "expected identifier, got {:?}",
                self.tokens[self.pos].kind
            )))
        }
    }

    fn current_span(&self) -> Span {
        self.tokens[self.pos].span
    }

    fn at_eof(&self) -> bool {
        self.tokens[self.pos].kind == TokenKind::Eof
    }

    fn error(&self, msg: &str) -> ParseError {
        ParseError {
            message: msg.to_string(),
            offset: self.tokens[self.pos].span.start,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::lexer::Lexer;

    #[test]
    fn parse_hello_world() {
        let source = r#"fn main() can Console {
    print("Hello, world.")
}"#;
        let tokens = Lexer::new(source).tokenize().unwrap();
        let module = Parser::new(tokens).parse_module().unwrap();
        assert_eq!(module.items.len(), 1);

        let Item::Function(f) = &module.items[0] else {
            panic!("expected function");
        };
        assert_eq!(f.name, "main");
        assert_eq!(f.params.len(), 0);
        assert!(f.return_type.is_none());
        assert_eq!(f.effects, vec![Effect::Console]);
        assert_eq!(f.body.len(), 1);
    }

    #[test]
    fn parse_pure_function() {
        let source = "fn add() { 42 }";
        let tokens = Lexer::new(source).tokenize().unwrap();
        let module = Parser::new(tokens).parse_module().unwrap();

        let Item::Function(f) = &module.items[0] else {
            panic!("expected function");
        };
        assert_eq!(f.name, "add");
        assert!(f.effects.is_empty());
    }

    #[test]
    fn parse_multiple_effects() {
        let source = "fn fetch() can Net, Db, Fail { }";
        let tokens = Lexer::new(source).tokenize().unwrap();
        let module = Parser::new(tokens).parse_module().unwrap();

        let Item::Function(f) = &module.items[0] else {
            panic!("expected function");
        };
        assert_eq!(f.effects, vec![Effect::Net, Effect::Db, Effect::Fail]);
    }

    #[test]
    fn parse_struct_def() {
        let source = "struct Point { x: Int, y: Int }";
        let tokens = Lexer::new(source).tokenize().unwrap();
        let module = Parser::new(tokens).parse_module().unwrap();

        let Item::Struct(s) = &module.items[0] else {
            panic!("expected struct");
        };
        assert_eq!(s.name, "Point");
        assert_eq!(s.fields.len(), 2);
        assert_eq!(s.fields[0].name, "x");
        assert_eq!(s.fields[1].name, "y");
    }

    #[test]
    fn parse_struct_literal_and_field_access() {
        let source = r#"fn main() {
    let p = Point { x: 1, y: 2 }
    p.x
}"#;
        let tokens = Lexer::new(source).tokenize().unwrap();
        let module = Parser::new(tokens).parse_module().unwrap();

        let Item::Function(f) = &module.items[0] else {
            panic!("expected function");
        };
        assert_eq!(f.body.len(), 2); // let + expr
    }
}
