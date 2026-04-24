"""Extended policy tests: allow policies, mutual exclusion, edge cases."""

import json
import tempfile
from pathlib import Path

import pytest

from libgaze import Effect, analyze_source, check_policy
from libgaze.policy import Policy, PolicyViolation, load_policy, _parse_policy


class TestAllowPolicy:
    def test_allow_permits_listed_effects(self):
        source = """
import requests

def fetch(url):
    return requests.get(url)
"""
        result = analyze_source(source)
        policy = Policy(allow={Effect.NET})
        violations = check_policy(result, policy)
        assert len(violations) == 0

    def test_allow_denies_unlisted_effects(self):
        source = """
import requests

def fetch(url):
    return requests.get(url)

def save(path, data):
    with open(path, "w") as f:
        f.write(data)
"""
        result = analyze_source(source)
        policy = Policy(allow={Effect.NET})
        violations = check_policy(result, policy)
        # save() has Fs, which is not in allow
        fs_violations = [v for v in violations if v.effect == Effect.FS]
        assert len(fs_violations) > 0

    def test_allow_empty_requires_pure(self):
        source = """
def add(a, b):
    return a + b

def greet():
    print("hello")
"""
        result = analyze_source(source)
        policy = Policy(allow=set())
        violations = check_policy(result, policy)
        # greet() has Console, which is not in empty allow set
        assert len(violations) > 0
        assert all(v.function == "greet" for v in violations)

    def test_allow_empty_passes_pure_code(self):
        source = """
def add(a, b):
    return a + b
"""
        result = analyze_source(source)
        policy = Policy(allow=set())
        violations = check_policy(result, policy)
        assert len(violations) == 0


class TestPolicyMutualExclusion:
    def test_allow_and_deny_raises(self):
        with pytest.raises(ValueError, match="both 'allow' and 'deny'"):
            _parse_policy({"allow": ["Net"], "deny": ["Unsafe"]})

    def test_function_level_allow_and_deny_raises(self):
        with pytest.raises(ValueError, match="both 'allow' and 'deny'"):
            _parse_policy({
                "deny": ["Unsafe"],
                "functions": {
                    "fetch": {"allow": ["Net"], "deny": ["Fs"]}
                }
            })


class TestPolicyFromFile:
    def test_load_allow_policy(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".gazepolicy", delete=False) as f:
            json.dump({"allow": ["Net", "Fs"]}, f)
            f.flush()
            policy = load_policy(Path(f.name))
            assert policy.allow == {Effect.NET, Effect.FS}
            assert policy.deny is None

    def test_load_empty_policy(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".gazepolicy", delete=False) as f:
            json.dump({}, f)
            f.flush()
            policy = load_policy(Path(f.name))
            assert policy.allow is None
            assert policy.deny is None


class TestPolicyViolationFormat:
    def test_violation_to_dict(self):
        v = PolicyViolation(
            function="fetch",
            line=10,
            effect=Effect.NET,
            reason="explicitly denied by policy",
        )
        d = v.to_dict()
        assert d["function"] == "fetch"
        assert d["line"] == 10
        assert d["effect"] == "Net"
        assert d["reason"] == "explicitly denied by policy"

    def test_violation_str(self):
        v = PolicyViolation(
            function="fetch",
            line=10,
            effect=Effect.NET,
            reason="explicitly denied by policy",
        )
        s = str(v)
        assert "fetch:10" in s
        assert "Net" in s


class TestModuleLevelPolicyChecking:
    def test_module_level_effects_checked(self):
        source = """
import requests
"""
        result = analyze_source(source)
        policy = Policy(deny={Effect.NET})
        violations = check_policy(result, policy)
        module_violations = [v for v in violations if v.function == "(module level)"]
        assert len(module_violations) > 0
