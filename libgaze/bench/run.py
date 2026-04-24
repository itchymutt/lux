"""
Benchmark runner for libgaze.

Reads all .py files in bench/, parses # EXPECT: comments,
runs libgaze, and compares per-function.

Usage:
    uv run --extra dev python bench/run.py
    uv run --extra dev python bench/run.py --verbose
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Add the src directory to the path so we can import libgaze
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from libgaze import analyze_file


@dataclass
class Expected:
    function_name: str
    effects: set[str]  # set of effect names, or {"pure"}
    file: str
    line: int


@dataclass
class Result:
    tp: int = 0  # true positives (effect correctly detected)
    fp: int = 0  # false positives (effect reported but not in ground truth)
    fn: int = 0  # false negatives (effect in ground truth but not detected)
    details: list[str] = field(default_factory=list)

    @property
    def precision(self) -> float:
        return self.tp / (self.tp + self.fp) if (self.tp + self.fp) > 0 else 1.0

    @property
    def recall(self) -> float:
        return self.tp / (self.tp + self.fn) if (self.tp + self.fn) > 0 else 1.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) > 0 else 0.0


def parse_expectations(path: Path) -> list[Expected]:
    """Parse # EXPECT: comments from a Python file.

    The comment must appear on the line immediately before a def statement.
    """
    lines = path.read_text().splitlines()
    expectations = []
    pending_expect = None
    pending_line = 0

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # Look for # EXPECT: comments
        match = re.match(r"^#\s*EXPECT:\s*(.+)$", stripped)
        if match:
            raw = match.group(1).strip()
            if raw.lower() == "pure":
                pending_expect = set()
            else:
                pending_expect = {e.strip() for e in raw.split(",")}
            pending_line = i
            continue

        # Look for def statements after an EXPECT comment
        def_match = re.match(r"^def\s+(\w+)", stripped)
        if def_match and pending_expect is not None:
            expectations.append(Expected(
                function_name=def_match.group(1),
                effects=pending_expect,
                file=str(path),
                line=pending_line,
            ))
            pending_expect = None

        # Reset if we hit a non-comment, non-blank, non-decorator line without a def
        if stripped and not stripped.startswith("#") and not stripped.startswith("@") and not def_match:
            pending_expect = None

    return expectations


def run_benchmark(bench_dir: Path, verbose: bool = False) -> Result:
    """Run the benchmark on all .py files in the directory."""
    result = Result()
    files = sorted(p for p in bench_dir.glob("*.py") if p.name != "run.py")

    if not files:
        print("No benchmark files found.")
        return result

    total_functions = 0

    for path in files:
        expectations = parse_expectations(path)
        if not expectations:
            continue

        analysis = analyze_file(path)
        fn_by_name = {fn.name: fn for fn in analysis.functions}

        file_tp = 0
        file_fp = 0
        file_fn = 0

        for exp in expectations:
            total_functions += 1
            actual_fn = fn_by_name.get(exp.function_name)

            if actual_fn is None:
                # Function not found in analysis (shouldn't happen)
                result.details.append(f"  MISSING  {path.name}:{exp.function_name}")
                result.fn += len(exp.effects)
                file_fn += len(exp.effects)
                continue

            actual_effects = {str(e) for e in actual_fn.effects}
            expected_effects = exp.effects

            if expected_effects == set():
                # Expected pure
                if actual_effects:
                    # False positives: reported effects on a pure function
                    for e in sorted(actual_effects):
                        result.fp += 1
                        file_fp += 1
                        result.details.append(
                            f"  FP  {path.name}:{exp.function_name}  "
                            f"reported {e} but expected pure"
                        )
                else:
                    # Correctly identified as pure (counts as 1 TP)
                    result.tp += 1
                    file_tp += 1
            else:
                # Expected specific effects
                for e in expected_effects:
                    if e in actual_effects:
                        result.tp += 1
                        file_tp += 1
                    else:
                        result.fn += 1
                        file_fn += 1
                        result.details.append(
                            f"  FN  {path.name}:{exp.function_name}  "
                            f"missed {e}"
                        )

                for e in actual_effects:
                    if e not in expected_effects:
                        result.fp += 1
                        file_fp += 1
                        result.details.append(
                            f"  FP  {path.name}:{exp.function_name}  "
                            f"reported {e} but not expected"
                        )

        # Per-file summary
        if verbose or file_fp > 0 or file_fn > 0:
            status = "PASS" if file_fp == 0 and file_fn == 0 else "FAIL"
            print(f"  {status}  {path.name}  "
                  f"({len(expectations)} functions, "
                  f"{file_tp} TP, {file_fp} FP, {file_fn} FN)")
        else:
            print(f"  PASS  {path.name}  ({len(expectations)} functions)")

    # Summary
    print()
    print(f"  {total_functions} functions across {len(files)} files")
    print(f"  {result.tp} true positives, {result.fp} false positives, {result.fn} false negatives")
    print()
    print(f"  precision  {result.precision:.1%}")
    print(f"  recall     {result.recall:.1%}")
    print(f"  F1         {result.f1:.1%}")

    if verbose and result.details:
        print()
        print("  Details:")
        for d in result.details:
            print(f"    {d}")

    return result


if __name__ == "__main__":
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    bench_dir = Path(__file__).parent

    print()
    print("  libgaze benchmark")
    print("  " + "=" * 40)
    print()

    result = run_benchmark(bench_dir, verbose=verbose)

    print()

    # Exit non-zero if precision or recall dropped below thresholds
    if result.precision < 0.95:
        print(f"  FAIL: precision {result.precision:.1%} < 95%")
        sys.exit(1)
    if result.recall < 0.80:
        print(f"  FAIL: recall {result.recall:.1%} < 80%")
        sys.exit(1)

    print("  PASS")
