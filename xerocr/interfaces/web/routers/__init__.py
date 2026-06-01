"""Routeurs HTTP (couche 8) — chacun est une **fonction builder**.

``no_side_effect_imports`` interdit ``APIRouter()`` au niveau module (fabrique à
effet de bord) : un routeur se construit donc **dans une fonction**
(``build_*_router(...) -> APIRouter``) appelée par ``create_app``. Mince, sans
effet de bord à l'import.
"""

from __future__ import annotations
