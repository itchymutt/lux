use std::collections::{HashMap, HashSet};
use std::fmt;

use crate::ast::{Expr, Function, Module};

/// The ten Lux effects. Fixed vocabulary. Not extensible.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum Effect {
    Net,
    Fs,
    Db,
    Console,
    Env,
    Time,
    Rand,
    Async,
    Unsafe,
    Fail,
}

impl fmt::Display for Effect {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Effect::Net => write!(f, "Net"),
            Effect::Fs => write!(f, "Fs"),
            Effect::Db => write!(f, "Db"),
            Effect::Console => write!(f, "Console"),
            Effect::Env => write!(f, "Env"),
            Effect::Time => write!(f, "Time"),
            Effect::Rand => write!(f, "Rand"),
            Effect::Async => write!(f, "Async"),
            Effect::Unsafe => write!(f, "Unsafe"),
            Effect::Fail => write!(f, "Fail"),
        }
    }
}

impl Effect {
    pub fn as_str(&self) -> &'static str {
        match self {
            Effect::Net => "Net",
            Effect::Fs => "Fs",
            Effect::Db => "Db",
            Effect::Console => "Console",
            Effect::Env => "Env",
            Effect::Time => "Time",
            Effect::Rand => "Rand",
            Effect::Async => "Async",
            Effect::Unsafe => "Unsafe",
            Effect::Fail => "Fail",
        }
    }

    pub fn from_str(s: &str) -> Option<Effect> {
        match s {
            "Net" => Some(Effect::Net),
            "Fs" => Some(Effect::Fs),
            "Db" => Some(Effect::Db),
            "Console" => Some(Effect::Console),
            "Env" => Some(Effect::Env),
            "Time" => Some(Effect::Time),
            "Rand" => Some(Effect::Rand),
            "Async" => Some(Effect::Async),
            "Unsafe" => Some(Effect::Unsafe),
            "Fail" => Some(Effect::Fail),
            _ => None,
        }
    }
}

/// Builtins: functions the language provides, and their required effects.
pub fn builtin_effects(name: &str) -> Option<HashSet<Effect>> {
    match name {
        "print" | "println" | "eprint" | "eprintln" => {
            Some(HashSet::from([Effect::Console]))
        }
        _ => None,
    }
}

/// Effect check error.
#[derive(Debug)]
pub struct EffectError {
    pub function_name: String,
    pub missing_effect: Effect,
    pub caused_by: String,
    pub offset: u32,
}

impl fmt::Display for EffectError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(
            f,
            "effect error in `{}`: `{}` requires `can {}`, but it is not declared",
            self.function_name, self.caused_by, self.missing_effect
        )
    }
}

/// Check all functions in a module for effect correctness.
pub fn check_module(module: &Module) -> Vec<EffectError> {
    // Build function effect table: name -> declared effects
    let mut fn_effects: HashMap<String, HashSet<Effect>> = HashMap::new();
    for item in &module.items {
        if let crate::ast::Item::Function(func) = item {
            fn_effects.insert(
                func.name.clone(),
                func.effects.iter().copied().collect(),
            );
        }
    }

    let mut errors = Vec::new();
    for item in &module.items {
        match item {
            crate::ast::Item::Function(func) => {
                check_function(func, &fn_effects, &mut errors);
            }
            crate::ast::Item::Struct(_) | crate::ast::Item::Enum(_) => {
                // Type definitions have no effects
            }
        }
    }
    errors
}

fn check_function(
    func: &Function,
    fn_effects: &HashMap<String, HashSet<Effect>>,
    errors: &mut Vec<EffectError>,
) {
    let declared: HashSet<Effect> = func.effects.iter().copied().collect();
    for stmt in &func.body {
        match stmt {
            crate::ast::Stmt::Expr(expr) => {
                check_expr(expr, &declared, &func.name, fn_effects, errors);
            }
            crate::ast::Stmt::Let(let_stmt) => {
                check_expr(&let_stmt.value, &declared, &func.name, fn_effects, errors);
            }
        }
    }
}

fn check_expr(
    expr: &Expr,
    declared: &HashSet<Effect>,
    func_name: &str,
    fn_effects: &HashMap<String, HashSet<Effect>>,
    errors: &mut Vec<EffectError>,
) {
    match expr {
        Expr::Call { callee, args, span } => {
            if let Expr::Ident(name, _) = callee.as_ref() {
                // Check builtin effects
                if let Some(required) = builtin_effects(name) {
                    for effect in required {
                        if !declared.contains(&effect) {
                            errors.push(EffectError {
                                function_name: func_name.to_string(),
                                missing_effect: effect,
                                caused_by: name.clone(),
                                offset: span.start,
                            });
                        }
                    }
                }
                // Check user-defined function effects: caller must declare
                // everything the callee declares
                if let Some(callee_effects) = fn_effects.get(name.as_str()) {
                    for effect in callee_effects {
                        if !declared.contains(effect) {
                            errors.push(EffectError {
                                function_name: func_name.to_string(),
                                missing_effect: *effect,
                                caused_by: name.clone(),
                                offset: span.start,
                            });
                        }
                    }
                }
            }
            // Recurse into callee and args
            check_expr(callee, declared, func_name, fn_effects, errors);
            for arg in args {
                check_expr(arg, declared, func_name, fn_effects, errors);
            }
        }
        Expr::BinOp { left, right, .. } => {
            check_expr(left, declared, func_name, fn_effects, errors);
            check_expr(right, declared, func_name, fn_effects, errors);
        }
        Expr::StructLit { fields, .. } => {
            for field in fields {
                check_expr(&field.value, declared, func_name, fn_effects, errors);
            }
        }
        Expr::FieldAccess { object, .. } => {
            check_expr(object, declared, func_name, fn_effects, errors);
        }
        Expr::Match { subject, arms, .. } => {
            check_expr(subject, declared, func_name, fn_effects, errors);
            for arm in arms {
                check_expr(&arm.body, declared, func_name, fn_effects, errors);
            }
        }
        Expr::StringLit(_, _)
        | Expr::IntLit(_, _)
        | Expr::FloatLit(_, _)
        | Expr::BoolLit(_, _)
        | Expr::Ident(_, _) => {}
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::ast::*;
    use crate::token::Span;

    fn make_print_call() -> Expr {
        Expr::Call {
            callee: Box::new(Expr::Ident("print".into(), Span::new(0, 5))),
            args: vec![Expr::StringLit("hi".into(), Span::new(6, 10))],
            span: Span::new(0, 11),
        }
    }

    #[test]
    fn print_allowed_with_console_effect() {
        let module = Module {
            items: vec![Item::Function(Function {
                name: "main".into(),
                params: vec![],
                return_type: None,
                effects: vec![Effect::Console],
                body: vec![Stmt::Expr(make_print_call())],
                span: Span::new(0, 50),
            })],
        };
        let errors = check_module(&module);
        assert!(errors.is_empty(), "expected no errors, got: {errors:?}");
    }

    #[test]
    fn print_rejected_without_console_effect() {
        let module = Module {
            items: vec![Item::Function(Function {
                name: "pure_fn".into(),
                params: vec![],
                return_type: None,
                effects: vec![], // no effects declared — pure
                body: vec![Stmt::Expr(make_print_call())],
                span: Span::new(0, 50),
            })],
        };
        let errors = check_module(&module);
        assert_eq!(errors.len(), 1);
        assert_eq!(errors[0].missing_effect, Effect::Console);
        assert_eq!(errors[0].function_name, "pure_fn");
        assert_eq!(errors[0].caused_by, "print");
    }

    #[test]
    fn pure_function_with_no_calls_passes() {
        let module = Module {
            items: vec![Item::Function(Function {
                name: "add".into(),
                params: vec![],
                return_type: None,
                effects: vec![],
                body: vec![Stmt::Expr(Expr::IntLit(42, Span::new(0, 2)))],
                span: Span::new(0, 20),
            })],
        };
        let errors = check_module(&module);
        assert!(errors.is_empty());
    }
}
