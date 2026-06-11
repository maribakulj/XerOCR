"""Routeur vitrine : liste des rapports + rendu HTML d'un ``RunResult`` sauvé."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from xerocr.app.report_images import build_thumbnails
from xerocr.app.results import RunResultError, load_run_result
from xerocr.app.security import PathSecurityError
from xerocr.interfaces.web.catalog import available_reports, resolve_report
from xerocr.reports import default_report_renderer


def build_reports_router(reports_dir: Path) -> APIRouter:
    """Construit le routeur des rapports (monté par ``create_app``)."""
    router = APIRouter()

    @router.get("/api/reports")
    def list_reports() -> dict[str, list[str]]:
        return {"reports": available_reports(reports_dir)}

    @router.get("/reports/{name}", response_class=HTMLResponse)
    def get_report(name: str, lang: str = "fr") -> str:
        try:
            path = resolve_report(reports_dir, name)
        except PathSecurityError as exc:
            # introuvable OU hors zone → même réponse (pas de fuite).
            raise HTTPException(status_code=404, detail="rapport introuvable") from exc
        try:
            result = load_run_result(path)
        except RunResultError as exc:
            raise HTTPException(status_code=500, detail="rapport illisible") from exc
        # Langue du glossaire pédagogique (fr par défaut ; en seul autre porté).
        report_lang = "en" if lang == "en" else "fr"
        return default_report_renderer().render(
            result,
            title=f"XerOCR — {result.manifest.run_id}",
            lang=report_lang,
            images=build_thumbnails(result),
        )

    return router


__all__ = ["build_reports_router"]
