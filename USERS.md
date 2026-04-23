# Who Uses Lux

User research conducted April 2026. Grounded in real companies, real incidents, real adoption patterns.

## The Market in One Paragraph

In 2026, autonomous coding agents (Devin, Factory Droids, Poolside) are deployed at companies like Nubank, Ramp, Klarna, and Gumroad, merging thousands of PRs with minimal human review. Agent sandbox platforms (E2B, Modal, Docker) run 500M+ sandboxes. Agent frameworks (LangChain, CrewAI) process 450M+ workflows monthly across 60% of the Fortune 500. Security incidents are accelerating: the ClawHavoc campaign planted 341 malicious agent Skills on ClawHub, the Vercel breach originated from an AI tool's OAuth permissions, and Grafana, Microsoft, and Salesforce all patched AI agent data leaks in early 2026. OWASP named the problems (LLM07: Insecure Plugin Design, LLM08: Excessive Agency). Nobody has a language-level solution.

## Five Personas

### 1. The Agent Platform Engineer

**Who:** Senior Platform Engineer at E2B, Modal, Docker, Fly.io, or Railway.
**Company size:** 50-500 engineers.
**Problem:** They sandbox agent-generated code with Firecracker microVMs, Docker containers, seccomp profiles, and network policies. These are all enforcement mechanisms. None tell you what the code *intends* to do before it runs. You can block a syscall after it's attempted. You can't express "this agent task should only read files and make HTTP requests, not write to disk or spawn processes."
**Current workaround:** Firecracker isolation, Docker cap_add/cap_drop, seccomp-bpf, AppArmor, OPA policies.
**What they want from liblux:** A library that does static analysis of agent-generated code and produces an effect manifest (Net, Fs, Db, etc.) that can be compared against a policy before execution. Pre-screening, not runtime enforcement (they already have that).
**Rejection risk:** Only works for one language. Too many false positives. Adds latency to the agent execution loop.
**Discovery:** HN, GitHub trending, E2B/Modal/LangChain engineering blogs, AI Engineer Summit.

### 2. The Agent Framework Developer

**Who:** Core Maintainer or Staff Engineer at LangChain, CrewAI, AutoGen, Composio.
**Company size:** 20-200 engineers, but their framework is used by thousands of companies.
**Problem:** Their frameworks let agents call tools, but they have no way to statically verify that a tool chain stays within declared capabilities. CrewAI has "Task guardrails" (runtime checks). LangChain has observability (LangSmith traces). Neither has pre-execution effect analysis.
**Current workaround:** Runtime tool-call filtering, human-in-the-loop approval gates, LLM-as-judge evaluation.
**What they want from liblux:** Effect annotations on tool definitions. A decorator that says `@effects(Net, Fs.Read)` on a tool function, and liblux verifies the implementation matches. Automatic effect propagation through tool chains.
**Rejection risk:** Requires restructuring framework internals. Doesn't integrate with Python/TypeScript. Value is theoretical, not demonstrated against real attacks.
**Discovery:** GitHub issues on their repos, community Slack/Discord, AI Engineer Summit, Twitter/X.

### 3. The Security Engineer at an Agent-Heavy Company

**Who:** Application Security Engineer at a company with 100+ engineers using Cursor, Windsurf, Devin, or Copilot at scale.
**Companies:** Nubank (6M+ lines migrated by Devin), Ramp, Klarna, Shopify, Gumroad (1,500+ Devin PRs merged).
**Problem:** AI coding tools generate code that SAST scanners flag after the fact. For autonomous agents like Devin that merge their own PRs, security review happens after the code is in the codebase. The Vercel breach showed what happens when AI tools get overpermissioned OAuth grants.
**Current workaround:** Snyk Code, Semgrep, GitHub Advanced Security, custom CI rules.
**What they want from liblux:** A CI step that analyzes AI-generated code diffs and reports the effect signature. "This PR adds Net access to a module that previously had none." The effect diff as a security signal. If a PR from Devin introduces `Unsafe` or `Db` effects in a frontend component, flag it.
**Rejection risk:** Doesn't integrate with GitHub Actions/GitLab CI. Requires code changes. Effect vocabulary too coarse or too fine.
**Discovery:** RSA Conference, Black Hat, Snyk blog, Dark Reading, vendor evaluations.

### 4. The DevSecOps Policy Engineer

**Who:** DevSecOps Engineer or Platform Security Engineer at a 500+ engineer org.
**Problem:** They write OPA/Rego policies for infrastructure (Terraform plans, Kubernetes manifests) but have no equivalent for application-level effect policies. They can say "no container may have NET_RAW capability" but can't say "no service in the payments domain may write to the users database."
**Current workaround:** OPA/Rego for infrastructure, custom Semgrep rules for code patterns, manual architecture reviews.
**What they want from liblux:** Policy-as-code for effects. A `.luxpolicy` file that says "services in /payments/ must not have effects: [Net.External, Unsafe]" and liblux checks every PR against it.
**Rejection risk:** Standalone tool that doesn't integrate with existing policy framework. Steep learning curve.
**Discovery:** HashiConf, KubeCon, internal platform engineering Slack, Thoughtworks Technology Radar.

### 5. The Language Enthusiast

**Who:** Software engineer who follows r/ProgrammingLanguages, reads PL papers, has opinions about algebraic effects vs monads.
**Problem:** Effect systems are well-studied in PL research but have zero production-grade implementations outside Koka and Unison. They want to see a practical application.
**What they want from Lux:** A real language with a real effect system that solves a real problem. Not another research language. Not another "we'll get to production eventually." A language they can write real programs in.
**Rejection risk:** The language is vaporware (spec only, no compiler). The effect system is too simple (only 10 effects, no user-defined effects). The language is too similar to Rust.
**Discovery:** HN, r/ProgrammingLanguages, Lobsters, PL Twitter/X, Strange Loop talks.

## Who Pays

**Personas 1-4 pay.** They have budgets for security tooling, CI infrastructure, and platform engineering. The buyer is the Platform Engineering Director (personas 1, 4), the VP of Engineering (persona 2), or the CISO/Head of AppSec (persona 3).

**Persona 5 doesn't pay** but builds the compiler, files bugs, writes blog posts, and creates the community buzz that attracts personas 1-4.

## The Adoption Sequence

1. **liblux CLI for Python/JS** (personas 1, 2, 3): `liblux check agent_code.py` produces an effect report. No new language. No code changes. Works on existing agent code.

2. **liblux CI integration** (personas 3, 4): GitHub Action that checks effect policies on every PR. `.luxpolicy` files checked into repos. Effect diffs in PR comments.

3. **Lux the language** (persona 5, then all): By this point the vocabulary is battle-tested. The language is "what if your compiler enforced these effects natively?"

## Evidence That the Pain Is Real

- **341 malicious agent Skills** found on ClawHub (ClawHavoc campaign, Jan 2026)
- **Vercel breach** via AI tool OAuth overpermissioning (Apr 2026)
- **Grafana, Microsoft, Salesforce** all patched AI agent data leaks (Apr 2026)
- **97% of security leaders** call for AI security mandates (Snyk 2026 report)
- **HackerOne suspended bug bounties** due to AI-generated submission flood (Mar 2026)
- **OWASP LLM07/LLM08** formally categorize the risks Lux addresses
- **Dark Reading:** "2026: The Year Agentic AI Becomes the Attack-Surface Poster Child"

## Companies Most Likely to Be First Customers

Based on the research, not hypothetical:

1. **E2B** -- They sandbox 500M+ agent executions. They need pre-execution screening. liblux effect manifests are the missing layer between "the agent generated code" and "we ran it in a Firecracker VM."

2. **LangChain** -- 100M+ monthly downloads. They need effect annotations for tool definitions. liblux decorators on tool functions would be a natural integration.

3. **Security teams at Devin-heavy companies** (Nubank, Ramp, Gumroad) -- They're merging thousands of AI-generated PRs. They need effect diffs in CI. The Vercel breach is their nightmare scenario.

4. **Docker** -- The Dash platform already has compartments, capability grants, and egress policies. liblux effect manifests map directly to Dash's permission model.

5. **Poolside** -- Their enterprise pitch explicitly includes "Executive-grade governance" and "Risk controls and auditability." liblux is the technical implementation of what they're promising.
