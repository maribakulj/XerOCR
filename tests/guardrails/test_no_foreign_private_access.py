"""Garde-fou : pas de **nouvel** accès à un attribut privé d'une lib tierce.

L'épinglage IP anti-DNS-rebinding doit toucher des internes de ``httpx`` /
``httpcore`` (``transport._pool``, ``pool._network_backend``) faute d'API
publique. C'est **toléré en un seul endroit** (allowlist) et gardé bruyamment
(un ``isinstance`` échoue si la forme interne change). Ce test verrouille ce
couplage fragile : il interdit qu'il **se propage** ailleurs dans ``xerocr/``.

Verrou **passant** (pas ``xfail``) : il fige l'exception acceptée et bloque
toute nouvelle occurrence.
"""

from __future__ import annotations

import ast
from pathlib import Path

XEROCR = Path(__file__).resolve().parents[2] / "xerocr"

#: Attributs privés de libs tierces accédés faute d'API publique.
_FOREIGN_PRIVATE = frozenset({"_pool", "_network_backend"})

#: Seul fichier autorisé à toucher ces internes (épinglage IP anti-rebinding).
_ALLOWLIST = frozenset({"adapters/corpus/_http.py"})


def _foreign_private_hits() -> dict[str, list[str]]:
    hits: dict[str, list[str]] = {}
    for path in XEROCR.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        found = [
            f"{node.attr} L{node.lineno}"
            for node in ast.walk(tree)
            if isinstance(node, ast.Attribute) and node.attr in _FOREIGN_PRIVATE
        ]
        if found:
            hits[path.relative_to(XEROCR).as_posix()] = found
    return hits


def test_foreign_private_access_confined_to_allowlist() -> None:
    offenders = {
        rel: hits
        for rel, hits in _foreign_private_hits().items()
        if rel not in _ALLOWLIST
    }
    assert not offenders, (
        "Accès à un attribut privé de lib tierce hors allowlist "
        f"(couplage d'implémentation à proscrire) : {offenders}"
    )
