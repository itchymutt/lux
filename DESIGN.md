# Lux: A Language That Shows Its Work

## Thesis

Lux is a general-purpose programming language designed for a world where most code is written by machines and read by humans. Its core belief: **every observable behavior of a program should be visible in its type signature.**

Memory safety is table stakes. The novel contribution is *effect safety*: the compiler tracks what a function does to the world, not just what it returns. A function that touches the network says so. A function that writes to disk says so. A function that mutates shared state says so. Silence means purity.

This matters because AI agents generate plausible code at scale. In languages where side effects are invisible, a "pure" function that secretly makes HTTP calls passes code review (human and automated). In Lux, it doesn't compile.

## Lineage

Lux draws from seven languages, taking specific ideas from each:

| Language | What Lux takes | What Lux avoids |
|----------|---------------|-----------------|
| **Rust** | Result types, pattern matching, no null, LLVM backend | Borrow checker complexity, lifetime annotations |
| **Go** | Structural simplicity, one way to do things, gofmt | No sum types, no generics (pre-1.18), error handling verbosity |
| **Koka** | Row-polymorphic effect types, Perceus reference counting | Deep handler performance overhead |
| **Austral** | Capability-based I/O, linear types for resources, simplicity as constraint | Extreme verbosity of threading linear values |
| **Hylo** | Mutable value semantics, subscripts/projections, parameter conventions | Unproven ergonomics for graph-shaped data |
| **Julia** | Multiple dispatch expressiveness, type specialization | Dynamic typing, no effect tracking, GC |
| **HCL** | The belief that a language should have an opinion about program structure | Domain-specificity (Lux is general-purpose) |

See RESEARCH.md for the full competitive analysis.

## Design Principles

1. **Silence is purity.** A function with no effect annotation is pure. It takes values, returns values, touches nothing. This is the default. Effects are opt-in, explicit, and visible.

2. **The signature is the contract.** If you can read the function signature, you know everything the function can do. Not "might do." Can do. The compiler enforces this.

3. **Composition is pipelines.** The primary way to build programs is to compose functions in sequence. Data flows through transformations. Each stage declares its effects. The pipeline is both the program and its security manifest.

4. **Constraints are features.** The language is opinionated about program structure. One way to do most things. The compiler enforces conventions that other languages delegate to linters. This makes AI-generated code predictable and human-reviewed code skimmable.

5. **Two users, one language.** Every program has a human reader and a machine writer. The syntax optimizes for human readability. The structure optimizes for machine generation. These are not in conflict when the language is sufficiently constrained.

## The Effect System

### Core Concept

Every function in Lux has an effect set: the collection of effects it may perform. The effect set is part of the function's type. Functions compose only when their effects are compatible with the calling context.

```lux
// Pure function. No effects. The default.
fn add(a: i32, b: i32) -> i32 {
    a + b
}

// Function with declared effects.
fn fetch_user(id: UserId) -> User can Net, Db {
    let response = net.get("/users/{id}")?
    parse_user(response.body)
}
```

The keyword `can` reads as English: "this function *can* touch the network and database." Silence means purity. A function with no `can` clause takes values, returns values, touches nothing.

### Effect Inference

Effects are declared in signatures but **inferred at call sites**. You don't annotate every line. The compiler traces which calls contribute which effects and verifies that the signature covers them all.

```lux
fn save_user(user: User) -> UserId can Db, Fail {
    db.insert("users", user)?   // compiler infers this needs Db
}

// Calling a Db function from a pure context is a compile error:
fn process(user: User) -> UserId {
    save_user(user)  // ERROR: `save_user` requires Db, but `process` is pure
}
```

### Built-in Effects

Lux ships with a fixed set of effects. Not extensible by user code. This is a deliberate constraint: the effect set is a security manifest. A fixed vocabulary means every Lux program's effects are comparable, auditable, and toolable.

| Effect | What it covers |
|--------|---------------|
| `Net` | Network I/O: HTTP, TCP, UDP, DNS, sockets |
| `Fs` | Filesystem reads and writes |
| `Db` | Database queries and mutations |
| `Console` | Terminal I/O: stdin, stdout, stderr |
| `Env` | Environment variables, system properties |
| `Time` | Clock reads, sleep, timeouts |
| `Rand` | Random number generation |
| `Async` | Spawning concurrent tasks |
| `Unsafe` | Raw pointer operations, FFI |
| `Fail` | Operations that can fail (replaces Result/Option ceremony) |

`Fail` deserves explanation. Instead of wrapping every return type in `Result<T, E>`, a function that can fail says `can Fail`. The `?` operator propagates failures. The caller decides how to handle them. This is the Koka insight: exceptions are just an effect.

```lux
// Instead of -> Result<User, AppError>
fn find_user(id: UserId) -> User can Db, Fail {
    db.query("select * from users where id = ?", id)?
}

// The caller can handle the failure
fn maybe_find(id: UserId) -> Option<User> can Db {
    catch find_user(id) {
        Ok(user) => Some(user),
        Err(_)   => None,
    }
}
```

### Effect Polymorphism

Higher-order functions are generic over effects:

```lux
// map is pure if f is pure. map has whatever effects f has.
fn map<T, U>(list: List<T>, f: fn(T) -> U can E) -> List<U> can E {
    // ...
}

let doubled = map(numbers, |n| n * 2)           // pure
let fetched = map(ids, |id| fetch_user(id))      // can Net, Db
```

### Effect Boundaries

A `contain` block absorbs effects. Code inside can perform effects, but the boundary is pure from the outside.

```lux
// Pure from the caller's perspective.
// The mutation is contained.
fn fibonacci(n: u64) -> u64 {
    contain Mut {
        let cache = MutMap.new()
        fn fib(n: u64) -> u64 can Mut {
            cache.get(n) ?? {
                let r = if n <= 1 { n } else { fib(n - 1) + fib(n - 2) }
                cache.set(n, r)
                r
            }
        }
        fib(n)
    }
}
```

### How Effects Connect to Code

Each built-in effect corresponds to a standard library module with the same name. `Net` is both an effect and a module. `Fs` is both an effect and a module. The `can` clause is a permission gate: you can only call functions from the `net` module if your function declares `can Net`.

```lux
fn main() can Net, Fs, Console, Fail {
    let config = load_config()?           // load_config uses fs module
    let users = fetch_users(config.url)?  // fetch_users uses net module
    print(format_report(users))           // print uses console module
    write_report(users, config.path)?     // write_report uses fs module
}
```

No magic globals. No hidden parameters. `net.get(url)` is a normal function call to the `net` module. The compiler checks that the calling function has declared `can Net`. If it hasn't, the call is a compile error.

This means the effect system is not a separate layer bolted onto the language. It IS the module permission system. Effects are modules. Modules are effects. One concept, not two.

### Capability Narrowing (Sandboxing)

Capabilities can be narrowed for sandboxing. A restricted capability looks identical to the callee but limits what it can reach:

```lux
fn run_sandboxed() can Net, Fs, Fail {
    let net = Net.restrict(["api.example.com"])
    let fs = Fs.restrict_to("/tmp/sandbox")
    agent_task(net, fs)?
}

// This function doesn't know it's restricted.
// It receives Net and Fs that look normal but are narrowed.
fn agent_task(net: Net, fs: Fs) -> AgentOutput can Fail {
    let data = net.get("https://api.example.com/data")?  // OK
    // net.get("https://evil.com/steal")  would fail at runtime
    let result = transform(data.body)
    fs.write("output.json", result)?
    AgentOutput { path: "output.json", size: result.len() }
}
```

When a function receives a narrowed capability as a parameter, it uses that parameter instead of the module global. This is the only case where capabilities appear as function parameters: when the caller is restricting what the callee can do.

### The `.` Shorthand (Field Projections in Closures)

For pipelines and higher-order functions, Lux supports field projection shorthand:

```lux
// These are equivalent:
items |> map(|i| i.unit_price)
items |> map(.unit_price)

// Works with expressions:
items |> map(.unit_price * .quantity)
items |> sort_by(.name)
items |> filter(.active)
```

This is syntactic sugar. `.field` in a closure position expands to `|it| it.field`. It makes pipelines read like sentences.

## Syntax Overview

### Functions

```lux
// Pure function
fn greet(name: String) -> String {
    "Hello, {name}"
}

// Effectful function
fn read_config(path: Path) -> Config can Fs, Fail {
    let contents = fs.read(path)?
    parse_toml(contents)?
}
```

### Pipelines

```lux
fn handle(req: Request) -> Response can Net, Db, Fail {
    req
        |> authenticate
        |> parse_body
        |> authorize
        |> persist
        |> respond
}
```

### Pattern Matching

```lux
fn describe(status: Status) -> String {
    match status {
        Running(since) => "Running since {since}",
        Stopped(reason) => "Stopped: {reason}",
        Unknown => "Unknown status",
    }
}
```

### Structs and Enums

```lux
struct User {
    id: UserId,
    name: String,
    email: Email,
}

enum Status {
    Running(Timestamp),
    Stopped(String),
    Unknown,
}
```

### Error Handling

`Fail` is an effect. `?` propagates it. `catch` handles it.

```lux
fn load_user(id: UserId) -> User can Net, Db, Fail {
    let cached = cache.get(id)?
    if cached.is_some() {
        return cached.unwrap()
    }
    let user = fetch_user(id)?
    cache.set(id, user)?
    user
}
```

### Operators for Absence

Lux has no null. `Option<T>` represents values that might not exist. Two operators make working with optionals concise:

```lux
// ?? is the nil coalescing operator. Use the left side, or fall back to the right.
let city = env.arg(1) ?? "San Francisco"
let name = user.nickname ?? user.full_name ?? "Anonymous"

// ? propagates failure. If the left side is None or Err, return early.
let user = find_user(id)?
```

`??` can also take a block for computed defaults:

```lux
let cached = cache.get(id) ?? {
    let fresh = compute_expensive_thing()
    cache.set(id, fresh)
    fresh
}
```

### String Interpolation

```lux
let name = "world"
let greeting = "Hello, {name}"
let math = "2 + 2 = {2 + 2}"
let nested = "User {user.name} has {user.items.len()} items"
```

### String Concatenation

```lux
// ++ concatenates strings. Not +. Strings are not numbers.
let full = first_name ++ " " ++ last_name
let multiline = "line one\n"
             ++ "line two\n"
             ++ "line three"
```

### Modules

```lux
// One file = one module. No choice.
// Public items are explicitly marked.
// Everything else is private.

pub fn create_user(name: String) -> User can Db, Fail {
    let id = generate_id()
    let user = User { id, name, email: Email.empty() }
    db.insert("users", user)?
    user
}

fn generate_id() -> UserId {
    UserId.from_hash(timestamp_seed())
}
```

## Memory Model

Lux uses **mutable value semantics** (from Hylo) with **Perceus reference counting** (from Koka). No garbage collector. No borrow checker. No lifetime annotations.

### Value Semantics

All types in Lux behave like values. Assignment copies. There is no aliasing. There is no shared mutable state. If you have a value, you are the only one who has it.

```lux
let a = Point { x: 1, y: 2 }
let b = a          // b is an independent copy
// a and b are completely independent values
```

### Parameter Passing

Functions declare how they use their parameters:

```lux
fn read_point(let p: Point) -> i32 {       // read-only access
    p.x + p.y
}

fn move_point(inout p: Point, dx: i32) {    // mutable access (exclusive)
    p.x = p.x + dx
}

fn consume_point(sink p: Point) -> i32 {    // takes ownership, p is consumed
    p.x + p.y
    // p is gone after this function
}
```

- `let`: read-only. The callee cannot modify the value.
- `inout`: mutable, exclusive access. The callee can modify the value in place. The caller cannot use it during the call.
- `sink`: ownership transfer. The callee consumes the value. The caller cannot use it after the call.

These conventions are visible at every call site, which is exactly what a human reviewer or AI auditor needs.

### Subscripts (Projections, Not References)

When you need to work with part of a larger structure in place, Lux uses subscripts. A subscript yields a temporary projection of a value, not a reference to it.

```lux
fn swap_coordinates(inout p: Point) {
    let temp = p.x
    p.x = p.y
    p.y = temp
}

// Subscripts for collection access
subscript items[index: usize](inout self: List<T>) -> T {
    // yields a projection of the element at index
    // the projection is lexically scoped, no lifetime needed
}
```

Projections cannot be stored, returned, or outlive their scope. This eliminates dangling references by construction. No lifetime annotations needed because the scope is always lexical.

### Perceus Reference Counting

Under the hood, Lux uses Perceus (from Koka): precise, compiler-inserted reference counting with reuse optimization.

- When a value has a single reference, operations on it are in-place (no copy).
- When a value is shared (e.g., passed to two functions), the compiler inserts a copy.
- The reuse optimization detects when a data structure is consumed and immediately reconstructed, and reuses the memory.

The programmer never sees reference counts. The compiler manages them. There are no GC pauses, no manual memory management, and no borrow checker fights.

### Unsafe Code

There is no `unsafe` keyword. The equivalent is the `Unsafe` effect:

```lux
fn call_c_library(ptr: RawPtr) -> i32 can Unsafe {
    ffi.call("some_c_function", ptr)
}
```

Raw pointer operations require the `Unsafe` effect, which `lux audit` flags and CI policies can reject. FFI boundaries are the only place this appears.

## Compilation and Tooling

- **`lux build`**: Compile to native code (LLVM backend, like Rust)
- **`lux check`**: Type-check and effect-check without compiling
- **`lux audit`**: Print the effect manifest for a program (every function, its effects, its capabilities)
- **`lux fmt`**: Format code (one canonical style, like `gofmt`, not configurable)
- **`lux test`**: Run tests (tests are pure by default, effectful tests require explicit capability injection)
- **`lux sandbox`**: Run a program with restricted capabilities (e.g., no network, filesystem limited to one directory)

### The Audit Tool

`lux audit` is the killer feature for AI-native development. It produces a complete manifest:

```
$ lux audit src/main.lux

main                    can Net, Fs, Console, Fail
  load_config           can Fs, Fail
  fetch_users           can Net, Fail
    net.get             can Net, Fail
    parse_users         (pure)
  format_report         (pure)
  print                 can Console
  write_report          can Fs, Fail
    fs.write            can Fs, Fail
```

An AI agent's output can be audited before execution. A CI pipeline can reject PRs that introduce unexpected effects. A security team can set policy: "this service may not use `Proc` or `Unsafe`."

## Open Questions

1. **Async model.** Is async an effect (`Proc`) or a language primitive? Rust's async is powerful but complex. Go's goroutines are simple but hide concurrency. Where does Lux land?

2. **Standard library scope.** Minimal (like Rust) or batteries-included (like Go)? The effect system makes batteries-included safer (every stdlib function declares its effects), but a large stdlib is a large maintenance burden.

3. **Interop story.** C FFI is essential for adoption. How does the effect system interact with foreign code? (Likely: all FFI calls are `! {Unsafe}` by default, with manual effect annotations for well-known libraries.)

4. **Effect inference.** Should the compiler infer effects for private functions? (Probably yes for ergonomics, but explicit annotations on public functions are mandatory.)

5. **Generics model.** Rust-style monomorphization or Go-style boxing? Monomorphization is faster but produces larger binaries and slower compiles. The AI-native tradeoff might favor faster compiles.

6. **REPL and incremental compilation.** AI agents benefit from fast feedback loops. A REPL with effect tracking would be valuable but is hard to build for a compiled language.

## Influences

See the Lineage table at the top of this document and RESEARCH.md for the full analysis.

## Non-Goals

- **Backward compatibility with C/C++.** Lux is not a C replacement. It's a new language for new code. FFI exists for interop, not for migration.
- **Maximum expressiveness.** Lux deliberately constrains what you can express. The constraint is the feature.
- **Academic purity.** The effect system is practical, not theoretically complete. It covers the effects that matter for real programs, not every possible effect.
- **Gradual adoption.** Lux is not designed to be sprinkled into existing codebases. It's designed for new projects that want the full safety guarantee from day one.
