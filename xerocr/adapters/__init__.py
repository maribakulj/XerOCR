"""Couche 5 — ``adapters`` : modules concrets (starter pack).

Chaque adapter implémente directement le ``Module`` Protocol (couche 4). Les
dépendances lourdes (SDK LLM, moteurs OCR) sont des extras optionnels, importés
dans le module qui les utilise — jamais ici. ``__init__`` mince, sans effet de
bord.
"""

from __future__ import annotations
