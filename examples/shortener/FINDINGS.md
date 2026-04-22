# URL Shortener: What We Learned

Writing a real program (5 modules, ~400 lines) surfaced design questions the small examples didn't.

## What Worked

1. **The effect signatures read well.** `fn save_link(link: ShortLink) can Db, Fail` is immediately clear. You know what this function does to the world without reading the body. The `can` keyword carries its weight.

2. **Pure functions are the majority.** model.lux is entirely pure. slug.lux is mostly pure (only `generate_slug` needs Rand). The response helpers in handler.lux are pure. The effect system naturally pushes logic toward purity because it's the path of least resistance.

3. **The pipeline + field projection combo is pleasant.** `links |> map(.url.to_string()) |> sort_by(.clicks)` reads like a sentence. This is the syntax at its best.

4. **Testing pure code is trivially easy.** No mocks, no setup, no teardown. `assert_eq(validate_slug("abc"), Some(SlugTooShort))` is a complete test. This is the payoff of the effect system: pure functions are free to test.

5. **Error handling with `catch` is readable.** The redirect handler's `catch store.record_click(slug, now) { Ok(url) => ..., Err(Expired(_)) => ... }` reads naturally. Better than nested match on Result.

## What's Awkward

1. **Anonymous struct literals.** In handler.lux, `json_response(201, { slug: link.slug, url: ... })` uses an anonymous struct literal. This isn't defined in the grammar or type system. What type is `{ slug: String, url: String }`? Is it a structural type (like TypeScript)? A Map? A JSON value? We need to decide. Options:
   - Structural types (anonymous structs): powerful but complex to type-check
   - A `Json` type with builder syntax: `Json.object([ ("slug", link.slug), ... ])`
   - Named structs for everything: verbose but explicit

2. **`impl Encode` in function parameters.** `fn json_response(status: u16, data: impl Encode)` uses Rust's `impl Trait` syntax. We haven't defined whether Lux supports this. Options:
   - `impl Trait` in argument position (like Rust): convenient but has subtle scoping rules
   - Generic with bound: `fn json_response<T: Encode>(status: u16, data: T)`: explicit
   - Both: `impl Trait` is sugar for the generic version

3. **`fail` as a keyword.** In slug.lux, `fail err` is used to raise an error. But `Fail` is an effect, and `?` propagates it. Is `fail` the way you *create* a failure, and `?` the way you *propagate* one? That's two mechanisms for one concept. Alternative: `return Err(err)` like Rust, but that brings back the Result ceremony we eliminated. Or: `?` on the value itself: `None? ` means "fail if None." This needs resolution.

4. **`??` with `fail`.** The pattern `req.body ?? fail json_error(...)` mixes nil coalescing with failure. Is `fail` an expression that returns `!` (never type)? It must be, for this to type-check. That's fine but needs to be specified.

5. **Module imports and effect modules.** `import store` imports the store module. But `db.execute(...)` calls the `db` effect module. How does the compiler distinguish between user modules and effect modules? Options:
   - Effect modules are built-in and don't need imports (current implicit behavior)
   - Effect modules are imported like everything else: `import std.db`
   - Effect modules are accessed through a prefix: `Db.execute(...)` (capitalized)

6. **Closures in `net.serve`.** In main.lux, `net.serve(config.port, |req| { ... })` passes a closure to the server. What effects can the closure have? It calls `handler.route` which is `can Db, Time, Rand, Fail`. Does the closure inherit the caller's effects? Does it need its own `can` clause? This is the effect polymorphism question applied to closures, and it's not trivial.

7. **`Rand` as a separate effect from `Time`.** `generate_slug` needs `Rand`. But in practice, most random number generators are seeded from the clock or OS entropy. Is `Rand` really independent from `Time` and `Env`? Pragmatically yes (you want to track randomness separately for reproducibility). But it means `build_link` is `can Rand, Fail` even though it's "almost pure."

8. **Database connection lifecycle.** `db.connect(url)` in main.lux establishes a connection. But the `db` module functions in store.lux use `db.execute(...)` without any connection parameter. How does the connection flow? Is it implicit global state? That contradicts the "no magic globals" principle. Options:
   - Connection is a capability that's passed explicitly: `fn save_link(db: Db, link: ShortLink)`
   - Connection is module-level state, established once, used everywhere (Go's `sql.DB` pattern)
   - Connection pool is part of the effect system: `can Db` means "has access to a database connection"

## Design Decisions Needed

Ranked by impact:

1. **Anonymous struct literals / structural types.** This affects every handler, every JSON response, every API boundary. Needs a decision before the language is usable for web services.

2. **Database connection model.** Implicit connection state vs explicit passing. This is the biggest tension between beauty (no connection parameter everywhere) and transparency (the signature tells you everything).

3. **`fail` semantics.** Is it a keyword, a function, an expression? What's its type? How does it interact with `?` and `catch`?

4. **Closure effect inference.** When a closure is passed to a higher-order function, how are its effects tracked? This affects every callback, every event handler, every `map` with side effects.

5. **Effect module access pattern.** Built-in magic vs explicit import. Affects every file in every program.
