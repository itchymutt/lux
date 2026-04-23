use crate::effects::Effect;
use crate::token::Span;

/// A Gaze source file: a list of top-level items.
#[derive(Debug)]
pub struct Module {
    pub items: Vec<Item>,
}

#[derive(Debug)]
pub enum Item {
    Function(Function),
    Struct(StructDef),
    Enum(EnumDef),
}

#[derive(Debug)]
pub struct EnumDef {
    pub name: String,
    pub variants: Vec<VariantDef>,
    pub span: Span,
}

#[derive(Debug)]
pub struct VariantDef {
    pub name: String,
    pub fields: Vec<TypeExpr>,  // positional fields
    pub span: Span,
}

#[derive(Debug)]
pub struct StructDef {
    pub name: String,
    pub fields: Vec<FieldDef>,
    pub span: Span,
}

#[derive(Debug)]
pub struct FieldDef {
    pub name: String,
    pub ty: TypeExpr,
    pub span: Span,
}

#[derive(Debug)]
pub struct Function {
    pub name: String,
    pub params: Vec<Param>,
    pub return_type: Option<TypeExpr>,
    pub effects: Vec<Effect>,
    pub body: Vec<Stmt>,
    pub span: Span,
}

#[derive(Debug)]
pub struct Param {
    pub name: String,
    pub ty: TypeExpr,
    pub span: Span,
}

#[derive(Debug)]
pub struct TypeExpr {
    pub name: String,
    pub span: Span,
}

#[derive(Debug)]
pub enum Stmt {
    Expr(Expr),
    Let(LetStmt),
}

#[derive(Debug)]
pub struct LetStmt {
    pub name: String,
    pub value: Expr,
    pub span: Span,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum BinOp {
    Add,
    Sub,
    Mul,
    Div,
    Eq,
    NotEq,
    Lt,
    Gt,
    LtEq,
    GtEq,
}

#[derive(Debug)]
pub struct FieldInit {
    pub name: String,
    pub value: Expr,
    pub span: Span,
}

#[derive(Debug)]
pub enum Expr {
    StringLit(String, Span),
    IntLit(i64, Span),
    FloatLit(f64, Span),
    BoolLit(bool, Span),
    Ident(String, Span),
    Call {
        callee: Box<Expr>,
        args: Vec<Expr>,
        span: Span,
    },
    BinOp {
        op: BinOp,
        left: Box<Expr>,
        right: Box<Expr>,
        span: Span,
    },
    /// Struct construction: Point { x: 1, y: 2 }
    StructLit {
        name: String,
        fields: Vec<FieldInit>,
        span: Span,
    },
    /// Field access: p.x
    FieldAccess {
        object: Box<Expr>,
        field: String,
        span: Span,
    },
    /// Match expression
    Match {
        subject: Box<Expr>,
        arms: Vec<MatchArm>,
        span: Span,
    },
}

#[derive(Debug)]
pub struct MatchArm {
    pub pattern: Pattern,
    pub body: Expr,
    pub span: Span,
}

#[derive(Debug)]
pub enum Pattern {
    /// Variant pattern: Circle(r) or Rect(w, h)
    Variant {
        name: String,
        bindings: Vec<String>,
        span: Span,
    },
    /// Wildcard: _
    Wildcard(Span),
    /// Literal int
    IntLit(i64, Span),
    /// Variable binding (catch-all)
    Ident(String, Span),
}

impl Expr {
    pub fn span(&self) -> Span {
        match self {
            Expr::StringLit(_, s) => *s,
            Expr::IntLit(_, s) => *s,
            Expr::FloatLit(_, s) => *s,
            Expr::BoolLit(_, s) => *s,
            Expr::Ident(_, s) => *s,
            Expr::Call { span, .. } => *span,
            Expr::BinOp { span, .. } => *span,
            Expr::StructLit { span, .. } => *span,
            Expr::FieldAccess { span, .. } => *span,
            Expr::Match { span, .. } => *span,
        }
    }
}
