"""Routeur d'accueil : shell de pilotage **mince** (couche 8).

Pas de SPA lourde (anti-pattern hérité, D-β) : une page HTML minimale qui
liste les rapports et y mène. Les noms sont **échappés** (HTML) et **URL-encodés**
(chemin) — défense XSS de base sur des stems venant du système de fichiers.
"""

from __future__ import annotations

from html import escape
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from xerocr.interfaces.web.catalog import available_reports


def build_home_router(reports_dir: Path) -> APIRouter:
    """Construit le routeur d'accueil (monté par ``create_app``)."""
    router = APIRouter()

    @router.get("/", response_class=HTMLResponse)
    def home() -> str:
        return _render_home(available_reports(reports_dir))

    return router


def _render_home(names: list[str]) -> str:
    items = "".join(
        f'<li><a href="/reports/{escape(quote(name), quote=True)}">'
        f"{escape(name)}</a></li>\n"
        for name in names
    ) or "<li>(aucun rapport)</li>\n"
    return (
        '<!DOCTYPE html>\n<html lang="fr"><head><meta charset="utf-8">'
        "<title>XerOCR — rapports</title></head><body>\n"
        "<h1>XerOCR — rapports</h1>\n"
        f"<ul>\n{items}</ul>\n</body></html>\n"
    )


__all__ = ["build_home_router"]
