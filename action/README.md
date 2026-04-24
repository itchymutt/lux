# Gaze Effect Check Action

Gate PRs on what the code does to the world.

## Usage

### Deny specific effects

```yaml
- uses: itchymutt/gaze/action@main
  with:
    path: src/tools/
    deny: Unsafe,Db
```

### Use a policy file

```yaml
- uses: itchymutt/gaze/action@main
  with:
    path: src/
    policy: .gazepolicy
```

### Report only (no gate)

```yaml
- uses: itchymutt/gaze/action@main
  with:
    path: src/
```

## Policy file format

```json
{
    "deny": ["Unsafe"],
    "functions": {
        "process_data": { "allow": [] }
    }
}
```

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
| `Unsafe` | Subprocess, exec, eval, FFI |
| `Fail` | Can fail (sys.exit, etc.) |
