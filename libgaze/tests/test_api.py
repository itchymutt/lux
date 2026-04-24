"""Tests for the public API surface.

Verifies that the documented API works as expected for programmatic users.
"""

from pathlib import Path

from libgaze import Effect, analyze_file, analyze_source
from libgaze.analyzer import FunctionEffects, ModuleEffects


FIXTURES = Path(__file__).parent / "fixtures"


class TestAnalyzeSource:
    def test_returns_module_effects(self):
        result = analyze_source("def add(a, b): return a + b")
        assert isinstance(result, ModuleEffects)

    def test_path_defaults_to_string(self):
        result = analyze_source("x = 1")
        assert result.path == "<string>"

    def test_custom_path(self):
        result = analyze_source("x = 1", path="custom.py")
        assert result.path == "custom.py"

    def test_source_preserved(self):
        src = "def add(a, b): return a + b"
        result = analyze_source(src)
        assert result.source == src

    def test_empty_source(self):
        result = analyze_source("")
        assert len(result.functions) == 0
        assert len(result.all_effects) == 0

    def test_syntax_error_raises(self):
        import pytest
        with pytest.raises(SyntaxError):
            analyze_source("def broken(")


class TestAnalyzeFile:
    def test_returns_module_effects(self):
        result = analyze_file(FIXTURES / "pure.py")
        assert isinstance(result, ModuleEffects)

    def test_path_is_string(self):
        result = analyze_file(FIXTURES / "pure.py")
        assert isinstance(result.path, str)

    def test_accepts_string_path(self):
        result = analyze_file(str(FIXTURES / "pure.py"))
        assert isinstance(result, ModuleEffects)


class TestFunctionEffectsDataclass:
    def test_is_pure_when_no_effects(self):
        fn = FunctionEffects(name="add", lineno=1)
        assert fn.is_pure is True

    def test_not_pure_when_effects(self):
        fn = FunctionEffects(name="fetch", lineno=1, effects={Effect.NET})
        assert fn.is_pure is False

    def test_calls_and_evidence_default_empty(self):
        fn = FunctionEffects(name="add", lineno=1)
        assert fn.calls == []
        assert fn.evidence == []


class TestModuleEffectsProperties:
    def test_all_effects_includes_module_and_function(self):
        result = analyze_source("""
import requests

def fetch(url):
    return requests.get(url)

def save(path):
    with open(path, "w") as f:
        f.write("data")
""")
        assert Effect.NET in result.all_effects
        assert Effect.FS in result.all_effects

    def test_pure_functions_property(self):
        result = analyze_source("""
def add(a, b):
    return a + b

def greet():
    print("hello")
""")
        assert len(result.pure_functions) == 1
        assert result.pure_functions[0].name == "add"

    def test_effectful_functions_property(self):
        result = analyze_source("""
def add(a, b):
    return a + b

def greet():
    print("hello")
""")
        assert len(result.effectful_functions) == 1
        assert result.effectful_functions[0].name == "greet"


class TestEffectEnum:
    def test_all_ten_effects_exist(self):
        effects = [
            Effect.NET, Effect.FS, Effect.DB, Effect.CONSOLE, Effect.ENV,
            Effect.TIME, Effect.RAND, Effect.ASYNC, Effect.UNSAFE, Effect.FAIL,
        ]
        assert len(effects) == 10

    def test_str_representation(self):
        assert str(Effect.NET) == "Net"
        assert str(Effect.FS) == "Fs"
        assert str(Effect.UNSAFE) == "Unsafe"

    def test_construct_from_string(self):
        assert Effect("Net") == Effect.NET
        assert Effect("Unsafe") == Effect.UNSAFE


class TestCallGraphPropagation:
    def test_self_method_propagation(self):
        result = analyze_source("""
class Service:
    def connect(self):
        import requests
        return requests.get("http://example.com")

    def run(self):
        self.connect()
""")
        run_fn = next(f for f in result.functions if f.name == "run")
        assert Effect.NET in run_fn.effects

    def test_classname_method_propagation(self):
        result = analyze_source("""
class FileManager:
    def read(self):
        return open("file.txt").read()

    def process(self):
        FileManager.read(self)
""")
        process_fn = next(f for f in result.functions if f.name == "process")
        assert Effect.FS in process_fn.effects

    def test_bare_function_propagation(self):
        result = analyze_source("""
def write_log():
    print("log entry")

def process():
    write_log()
""")
        process_fn = next(f for f in result.functions if f.name == "process")
        assert Effect.CONSOLE in process_fn.effects

    def test_no_self_recursion(self):
        result = analyze_source("""
def recurse(n):
    if n > 0:
        recurse(n - 1)
""")
        fn = result.functions[0]
        assert fn.is_pure

    def test_transitive_propagation(self):
        result = analyze_source("""
def a():
    print("hello")

def b():
    a()

def c():
    b()
""")
        c_fn = next(f for f in result.functions if f.name == "c")
        assert Effect.CONSOLE in c_fn.effects


class TestAsyncDetection:
    def test_async_function_has_async_effect(self):
        result = analyze_source("""
async def fetch_data():
    pass
""")
        fn = result.functions[0]
        assert Effect.ASYNC in fn.effects
