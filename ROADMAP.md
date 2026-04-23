# Lux Roadmap

## Two artifacts, not one

Lux produces two things:

1. **The language**: a general-purpose programming language with effect-tracked types, value semantics, and Perceus RC. This is the visible product.
2. **liblux**: the effect checker as a standalone library. A formal system for tracking what code does to the world, extractable to other languages, AI agent protocols, and CI pipelines. This is the lasting contribution.

The language is the demo. The effect system is the library. See MANIFESTO.md for the full argument.

## What "building a language" means

A programming language is six things, built in roughly this order:

1. **Specification**: what the language IS (syntax, semantics, type system, effect system)
2. **Parser**: text -> AST
3. **Type checker**: AST -> typed AST (including effect checking)
4. **Interpreter or compiler**: typed AST -> executable
5. **Standard library**: the batteries
6. **Tooling**: formatter, linter, LSP, package manager, REPL

Each phase produces something usable. You don't need all six to start learning from the language.

---

## Phase 0: Specification (current)

**Goal**: A complete enough spec that someone could implement Lux from the document alone.

Deliverables:
- [x] DESIGN.md: thesis, principles, effect system overview
- [x] RESEARCH.md: competitive analysis (Julia, Koka, Unison, Austral, Vale, Hylo)
- [ ] SPEC.md: formal specification
  - [ ] Lexical grammar (tokens, keywords, operators)
  - [ ] Syntax grammar (PEG or BNF)
  - [ ] Type system rules (inference, checking, subtyping)
  - [ ] Effect system rules (propagation, polymorphism, boundaries, capabilities)
  - [ ] Memory model (value semantics, Perceus RC, subscripts/projections)
  - [ ] Module system (one file = one module, visibility, imports)
  - [ ] Error handling (Result types, ? propagation, effect interaction)
- [ ] examples/: enough programs to exercise every language feature
- [ ] Decision log: every "X over Y because Z" recorded

**Key decisions to make in Phase 0:**
1. Value semantics (Hylo) vs ownership (Rust) vs GC
2. Fixed effects vs open effects vs hybrid
3. Algebraic effects with handlers vs simpler effect tracking
4. Multiple dispatch (Julia) vs traits (Rust) vs type classes (Haskell)
5. Async model: effect-based, language primitive, or runtime-provided
6. Metaprogramming: none, hygienic macros, or comptime (Zig)

---

## Phase 1: Tree-Walk Interpreter

**Goal**: Run Lux programs. Slowly. Correctly.

A tree-walk interpreter executes the AST directly. No compilation, no optimization. The point is to validate the language design by running real programs and discovering what's awkward, what's missing, and what's wrong.

Implementation language: **Rust** (ironic but practical: fast, good parsing libraries, pattern matching for AST traversal, no GC to interfere with Lux's own memory model experiments).

**Build methodology: sprint to demos.**

Don't build the lexer, then the parser, then the type checker, then the interpreter as separate phases. Build the thinnest possible vertical slice that runs a real program, then widen. Each demo proves the design works for one more program. One or two demos per week. Do not let perfection be an enemy of progress. (This is Mitchell Hashimoto's approach from "Building Large Technical Projects": decompose into small problems where you can see results, solve each only enough to progress toward a demo, adopt your own software ASAP.)

Demo sequence:

1. **`hello.lux` runs.** Parse it, type-check it (trivial: one function, `can Console`), interpret it, see "Hello, world!" on screen. This proves: lexer, parser, basic type checker, basic interpreter, Console effect module. First demo.

2. **`pure_logic.lux` runs.** Pure functions, pattern matching, pipelines, field projections. This proves: value semantics, function calls, match expressions, the pipeline operator. No effects needed beyond what's already built.

3. **`lux check` works on all examples.** Type-check and effect-check without interpreting. This proves: the full effect system (inference, propagation, polymorphism, boundaries). This is the first tool that's useful independent of the interpreter.

4. **`lux audit` works on all examples.** Print the effect manifest. Machine-readable JSON output. This proves: the audit tool, the manifest format. This is the second independently useful tool.

5. **`weather.lux` runs.** Net, Fs, Env, Console, Fail — five effects in one program. This proves: multiple effect modules, `?` propagation, `catch`, capability access, string interpolation.

6. **`sandbox.lux` runs.** Capability narrowing. This proves: `Net.restrict()`, `Fs.restrict_to()`, the capability model. The thesis demo.

7. **`shortener/` runs.** The full URL shortener: 5 modules, 400+ lines, 7 effects. This proves: the module system, imports, the full effect system under real-world stress. If this runs correctly, the language design is validated.

Deliverables (emerge from the demo sequence):
- [ ] Lexer (source text -> tokens)
- [ ] Parser (tokens -> AST)
- [ ] Type checker (AST -> typed AST, including effect inference)
- [ ] Interpreter (typed AST -> execution)
- [ ] `lux check`: type-check and effect-check without running
- [ ] `lux audit`: print the effect manifest
- [ ] REPL (read-eval-print loop with effect tracking display)
- [ ] Test suite: every example program runs correctly

**Implementation principles for Phase 1:**

The interpreter should practice what the language preaches. Three rules, all from the same insight: don't pay for failure on the success path.

1. **Store byte offsets, not line/column.** The AST records byte positions (one `u32` per node). Line and column numbers are reconstructed on demand by scanning the source when an error needs to be reported. Parsing succeeds most of the time. This is the Zig compiler's approach: reparses on error rather than tracking position metadata that's only needed when things go wrong.

2. **`fail` is a tag, not an allocation.** The runtime representation of a failure is a discriminant flip on a tagged union, not a heap-allocated error object. Stack traces, formatted messages, and diagnostic context are constructed lazily when a `catch` block inspects the error. The `?` propagation path is a branch and a return.

3. **Effect-aware optimization.** Pure functions (no effects) need zero error-handling scaffolding. `can Fail` functions need the branch but not the allocation. The interpreter can use effect annotations to skip work the type system proves unnecessary.

**What we learn in Phase 1:**
- Is the effect system ergonomic? Do programmers (and AI) find it natural?
- Are the capability tokens too verbose? Not verbose enough?
- Does value semantics work for real programs or does it force awkward patterns?
- What's missing from the standard prelude?
- Does lazy error construction make debugging harder in practice?
- Does it feel right? (Tao principle 12: sit with it, use it, live with it.)

---

## Phase 2: Bytecode Compiler + VM

**Goal**: Run Lux programs fast enough for real use.

Compile to a custom bytecode and execute on a stack-based VM. This is the Lua/Python/Ruby approach. Not as fast as native code, but fast enough for most programs and much faster than tree-walking.

Deliverables:
- [ ] Bytecode format specification
- [ ] Compiler (typed AST -> bytecode)
- [ ] Virtual machine (bytecode -> execution)
- [ ] Perceus reference counting implementation
- [ ] `lux build`: compile to bytecode
- [ ] `lux run`: compile and execute
- [ ] Benchmark suite: compare to Python, Ruby, Lua, Go

---

## Phase 3: Native Compilation

**Goal**: Lux programs compile to native binaries.

LLVM backend (like Rust, Zig, Koka) or Cranelift (like Wasmtime, faster compilation). Native compilation is where Lux becomes a real systems language.

Deliverables:
- [ ] LLVM or Cranelift backend
- [ ] Optimization passes (inlining, dead code, constant folding)
- [ ] Perceus RC optimizations (reuse analysis, elision)
- [ ] `lux build --release`: optimized native binary
- [ ] Benchmark suite: compare to Rust, Go, C

---

## Phase 4: Ecosystem

**Goal**: Lux is usable for real projects.

Deliverables:
- [ ] Standard library (collections, I/O, networking, JSON, HTTP)
- [ ] Package manager (`lux pkg`)
- [ ] `lux fmt`: canonical formatter
- [ ] `lux test`: test runner with effect-aware testing
- [ ] LSP server (editor integration)
- [ ] `lux sandbox`: restricted capability execution
- [ ] Documentation generator
- [ ] CI/CD integration (GitHub Actions, etc.)

---

## Phase 5: liblux (The Effect Checker as a Library)

**Goal**: Extract the effect system as a standalone tool that works beyond Lux.

This is the Ghostty/libghostty move. The language validates the effect system. The library makes it available everywhere.

Deliverables:
- [ ] `liblux-spec`: formal specification of the effect vocabulary, propagation rules, and capability model
- [ ] `liblux-core`: Rust library implementing effect checking on a generic AST
- [ ] `lux audit` as a CI gate (reject PRs with unexpected effects)
- [ ] Effect policy files: declare what effects a codebase, module, or function is allowed to use
- [ ] Adapters for other languages:
  - [ ] TypeScript plugin (effect annotations in JSDoc or decorators)
  - [ ] Python static analyzer (`@effects(Net, Fs)` decorators)
  - [ ] Rust proc macro (`#[can(Net, Db)]`)
- [ ] AI agent protocol: generated code ships with an effect manifest, orchestrator verifies before execution
- [ ] Sandbox runtime for untrusted AI-generated code
- [ ] Benchmark: measure AI code generation accuracy in Lux vs Rust vs Go vs Python

---

## Phase 6: Ecosystem and Adoption

**Goal**: Lux is usable for real projects. liblux is integrated into real CI pipelines.

Deliverables:
- [ ] Package manager (`lux pkg`)
- [ ] LSP server (editor integration)
- [ ] Documentation generator
- [ ] GitHub Actions for `lux audit` and effect policy enforcement
- [ ] Case studies: real projects built in Lux, real CI pipelines using liblux

---

## What to build first

Phase 0 is where we are. The next concrete step is finishing the specification, then building the tree-walk interpreter. The interpreter is the fastest path to learning whether the language design works.

But the liblux extraction can start in parallel with Phase 1. The effect checking rules are already specified. A standalone Rust library that takes an AST and returns an effect manifest could exist before the full language interpreter does. This is the artifact most likely to matter in the short term: AI agent orchestrators need effect checking now, not after a five-phase language build.

The implementation language question: **Rust** is the pragmatic choice (fast, good ecosystem, pattern matching). **Lux itself** is the aspirational choice (self-hosting, but requires bootstrapping). **Go** is the simple choice (fast compilation, easy to write, but no sum types or pattern matching). **Zig** is the interesting choice (comptime, manual memory, no hidden allocations).

Recommendation: start in Rust. Self-host later when Lux is mature enough.
