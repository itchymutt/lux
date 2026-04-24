# libgaze

See what your code does to the world before it runs.

```
$ libgaze check agent_tool.py

agent_tool.py  can Fs, Net, Unsafe

  restricted_import:75  can Unsafe
    99 | return __import__(name, custom_globals, custom_locals, fromlist or (), level)
  exec:119  can Unsafe
    126 | exec(code, {"__builtins__": SandboxPython.safe_builtins()}, locals)
  _run:194  can Fs, Net, Unsafe
    calls run_code_unsafe (line 347)
    calls run_code_safety (line 281)
  run_code_unsafe:347  can Unsafe
    365 | os.system(f"pip install {library}")
    370 | exec(code, {}, exec_locals)

2/13 functions are pure.
```

libgaze is a static effect analyzer for Python. It scans your code and reports which of 10 effects each function performs. Effects propagate through the call graph: if function A calls function B, A inherits B's effects.

## Install

```
pip install libgaze
```

## Usage

```bash
# Check a file
libgaze check myfile.py

# JSON output (for CI pipelines and agents)
libgaze check myfile.py --json

# Scan a directory
libgaze scan src/tools/

# Fail if denied effects are found (CI gate)
libgaze scan src/ --deny Unsafe,Db

# Check against a policy file
libgaze policy myfile.py --policy .gazepolicy
```

### Policy files

A `.gazepolicy` file declares which effects are allowed or denied:

```json
{
    "deny": ["Unsafe", "Db"],
    "functions": {
        "transform": { "allow": [] }
    }
}
```

`allow` means only these effects are permitted (anything else is a violation). `deny` means these effects are forbidden. They're mutually exclusive at each level. Function-level policies override the module-level policy.

## The ten effects

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
| `Unsafe` | Subprocess, exec, eval, FFI, deserialization |
| `Fail` | Can fail (sys.exit, etc.) |

## How it works

Two-pass analysis:

1. **AST walk.** Detect direct effects from known functions (`open`, `subprocess.run`, `os.getenv`, etc.) and module imports (`requests`, `sqlite3`, `docker`, etc.).

2. **Call graph propagation.** Trace `self.method()`, `ClassName.method()`, and bare `function()` calls within the same file. If a callee has effects, the caller inherits them. Iterate until stable.

This catches the common patterns. It does not catch effects hidden behind `getattr`, dynamic imports, method calls on injected objects, or metaclass magic. Silence doesn't mean safe.

## Benchmark

Two benchmarks: a labeled accuracy suite and an unlabeled scale scan.

### Accuracy (labeled, 101 functions)

8 files, 101 functions with human-labeled `# EXPECT:` ground truth. Stdlib patterns, class method propagation, async, network, edge cases, pure code, and real-world agent tools from CrewAI.

```
precision  100.0%
recall     100.0%
F1         100.0%
```

```bash
uv run --extra dev python bench/run.py
```

100% on a benchmark you wrote yourself is expected. It proves the tool works on the patterns it was designed for and catches regressions. Add a `.py` file to `bench/` with `# EXPECT:` comments to extend it.

### Scale (unlabeled, 12,511 functions)

1,604 files across 4 real agent framework repos: CrewAI Tools, LangChain Community, LangChain Core, and AutoGPT.

```
1,604 files, 12,511 functions
8,251 pure (66%), 4,260 effectful (34%)
71 functions with Unsafe + other effects
```

Effect frequency across all effectful functions:

| Effect | Count | % of effectful |
|--------|------:|---------------:|
| Async | 2,125 | 50% |
| Net | 1,621 | 38% |
| Fs | 342 | 8% |
| Time | 250 | 6% |
| Db | 238 | 6% |
| Console | 220 | 5% |
| Env | 168 | 4% |
| Unsafe | 106 | 2% |
| Rand | 20 | <1% |

Spot-checked against source code: every flagged effect verified as real. Known false negatives occur on method calls to injected objects (e.g., `self._firecrawl.scrape_url()` where `_firecrawl` is a `FirecrawlApp` instance set in `__init__`). These are correctly reported as pure because libgaze does single-file analysis and cannot resolve the type.

```bash
uv run --extra dev python bench/scan_repos.py
```

## Limitations

libgaze uses static AST analysis. Python is dynamic. The things it catches:

- Direct calls to stdlib functions (`open`, `os.system`, `subprocess.run`)
- Imports of known modules (`requests`, `docker`, `sqlite3`)
- Intra-module call propagation (`self.method()`, `ClassName.method()`)
- Builtins (`print`, `input`, `exec`, `eval`)

The things it misses:

- Method calls on injected objects (`container.exec_run()`)
- Dynamic dispatch (`getattr(obj, name)()`)
- Metaclass magic, monkey-patching, `*args/**kwargs` forwarding
- Cross-file analysis (effects from imported user modules)

It's a first line of defense, not a proof.

## Part of Gaze

libgaze is the Python effect analyzer from the [Gaze project](https://github.com/itchymutt/gaze). The same ten effects are used in:

- **Gaze language** — compiler-enforced effects (Rust)
- **libgaze** — static analysis for Python (this package)
- **[libgaze-ts](../libgaze-ts/)** — static analysis for TypeScript

The vocabulary is language-independent. It was tested against 15,293 functions across Python and TypeScript without modification.
