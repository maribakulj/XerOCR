"""Couche 8 — ``interfaces`` : transport (CLI). Feuille de l'architecture.

``__init__`` mince, sans effet de bord (pas de singleton à l'import — la CLI
construit tout dans ``main``).
"""

from __future__ import annotations

from xerocr.interfaces.cli import main

__all__ = ["main"]
