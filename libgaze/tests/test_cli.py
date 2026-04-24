"""Tests for the CLI interface.

Verifies exit codes, output formats, error handling, and flag behavior.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"

# Find the libgaze entry point. Prefer the installed script, fall back to module.
_libgaze_bin = shutil.which("libgaze")
if _libgaze_bin:
    CLI = [_libgaze_bin]
else:
    CLI = [sys.executable, "-m", "libgaze"]


def run_cli(*args: str, expect_fail: bool = False) -> subprocess.CompletedProcess:
    result = subprocess.run(
        [*CLI, *args],
        capture_output=True,
        text=True,
    )
    if not expect_fail:
        assert result.returncode == 0, f"CLI failed (exit {result.returncode}): {result.stderr}\nstdout: {result.stdout}"
    return result


class TestCheckCommand:
    def test_check_pure_file(self):
        r = run_cli("check", str(FIXTURES / "pure.py"))
        assert "(pure" in r.stdout
        assert "3 functions" in r.stdout

    def test_check_effectful_file(self):
        r = run_cli("check", str(FIXTURES / "mixed.py"))
        assert "can" in r.stdout
        assert "Net" in r.stdout

    def test_check_json_output(self):
        r = run_cli("check", str(FIXTURES / "mixed.py"), "--json")
        data = json.loads(r.stdout)
        assert "file" in data
        assert "effects" in data
        assert "functions" in data
        assert isinstance(data["effects"], list)
        assert isinstance(data["functions"], list)

    def test_check_json_pure_file(self):
        r = run_cli("check", str(FIXTURES / "pure.py"), "--json")
        data = json.loads(r.stdout)
        assert data["effects"] == []
        assert all(fn["pure"] for fn in data["functions"])

    def test_check_quiet_suppresses_source_lines(self):
        r = run_cli("check", str(FIXTURES / "mixed.py"), "--quiet")
        # Quiet mode should not show source line numbers with |
        lines = r.stdout.strip().split("\n")
        source_lines = [line for line in lines if " | " in line]
        assert len(source_lines) == 0

    def test_check_deny_passes_when_clean(self):
        r = run_cli("check", str(FIXTURES / "pure.py"), "--deny", "Unsafe,Db")
        assert r.returncode == 0

    def test_check_deny_fails_when_found(self):
        r = run_cli(
            "check", str(FIXTURES / "agent.py"), "--deny", "Unsafe",
            expect_fail=True,
        )
        assert r.returncode == 1
        assert "FAIL" in r.stdout
        assert "Unsafe" in r.stdout

    def test_check_missing_file(self):
        r = run_cli("check", "/nonexistent/file.py", expect_fail=True)
        assert r.returncode == 1
        assert "not found" in r.stderr

    def test_check_no_args(self):
        r = run_cli(expect_fail=True)
        assert r.returncode == 1


class TestScanCommand:
    def test_scan_directory(self):
        r = run_cli("scan", str(FIXTURES))
        assert "files scanned" in r.stdout

    def test_scan_json_output(self):
        r = run_cli("scan", str(FIXTURES), "--json")
        data = json.loads(r.stdout)
        assert isinstance(data, list)
        assert len(data) > 0

    def test_scan_quiet_hides_pure(self):
        r = run_cli("scan", str(FIXTURES), "--quiet")
        assert "(pure)" not in r.stdout

    def test_scan_deny_fails_when_found(self):
        r = run_cli(
            "scan", str(FIXTURES), "--deny", "Unsafe",
            expect_fail=True,
        )
        assert r.returncode == 1
        assert "FAIL" in r.stdout

    def test_scan_deny_passes_when_clean(self):
        # Create a temp dir with only pure code
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            pure = Path(tmp) / "pure.py"
            pure.write_text("def add(a, b):\n    return a + b\n")
            r = run_cli("scan", tmp, "--deny", "Unsafe,Net,Fs")
            assert r.returncode == 0

    def test_scan_missing_directory(self):
        r = run_cli("scan", "/nonexistent/dir", expect_fail=True)
        assert r.returncode == 1
        assert "not found" in r.stderr

    def test_scan_file_not_directory(self):
        r = run_cli("scan", str(FIXTURES / "pure.py"), expect_fail=True)
        assert r.returncode == 1
        assert "not a directory" in r.stderr


class TestPolicyCommand:
    def test_policy_pass(self):
        r = run_cli(
            "policy", str(FIXTURES / "pure.py"),
            "--policy", str(FIXTURES / "sample.gazepolicy"),
        )
        assert "PASS" in r.stdout

    def test_policy_fail(self):
        r = run_cli(
            "policy", str(FIXTURES / "agent.py"),
            "--policy", str(FIXTURES / "sample.gazepolicy"),
            expect_fail=True,
        )
        assert r.returncode == 1
        assert "FAIL" in r.stdout
        assert "violation" in r.stdout.lower()

    def test_policy_json_output(self):
        r = run_cli(
            "policy", str(FIXTURES / "agent.py"),
            "--policy", str(FIXTURES / "sample.gazepolicy"),
            "--json",
            expect_fail=True,
        )
        data = json.loads(r.stdout)
        assert "pass" in data
        assert data["pass"] is False
        assert "violations" in data
        assert len(data["violations"]) > 0

    def test_policy_missing_file(self):
        r = run_cli(
            "policy", "/nonexistent/file.py",
            "--policy", str(FIXTURES / "sample.gazepolicy"),
            expect_fail=True,
        )
        assert r.returncode == 1

    def test_policy_missing_policy_file(self):
        r = run_cli(
            "policy", str(FIXTURES / "pure.py"),
            "--policy", "/nonexistent/policy",
            expect_fail=True,
        )
        assert r.returncode == 1
