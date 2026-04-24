# libgaze benchmark

Measures precision and recall of effect detection against human-labeled ground truth.

## Run

```bash
cd libgaze
uv run --extra dev python bench/run.py
```

## Ground truth format

Each benchmark file contains functions with `# EXPECT:` comments:

```python
# EXPECT: Fs, Unsafe
def dangerous_write(path, code):
    with open(path, "w") as f:
        f.write(code)
    exec(code)

# EXPECT: pure
def add(a, b):
    return a + b
```

The runner parses these, runs libgaze, and compares per-function.

## Scoring

- **True positive**: libgaze reports an effect that the ground truth says exists
- **False positive**: libgaze reports an effect that the ground truth says doesn't exist
- **False negative**: libgaze misses an effect that the ground truth says exists
- **Precision**: TP / (TP + FP)
- **Recall**: TP / (TP + FN)

## Adding fixtures

Create a new `.py` file in `bench/`. Add `# EXPECT:` comments above each function.
The runner picks up all `.py` files in this directory automatically.
