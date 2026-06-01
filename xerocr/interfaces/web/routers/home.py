"""Routeur d'accueil : la **coquille de pilotage** au design (couche 8).

Rendu **serveur** (Jinja2 + tokens/polices du design, JS zéro) — pas de SPA
(anti-pattern hérité, D-β). La page pose le chrome complet (rail à pilules,
hero, panneau système, bascule FR/EN) et **réserve tous les emplacements de
nav** — Bibliothèque · Banc d'essai · Rapports · Segmentation · Historique ·
Moteurs — même si seul « Rapports » est fonctionnel à cette tranche (TU1). Les
autres sont des placeholders honnêtes (badge « à venir »), sans fausse donnée.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from xerocr.interfaces.web.catalog import available_reports
from xerocr.interfaces.web.i18n import normalize_lang, strings_for

#: Emplacements de nav réservés dès TU1 (ordre fixé par la spec). Seul
#: ``reports`` est fonctionnel ; les autres arrivent à leurs tranches (TU2+).
_NAV_IDS = ("library", "benchmark", "reports", "segmentation", "history", "engines")
_ACTIVE_NAV = "reports"


def _resolve_version() -> str:
    try:
        return version("xerocr")
    except PackageNotFoundError:  # pragma: no cover (paquet non installé)
        from xerocr.domain._version_fallback import FALLBACK_VERSION

        return FALLBACK_VERSION


def build_home_router(reports_dir: Path, templates: Jinja2Templates) -> APIRouter:
    """Construit le routeur d'accueil (monté par ``create_app``)."""
    router = APIRouter()
    app_version = _resolve_version()

    @router.get("/", response_class=HTMLResponse)
    def home(request: Request, lang: str = "fr") -> HTMLResponse:
        lang = normalize_lang(lang)
        t = strings_for(lang)
        names = available_reports(reports_dir)
        nav = [
            {
                "id": nav_id,
                "label": t[f"nav_{nav_id}"],
                "active": nav_id == _ACTIVE_NAV,
                "meta": str(len(names)) if nav_id == _ACTIVE_NAV else "",
                "href": f"/?lang={lang}",
            }
            for nav_id in _NAV_IDS
        ]
        reports = [
            {"name": name, "href": f"/reports/{quote(name, safe='')}"}
            for name in names
        ]
        return templates.TemplateResponse(
            request,
            "shell.html",
            {
                "lang": lang,
                "t": t,
                "nav": nav,
                "reports": reports,
                "n_reports": len(names),
                "version": app_version,
            },
        )

    return router


__all__ = ["build_home_router"]
