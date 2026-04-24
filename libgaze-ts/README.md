# libgaze-ts

See what your code does to the world before it runs.

```
$ libgaze-ts check server.ts

server.ts  can Env, Fs, Net

  loadConfig:12  can Env, Fs
    readFileSync() (line 14)
    process.env (line 13)
  startServer:24  can Net
    fetch() (line 28)
  transform:35  (pure)

1/3 functions are pure.
```

libgaze-ts is a static effect analyzer for TypeScript. Same ten effects as [libgaze](../libgaze/) (Python), same two-pass architecture, different AST.

## Install

```bash
npm install libgaze-ts
```

## Usage

### CLI

```bash
# Check a file
libgaze-ts check myfile.ts

# JSON output
libgaze-ts check myfile.ts --json

# Scan a directory
libgaze-ts scan src/

# Fail if denied effects are found (CI gate)
libgaze-ts scan src/ --deny Unsafe,Db

# Check against a policy file
libgaze-ts policy myfile.ts -p .gazepolicy
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

### Programmatic API

```typescript
import { analyzeSource, analyzeFilePath, Effect } from "libgaze-ts";

// Analyze a source string
const result = analyzeSource(`
  function greet() { console.log("hello"); }
`);
console.log(result.allEffects); // Set { "Console" }

// Analyze a file
const fileResult = analyzeFilePath("server.ts");
for (const fn of fileResult.functions) {
  if (!fn.pure) {
    console.log(`${fn.name}: ${[...fn.effects].join(", ")}`);
  }
}
```

## The ten effects

| Effect | What it means |
|--------|--------------|
| `Net` | Touches the network (fetch, http, axios, openai, etc.) |
| `Fs` | Reads or writes files (fs, fs/promises, fs-extra) |
| `Db` | Queries a database (pg, prisma, redis, mongodb, etc.) |
| `Console` | Terminal I/O (console.log, readline, inquirer, chalk) |
| `Env` | Reads environment (process.env, dotenv) |
| `Time` | Clock or sleep (setTimeout, Date.now, performance.now) |
| `Rand` | Randomness (Math.random, crypto.randomUUID) |
| `Async` | Concurrency (worker_threads, child_process) |
| `Unsafe` | Subprocess, exec, eval, FFI, deserialization |
| `Fail` | Can fail (sys.exit, process.exit) |

## Benchmark

54 functions across 4 files. Stdlib patterns, class method propagation, edge cases, pure code.

```
precision  100.0%
recall     100.0%
F1         100.0%
```

Scale scan: 1,607 files and 2,782 functions across MCP Servers, Vercel AI SDK, and OpenAI Agents JS. Zero parse failures.

```bash
npm run build && node dist/bench/run.js        # labeled benchmark
npm run build && node dist/bench/scan_repos.js  # scale scan
```

## How it works

Same architecture as libgaze (Python):

1. **AST walk.** Detect effects from known functions (`fetch`, `readFileSync`, `console.log`) and module imports (`openai`, `pg`, `node:fs`).
2. **Call graph propagation.** Trace `this.method()`, `ClassName.method()`, and bare `function()` calls within the same file. Iterate until stable.

Uses [oxc-parser](https://oxc.rs/) for TypeScript parsing (~2.4MB installed, vs ~50MB for ts-morph).

## Limitations

Same boundaries as the Python analyzer. Catches direct calls and intra-module propagation. Misses method calls on injected objects, dynamic property access, and cross-file analysis.

## Part of Gaze

libgaze-ts is the TypeScript effect analyzer from the [Gaze project](https://github.com/itchymutt/gaze). The ten effects are the same vocabulary in the Gaze language (compiler-enforced), libgaze (Python), and libgaze-ts (TypeScript).
