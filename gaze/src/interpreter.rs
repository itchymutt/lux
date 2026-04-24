use std::collections::HashMap;

use crate::ast::{BinOp, Expr, Function, Module, Stmt};

/// Runtime value.
#[derive(Debug, Clone)]
pub enum Value {
    String(String),
    Int(i64),
    Float(f64),
    Bool(bool),
    Struct {
        name: String,
        fields: HashMap<String, Value>,
    },
    Enum {
        variant: String,
        fields: Vec<Value>,
    },
    Unit,
}

impl std::fmt::Display for Value {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Value::String(s) => write!(f, "{s}"),
            Value::Int(n) => write!(f, "{n}"),
            Value::Float(n) => write!(f, "{n}"),
            Value::Bool(b) => write!(f, "{b}"),
            Value::Struct { name, fields } => {
                let pairs: Vec<String> = fields
                    .iter()
                    .map(|(k, v)| format!("{k}: {v}"))
                    .collect();
                write!(f, "{name} {{ {} }}", pairs.join(", "))
            }
            Value::Enum { variant, fields } => {
                if fields.is_empty() {
                    write!(f, "{variant}")
                } else {
                    let parts: Vec<String> = fields.iter().map(|v| v.to_string()).collect();
                    write!(f, "{variant}({})", parts.join(", "))
                }
            }
            Value::Unit => write!(f, "()"),
        }
    }
}

/// Interpreter error.
#[derive(Debug)]
pub struct RuntimeError {
    pub message: String,
    pub offset: u32,
}

impl std::fmt::Display for RuntimeError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "runtime error: {}", self.message)
    }
}

/// Variable environment. Scoped: each function call gets a new frame.
struct Env {
    frames: Vec<HashMap<String, Value>>,
}

impl Env {
    fn new() -> Self {
        Env {
            frames: vec![HashMap::new()],
        }
    }

    fn push_frame(&mut self) {
        self.frames.push(HashMap::new());
    }

    fn pop_frame(&mut self) {
        self.frames.pop();
    }

    fn define(&mut self, name: String, value: Value) {
        if let Some(frame) = self.frames.last_mut() {
            frame.insert(name, value);
        }
    }

    fn get(&self, name: &str) -> Option<&Value> {
        // Search from innermost frame outward
        for frame in self.frames.iter().rev() {
            if let Some(v) = frame.get(name) {
                return Some(v);
            }
        }
        None
    }
}

/// Variant info: how many fields a variant takes.
struct VariantInfo {
    arity: usize,
}

/// Execute a module by finding and running `fn main()`.
pub fn execute(module: &Module) -> Result<(), RuntimeError> {
    // Build function table
    let functions: HashMap<&str, &Function> = module
        .items
        .iter()
        .filter_map(|item| match item {
            crate::ast::Item::Function(f) => Some((f.name.as_str(), f)),
            _ => None,
        })
        .collect();

    // Build variant table (variant name -> arity)
    let mut variants: HashMap<String, VariantInfo> = HashMap::new();
    for item in &module.items {
        if let crate::ast::Item::Enum(enum_def) = item {
            for variant in &enum_def.variants {
                variants.insert(
                    variant.name.clone(),
                    VariantInfo {
                        arity: variant.fields.len(),
                    },
                );
            }
        }
    }

    if !functions.contains_key("main") {
        return Err(RuntimeError {
            message: "no `fn main()` found".into(),
            offset: 0,
        });
    }

    let mut env = Env::new();
    call_function("main", &[], &functions, &variants, &mut env)?;
    Ok(())
}

fn call_function(
    name: &str,
    args: &[Value],
    functions: &HashMap<&str, &Function>,
    variants: &HashMap<String, VariantInfo>,
    env: &mut Env,
) -> Result<Value, RuntimeError> {
    let func = functions.get(name).ok_or_else(|| RuntimeError {
        message: format!("undefined function `{name}`"),
        offset: 0,
    })?;

    // Create new scope with parameters bound
    env.push_frame();
    for (param, arg) in func.params.iter().zip(args.iter()) {
        env.define(param.name.clone(), arg.clone());
    }

    // Execute body, last expression is the return value
    let mut result = Value::Unit;
    for stmt in &func.body {
        result = exec_stmt(stmt, functions, variants, env)?;
    }

    env.pop_frame();
    Ok(result)
}

fn exec_stmt(
    stmt: &Stmt,
    functions: &HashMap<&str, &Function>,
    variants: &HashMap<String, VariantInfo>,
    env: &mut Env,
) -> Result<Value, RuntimeError> {
    match stmt {
        Stmt::Expr(expr) => eval_expr(expr, functions, variants, env),
        Stmt::Let(let_stmt) => {
            let val = eval_expr(&let_stmt.value, functions, variants, env)?;
            env.define(let_stmt.name.clone(), val);
            Ok(Value::Unit)
        }
    }
}

fn eval_expr(
    expr: &Expr,
    functions: &HashMap<&str, &Function>,
    variants: &HashMap<String, VariantInfo>,
    env: &mut Env,
) -> Result<Value, RuntimeError> {
    match expr {
        Expr::StringLit(s, _) => Ok(Value::String(s.clone())),
        Expr::IntLit(n, _) => Ok(Value::Int(*n)),
        Expr::FloatLit(n, _) => Ok(Value::Float(*n)),
        Expr::BoolLit(b, _) => Ok(Value::Bool(*b)),

        Expr::Ident(name, span) => {
            // Check variables first, then zero-arity enum variants
            if let Some(val) = env.get(name) {
                Ok(val.clone())
            } else if let Some(info) = variants.get(name.as_str()) {
                if info.arity == 0 {
                    Ok(Value::Enum {
                        variant: name.clone(),
                        fields: vec![],
                    })
                } else {
                    Err(RuntimeError {
                        message: format!("`{name}` is a variant that takes {} argument(s)", info.arity),
                        offset: span.start,
                    })
                }
            } else {
                Err(RuntimeError {
                    message: format!("undefined variable `{name}`"),
                    offset: span.start,
                })
            }
        }

        Expr::BinOp {
            op,
            left,
            right,
            span,
        } => {
            let lhs = eval_expr(left, functions, variants, env)?;
            let rhs = eval_expr(right, functions, variants, env)?;
            eval_binop(*op, &lhs, &rhs, *span)
        }

        Expr::Call { callee, args, span } => {
            let func_name = match callee.as_ref() {
                Expr::Ident(name, _) => name.as_str(),
                _ => {
                    return Err(RuntimeError {
                        message: "only named function calls are supported".into(),
                        offset: span.start,
                    });
                }
            };

            // Evaluate arguments
            let arg_values: Vec<Value> = args
                .iter()
                .map(|a| eval_expr(a, functions, variants, env))
                .collect::<Result<Vec<_>, _>>()?;

            // Try builtins, then variants, then user-defined functions
            match func_name {
                "print" | "println" => builtin_print(&arg_values),
                _ => {
                    if let Some(_info) = variants.get(func_name) {
                        // Enum variant construction
                        Ok(Value::Enum {
                            variant: func_name.to_string(),
                            fields: arg_values,
                        })
                    } else if functions.contains_key(func_name) {
                        call_function(func_name, &arg_values, functions, variants, env)
                    } else {
                        Err(RuntimeError {
                            message: format!("undefined function `{func_name}`"),
                            offset: span.start,
                        })
                    }
                }
            }
        }

        Expr::StructLit {
            name,
            fields,
            span: _,
        } => {
            let mut field_values = HashMap::new();
            for field in fields {
                let val = eval_expr(&field.value, functions, variants, env)?;
                field_values.insert(field.name.clone(), val);
            }
            Ok(Value::Struct {
                name: name.clone(),
                fields: field_values,
            })
        }

        Expr::FieldAccess {
            object,
            field,
            span,
        } => {
            let obj = eval_expr(object, functions, variants, env)?;
            match &obj {
                Value::Struct { fields, name } => {
                    fields.get(field).cloned().ok_or_else(|| RuntimeError {
                        message: format!("struct `{name}` has no field `{field}`"),
                        offset: span.start,
                    })
                }
                _ => Err(RuntimeError {
                    message: format!("cannot access field `{field}` on {}", value_type_name(&obj)),
                    offset: span.start,
                }),
            }
        }

        Expr::If {
            condition,
            then_body,
            else_body,
            span: _,
        } => {
            let cond = eval_expr(condition, functions, variants, env)?;
            let is_true = match &cond {
                Value::Bool(b) => *b,
                _ => {
                    return Err(RuntimeError {
                        message: format!("if condition must be Bool, got {}", value_type_name(&cond)),
                        offset: condition.span().start,
                    });
                }
            };

            let stmts = if is_true {
                then_body
            } else if let Some(else_stmts) = else_body {
                else_stmts
            } else {
                return Ok(Value::Unit);
            };

            let mut result = Value::Unit;
            for stmt in stmts {
                result = exec_stmt(stmt, functions, variants, env)?;
            }
            Ok(result)
        }

        Expr::Match {
            subject,
            arms,
            span,
        } => {
            let val = eval_expr(subject, functions, variants, env)?;
            for arm in arms {
                if let Some(bindings) = match_pattern(&arm.pattern, &val, variants) {
                    env.push_frame();
                    for (name, bound_val) in bindings {
                        env.define(name, bound_val);
                    }
                    let result = eval_expr(&arm.body, functions, variants, env)?;
                    env.pop_frame();
                    return Ok(result);
                }
            }
            Err(RuntimeError {
                message: "no match arm matched".into(),
                offset: span.start,
            })
        }
    }
}

/// Try to match a value against a pattern. Returns bindings if successful.
fn match_pattern(
    pattern: &crate::ast::Pattern,
    value: &Value,
    variants: &HashMap<String, VariantInfo>,
) -> Option<Vec<(String, Value)>> {
    use crate::ast::Pattern;
    match pattern {
        Pattern::Wildcard(_) => Some(vec![]),
        Pattern::Ident(name, _) => {
            // If the name is a known zero-arity variant, match against it
            if let Some(info) = variants.get(name.as_str()) {
                if info.arity == 0 {
                    if let Value::Enum { variant, fields } = value {
                        if variant == name && fields.is_empty() {
                            return Some(vec![]);
                        }
                    }
                    return None;
                }
            }
            // Otherwise it's a catch-all variable binding
            Some(vec![(name.clone(), value.clone())])
        }
        Pattern::IntLit(n, _) => {
            if let Value::Int(v) = value {
                if v == n {
                    return Some(vec![]);
                }
            }
            None
        }
        Pattern::Variant {
            name, bindings, ..
        } => {
            if let Value::Enum { variant, fields } = value {
                if variant == name && fields.len() == bindings.len() {
                    let bound: Vec<(String, Value)> = bindings
                        .iter()
                        .zip(fields.iter())
                        .map(|(b, v)| (b.clone(), v.clone()))
                        .collect();
                    return Some(bound);
                }
            }
            None
        }
    }
}

fn value_type_name(v: &Value) -> &'static str {
    match v {
        Value::String(_) => "String",
        Value::Int(_) => "Int",
        Value::Float(_) => "Float",
        Value::Bool(_) => "Bool",
        Value::Struct { .. } => "Struct",
        Value::Enum { .. } => "Enum",
        Value::Unit => "Unit",
    }
}

fn eval_binop(op: BinOp, lhs: &Value, rhs: &Value, span: crate::token::Span) -> Result<Value, RuntimeError> {
    match (lhs, rhs) {
        (Value::Int(a), Value::Int(b)) => match op {
            BinOp::Add => Ok(Value::Int(a + b)),
            BinOp::Sub => Ok(Value::Int(a - b)),
            BinOp::Mul => Ok(Value::Int(a * b)),
            BinOp::Div => {
                if *b == 0 {
                    Err(RuntimeError {
                        message: "division by zero".into(),
                        offset: span.start,
                    })
                } else {
                    Ok(Value::Int(a / b))
                }
            }
            BinOp::Eq => Ok(Value::Bool(a == b)),
            BinOp::NotEq => Ok(Value::Bool(a != b)),
            BinOp::Lt => Ok(Value::Bool(a < b)),
            BinOp::Gt => Ok(Value::Bool(a > b)),
            BinOp::LtEq => Ok(Value::Bool(a <= b)),
            BinOp::GtEq => Ok(Value::Bool(a >= b)),
        },
        (Value::Float(a), Value::Float(b)) => match op {
            BinOp::Add => Ok(Value::Float(a + b)),
            BinOp::Sub => Ok(Value::Float(a - b)),
            BinOp::Mul => Ok(Value::Float(a * b)),
            BinOp::Div => Ok(Value::Float(a / b)),
            BinOp::Eq => Ok(Value::Bool(a == b)),
            BinOp::NotEq => Ok(Value::Bool(a != b)),
            BinOp::Lt => Ok(Value::Bool(a < b)),
            BinOp::Gt => Ok(Value::Bool(a > b)),
            BinOp::LtEq => Ok(Value::Bool(a <= b)),
            BinOp::GtEq => Ok(Value::Bool(a >= b)),
        },
        (Value::String(a), Value::String(b)) => match op {
            BinOp::Add => Ok(Value::String(format!("{a}{b}"))),
            BinOp::Eq => Ok(Value::Bool(a == b)),
            BinOp::NotEq => Ok(Value::Bool(a != b)),
            _ => Err(RuntimeError {
                message: format!("cannot apply `{op:?}` to strings"),
                offset: span.start,
            }),
        },
        _ => Err(RuntimeError {
            message: format!("type mismatch in `{op:?}` operation"),
            offset: span.start,
        }),
    }
}

fn builtin_print(args: &[Value]) -> Result<Value, RuntimeError> {
    let parts: Vec<String> = args.iter().map(|v| v.to_string()).collect();
    println!("{}", parts.join(" "));
    Ok(Value::Unit)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::ast::*;
    use crate::effects::Effect;
    use crate::token::Span;

    #[test]
    fn execute_hello_world() {
        let module = Module {
            items: vec![Item::Function(Function {
                name: "main".into(),
                params: vec![],
                return_type: None,
                effects: vec![Effect::Console],
                body: vec![Stmt::Expr(Expr::Call {
                    callee: Box::new(Expr::Ident("print".into(), Span::new(0, 5))),
                    args: vec![Expr::StringLit("Hello, world.".into(), Span::new(6, 21))],
                    span: Span::new(0, 22),
                })],
                span: Span::new(0, 50),
            })],
        };
        execute(&module).unwrap();
    }

    #[test]
    fn error_on_missing_main() {
        let module = Module {
            items: vec![Item::Function(Function {
                name: "not_main".into(),
                params: vec![],
                return_type: None,
                effects: vec![],
                body: vec![],
                span: Span::new(0, 20),
            })],
        };
        let err = execute(&module).unwrap_err();
        assert!(err.message.contains("no `fn main()`"));
    }

    #[test]
    fn arithmetic() {
        let module = Module {
            items: vec![
                Item::Function(Function {
                    name: "add".into(),
                    params: vec![
                        Param {
                            name: "a".into(),
                            ty: TypeExpr {
                                name: "Int".into(),
                                span: Span::new(0, 3),
                            },
                            span: Span::new(0, 3),
                        },
                        Param {
                            name: "b".into(),
                            ty: TypeExpr {
                                name: "Int".into(),
                                span: Span::new(0, 3),
                            },
                            span: Span::new(0, 3),
                        },
                    ],
                    return_type: None,
                    effects: vec![],
                    body: vec![Stmt::Expr(Expr::BinOp {
                        op: BinOp::Add,
                        left: Box::new(Expr::Ident("a".into(), Span::new(0, 1))),
                        right: Box::new(Expr::Ident("b".into(), Span::new(4, 5))),
                        span: Span::new(0, 5),
                    })],
                    span: Span::new(0, 30),
                }),
                Item::Function(Function {
                    name: "main".into(),
                    params: vec![],
                    return_type: None,
                    effects: vec![Effect::Console],
                    body: vec![
                        Stmt::Let(LetStmt {
                            name: "x".into(),
                            value: Expr::Call {
                                callee: Box::new(Expr::Ident("add".into(), Span::new(0, 3))),
                                args: vec![
                                    Expr::IntLit(2, Span::new(4, 5)),
                                    Expr::IntLit(3, Span::new(7, 8)),
                                ],
                                span: Span::new(0, 9),
                            },
                            span: Span::new(0, 15),
                        }),
                        Stmt::Expr(Expr::Call {
                            callee: Box::new(Expr::Ident("print".into(), Span::new(0, 5))),
                            args: vec![Expr::Ident("x".into(), Span::new(6, 7))],
                            span: Span::new(0, 8),
                        }),
                    ],
                    span: Span::new(0, 50),
                }),
            ],
        };
        // Should print "5" and not error
        execute(&module).unwrap();
    }
}
