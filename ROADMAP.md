# Gaze Roadmap

## What exists today

### The vocabulary

Ten effects: Net, Fs, Db, Console, Env, Time, Rand, Async, Unsafe, Fail. Fixed. Not extensible. Tested against 15,293 functions across Python and TypeScript without modification.

### Gaze language (Rust, ~3,400 lines, 75 tests)

A tree-walk interpreter that enforces effects at compile time.

- [x] Functions, let bindings, arithmetic, comparisons
- [x] Structs with field access
- [x] Enums with pattern matching and destructuring
- [x] Pipeline operator `|>`
- [x] `if`/`else` expressions
- [x] Effect declarations (`can`) and propagation through call graph
- [x] `gaze run`, `gaze check`, `gaze audit`, `gaze fmt`
- [x] Error messages with source context and fix suggestions

### libgaze (Python, ~510 lines, 78 tests + 101 benchmark)

Static effect analyzer for Python. Two-pass: AST walk + call graph propagation. Published on [PyPI](https://pypi.org/project/libgaze/).

- [x] Detect effects from stdlib, builtins, and 60+ third-party libraries
- [x] Intra-module call graph propagation (self.method(), ClassName.method())
- [x] CLI: `libgaze check`, `libgaze scan`, `libgaze policy`
- [x] JSON output for CI pipelines
- [x] Policy files (.gazepolicy) with allow/deny lists and per-function rules
- [x] Unit tests: CLI exit codes, error cases, API surface, policy system (78 tests)
- [x] Labeled benchmark: 101 functions, 100% precision/recall
- [x] Scale scan: 12,511 functions across CrewAI, LangChain, AutoGPT

### libgaze-ts (TypeScript, ~750 lines, 64 tests + 54 benchmark)

Static effect analyzer for TypeScript. Same vocabulary, same architecture, full feature parity with Python.

- [x] Detect effects from Node.js stdlib and 40+ npm packages
- [x] Import resolution (named, default, namespace, require())
- [x] Intra-module call graph propagation
- [x] CLI: check, scan, policy, --deny, --json
- [x] Policy files (.gazepolicy) with allow/deny lists and per-function rules
- [x] Unit tests: API surface, CLI commands, policy system (64 tests)
- [x] Labeled benchmark: 54 functions, 100% precision/recall
- [x] Scale scan: 2,782 functions across MCP Servers, Vercel AI SDK, OpenAI Agents JS

### GitHub Action

- [x] `action/action.yml` for CI gating on effects

## What's next

### Ship (highest priority)

- [x] Publish libgaze to PyPI (`pip install libgaze`)
- [ ] Publish libgaze-ts to npm (`npm install libgaze-ts`)
- [x] Make the repo public
- [ ] Write the blog post (the CrewAI finding is the lede)
- [ ] Publish the GitHub Action to the marketplace

### Improve the analyzers

- [ ] Cross-file analysis (follow imports to user modules)
- [ ] Type-aware resolution for injected objects (the 12% recall gap)
- [ ] Expand labeled benchmarks with external contributors

### Grow the language

- [ ] String operations (concatenation, interpolation, length, slicing)
- [ ] Arrays/lists with iteration
- [ ] Modules and imports
- [ ] Error handling (`fail`, `?`, `catch`)
- [ ] Runtime effect modules (actual Net, Fs, Console implementations)

### Long term

- [ ] Bytecode compiler + VM
- [ ] Integration with runtime agent sandboxes (pre-check code against capability policies)
- [ ] The vocabulary as a standard (RFC or spec document)
