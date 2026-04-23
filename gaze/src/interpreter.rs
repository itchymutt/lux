use std::collections::HashMap;

use crate::ast::{BinOp, Expr, Function, Module, Stmt};

/// Runtime value.
#[derive(Debug, Clone)]
pub enum Value {
    String(String),
    Int(i64),
    Float(f64),
    Bool(bool),
    Unit,
}

impl std::fmt::Display for Value {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Value::String(s) => write!(f, "{s}"),
            Value::Int(n) => write!(f, "{n}"),
            Value::Float(n) => write!(f, "{n}"),
            Value::Bool(b) => write!(f, "{b}"),
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

/// Execute a module by finding and running `fn main()`.
pub fn execute(module: &Module) -> Result<(), RuntimeError> {
    // Build function table
    let functions: HashMap<&str, &Function> = module
        .items
        .iter()
        .filter_map(|item| match item {
            crate::ast::Item::Function(f) => Some((f.name.as_str(), f)),
        })
        .collect();

    if !functions.contains_key("main") {
        return Err(RuntimeError {
            message: "no `fn main()` found".into(),
            offset: 0,
        });
    }

    let mut env = Env::new();
    call_function("main", &[], &functions, &mut env)?;
    Ok(())
}

fn call_function(
    name: &str,
    args: &[Value],
    functions: &HashMap<&str, &Function>,
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
        result = exec_stmt(stmt, functions, env)?;
    }

    env.pop_frame();
    Ok(result)
}

fn exec_stmt(
    stmt: &Stmt,
    functions: &HashMap<&str, &Function>,
    env: &mut Env,
) -> Result<Value, RuntimeError> {
    match stmt {
        Stmt::Expr(expr) => eval_expr(expr, functions, env),
        Stmt::Let(let_stmt) => {
            let val = eval_expr(&let_stmt.value, functions, env)?;
            env.define(let_stmt.name.clone(), val);
            Ok(Value::Unit)
        }
    }
}

fn eval_expr(
    expr: &Expr,
    functions: &HashMap<&str, &Function>,
    env: &mut Env,
) -> Result<Value, RuntimeError> {
    match expr {
        Expr::StringLit(s, _) => Ok(Value::String(s.clone())),
        Expr::IntLit(n, _) => Ok(Value::Int(*n)),
        Expr::FloatLit(n, _) => Ok(Value::Float(*n)),
        Expr::BoolLit(b, _) => Ok(Value::Bool(*b)),

        Expr::Ident(name, span) => env.get(name).cloned().ok_or_else(|| RuntimeError {
            message: format!("undefined variable `{name}`"),
            offset: span.start,
        }),

        Expr::BinOp {
            op,
            left,
            right,
            span,
        } => {
            let lhs = eval_expr(left, functions, env)?;
            let rhs = eval_expr(right, functions, env)?;
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
                .map(|a| eval_expr(a, functions, env))
                .collect::<Result<Vec<_>, _>>()?;

            // Try builtins first, then user-defined functions
            match func_name {
                "print" | "println" => builtin_print(&arg_values),
                _ => {
                    if functions.contains_key(func_name) {
                        call_function(func_name, &arg_values, functions, env)
                    } else {
                        Err(RuntimeError {
                            message: format!("undefined function `{func_name}`"),
                            offset: span.start,
                        })
                    }
                }
            }
        }
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
