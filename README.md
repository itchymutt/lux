# Gaze

Every function tells you what it does to the world.

Ten effects. Fixed vocabulary. Not extensible.

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
| `Fail` | Can fail (exit, panic, unhandled exceptions) |

## Three implementations, one vocabulary

| Component | What it does | Language |
|---|---|---|
| **gaze** | Interpreter. Effects enforced before execution. | Rust |
| **[libgaze](https://pypi.org/project/libgaze/)** | Static analyzer for Python. Effects detected and reported. | Python |
| **[libgaze-ts](https://www.npmjs.com/package/libgaze-ts)** | Static analyzer for TypeScript. Same vocabulary, different AST. | TypeScript |

The vocabulary is the contribution. The implementations prove it works.

## Quick start

### Analyze Python code

```bash
pip install libgaze
libgaze check your_file.py
```

### Analyze TypeScript code

```bash
npm install libgaze-ts
libgaze-ts check your_file.ts
```

### Run the Gaze language (requires Rust)

```bash
cargo install --path gaze
gaze run examples/hello.gaze
```

## What the analyzers find

```
$ libgaze check code_interpreter.py

code_interpreter.py  can Fs, Net, Unsafe

  restricted_import:75  can Unsafe
    99 | return __import__(name, custom_globals, custom_locals, fromlist or (), level)
  safe_builtins:102  (pure)
  exec:119  can Unsafe
    126 | exec(code, {"__builtins__": SandboxPython.safe_builtins()}, locals)
  _run:194  can Fs, Net, Unsafe
    347 | os.system(f"pip install {library}")
    281 | exec(code, {}, exec_locals)

2/13 functions are pure.
```

Two-pass analysis: walk the AST to detect direct effects, then propagate through the intra-module call graph. If `_run()` calls `self.run_code_unsafe()`, it inherits `Unsafe`.

## Scale

Scanned 3,211 files and 15,293 functions across six projects (CrewAI, LangChain, AutoGPT, MCP Servers, Vercel AI SDK, OpenAI Agents JS). The vocabulary didn't change between Python and TypeScript. Not one effect was added, removed, or renamed.

| | Python | TypeScript |
|---|---|---|
| Files | 1,604 | 1,607 |
| Functions | 12,511 | 2,782 |
| Pure | 66% | 78% |

Labeled benchmarks: 101 Python functions, 54 TypeScript functions. 100% precision, 100% recall on both.

## Policy files

Both analyzers support `.gazepolicy` files for fine-grained control:

```json
{
    "deny": ["Unsafe", "Db"],
    "functions": {
        "transform": { "allow": [] }
    }
}
```

```bash
libgaze policy myfile.py -p .gazepolicy
libgaze-ts policy myfile.ts -p .gazepolicy
```

## CI gate

```yaml
- uses: itchymutt/gaze/action@main
  with:
    path: src/tools/
    deny: Unsafe
```

The GitHub Action scans Python files. For TypeScript, use `libgaze-ts` directly in your CI script.

## The language

```gaze
fn read_config(path: String) can Fs -> Config {
    let text = fs.read(path)
    parse(text)
}

fn transform(data: Config) -> Result {
    // no `can` clause = pure
    // calling fs.read() here is a compile error
}
```

The language is the proof that the vocabulary holds together as a complete programming model. 75 tests. See `gaze/` and `examples/`.

## License

MIT.
