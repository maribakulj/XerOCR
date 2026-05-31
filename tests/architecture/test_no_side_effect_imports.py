"""Aucun effet de bord à l'import (`CLAUDE.md` §7).

Anti-pattern proscrit (hérité de Picarones) : un ``__init__.py`` qui exécute du
code au chargement — ``register_default_metrics()`` implicite, ``app = FastAPI()``
au niveau module, ``JOB_STORE = get_default_store()`` qui ouvre une SQLite à
l'import. Conséquence : tout import tire des deps lourdes et casse l'installation
minimale. Tout enregistrement doit être **explicite, idempotent, testable à part**.

Deux barrières :

1. **statique** (AST) : aucun module ne contient (a) d'appel **nu** au niveau
   module, ni (b) d'affectation à une **fabrique impure connue**. Les constantes
   pures (``re.compile``, ``ConfigDict``, ``frozenset``…) restent autorisées ;
2. **dynamique** (subprocess) : importer une couche construite ne charge aucune
   lib externe lourde.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

import pytest

XEROCR = Path(__file__).resolve().parents[2] / "xerocr"

#: Fabriques à effet de bord : instancier un serveur/routeur, ouvrir un store,
#: installer un handler global, enregistrer dans un registre. Interdites au
#: niveau module (doivent vivre dans une fonction appelée explicitement).
_SIDE_EFFECT_FACTORIES = frozenset({
    "FastAPI",
    "APIRouter",
    "get_default_store",
    "create_engine",
    "connect",
    "install_opener",
    "build_opener",
    "register_default_metrics",
    "bootstrap_default_registries",
})

#: Appels nus PURS et nécessaires, tolérés au niveau module : résolution de
#: références avant Pydantic pour les modèles récursifs (idempotent, sans I/O).
_ALLOWED_BARE_CALLS = frozenset({"model_rebuild", "update_forward_refs"})

#: Libs lourdes qui ne doivent jamais être chargées par le simple import d'une
#: couche (signe d'un bootstrap magique).
_HEAVY = (
    "numpy",
    "scipy",
    "fastapi",
    "starlette",
    "uvicorn",
    "jiwer",
    "rapidfuzz",
    "PIL",
)


def _call_name(node: ast.Call) -> str:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return "<call>"


def _module_level_side_effects(tree: ast.Module) -> list[str]:
    offenders: list[str] = []
    for stmt in tree.body:
        # (a) ``foo()`` nu — la valeur est jetée : seul l'effet compte
        # (sauf résolution de réfs Pydantic, pure et requise).
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            name = _call_name(stmt.value)
            if name not in _ALLOWED_BARE_CALLS:
                offenders.append(name + "()")
        # (b) ``X = fabrique_impure()``.
        elif isinstance(stmt, (ast.Assign, ast.AnnAssign)) and isinstance(
            stmt.value, ast.Call
        ):
            name = _call_name(stmt.value)
            if name in _SIDE_EFFECT_FACTORIES:
                offenders.append(name + "()")
    return offenders


def test_no_module_level_side_effects() -> None:
    hits: dict[str, list[str]] = {}
    for path in XEROCR.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        calls = _module_level_side_effects(ast.parse(path.read_text(encoding="utf-8")))
        if calls:
            hits[str(path.relative_to(XEROCR))] = calls
    assert not hits, (
        f"\nEffet de bord exécuté à l'import (interdit) :\n  {hits}\n"
        "Tout enregistrement/instanciation doit être explicite (dans une "
        "fonction), jamais au niveau module."
    )


@pytest.mark.parametrize("layer", ["domain", "formats"])
def test_layer_import_loads_no_heavy_lib(layer: str) -> None:
    """Importer une couche construite ne charge aucune lib externe lourde."""
    code = (
        "import sys;"
        f"import xerocr.{layer};"
        "print(','.join(sorted(m for m in sys.modules if '.' not in m)))"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        cwd=XEROCR.parent,
    )
    assert proc.returncode == 0, f"import xerocr.{layer} a échoué :\n{proc.stderr}"
    loaded = set(proc.stdout.strip().split(","))
    heavy = sorted(loaded.intersection(_HEAVY))
    assert not heavy, (
        f"import xerocr.{layer} charge des libs lourdes par effet de bord : {heavy}"
    )
