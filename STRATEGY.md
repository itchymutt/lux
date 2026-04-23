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

Mitchell Hashimoto's original definition of "as code" (March 2025): not "as programming" but "as a system of principles or rules." Codification — getting knowledge out of people's heads and into an inscribed system that can be shared, versioned, and iterated upon. The effect vocabulary is "effects as code" in this original sense. Ten words that codify what programs do to the world. The vocabulary is the inscribed system.

**3. AI agents need a trust protocol. Effects are that protocol.**

When an AI agent generates code, there's a trust problem. The agent wants to be useful (solve the problem using whatever capabilities are available). The orchestrator wants to be safe (don't execute code that does unexpected things). Without a shared language for describing behavior, these goals conflict.

Effect manifests resolve the conflict. The agent declares what the code will do. The orchestrator verifies the declaration matches policy. The type system guarantees the declaration is honest. Neither side needs to trust the other. The protocol enforces cooperation.

This is stronger than runtime sandboxing (Docker containers, seccomp profiles, WASM capabilities). Runtime sandboxes detect violations after they happen. Effect manifests prevent violations before they happen. The code that would violate the policy doesn't compile.

There's a deeper framing here. Mitchell Hashimoto's "Prompt Engineering vs. Blind Prompting" (April 2023) describes a rigorous methodology: define a demonstration set (expected input → expected output), test prompt candidates against it, measure accuracy. The key rule: decompose into a single problem, keep the output simple, normalize in your application.

The effect manifest is this pattern applied to code generation. The manifest is the demonstration set — it declares what the code should do. The agent generates code (the completion). `lux check` verifies the completion matches the declaration (the accuracy test). If the code's actual effects don't match the declared effects, it doesn't compile. The accuracy is 100% or it fails. This is prompt engineering with a compiler as the test harness.

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

Ship the smallest useful thing first. Not "the effect checker for all languages." Ship `liblux` for Python — the analyzer that already exists, with a CLI (`liblux check agent.py`), a policy engine (`.luxpolicy` files), and JSON manifest output. That's the `libghostty-vt` equivalent: the smallest piece extracted from the larger vision, zero dependencies, immediately useful, widely portable.

This is the lesson from libghostty's rollout (September 2025): the first library wasn't all of libghostty. It was `libghostty-vt` — VT parsing and terminal state, nothing else. Zero dependencies. C API. The smallest useful building block. It reached millions of users in two months because it solved one problem completely.

Then `liblux` for JavaScript. Then the Rust core library. Then the protocol spec. Each ships independently. Each grows the vocabulary's adoption.

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

## The Building Block Economy

Mitchell Hashimoto, April 2026: libghostty reached multiple millions of daily users in two months. Ghostty the application took eighteen months to reach one million daily macOS update checks. The building block outgrew the application by an order of magnitude in a fraction of the time.

His explanation: the most effective way to build software and get massive adoption is no longer high-quality mainline applications but building blocks that enable others to build quantity over quality. The factory of today is agentic. Agents prefer to grab proven, well-documented components off the shelf and glue them together. The barrier to understanding component pieces well enough to assemble them is gone.

This is the economic argument for liblux-first.

**Lux the language is the application.** It requires adoption, learning, migration. It competes with every other language for mindshare. It's a high-quality mainline product that has to weigh every feature against every other feature.

**liblux is the building block.** It's a pip-installable effect checker that agents can call. It doesn't require learning Lux. It doesn't require migration. It makes existing Python and JavaScript code safer. An agent can grab it off the shelf, run `liblux check agent.py`, and get an effect manifest. No adoption decision needed.

The building block economy has a second implication: **liblux must be open. Unambiguously.** Hashimoto's observation, backed by independent research: models pick open and free software over closed and commercial. An effect checker that agents can't freely use is an effect checker that agents won't use. The vocabulary spreads through the building block. The building block spreads through openness.

The language can have a more nuanced licensing story. The library cannot. liblux is open source, permissively licensed, or it doesn't become the standard.

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

5. **Models get good enough to self-audit.** A model generates code AND a correct effect manifest without external tooling. liblux becomes redundant. Mitigation: this validates the vocabulary, not kills it. The model still needs the ten words to describe what it did. Who produces the manifest is an implementation detail. The vocabulary is the standard.

## Why This Survives Model Improvements

Foundation models leapfrog weekly. The question is whether Lux's thesis holds as models improve.

**Better models make the vocabulary more important, not less.** A model that writes 10x more code creates 10x more surface area to audit. The vocabulary scales linearly with code volume. The need for it grows with model capability.

**Three futures, one constant:**

- Models remain unreliable in adversarial conditions (current reality, likely persists): you need independent verification. A type system the model can't talk its way around.
- Models learn to self-audit: they need a vocabulary to report their effects. The ten words are the vocabulary.
- Models become perfectly reliable: nobody believes this, but even here, the vocabulary serves as documentation for humans reading the code.

The implementation layer (compiler, static analyzer, model self-report) is the part that changes. The vocabulary layer (Net, Fs, Db, Console, Env, Time, Rand, Async, Unsafe, Fail) is the part that persists. Build for the vocabulary.
