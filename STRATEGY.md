# Lux Strategy

## The Game

Lux enters a world with established programming languages, growing AI agent ecosystems, and no standard for describing what code does to the world. This document is about how to win that game.

## Three Observations

**1. Languages don't win by being better. They win by solving a problem nobody else solves.**

Rust didn't beat C++ by being a better C++. It solved memory safety without garbage collection, a problem that had no existing solution. Go didn't beat Java by being a better Java. It solved compilation speed and deployment simplicity for networked services. Both created new categories rather than competing in existing ones.

Lux's category: **effect safety for machine-generated code.** No existing language tracks what functions do to the world in a way that's practical, auditable, and enforceable. Haskell's IO monad is theoretically sound but practically unusable for most programmers. Rust's ownership system constrains memory access but not network access, not filesystem access, not database access. Every mainstream language lets a function secretly make HTTP calls with no indication in its signature.

This is the problem Lux solves. Not "a better Rust." Not "a safer Python." A language where the signature tells you everything the function can do, enforced by the compiler, auditable by machines.

**2. The vocabulary is more valuable than the language.**

Ten effects: Net, Fs, Db, Console, Env, Time, Rand, Async, Unsafe, Fail. This is a vocabulary for describing what code does to the world. It's small enough to memorize, fixed enough to standardize, and precise enough to enforce.

If this vocabulary becomes the standard way to describe code behavior, Lux wins regardless of adoption. A TypeScript project that annotates functions with `@can(Net, Db)` is using Lux's vocabulary. A Python linter that checks `# effects: Fs, Fail` comments is using Lux's vocabulary. An AI agent protocol that includes an effect manifest in every code submission is using Lux's vocabulary.

The vocabulary is the platform. The language is one implementation of the platform. liblux (the effect checker as a library) is the distribution mechanism.

This is the HCL pattern. HCL is a configuration language that became the standard for infrastructure-as-code. It succeeded not because everyone switched to HCL, but because the concepts it introduced (declarative infrastructure, plan-then-apply, human-readable-and-machine-parseable) became the standard way to think about infrastructure. Lux's effect vocabulary should do the same for code behavior.

**3. AI agents need a trust protocol. Effects are that protocol.**

When an AI agent generates code, there's a trust problem. The agent wants to be useful (solve the problem using whatever capabilities are available). The orchestrator wants to be safe (don't execute code that does unexpected things). Without a shared language for describing behavior, these goals conflict.

Effect manifests resolve the conflict. The agent declares what the code will do. The orchestrator verifies the declaration matches policy. The type system guarantees the declaration is honest. Neither side needs to trust the other. The protocol enforces cooperation.

This is stronger than runtime sandboxing (Docker containers, seccomp profiles, WASM capabilities). Runtime sandboxes detect violations after they happen. Effect manifests prevent violations before they happen. The code that would violate the policy doesn't compile.

The trust protocol has three components:
- **The vocabulary:** ten effects that describe what code does
- **The manifest:** a machine-readable declaration of every function's effects (the output of `lux audit`)
- **The policy:** a project-level or organization-level file that declares which effects are permitted

An AI agent that generates code with a manifest, verified against a policy, before execution: that's the product.

## The Sequence

### Phase 1: The Vocabulary (now)

Establish the ten-effect vocabulary through the language specification, example programs, and the Tao. The vocabulary must be simple enough that someone can learn it in five minutes and remember it permanently.

The specification is the reference. The examples are the proof. The Tao is the argument.

### Phase 2: The Library (next)

Extract the effect checker as liblux: a Rust library that takes an AST (or annotations) and produces an effect manifest. Ship adapters for TypeScript, Python, and Rust.

liblux enters a positive-sum game. It doesn't compete with existing languages. It makes them better. Every language that adopts liblux grows the market for effect-aware programming, which makes Lux (the native implementation) more attractive.

The library should ship before the language is complete. The language can take years. The library should take months.

### Phase 3: The Protocol

Define the effect manifest format as a specification. JSON schema. Machine-readable. Embeddable in code review tools, CI pipelines, and AI agent frameworks.

```json
{
  "module": "shortener/handler",
  "functions": [
    {
      "name": "route",
      "effects": ["Time", "Rand", "Fail"],
      "capabilities": ["Db"],
      "calls": ["create", "list", "stats", "delete", "redirect"]
    },
    {
      "name": "redirect",
      "effects": ["Time", "Fail"],
      "capabilities": ["Db"],
      "pure_calls": ["not_found", "gone"],
      "effectful_calls": ["store.record_click"]
    }
  ]
}
```

The protocol is the thing that AI agent frameworks adopt. Not the language. Not the library. The protocol. A framework that speaks the protocol can work with any language that produces manifests.

### Phase 4: The Killer App

An AI agent orchestrator built in Lux. It uses effect manifests as its security model:

1. Agent generates code with a manifest
2. Orchestrator checks manifest against policy
3. If manifest violates policy, reject before execution
4. If manifest passes, execute with capability narrowing
5. Runtime verifies the code doesn't exceed its declared effects

This is the focal point. The thing that makes someone say "I need to learn this language" or "I need to adopt this protocol." It demonstrates the thesis with a real product that solves a real problem.

### Phase 5: The Language

The full Lux compiler, standard library, package manager, and ecosystem. By this point, the vocabulary is established, the library is adopted, the protocol is standardized, and the killer app has proven the thesis. The language is the capstone, not the foundation.

## What We're Betting On

1. **AI agents will write most code within five years.** If this is wrong, Lux is a nice language with an effect system. If this is right, Lux is infrastructure.

2. **Effect safety will matter as much as memory safety.** Memory safety prevents crashes and CVEs. Effect safety prevents unauthorized behavior. In a world of autonomous agents, unauthorized behavior is the bigger risk.

3. **A fixed vocabulary beats an extensible one.** Ten effects that everyone agrees on is more valuable than infinite effects that nobody agrees on. The vocabulary must be small enough to standardize.

4. **The library-first strategy works.** Shipping liblux before the language is complete lets us enter the positive-sum game early. The risk: the library without the language is less compelling. The mitigation: the language specification and examples exist as proof of concept.

## What Could Kill This

1. **An existing language adds effect tracking.** If Rust ships an effect system RFC, or TypeScript adds effect annotations, the "no existing solution" claim dies. Mitigation: move fast on liblux. Be the standard before someone else is.

2. **AI agents don't need effect safety.** If runtime sandboxing (Docker, WASM) turns out to be sufficient, the compile-time argument is academic. Mitigation: the trust protocol is still valuable even if runtime sandboxing works, because it's cheaper and catches problems earlier.

3. **The vocabulary is wrong.** If ten effects aren't enough, or the categories are wrong, the standard fractures. Mitigation: the categories are based on real programs (the URL shortener stress test covered 7 of 10). But this is the highest-risk bet.

4. **Nobody cares.** The problem is real but the market doesn't feel the pain yet. AI agents are still mostly writing code that humans review carefully. When agents write code that executes autonomously, the pain becomes acute. Timing matters.
