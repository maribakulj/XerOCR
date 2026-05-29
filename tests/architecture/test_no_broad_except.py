"""Interdiction de ``except Exception: pass`` (et bare except: pass)."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "xerocr"


def _has_broad_silent_except(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                t = node.type
                if t is None:
                    return True
                if isinstance(t, ast.Name) and t.id in {"Exception", "BaseException"}:
                    return True
    return False


def test_no_broad_silent_except():
    offenders = [
        str(p.relative_to(ROOT))
        for p in ROOT.rglob("*.py")
        if _has_broad_silent_except(ast.parse(p.read_text(encoding="utf-8")))
    ]
    assert not offenders, f"`except Exception: pass` interdit : {offenders}"
