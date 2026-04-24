"""
libgaze CLI.

Usage:
    libgaze check <file.py>              Report effects with source context
    libgaze check <file.py> --json       Output as JSON manifest
    libgaze check <file.py> --quiet      Terse output (no source lines)
    libgaze check <file.py> --deny Unsafe,Db   Fail if these effects are found
    libgaze scan <dir>                   Scan all Python files in a directory
    libgaze scan <dir> --deny Unsafe     Fail if denied effects are found
    libgaze policy <file.py> -p .gazepolicy    Check against a policy file
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .analyzer import ModuleEffects, analyze_file
from .effects import Effect
from .policy import check_policy, load_policy


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="libgaze",
        description="See what your code does to the world before it runs.",
    )
    subparsers = parser.add_subparsers(dest="command")

    # check command
    check_parser = subparsers.add_parser(
        "check", help="Report effects in a Python file"
    )
    check_parser.add_argument("file", type=Path, help="Python file to analyze")
    check_parser.add_argument(
        "--json", action="store_true", dest="json_output", help="Output as JSON"
    )
    check_parser.add_argument(
        "--quiet", "-q", action="store_true", help="Terse output (no source lines)"
    )
    check_parser.add_argument(
        "--deny",
        type=str,
        default=None,
        help="Comma-separated effects to deny (exits non-zero if found)",
    )

    # policy command
    policy_parser = subparsers.add_parser(
        "policy", help="Check a file against an effect policy"
    )
    policy_parser.add_argument("file", type=Path, help="Python file to analyze")
    policy_parser.add_argument(
        "--policy", "-p", type=Path, required=True, help="Policy file (.gazepolicy)"
    )
    policy_parser.add_argument(
        "--json", action="store_true", dest="json_output", help="Output as JSON"
    )

    # scan command
    scan_parser = subparsers.add_parser(
        "scan", help="Scan all Python files in a directory"
    )
    scan_parser.add_argument("path", type=Path, help="Directory to scan")
    scan_parser.add_argument(
        "--json", action="store_true", dest="json_output", help="Output as JSON"
    )
    scan_parser.add_argument(
        "--quiet", "-q", action="store_true", help="Only show effectful files"
    )
    scan_parser.add_argument(
        "--deny",
        type=str,
        default=None,
        help="Comma-separated effects to deny (exits non-zero if found)",
    )

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    if args.command == "check":
        run_check(args)
    elif args.command == "scan":
        run_scan(args)
    elif args.command == "policy":
        run_policy(args)


def run_check(args: argparse.Namespace) -> None:
    if not args.file.exists():
        print(f"error: {args.file} not found", file=sys.stderr)
        sys.exit(1)

    if args.file.is_dir():
        print(f"error: {args.file} is a directory (use 'libgaze scan' for directories)", file=sys.stderr)
        sys.exit(1)

    try:
        result = analyze_file(args.file)
    except SyntaxError as e:
        print(f"error: {args.file} has a syntax error: {e.msg} (line {e.lineno})", file=sys.stderr)
        sys.exit(1)

    if args.json_output:
        print(json.dumps(to_json(result), indent=2))
        return

    print_report(result, quiet=args.quiet)

    # --deny: exit non-zero if denied effects are found
    if args.deny:
        denied = {Effect(e.strip()) for e in args.deny.split(",")}
        found = result.all_effects & denied
        if found:
            names = ", ".join(sorted(str(e) for e in found))
            print(f"\nFAIL  denied effects found: {names}")
            sys.exit(1)


def run_scan(args: argparse.Namespace) -> None:
    if not args.path.exists():
        print(f"error: {args.path} not found", file=sys.stderr)
        sys.exit(1)

    if not args.path.is_dir():
        print(f"error: {args.path} is not a directory", file=sys.stderr)
        sys.exit(1)

    # Collect all .py files, skip venvs and hidden dirs
    py_files = sorted(
        p for p in args.path.rglob("*.py")
        if not any(part.startswith(".") or part in ("venv", ".venv", "node_modules", "__pycache__")
                   for part in p.parts)
    )

    if not py_files:
        print(f"no Python files found in {args.path}")
        return

    results = []
    for f in py_files:
        try:
            result = analyze_file(f)
            results.append(result)
        except SyntaxError:
            pass  # skip files that don't parse

    if args.json_output:
        print(json.dumps([to_json(r) for r in results], indent=2))
        return

    # Summary view
    effectful = [r for r in results if r.all_effects]
    pure = [r for r in results if not r.all_effects]

    for r in effectful:
        effect_str = ", ".join(sorted(str(e) for e in r.all_effects))
        fn_count = len(r.functions)
        pure_count = len(r.pure_functions)
        print(f"  {r.path}  can {effect_str}  ({pure_count}/{fn_count} pure)")

    if not args.quiet and pure:
        print()
        for r in pure:
            print(f"  {r.path}  (pure)")

    print()
    print(f"{len(results)} files scanned. {len(effectful)} effectful, {len(pure)} pure.")

    # --deny: exit non-zero if denied effects are found anywhere
    if args.deny:
        denied = {Effect(e.strip()) for e in args.deny.split(",")}
        violations = []
        for r in results:
            found = r.all_effects & denied
            if found:
                names = ", ".join(sorted(str(e) for e in found))
                violations.append(f"  {r.path}: {names}")
        if violations:
            print()
            print("FAIL  denied effects found:")
            for v in violations:
                print(v)
            sys.exit(1)


def run_policy(args: argparse.Namespace) -> None:
    if not args.file.exists():
        print(f"error: {args.file} not found", file=sys.stderr)
        sys.exit(1)
    if not args.policy.exists():
        print(f"error: {args.policy} not found", file=sys.stderr)
        sys.exit(1)

    try:
        result = analyze_file(args.file)
    except SyntaxError as e:
        print(f"error: {args.file} has a syntax error: {e.msg} (line {e.lineno})", file=sys.stderr)
        sys.exit(1)

    try:
        policy = load_policy(args.policy)
    except json.JSONDecodeError as e:
        print(f"error: {args.policy} is not valid JSON: {e.msg} (line {e.lineno})", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"error: {args.policy}: {e}", file=sys.stderr)
        sys.exit(1)

    violations = check_policy(result, policy)

    if args.json_output:
        print(json.dumps({
            "file": str(args.file),
            "policy": str(args.policy),
            "pass": len(violations) == 0,
            "violations": [v.to_dict() for v in violations],
        }, indent=2))
    else:
        if violations:
            print(f"FAIL  {args.file}")
            print()
            for v in violations:
                # Show source context for the violation
                source_line = _get_source_line(result.source, v.line)
                if source_line and v.line > 0:
                    print(f"  {v.function}:{v.line}  {v.effect} -- {v.reason}")
                    print(f"    {v.line} | {source_line}")
                else:
                    print(f"  {v.function}  {v.effect} -- {v.reason}")
            print()
            print(f"{len(violations)} violation(s) found.")
            sys.exit(1)
        else:
            print(f"PASS  {args.file}")


def print_report(result: ModuleEffects, quiet: bool = False) -> None:
    effects = result.all_effects
    if not effects:
        total = len(result.functions)
        if total > 0:
            print(f"{result.path}  (pure, {total} functions)")
        else:
            print(f"{result.path}  (pure)")
        return

    effect_str = ", ".join(sorted(str(e) for e in effects))
    print(f"{result.path}  can {effect_str}")
    print()

    source_lines = result.source.splitlines() if result.source else []

    for fn in result.functions:
        if fn.is_pure:
            print(f"  {fn.name}:{fn.lineno}  (pure)")
        else:
            fn_effects = ", ".join(sorted(str(e) for e in fn.effects))
            print(f"  {fn.name}:{fn.lineno}  can {fn_effects}")
            if not quiet:
                for ev in fn.evidence:
                    # Parse "subprocess.run() (line 10)" to get line number
                    ev_line = _parse_evidence_line(ev)
                    if ev_line and 0 < ev_line <= len(source_lines):
                        src = source_lines[ev_line - 1].strip()
                        print(f"    {ev_line} | {src}")
                    else:
                        print(f"    {ev}")

    if result.module_level_effects:
        print()
        mod_effects = ", ".join(
            sorted(str(e) for e in result.module_level_effects)
        )
        print(f"  (module level)  can {mod_effects}")

    # Summary
    pure_count = len(result.pure_functions)
    total = len(result.functions)
    if total > 0:
        print()
        print(f"{pure_count}/{total} functions are pure.")


def _parse_evidence_line(evidence: str) -> int | None:
    """Extract line number from evidence string like 'subprocess.run() (line 10)'."""
    try:
        if "(line " in evidence:
            part = evidence.split("(line ")[1].rstrip(")")
            return int(part)
    except (IndexError, ValueError):
        pass
    return None


def _get_source_line(source: str, lineno: int) -> str | None:
    """Get a source line by 1-indexed line number."""
    if not source or lineno < 1:
        return None
    lines = source.splitlines()
    if lineno <= len(lines):
        return lines[lineno - 1].strip()
    return None


def to_json(result: ModuleEffects) -> dict:
    return {
        "file": result.path,
        "effects": sorted(str(e) for e in result.all_effects),
        "functions": [
            {
                "name": fn.name,
                "line": fn.lineno,
                "effects": sorted(str(e) for e in fn.effects),
                "pure": fn.is_pure,
                "evidence": fn.evidence,
                "calls": fn.calls,
            }
            for fn in result.functions
        ],
        "module_level_effects": sorted(
            str(e) for e in result.module_level_effects
        ),
    }
