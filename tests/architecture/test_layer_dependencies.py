"""La couche domain n'importe que stdlib + pydantic + pydantic_core."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

DOMAIN = Path(__file__).resolve().parents[2] / "xerocr" / "domain"
ALLOWED_EXT = {"pydantic", "pydantic_core", "typing_extensions", "annotated_types"}
STDLIB = set(sys.stdlib_module_names)


def _imported_modules(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                yield "xerocr.domain"
            elif node.module:
                yield node.module


def test_domain_imports_are_pure():
    offenders: dict[str, list[str]] = {}
    for path in DOMAIN.glob("*.py"):
        bad: list[str] = []
        for mod in _imported_modules(path):
            top = mod.split(".")[0]
            if mod == "xerocr" or mod.startswith("xerocr.domain"):
                continue
            if mod == "__future__" or top in ALLOWED_EXT or top in STDLIB:
                continue
            bad.append(mod)
        if bad:
            offenders[path.name] = bad
    assert not offenders, f"imports interdits dans domain : {offenders}"
