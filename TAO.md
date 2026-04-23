# The Tao of Lux

## Software is becoming invisible.

Most code will be written by machines. Not next decade. Now. The programs that run your infrastructure, process your data, and serve your users are increasingly authored by agents that generate plausible code at superhuman speed.

This changes what a programming language is for.

A language used to be a tool for expressing human intent to a machine. Now it's a contract between two machines, with a human as the auditor. The human doesn't write most of the code. The human reads it, reviews it, and decides whether to trust it.

Lux is designed for this world.

## The Principles

### 1. Show your work.

A program should not be able to do anything its signature doesn't declare. If a function touches the network, the signature says so. If it writes to disk, the signature says so. If it can fail, the signature says so. If the signature says nothing, the function is pure: it takes values, returns values, and touches nothing.

This is the foundational belief. Every other principle follows from it.

Showing your work is not a burden. It's a gift to the person reading your code at 2am during an incident. It's a gift to the AI agent that needs to know whether it's safe to call your function inside a sandbox. It's a gift to the CI pipeline that enforces security policy. The three seconds you spend writing `can Net, Fail` save hours of debugging, auditing, and guessing.

### 2. Purity is the default. Effects are the exception.

Most code should be pure. Data in, data out, nothing else. Pure code is testable without mocks, reproducible across runs, safe to parallelize, and trivial to reason about.

Effects (network, disk, database, randomness, time) are necessary but should be pushed to the edges of a program. The core logic is pure. The boundaries are effectful. The effect system makes this structure visible and enforceable.

A well-designed Lux program looks like a pure core wrapped in a thin effectful shell. If your business logic needs `can Net`, something is wrong with your architecture, not your language.

### 3. Constraints liberate.

The best tools have opinions. They don't ask "how would you like to format your code?" They format it. They don't ask "would you like to track your side effects?" They track them.

Lux is opinionated. One formatting style. One way to handle errors. One way to declare effects. One way to organize modules. These constraints are not limitations. They are decisions made once so they never have to be made again.

Every constraint in Lux exists because the alternative is a decision that wastes time. Should this function return `Result` or throw an exception? In Lux, it says `can Fail`. Should I use callbacks or promises or async/await? In Lux, you `spawn` and the effect system tracks it. Should I use a linter to enforce purity? In Lux, the compiler does it.

Constraints free you to think about the problem, not the language.

### 4. Two users, one program.

Every Lux program has two users: the human who reads it and the machine that writes it. Both are first-class.

For the human: the syntax reads like prose. `can Net, Fail` is English. Pipelines read top to bottom. Pattern matching is exhaustive. String interpolation is natural. The language disappears so the logic can speak.

For the machine: the structure is predictable. Effects are in a fixed vocabulary. Every function signature is a complete contract. The audit tool produces machine-readable manifests. An AI agent can generate Lux code and verify its own output before submitting it for review.

These goals are not in conflict. A language that's easy for machines to generate correctly is also easy for humans to read quickly. Predictability serves both.

### 5. The signature is the API.

If you can read the function signature, you know everything the function can do. Not "might do." Can do. The compiler guarantees this.

This means: no hidden side effects. No implicit state. No action at a distance. No "read the implementation to understand the behavior." The signature is complete.

This is a stronger claim than most languages make. In Python, a function signature tells you the parameter names. In TypeScript, it tells you the types. In Rust, it tells you the types and lifetimes. In Lux, it tells you the types, the effects, and the failure modes. The signature is the documentation, the contract, and the security manifest, all in one line.

### 6. Safety is not a feature. It's the material.

Memory safety, effect safety, and type safety are not features you add to a language. They are the material the language is made of. You don't "enable" safety in Lux. You would have to actively circumvent it, and the language makes that visible (`can Unsafe`).

This is the lesson of the last decade: C and C++ treated safety as optional, and the result is a permanent stream of CVEs. Rust proved that safety can be the default without sacrificing performance. Lux extends this to effects: side effects are not optional to track. They are tracked by the material of the language itself.

In a world where AI agents generate code at scale, every class of bug that the language permits will be generated at scale. The only bugs that don't happen are the ones the language makes impossible.

### 7. Fast feedback, fast programs.

Compilation should be fast. Execution should be fast. Error messages should be immediate and specific. The time between "I changed something" and "I know if it works" should be seconds, not minutes.

This matters doubly for AI agents, which operate in tight generate-check-fix loops. A language with 30-second compile times is a language that makes agents slow. A language with cryptic error messages is a language that makes agents waste tokens on misdiagnosis.

Lux targets fast compilation (incremental, parallel) and fast execution (native code via LLVM, Perceus reference counting with no GC pauses). The error messages name the problem, the location, and the fix.

### 8. Small core, sharp tools.

The language is small. The standard library is focused. The tooling is precise.

`lux build` compiles. `lux check` verifies. `lux audit` reports. `lux fmt` formats. `lux test` tests. `lux sandbox` restricts. Each tool does one thing. They compose through the filesystem and standard I/O, like Unix tools.

The language has ten effects, not a hundred. It has one error handling mechanism, not three. It has one formatting style, not a configuration file. Smallness is a feature because it means the entire language fits in one person's head. Or one agent's context window.

### 9. The library is the legacy.

A language is a vehicle. The ideas inside it are the destination.

Lux's effect system, the fixed vocabulary, the capability model, the audit tool, is a contribution that transcends the language. It can be extracted as a library, adapted to other languages, embedded in AI agent protocols, and used as a CI policy engine.

The language is the demo. The effect system is the lasting artifact. Build the language to validate the ideas. Extract the ideas to change how all code is written.

### 10. The vocabulary outlives the implementation.

Foundation models will get better. They will write more code, faster, with fewer mistakes. They may eventually self-audit their own effects. None of this changes the need for a shared vocabulary to describe what code does to the world.

A static analyzer can produce the vocabulary. A model can self-report it. A compiler can enforce it. A human can write it by hand. The implementation changes. The vocabulary does not. Net means network. Fs means filesystem. Unsafe means unsafe. These words mean the same thing regardless of who writes the code, who checks the code, or how good the models get.

The bet that survives any capability curve is not "humans need a compiler to catch their mistakes." It's "everyone needs a common language to describe what code does." Ten words. Fixed. Universal. That's the contribution.

If models become reliable enough that the Lux compiler is unnecessary, the vocabulary still matters. If liblux is replaced by model self-auditing, the vocabulary still matters. If every language adds native effect tracking, the vocabulary still matters, because someone has to agree on what the categories are.

Build for the vocabulary. The implementations are vehicles.

### 11. The compiler is the harness.

When an AI agent makes a mistake, the current practice is to write a rule in a markdown file so it doesn't make that mistake again. `AGENTS.md`: "don't make HTTP calls from pure functions." "Always run tests before committing." "Use the project's formatting style." These files grow. They're maintained by hand. They're ignored by new agents that haven't read them.

A programming language can be the harness instead. In Lux, "don't make HTTP calls from pure functions" isn't a rule in a file. It's a compiler error. "Use the project's formatting style" isn't a linter config. It's `lux fmt`, one style, not configurable. "Declare what your code does" isn't a code review checklist. It's the type system.

Every rule that lives in the compiler instead of a markdown file is a rule that never needs to be re-taught, never drifts, never gets ignored. The compiler is the harness that makes agents reliable. The more the language enforces, the less the human maintains.

### 12. You have to feel it.

Specifications, test suites, and benchmarks don't capture whether a language feels right. The feeling matters. The feeling is part of the requirements.

When you write `can Net, Fail` and it reads like English, that's a feeling. When you see the `lux audit` output and immediately understand what every function in a program does, that's a feeling. When you read a stranger's Lux function at 2am during an incident and the signature tells you everything, that's a feeling.

The interpreter isn't done when the tests pass. It's done when writing Lux feels like the obvious way to express what a program does. Sit with it. Use it. Live with it. If it doesn't feel right, it isn't right, regardless of what the specification says.

---

## What Lux Is Not

Lux is not a research language. It's not exploring the frontiers of type theory. It's taking proven ideas (effect tracking from Koka, value semantics from Hylo, capabilities from Austral, pipelines from Unix) and combining them into a practical tool for a specific moment in computing: the moment when machines started writing most of the code.

Lux is not a replacement for Rust. Rust is for systems programming where you need control over every byte. Lux is for application programming where you need control over every side effect.

Lux is not a gradual language. You don't sprinkle it into an existing codebase. You start a new project in Lux and get the full safety guarantee from line one. Half-measures in safety are no safety at all.

Lux is not neutral. It has opinions about how software should be built: pure by default, effects at the edges, signatures that tell the truth, constraints that free the programmer. If you disagree with these opinions, Lux is not for you. If you agree, it's the language you've been waiting for.
