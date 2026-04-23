"""
Static effect analyzer for Python source code.

Walks the AST and reports which of the 10 Gaze effects each function performs.
This is conservative: if we can't prove a function is pure, we report the
effects we can detect. We don't claim completeness (Python is dynamic),
but we catch the common patterns.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Union

from .effects import (
    ATTRIBUTE_EFFECTS,
    FUNCTION_EFFECTS,
    MODULE_EFFECTS,
    Effect,
)


@dataclass
class FunctionEffects:
    """The effects detected in a single function."""

    name: str
    lineno: int
    effects: set[Effect] = field(default_factory=set)
    calls: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)

    @property
    def is_pure(self) -> bool:
        return len(self.effects) == 0


@dataclass
class ModuleEffects:
    """The effects detected in an entire module (file)."""

    path: str
    source: str = ""  # original source text, for showing context in output
    functions: list[FunctionEffects] = field(default_factory=list)
    module_level_effects: set[Effect] = field(default_factory=set)
    imports: dict = field(default_factory=dict)  # alias -> module

    @property
    def all_effects(self) -> set[Effect]:
        effects = set(self.module_level_effects)
        for fn in self.functions:
            effects |= fn.effects
        return effects

    @property
    def pure_functions(self) -> list[FunctionEffects]:
        return [f for f in self.functions if f.is_pure]

    @property
    def effectful_functions(self) -> list[FunctionEffects]:
        return [f for f in self.functions if not f.is_pure]


class EffectAnalyzer(ast.NodeVisitor):
    """Walk a Python AST and detect effects."""

    def __init__(self, source_path: str = "<unknown>"):
        self.result = ModuleEffects(path=source_path)
        self._current_function: FunctionEffects | None = None
        self._imports: dict = {}  # alias -> full module name

    def analyze(self, source: str) -> ModuleEffects:
        self.result.source = source
        tree = ast.parse(source)
        self.visit(tree)
        self.result.imports = dict(self._imports)
        return self.result

    def analyze_file(self, path: Path) -> ModuleEffects:
        self.result.path = str(path)
        source = path.read_text()
        return self.analyze(source)

    # --- Import tracking ---

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            name = alias.asname or alias.name
            self._imports[name] = alias.name
            self._check_module_import(alias.name, node.lineno)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        for alias in node.names:
            full_name = f"{module}.{alias.name}" if module else alias.name
            local_name = alias.asname or alias.name
            self._imports[local_name] = full_name
            self._check_module_import(module, node.lineno)
            self._check_function_import(full_name, node.lineno)
        self.generic_visit(node)

    def _check_module_import(self, module: str, lineno: int) -> None:
        # Check exact match and prefix matches
        for mod_pattern, effect in MODULE_EFFECTS.items():
            if module == mod_pattern or module.startswith(mod_pattern + "."):
                self._add_effect(effect, f"import {module}", lineno)
                break

    def _check_function_import(self, full_name: str, lineno: int) -> None:
        if full_name in FUNCTION_EFFECTS:
            self._add_effect(
                FUNCTION_EFFECTS[full_name],
                f"import {full_name}",
                lineno,
            )

    # --- Function definitions ---

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        fn = self._visit_function(node)
        fn.effects.add(Effect.ASYNC)
        fn.evidence.append(f"async def {node.name} (line {node.lineno})")

    def _visit_function(self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef]) -> FunctionEffects:
        parent = self._current_function
        fn = FunctionEffects(name=node.name, lineno=node.lineno)
        self._current_function = fn
        self.result.functions.append(fn)
        self.generic_visit(node)
        self._current_function = parent
        return fn

    # --- Call detection ---

    def visit_Call(self, node: ast.Call) -> None:
        call_name = self._resolve_call(node.func)
        if call_name:
            if self._current_function:
                self._current_function.calls.append(call_name)
            self._check_call_effects(call_name, node.lineno)
        self.generic_visit(node)

    def _resolve_call(self, node: ast.expr) -> str | None:
        """Resolve a call expression to a dotted name string."""
        if isinstance(node, ast.Name):
            # Simple name: might be an imported function
            return self._imports.get(node.id, node.id)
        if isinstance(node, ast.Attribute):
            # Dotted name: obj.method
            parts = self._resolve_attribute_chain(node)
            if parts:
                dotted = ".".join(parts)
                # Resolve the first part through imports
                first = parts[0]
                if first in self._imports:
                    return self._imports[first] + "." + ".".join(parts[1:])
                return dotted
        return None

    def _resolve_attribute_chain(self, node: ast.expr) -> list | None:
        """Resolve a.b.c to ["a", "b", "c"]."""
        if isinstance(node, ast.Name):
            return [node.id]
        if isinstance(node, ast.Attribute):
            parent = self._resolve_attribute_chain(node.value)
            if parent is not None:
                return [*parent, node.attr]
        return None

    def _check_call_effects(self, call_name: str, lineno: int) -> None:
        # Check direct function match
        if call_name in FUNCTION_EFFECTS:
            self._add_effect(
                FUNCTION_EFFECTS[call_name], f"{call_name}()", lineno
            )
            return

        # Check if the call is on a module we know about
        parts = call_name.rsplit(".", 1)
        if len(parts) == 2:
            module_part = parts[0]
            for mod_pattern, effect in MODULE_EFFECTS.items():
                if module_part == mod_pattern or module_part.startswith(
                    mod_pattern + "."
                ):
                    self._add_effect(effect, f"{call_name}()", lineno)
                    return

        # Check builtins
        builtin_key = f"builtins.{call_name}"
        if builtin_key in FUNCTION_EFFECTS:
            self._add_effect(
                FUNCTION_EFFECTS[builtin_key], f"{call_name}()", lineno
            )

    # --- Attribute access detection ---

    def visit_Attribute(self, node: ast.Attribute) -> None:
        chain = self._resolve_attribute_chain(node)
        if chain:
            dotted = ".".join(chain)
            # Resolve through imports
            first = chain[0]
            if first in self._imports:
                dotted = self._imports[first] + "." + ".".join(chain[1:])

            if dotted in ATTRIBUTE_EFFECTS:
                self._add_effect(
                    ATTRIBUTE_EFFECTS[dotted], dotted, node.lineno
                )
        self.generic_visit(node)

    # --- Effect recording ---

    def _add_effect(self, effect: Effect, evidence: str, lineno: int) -> None:
        target = self._current_function
        if target:
            target.effects.add(effect)
            target.evidence.append(f"{evidence} (line {lineno})")
        else:
            self.result.module_level_effects.add(effect)


def analyze_source(source: str, path: str = "<string>") -> ModuleEffects:
    """Analyze a Python source string and return its effects."""
    analyzer = EffectAnalyzer(source_path=path)
    return analyzer.analyze(source)


def analyze_file(path: Union[str, Path]) -> ModuleEffects:
    """Analyze a Python file and return its effects."""
    path = Path(path)
    analyzer = EffectAnalyzer(source_path=str(path))
    return analyzer.analyze_file(path)
