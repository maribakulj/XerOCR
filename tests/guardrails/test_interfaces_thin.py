"""Garde-fou : la couche 8 (routeurs web) est du **transport mince**.

Un routeur de ``interfaces/web/routers/`` parse une requête, appelle un service
de la couche ``app`` (6) et renvoie une réponse. Il ne **construit pas** lui-même
les specs d'orchestration (``RunSpec``/``PipelineSpec``/``EvaluationView``…) :
assembler une spec est un acte de la couche ``app``, jamais d'une feuille de
transport. Le test d'``layer_dependencies`` autorise (légalement) ``interfaces``
à importer ``domain`` ; il ne capture donc pas cette fuite d'orchestration.

Actuellement ``runs.py`` et ``segmentation.py`` assemblent les specs dans le
handler → ``xfail(strict)``. Le jour où cette construction migre en couche
``app``, le test passe (XPASS) et le marqueur strict force son retrait.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROUTERS = (
    Path(__file__).resolve().parents[2]
    / "xerocr"
    / "interfaces"
    / "web"
    / "routers"
)

#: Constructeurs de specs d'orchestration : leur instanciation appartient à la
#: couche ``app`` (planification du run), pas à un routeur de transport.
_SPEC_CONSTRUCTORS = frozenset(
    {
        "RunSpec",
        "PipelineSpec",
        "PipelineStep",
        "EvaluationSpec",
        "EvaluationView",
        "ProjectionSpec",
    }
)


def _spec_constructions(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = (
            func.id
            if isinstance(func, ast.Name)
            else func.attr
            if isinstance(func, ast.Attribute)
            else None
        )
        if name in _SPEC_CONSTRUCTORS:
            found.append(f"{name}() L{node.lineno}")
    return found


@pytest.mark.xfail(
    strict=True,
    reason="un routeur (couche 8) ne doit pas construire de spec "
    "d'orchestration : déplacer la construction en couche app.",
)
def test_routers_do_not_build_orchestration_specs() -> None:
    offenders: dict[str, list[str]] = {}
    for path in sorted(ROUTERS.glob("*.py")):
        hits = _spec_constructions(path)
        if hits:
            offenders[path.name] = hits
    assert not offenders, (
        "Construction de specs d'orchestration dans des routeurs de transport "
        f"(doit vivre en couche app) : {offenders}"
    )
