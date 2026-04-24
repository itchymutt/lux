"""
Large-scale scan of real agent framework code.

Scans CrewAI tools, LangChain community tools, and AutoGPT blocks.
Reports aggregate statistics: how many files, functions, effects detected,
purity ratios, and the most common effect patterns.

This is NOT a precision/recall benchmark (no ground truth labels).
It measures coverage and usefulness: what does libgaze find when pointed
at real code it's never seen before?

Usage:
    # First, clone the repos:
    mkdir -p /tmp/gaze-scan && cd /tmp/gaze-scan
    git clone --depth 1 https://github.com/crewAIInc/crewAI-tools.git
    git clone --depth 1 https://github.com/langchain-ai/langchain-community.git
    git clone --depth 1 https://github.com/langchain-ai/langchain.git
    git clone --depth 1 https://github.com/Significant-Gravitas/AutoGPT.git

    # Then run:
    uv run --extra dev python bench/scan_repos.py
"""

from __future__ import annotations

import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from libgaze import analyze_file


@dataclass
class RepoStats:
    name: str
    files_scanned: int = 0
    files_failed: int = 0
    total_functions: int = 0
    pure_functions: int = 0
    effectful_functions: int = 0
    effect_counts: Counter = field(default_factory=Counter)
    effect_combos: Counter = field(default_factory=Counter)
    findings: list[str] = field(default_factory=list)


def scan_directory(name: str, path: Path, file_filter: str = "*.py") -> RepoStats:
    stats = RepoStats(name=name)

    py_files = sorted(
        p for p in path.rglob(file_filter)
        if not any(part.startswith(".") or part in (
            "venv", ".venv", "node_modules", "__pycache__",
            "test", "tests", "testing", "test_", "conftest",
        ) for part in p.parts)
        and p.name != "__init__.py"
        and "test" not in p.name.lower()
    )

    for f in py_files:
        try:
            result = analyze_file(f)
            stats.files_scanned += 1
        except (SyntaxError, UnicodeDecodeError, RecursionError):
            stats.files_failed += 1
            continue

        for fn in result.functions:
            stats.total_functions += 1
            if fn.is_pure:
                stats.pure_functions += 1
            else:
                stats.effectful_functions += 1
                for effect in fn.effects:
                    stats.effect_counts[str(effect)] += 1

                combo = ", ".join(sorted(str(e) for e in fn.effects))
                stats.effect_combos[combo] += 1

                # Flag interesting findings
                effects = {str(e) for e in fn.effects}
                if "Unsafe" in effects and len(effects) > 1:
                    rel = f.relative_to(path)
                    stats.findings.append(
                        f"  {rel}:{fn.name}:{fn.lineno}  can {combo}"
                    )

    return stats


def print_stats(stats: RepoStats) -> None:
    purity = stats.pure_functions / stats.total_functions * 100 if stats.total_functions else 0

    print(f"  {stats.name}")
    print(f"    {stats.files_scanned} files scanned ({stats.files_failed} failed to parse)")
    print(f"    {stats.total_functions} functions ({stats.pure_functions} pure, "
          f"{stats.effectful_functions} effectful, {purity:.0f}% purity)")
    print()

    if stats.effect_counts:
        print("    Effects detected:")
        for effect, count in stats.effect_counts.most_common():
            print(f"      {effect:10s}  {count}")
        print()

    if stats.effect_combos:
        print("    Most common effect combinations:")
        for combo, count in stats.effect_combos.most_common(10):
            print(f"      {combo:30s}  {count}")
        print()

    if stats.findings:
        print(f"    Unsafe + other effects ({len(stats.findings)} functions):")
        for f in stats.findings[:20]:
            print(f"    {f}")
        if len(stats.findings) > 20:
            print(f"    ... and {len(stats.findings) - 20} more")
        print()


REPOS = [
    ("CrewAI Tools", Path("/tmp/gaze-scan/crewAI-tools/crewai_tools")),
    ("LangChain Community", Path("/tmp/gaze-scan/langchain-community/libs/community/langchain_community")),
    ("LangChain Core", Path("/tmp/gaze-scan/langchain/libs/core/langchain_core")),
    ("AutoGPT Blocks", Path("/tmp/gaze-scan/AutoGPT/autogpt_platform/backend/backend/blocks")),
]


def main() -> None:
    print()
    print("  libgaze large-scale scan")
    print("  " + "=" * 50)
    print()

    all_stats: list[RepoStats] = []

    for name, path in REPOS:
        if not path.exists():
            print(f"  SKIP  {name} (not found at {path})")
            print("         Run the clone commands from the docstring first.")
            print()
            continue

        stats = scan_directory(name, path)
        all_stats.append(stats)
        print_stats(stats)

    # Aggregate
    if all_stats:
        total_files = sum(s.files_scanned for s in all_stats)
        total_fns = sum(s.total_functions for s in all_stats)
        total_pure = sum(s.pure_functions for s in all_stats)
        total_effectful = sum(s.effectful_functions for s in all_stats)
        total_findings = sum(len(s.findings) for s in all_stats)
        purity = total_pure / total_fns * 100 if total_fns else 0

        agg_effects: Counter = Counter()
        for s in all_stats:
            agg_effects += s.effect_counts

        print("  " + "=" * 50)
        print("  TOTAL")
        print(f"    {total_files} files, {total_fns} functions")
        print(f"    {total_pure} pure, {total_effectful} effectful ({purity:.0f}% purity)")
        print(f"    {total_findings} functions with Unsafe + other effects")
        print()
        print("    Aggregate effect frequency:")
        for effect, count in agg_effects.most_common():
            pct = count / total_effectful * 100 if total_effectful else 0
            print(f"      {effect:10s}  {count:5d}  ({pct:.0f}% of effectful)")
        print()


if __name__ == "__main__":
    main()
