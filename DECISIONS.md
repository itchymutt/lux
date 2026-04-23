# Design Decisions

Every "X over Y because Z" in one place. These are positions, not preferences.

---

## 1. No anonymous struct literals. Use record literals.

**Chose:** A built-in `Record` type for ad-hoc key-value data.
**Over:** Anonymous structural types (TypeScript-style) or named structs for everything.
**Because:** Anonymous structural types make the type checker dramatically more complex (structural subtyping, row polymorphism, width subtyping). Named structs for every JSON response shape is Java-level ceremony. A `Record` type is the honest middle: it's a `Map<String, Value>` with literal syntax.

```lux
// Record literal syntax: #{ key: value }
fn json_response(status: u16, data: Record) -> HttpResponse {
    HttpResponse {
        status,
        body: json.encode(data),
        headers: #{ "Content-Type": "application/json" },
    }
}

// Usage:
json_response(201, #{
    slug: link.slug,
    url: link.url.to_string(),
    short_url: "https://sho.rt/{link.slug}",
})
```

`#{ }` is the record literal. It's not a struct (no type name, no compile-time field checking). It's a bag of key-value pairs that serializes to JSON. The `#` prefix distinguishes it from blocks.

For typed APIs between Lux modules, use named structs. For serialization boundaries (JSON responses, config files, log entries), use records. Two tools, two jobs.

**Would revisit if:** The type system turns out to need structural types for other reasons (e.g., trait objects, database row types).

---

## 2. Effect modules are implicit. No import needed.

**Chose:** Effect modules (`net`, `fs`, `db`, `time`, `rand`, `env`, `console`) are available without import. The `can` clause is the permission gate.
**Over:** Requiring `import std.net` before using `net.get()`.
**Because:** Every file that does I/O would start with the same import block. That's boilerplate, not information. The `can` clause already declares the dependency. Requiring both `import std.net` and `can Net` is saying the same thing twice.

Effect modules are the only implicit imports. User modules always require explicit import. The distinction: effect modules are part of the language, not the ecosystem.

```lux
// No import needed for net, db, fs, etc.
// The can clause is the import AND the permission.
fn fetch(url: String) -> Bytes can Net, Fail {
    net.get(url)?
}

// User modules always need explicit import.
import store
import model.{User}
```

**Would revisit if:** The implicit/explicit distinction confuses newcomers or tooling.

---

## 3. Connections are capabilities, passed explicitly.

**Chose:** Database connections (and other stateful resources) are values passed through function parameters.
**Over:** Implicit module-level connection state (Go's `sql.DB` pattern).
**Because:** The thesis is "the signature tells you everything." A function that takes `db: Db` is honest about its dependency. A function that calls `db.execute()` on an invisible global is lying by omission. The effect system says *what* the function does (touches a database). The parameter says *which* database.

This matters for testing (pass an in-memory DB), sandboxing (pass a restricted DB), and multi-tenancy (pass different DBs for different tenants).

```lux
// The connection is a value. It flows through parameters.
fn main() can Console, Env, Fail {
    let config = load_config()?
    let db = Db.connect(config.database_url)?
    migrate(db)?

    print("shortener running on port {config.port}")

    net.serve(config.port, |req| {
        catch handler.route(db, req) {
            Ok(response) => response,
            Err(e) => error_response(e),
        }
    })
}

fn save_link(db: Db, link: ShortLink) can Fail {
    db.execute("insert into links ...", link)?
}
```

Wait. This changes the effect story. If `db` is a parameter, does the function still need `can Db`? No. The `Db` effect means "uses the implicit db module." If you pass a `db` value explicitly, you don't need the effect annotation. The capability IS the parameter.

This is the Austral model. And it's cleaner. Let me think through the implications...

**The resolution:** There are two modes of effect access.

- **Module access** (implicit): `net.get(url)` requires `can Net`. The runtime provides the capability. Simple, convenient, used for most code.
- **Capability access** (explicit): `db.execute(...)` where `db` is a parameter. No `can Db` needed because the capability is in the signature as a parameter. Used when you need to control *which* instance (which database, which restricted network).

Both are valid. Module access is the default. Capability access is for when you need control. The compiler accepts both.

```lux
// Module access: can Db grants access to the implicit db module
fn save_v1(link: ShortLink) can Db, Fail {
    db.execute("insert ...", link)?
}

// Capability access: db parameter IS the capability, no can Db needed
fn save_v2(db: Db, link: ShortLink) can Fail {
    db.execute("insert ...", link)?
}

// Both are valid. v1 is simpler. v2 is more controllable.
```

**Would revisit if:** Having two modes creates confusion about which to use. But the rule is simple: use module access unless you need to pass a specific instance.

---

## 4. `fail` is an expression of type `Never`.

**Chose:** `fail` is a keyword expression that produces a value of type `Never` (the bottom type). It can appear anywhere an expression is expected.
**Over:** `return Err(e)` (Rust-style, brings back Result ceremony) or `throw` (exception-style, implies unwinding).
**Because:** `fail` is the counterpart to `?`. `?` propagates a failure upward. `fail` creates a failure. Together they are the complete vocabulary for the `Fail` effect. `fail` having type `Never` means it's valid in any expression position:

```lux
let body = req.body ?? fail InvalidRequest("missing body")
let user = find_user(id) ?? fail NotFound(id)
let config = parse_config(raw) ?? fail BadConfig("invalid format")
```

`fail` requires `can Fail` in the enclosing function. The compiler checks this.

`catch` is how you handle failures. It's the boundary where `Fail` is absorbed:

```lux
let result = catch do_risky_thing() {
    Ok(value) => value,
    Err(e) => default_value,
}
// result is not Fail, the effect was handled
```

**Would revisit if:** The `fail`/`?`/`catch` trio feels like too many concepts. But each does one thing: create, propagate, handle.

---

## 5. Closure effects are inferred from the body.

**Chose:** Closures don't need `can` annotations. The compiler infers their effects from what they call.
**Over:** Requiring explicit `can` on every closure (verbose) or ignoring closure effects (unsafe).
**Because:** A closure is a small inline function. Requiring `can Net, Db, Fail` on `|req| handler.route(db, req)` is noise. The compiler can see the body. It knows `handler.route` is `can Db, Time, Rand, Fail`. The closure inherits those effects.

The enclosing function must declare effects that cover everything the closure does. If the closure calls `net.get()`, the enclosing function needs `can Net`.

```lux
// The closure's effects are inferred. main must cover them.
fn main() can Net, Console, Env, Fail {
    net.serve(config.port, |req| {    // closure inferred: can Db, Time, Rand, Fail
        handler.route(db, req)
    })
}
```

For function types in signatures (not inline closures), effects must be explicit:

```lux
// When a function type appears in a signature, effects are explicit.
fn map<T, U>(list: List<T>, f: fn(T) -> U can E) -> List<U> can E
```

**Would revisit if:** Effect inference on closures produces confusing error messages.

---

## 6. `impl Trait` is sugar for bounded generics.

**Chose:** `impl Trait` in argument position is allowed as sugar for a generic parameter with a trait bound.
**Over:** Only explicit generics (verbose for simple cases).
**Because:** `fn encode(data: impl Encode)` is clearer than `fn encode<T: Encode>(data: T)` when there's one bounded parameter. When there are multiple or the bound is used in the return type, use explicit generics.

```lux
// These are equivalent:
fn print_it(x: impl Display) can Console { print(x.display()) }
fn print_it<T: Display>(x: T) can Console { print(x.display()) }

// Use explicit generics when the type appears multiple times:
fn larger<T: Ord>(a: T, b: T) -> T { if a > b { a } else { b } }
```

**Would revisit if:** Never. This is a small convenience with no downside.

---

## 7. `Rand` stays independent.

**Chose:** `Rand` is a separate effect from `Time` and `Env`.
**Over:** Folding randomness into `Env` or `Time`.
**Because:** Reproducibility. A function marked `can Rand` can be made deterministic by seeding the RNG. A function marked `can Time` cannot (time always advances). Separating them means you can write property-based tests that control randomness without mocking the clock.

```lux
// In tests, seed the RNG for reproducibility:
test "slug generation is deterministic when seeded" can Rand {
    Rand.seed(42)
    let a = generate_slug()
    Rand.seed(42)
    let b = generate_slug()
    assert_eq(a, b)
}
```

**Would revisit if:** Never. Reproducibility is non-negotiable for testing.

---

## 8. `??` with `fail` works because `fail` is `Never`.

**Chose:** `a ?? fail e` is valid syntax. `??` takes an `Option<T>` on the left and a `T` on the right. `fail` has type `Never`, which is a subtype of every type.
**Over:** Special-casing `??` to accept `fail`.
**Because:** No special case needed. `Never` (bottom type) is a subtype of all types. `fail e` is an expression of type `Never`. `Never` unifies with `T`. So `a ?? fail e` type-checks naturally: if `a` is `Option<T>`, the right side needs to be `T`, and `Never <: T`.

This also means `fail` works in `if`/`else`, `match` arms, and any other expression position:

```lux
let x = if condition { value } else { fail SomeError }
let y = match thing {
    Good(v) => v,
    Bad => fail SomeError,
}
```

**Would revisit if:** Never. This falls out of the type system naturally.

---

## 9. Errors are lazy. The happy path pays nothing.

**Chose:** `fail` creates a lightweight failure marker. Stack traces, error messages, and diagnostic context are constructed only when a `catch` block inspects the error.
**Over:** Eager error construction (Rust's `Err(AppError::new(...))` allocates and formats immediately) or exception objects with pre-built stack traces (Java, Python).
**Because:** The happy path is the common path. A function that `can Fail` succeeds 99%+ of the time. Allocating error context on every call — tracking undo state, formatting messages, capturing backtraces — pessimizes the success case to optimize the failure case. That's backwards.

The principle comes from the Zig compiler's approach to error reporting: Zig doesn't store file/line/column info during parsing, because parsing succeeds most of the time and memory is speed (cache locality dominates). If an error occurs, Zig reparses from the beginning in a slow path that collects diagnostics. The error case is rare, so making it slower is free.

Applied to Lux:

```lux
// fail creates a marker, not a formatted error.
// No allocation, no string formatting, no stack capture.
let user = find_user(id) ?? fail NotFound(id)

// Only when someone catches and inspects does the error materialize.
catch find_user(id) {
    Ok(user) => user,
    Err(e) => {
        // e.message, e.trace, e.context are constructed HERE,
        // not at the fail site.
        log.error("lookup failed: {e}")
        default_user()
    },
}
```

This means `fail` is cheap — a tagged union discriminant flip, not a heap allocation. The `?` propagation path is a branch and a return, not a copy of an error object. Only `catch` pays for diagnostics, and only if the handler asks for them.

The compiler can use effect annotations to optimize further: a pure function (no `can Fail`) never needs error-handling scaffolding at all. A `can Fail` function needs the branch, but not the allocation.

**Would revisit if:** Lazy error construction makes debugging significantly harder (e.g., the fail site's context is lost by the time `catch` runs). Mitigation: the compiler can optionally capture byte offsets (cheap) at `fail` sites and reconstruct full diagnostics on demand, the same way Zig reparses.

---

## 10. liblux is open source, permissively licensed.

**Chose:** liblux (the effect checker library) is open source under a permissive license (MIT or Apache-2.0).
**Over:** Proprietary licensing, copyleft (GPL), or open-core with a commercial effect checker.
**Because:** liblux's value is proportional to its adoption. The vocabulary becomes a standard only if everyone can use it. A proprietary effect checker is an effect checker that agents won't use.

Mitchell Hashimoto's "building block economy" observation (April 2026): agents prefer open and free software over closed and commercial. Independent research confirms this — models pick open alternatives under diverse circumstances. libghostty reached millions of daily users in two months because it was a freely available building block. Ghostty the application took eighteen months to reach one million.

liblux is the building block. The vocabulary spreads through the building block. The building block spreads through openness. A permissively licensed liblux that any agent framework, CI pipeline, or IDE plugin can embed without legal review is the fastest path to making the ten-effect vocabulary the standard.

The language can have a more nuanced licensing story later. The library cannot. This is a distribution decision, not an ideological one.

**Would revisit if:** Never. A standard that requires a license is not a standard.
