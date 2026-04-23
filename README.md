# Lux

A programming language where every function shows what it does to the world.

```lux
fn fetch_forecast(city: String) -> Forecast can Net, Fail {
    let url = "https://api.weather.dev/v1/{city}"
    let response = net.get(url)?

    Forecast {
        city,
        temp: response.json("temp")?,
        condition: parse_condition(response.json("condition")?),
        wind: response.json("wind_speed")?,
    }
}

fn parse_condition(raw: String) -> Condition {
    match raw {
        "clear"  => Clear,
        "cloudy" => Cloudy,
        "rain"   => Rain(0.0),
        _        => Clear,
    }
}
```

`fetch_forecast` can touch the network and can fail. `parse_condition` can't do either. The compiler enforces this. An AI agent cannot introduce hidden side effects because the type system won't allow it.

## Why

AI agents generate plausible code at scale. In every mainstream language, a "pure" function can secretly make HTTP calls, write to disk, or access a database, and nothing in the signature reveals it. Code review catches some of it. Most of it ships.

Lux makes every observable behavior visible in the type signature. The keyword `can` declares what a function is allowed to do. Silence means purity. The compiler checks that the declaration is honest.

```lux
fn summarize(order: Order) -> Summary {
    let subtotal = order.items |> map(.unit_price * .quantity) |> sum
    let tax = subtotal * order.tax_rate
    Summary { subtotal, tax, total: subtotal + tax }
}
```

No `can` clause. This function takes values, returns values, touches nothing. Testable without mocks. Reproducible across runs. Safe by construction.

## Ten Effects

Every Lux program's behavior is described by a fixed vocabulary of ten effects:

| Effect | What it means |
|--------|--------------|
| `Net` | Touches the network |
| `Fs` | Reads or writes files |
| `Db` | Queries or mutates a database |
| `Console` | Reads or writes the terminal |
| `Env` | Reads environment variables |
| `Time` | Reads the clock or sleeps |
| `Rand` | Generates random numbers |
| `Async` | Spawns concurrent tasks |
| `Unsafe` | Raw pointers or FFI |
| `Fail` | Can fail (replaces Result/Exception ceremony) |

The vocabulary is fixed. Not extensible. This is deliberate: a fixed set means every Lux program's effects are comparable, auditable, and enforceable by CI policy.

## The Audit Tool

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
```

A complete manifest of what every function does. Machine-readable. Diffable. Enforceable as a CI gate.

## Two Products

**Lux** is a programming language with effect-tracked types, value semantics (no borrow checker, no GC), and Perceus reference counting. It's the native implementation of the effect system.

**liblux** is the effect checker extracted as a standalone library. It works on existing Python and JavaScript code. You don't need to learn Lux to use liblux. `liblux check agent.py` reports what your code does to the world.

The language is the long game. The library is what ships first.

## Key Ideas

**Silence is purity.** No annotation means no effects. The default is safe.

**`can` reads as English.** `fn save(user: User) can Db, Fail` means "this function can touch the database and can fail." The signature is the complete contract.

**`fail` and `?` replace Result ceremony.** Instead of `-> Result<User, Error>`, write `-> User can Fail`. Use `?` to propagate. Use `catch` to handle. Three operations, one concept.

**Pipelines with field projections.** `items |> map(.price * .quantity) |> sum` reads like a sentence.

**Effects are modules.** `can Net` grants permission to call the `net` module. The effect system IS the module permission system. One concept, not two.

**Capabilities can be narrowed.** Pass a restricted `Net` that only reaches `api.example.com`. The callee doesn't know it's restricted. The type system enforces the boundary.

## Examples

The `examples/` directory contains:

- **hello.lux** -- 5 lines. The simplest program.
- **pipeline.lux** -- A web request handler with effect-tracked stages.
- **pure_logic.lux** -- Business logic with zero effects.
- **weather.lux** -- A CLI tool composing Net, Fs, Env, and Console.
- **sandbox.lux** -- AI agent sandboxing via capability narrowing.
- **concurrent.lux** -- Async work with spawn/await.
- **testing.lux** -- Pure and effectful tests.
- **traits.lux** -- Trait system with effect-aware methods.
- **shortener/** -- A complete URL shortener (5 modules, 400+ lines) that stress-tested the language design.

## Documentation

| Document | What it covers |
|----------|---------------|
| [TAO.md](TAO.md) | Principles and worldview |
| [DESIGN.md](DESIGN.md) | Language specification |
| [DECISIONS.md](DECISIONS.md) | Design decisions with rationale |
| [GRAMMAR.md](GRAMMAR.md) | PEG grammar |
| [STRATEGY.md](STRATEGY.md) | Go-to-market and sequencing |
| [LANDSCAPE.md](LANDSCAPE.md) | Competitive analysis |
| [USERS.md](USERS.md) | User personas and adoption |
| [RESEARCH.md](RESEARCH.md) | 7-language comparison |
| [MANIFESTO.md](MANIFESTO.md) | Why Lux, why now |
| [ROADMAP.md](ROADMAP.md) | Build phases |

## Status

Lux is in the specification phase. The language design is documented, stress-tested against a real program (URL shortener), and the competitive landscape is mapped. No compiler exists yet.

Next: liblux (the effect checker for Python/JS), then the tree-walk interpreter for Lux itself.

## License

TBD
