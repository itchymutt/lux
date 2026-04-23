# Why Lux. Why Now.

## The Problem

In 2025, AI agents started writing production code. Not prototypes. Not suggestions. Actual code that ships to actual users, reviewed by humans who skim it and approve it because it looks right.

It usually is right. The problem is when it isn't.

An AI agent writing Python can import `requests` inside a function that's supposed to be a pure data transformation. The function signature says nothing about this. The code review catches nothing. The tests pass because nobody mocked the network call they didn't know existed. The function ships. It works. Until the network is down, or the endpoint changes, or the function runs in a sandbox that doesn't allow outbound HTTP, and then it fails in a way that nobody can diagnose because nobody knew it was making HTTP calls in the first place.

This is not a hypothetical. This is Tuesday.

The same class of problem exists in C and C++, but worse: an AI agent can generate code that reads memory it shouldn't, writes past buffer boundaries, or frees memory twice. These aren't logic bugs. They're security vulnerabilities. And they're being generated at scale by machines that don't understand what memory safety means, in languages that don't enforce it.

## The Bet

Lux bets that the next generation of programming languages will be designed for a world where most code is written by machines and read by humans. This changes the design priorities:

**Old priority: expressiveness.** Give the programmer maximum power. Trust them to use it wisely. (C, C++, Python, JavaScript)

**New priority: transparency.** Make every behavior visible. Trust nothing. Verify everything. (Lux)

There's already evidence for this bet. Mitchell Hashimoto, returning to Go in 2026, found that agents are "shockingly productive" at writing good Go — better than in any other language he'd used. The reason: `go doc`, `gopls`, one formatting style, structural simplicity. Go's constraints, which humans found limiting, turn out to be agent superpowers. One way to do things means agents don't waste tokens on style decisions. Rich introspection tools give agents context without reading source. Predictable structure means consistent output.

Go's constraints weren't designed for agents. They accidentally serve them. Lux's constraints are designed for agents from the start.

A function in Lux that touches the network says `can Net`. A function that writes to disk says `can Fs`. A function that can fail says `can Fail`. A function that says nothing is pure: it takes values, returns values, and touches nothing else. The compiler enforces this. An AI agent cannot introduce hidden side effects because the type system won't allow it.

This is not a new idea in academia. Haskell's IO monad, Koka's algebraic effects, and Austral's capability tokens all track what functions do to the world. What's new is the motivation: not theoretical purity, but practical safety in a world where the programmer is a machine.

## Two Artifacts, Not One

Mitchell Hashimoto built Ghostty, a terminal emulator. Then he revealed that Ghostty was a demo for libghostty, the terminal library underneath it. The visible product attracted users. The library attracted builders. The lasting contribution was the library.

Lux follows the same pattern.

**The language** is the visible product. It's what people write code in, what the examples demonstrate, what the website shows. It has syntax, a compiler, a standard library, a package manager. It's a real language for real programs.

**The effect checker** is the library underneath. It's a formal system for tracking what code does to the world: a fixed vocabulary of effects (Net, Fs, Db, Console, Env, Time, Rand, Async, Unsafe, Fail), a type-level permission system (`can`), capability narrowing for sandboxing, and an audit tool that produces machine-readable manifests of every function's effects.

The effect checker doesn't require Lux. It's a specification and a reference implementation that could be adapted to:

- **A TypeScript plugin** that checks effect annotations in JSDoc comments
- **A Python static analyzer** that verifies `@effects(Net, Fs)` decorators
- **A Rust proc macro** that adds effect tracking to function signatures
- **An AI agent protocol** where generated code ships with an effect manifest that the orchestrator verifies before execution
- **A CI gate** that rejects pull requests introducing effects not declared in a project's policy file

The language is the demo. The effect system is the contribution.

## Why a Designer Is Building This

Most programming languages are designed by compiler engineers. They start with the type theory, build the compiler, and then figure out what the syntax should look like. The result is languages that are powerful and hard to read. Rust's `fn fetch<'a, T: Deserialize<'a>>(url: &'a str) -> Result<T, Box<dyn Error>>` is correct. It is also hostile.

Lux starts from the other end. What does the code look like on screen? How does it feel to read a stranger's function at 2am during an incident? What does a junior developer see in their first hour? What does an AI agent see when it parses the audit output?

The `can` keyword exists because `! {Net, Db}` was ugly. `Fail` is an effect because `Result<User, AppError>` is ceremony. The `.field` shorthand exists because `|i| i.unit_price` is noise. Effects are modules because two concepts that map 1:1 should be one concept.

These are design decisions, not compiler decisions. They came from looking at the code and saying "this doesn't feel right." That's the value a designer brings to language design: the conviction that how it feels to use is as important as what it can do.

## The Workflow

The most effective pattern for human-agent collaboration is already emerging: the human scaffolds, the agent fills in. Mitchell Hashimoto, building a non-trivial Ghostty feature with agents (October 2025), describes his most productive pattern: create a file with function signatures, parameter types, and TODO comments. Then ask the agent to complete it. The human defines the contract. The agent writes the implementation.

Lux makes this pattern structural. The `can` clause is the scaffold. A human (or an architect agent) writes:

```lux
fn save_order(db: Db, order: Order) -> OrderId can Fail {
    // TODO: validate, persist, return id
}
```

The signature is the complete contract: takes a database capability and an order, returns an ID, can fail, touches nothing else. An agent fills in the body. The compiler verifies the body doesn't exceed the declared effects. The human reviews a function whose boundaries are already guaranteed.

This is why "the signature is the contract" matters for agent-generated code: the signature is the scaffold that makes the agent's output trustworthy before you read a single line of implementation.

## The Principles

1. **Silence is purity.** No annotation means no effects. The default is safe.
2. **The signature is the contract.** Read the function header, know everything it can do.
3. **Composition is pipelines.** Data flows through transformations. Each stage declares its effects.
4. **Constraints are features.** One way to do most things. The compiler enforces what linters suggest.
5. **Two users, one language.** Human readers and machine writers are both first-class.

## What Exists Today

- A design document with the full effect system, memory model, and syntax
- A competitive analysis of seven languages (Julia, Koka, Unison, Austral, Vale, Eff, Hylo)
- A PEG grammar
- Eight example programs covering pure logic, web handlers, CLI tools, concurrency, testing, traits, and AI sandboxing
- A five-phase roadmap from specification to AI-native tooling

## What's Next

The specification needs to be complete enough that a compiler engineer could implement Lux from the documents alone. Then: a tree-walk interpreter in Rust to validate the design by running real programs. Then: the effect checker extracted as a standalone library.

The language is the long game. The effect checker is the thing that could matter next year.

## Who This Is For

If you build compilers and you're tired of languages that treat side effects as someone else's problem.

If you build AI agents and you're tired of sandboxing them with Docker containers instead of type systems.

If you build developer tools and you want a language where `lux audit` tells you everything a program can do in one command.

If you think programming languages should be beautiful and safe, not one or the other.

Come build with us.

github.com/itchymutt/lux
