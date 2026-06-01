"""Routeur des **vues de la coquille** (couche 8) : accueil · Banc d'essai · Moteurs.

Rendu **serveur** (Jinja2 + tokens/polices du design) ; le Banc d'essai ajoute
un **JS léger auto-hébergé** (EventSource pour le SSE) — toujours pas de SPA. La
page « Moteurs » est, elle, **100 % rendue serveur** (aucun JS) : elle lit l'état
des moteurs (`app.engines`) côté serveur. Le rail réserve **tous** les
emplacements de nav ; les vivants sont liés, les autres restent « à venir ».
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from xerocr.app import resolve_code_version
from xerocr.app.engines import StatusProvider
from xerocr.interfaces.web.catalog import available_reports
from xerocr.interfaces.web.i18n import normalize_lang, strings_for

#: Emplacements de nav réservés dès TU1 (ordre fixé par la spec).
_NAV_IDS = ("library", "benchmark", "reports", "segmentation", "history", "engines")
#: Vues **vivantes** : id de nav → chemin. Les autres restent « à venir ».
_LIVE_VIEWS = {"reports": "/", "benchmark": "/benchmark", "engines": "/engines"}


def _nav(
    t: dict[str, str], lang: str, active: str, metas: dict[str, str]
) -> list[dict[str, str]]:
    """Construit les entrées de nav (états active/link/soon) pour la vue ``active``."""
    items: list[dict[str, str]] = []
    for nav_id in _NAV_IDS:
        if nav_id == active:
            state = "active"
        elif nav_id in _LIVE_VIEWS:
            state = "link"
        else:
            state = "soon"
        href = (
            f"{_LIVE_VIEWS[nav_id]}?lang={lang}" if nav_id in _LIVE_VIEWS else ""
        )
        items.append(
            {
                "id": nav_id,
                "label": t[f"nav_{nav_id}"],
                "state": state,
                "href": href,
                "meta": metas.get(nav_id, ""),
            }
        )
    return items


def build_home_router(
    reports_dir: Path, templates: Jinja2Templates, *, statuses: StatusProvider
) -> APIRouter:
    """Construit le routeur des vues de la coquille (monté par ``create_app``)."""
    router = APIRouter()
    app_version = resolve_code_version()

    def _base_context(
        lang: str, active: str, metas: dict[str, str]
    ) -> dict[str, object]:
        t = strings_for(lang)
        return {
            "lang": lang,
            "t": t,
            "nav": _nav(t, lang, active, metas),
            "version": app_version,
            "view_path": _LIVE_VIEWS[active],
        }

    @router.get("/", response_class=HTMLResponse)
    def home(request: Request, lang: str = "fr") -> HTMLResponse:
        lang = normalize_lang(lang)
        names = available_reports(reports_dir)
        context = _base_context(lang, "reports", {"reports": str(len(names))})
        context["reports"] = [
            {"name": name, "href": f"/reports/{quote(name, safe='')}"}
            for name in names
        ]
        context["n_reports"] = len(names)
        return templates.TemplateResponse(request, "home.html", context)

    @router.get("/benchmark", response_class=HTMLResponse)
    def benchmark(request: Request, lang: str = "fr") -> HTMLResponse:
        lang = normalize_lang(lang)
        return templates.TemplateResponse(
            request, "benchmark.html", _base_context(lang, "benchmark", {})
        )

    @router.get("/engines", response_class=HTMLResponse)
    def engines(request: Request, lang: str = "fr") -> HTMLResponse:
        lang = normalize_lang(lang)
        engine_list = statuses()
        n_ready = sum(1 for s in engine_list if s.available)
        context = _base_context(lang, "engines", {"engines": str(n_ready)})
        context["engines"] = engine_list
        context["n_ready"] = n_ready
        context["n_engines"] = len(engine_list)
        return templates.TemplateResponse(request, "engines.html", context)

    return router


__all__ = ["build_home_router"]

