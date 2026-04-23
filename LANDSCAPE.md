# Competitive Landscape

Research conducted April 2026. The question: is anyone doing what Lux proposes?

## The Short Answer

No. The combination of **static effect checking** + **fixed vocabulary** + **AI-native focus** is unoccupied. The PL research world builds open/extensible effect systems. The AI safety world builds runtime sandboxes. Nobody connects the two at the type system level.

## The Map

| Approach | Who | Static? | Fixed Vocabulary? | AI-Focused? | Status |
|---|---|---|---|---|---|
| **Lux** | Us | Yes (type system) | Yes (10 effects) | Yes | Specification |
| Koka | Microsoft Research | Yes (type system) | No (open) | No | Research, active |
| Scala capture checking | EPFL | Yes (type system) | No (any capability) | No | Experimental |
| Deno permissions | Deno team | No (runtime flags) | Yes (~7 categories) | No | Shipped |
| Spin manifests | Fermyon | No (deployment manifest) | Yes (declared) | No | Shipped |
| OCaml 5 effects | OCaml team | No (runtime only) | No (open) | No | Shipped |
| Unison abilities | Unison team | Yes (type system) | No (open) | No | Growing |
| Effekt | Research group | Yes (type system) | No (open) | No | Active research |
| Ante | Jake Fecher | Yes (type system) | No (open) | No | Early |
| Roc platforms | Richard Feldman | Partially | Partially | No | Alpha |
| Rust effects initiative | Rust team | Planned | No (async/const/try) | No | Draft RFCs |
| MCP | Anthropic | No (OAuth transport) | No | Partially | Shipped |
| Agent frameworks | Various | No (runtime sandbox) | No | Yes | Shipped |

## What Matters Most

### Go: The Agent Productivity Proof

Mitchell Hashimoto, April 2026, on writing Go again: "its shocking how productive agents are out of the box at writing [good] Go code versus other languages I've used." He attributes this to `go doc`, `gopls`, one formatting style, and the structural simplicity of the language. The "shitty ergonomics" of Go's CLI tools — designed for humans who found them clunky — turn out to be "agent superpowers."

This is the strongest external validation of Lux's thesis. Go's constraints weren't designed for agents, but they accidentally serve agents. One way to format code means agents don't waste tokens on style decisions. Rich introspection tools (`go doc`, `gopls`) give agents the context they need without reading source files. Structural simplicity means fewer ways to write the same thing, so agents produce more consistent output.

Lux's constraints *are* designed for agents. The effect system, the fixed vocabulary, `lux audit`, `lux fmt` — these are the Go pattern made intentional. If Go accidentally became agent-friendly through constraint, a language designed from the start for agent-generated code should be dramatically more so.

Hashimoto also describes Go + Zig as a productive pairing: Go for high-level concurrent code, Zig for zero-dependency cross-compiled performance-critical paths. This is the two-language pattern Lux competes against. Lux's bet is that one language with effect tracking, value semantics, and Perceus RC can cover both roles. If it can't — if the high-level orchestration code and the performance-critical inner loops still want different languages — the Go+Zig approach wins by default.

### Zig: The Performance Proof

Zig is being used for inference in production AI systems (K2.6). Hashimoto: "If you want absolute performance with exacting control over what your CPU executes and the way memory is laid out, Zig is the way." Zig's allocation discipline — no hidden allocations, explicit memory layout, `comptime` for zero-cost abstractions — is the performance standard Lux's native compilation (Phase 3) must eventually match.

Lux doesn't need to beat Zig at memory layout control. That's not the target audience. But Lux does need to be fast enough that the Go+Zig two-language pattern isn't strictly necessary. If a Lux program with `can Unsafe` for the hot path can match "Go for the easy parts, Zig for the fast parts," the single-language story holds.


### Deno: The Runtime Proof

Deno's permission system is the closest existing thing to Lux's effect vocabulary. Seven categories: read, write, net, env, run, ffi, sys. Enforced at process startup via CLI flags. Can be scoped to specific paths, domains, or variables.

Deno proves three things:
1. A fixed vocabulary of ~7-10 permission categories is sufficient for real programs
2. Developers accept declaring permissions (Deno has significant adoption)
3. The categories map naturally to what programs actually do

Deno's limitation: runtime enforcement. A Deno program that calls `fetch()` without `--allow-net` crashes at runtime. A Lux program that calls `net.get()` without `can Net` fails at compile time. The guarantee is strictly stronger.

Deno's Permission Broker protocol (2025-2026) externalizes permission decisions to an external process via JSON-RPC. This is relevant for liblux: the effect manifest format should be compatible with or inspired by Deno's protocol.

### Spin: The Deployment Proof

Fermyon's Spin framework requires WASM components to declare capabilities in `spin.toml`: which HTTP APIs they can call, which key-value stores they can access. This is capability restriction at the deployment boundary.

A Lux program compiled to WASM could auto-generate its Spin manifest from its effect declarations. The compile-time guarantee (Lux) and the runtime enforcement (Spin/WASM) would be complementary layers.

### OWASP: The Market Demand

OWASP's Top 10 for LLM Applications (v2025) names the problems Lux solves:

- **LLM07: Insecure Plugin Design.** "LLM plugins processing untrusted inputs and having insufficient access control risk severe exploits." Lux's capability narrowing is the access control mechanism.
- **LLM08: Excessive Agency.** "Granting LLMs unchecked autonomy to take action can lead to unintended consequences." Lux's effect system is the check on autonomy.

OWASP creates the demand. Lux is the supply.

### Rust Effects Initiative: The Clock

The Rust team has an active effects initiative (formerly "keyword generics"). Goal: make functions generic over async, const, try, and potentially other effects. Draft RFCs exist. Weekly meetings.

This is not a competitor (Rust's effects are about polymorphism, not restriction), but it normalizes effect vocabulary in mainstream programming. If Rust ships keyword generics, it validates Lux's thesis. The risk: if Rust's initiative expands to include I/O capability tracking, it could occupy Lux's space with the weight of Rust's ecosystem behind it.

Current assessment: low risk. Rust's initiative is narrowly scoped to async/const/try. Expanding to I/O capabilities would be a multi-year effort on top of an already multi-year effort. But watch it.

### The Academic Gap

No published papers exist on "effect systems for AI-generated code" (2024-2026). The PL theory community studies effect systems. The AI safety community studies sandboxing. Nobody has connected them formally. A paper on Lux's approach would be novel and citable.

## What Nobody Is Doing

1. **Compile-time effect checking with a fixed vocabulary.** Every academic effect system is open/extensible. Lux's fixed vocabulary is a deliberate constraint that enables standardization.

2. **Effect manifests as an AI agent protocol.** No agent framework (LangChain, CrewAI, OpenAI SDK, Anthropic tools) has a formal declaration of what generated code will do. They all rely on runtime sandboxing.

3. **Connecting PL effect theory to AI safety practice.** The two communities don't talk to each other. Lux sits at the intersection.

## Allies, Not Competitors

- **Deno**: Validates the fixed-vocabulary model. Potential protocol compatibility.
- **Spin/WASM**: Complementary runtime enforcement. Auto-generated manifests from Lux types.
- **OWASP**: Creates market demand for what Lux supplies.
- **Koka/Effekt**: Academic credibility. Lux can cite their work as theoretical foundation.
- **Rust effects initiative**: Normalizes effect vocabulary in mainstream programming.

## Threats

1. **Deno adds static checking.** If Deno's TypeScript integration gains compile-time permission verification, it occupies Lux's space with an existing ecosystem. Probability: low (Deno's team is focused on runtime, not type theory).

2. **A major AI lab ships an effect protocol.** If OpenAI or Anthropic defines a standard for "what this code can do," it could become the de facto vocabulary before Lux establishes its own. Probability: medium (the labs are focused on model capabilities, not code safety, but this could change).

3. **"Good enough" runtime sandboxing.** If Docker + seccomp + WASM turns out to be sufficient for AI agent safety, the compile-time argument is academic. Probability: medium (runtime sandboxing works but is expensive and coarse-grained).
