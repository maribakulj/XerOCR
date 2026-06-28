"""Routeur vitrine : liste des rapports + rendu HTML d'un ``RunResult`` sauvé."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, Response

from cinoc.app.alto_store import AltoStore
from cinoc.app.report_images import (
    build_facsimiles,
    build_report_zip,
    build_thumbnails,
)
from cinoc.app.results import RunResultError, load_run_result
from cinoc.app.security import PathSecurityError
from cinoc.interfaces.web.catalog import available_reports, resolve_report
from cinoc.reports import default_report_renderer


def build_reports_router(
    reports_dir: Path, *, alto_store: AltoStore | None = None
) -> APIRouter:
    """Construit le routeur des rapports (monté par ``create_app``).

    ``alto_store`` (optionnel) sert les exports ALTO persistés d'un run via
    ``/reports/{name}/alto.zip`` ; absent → l'endpoint répond ``404``.
    """
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
            title=f"Cinoc — {result.manifest.run_id}",
            lang=report_lang,
            images=build_thumbnails(result),
            facsimiles=build_facsimiles(result),
        )

    @router.get("/reports/{name}/bundle.zip")
    def get_report_bundle(name: str, lang: str = "fr") -> Response:
        """Télécharge le rapport en **bundle dossier zippé** (saveur dossier) :
        ``report.html`` + ``report-assets/`` (images réelles, hors-ligne). Rendu
        à la demande depuis le ``RunResult`` sauvé — rien de pré-écrit."""
        try:
            path = resolve_report(reports_dir, name)
        except PathSecurityError as exc:
            raise HTTPException(status_code=404, detail="rapport introuvable") from exc
        try:
            result = load_run_result(path)
        except RunResultError as exc:
            raise HTTPException(status_code=500, detail="rapport illisible") from exc
        report_lang = "en" if lang == "en" else "fr"
        data = build_report_zip(
            result,
            render=default_report_renderer().render,
            title=f"Cinoc — {result.manifest.run_id}",
            lang=report_lang,
        )
        # ``name`` est déjà validé (resolve_report) → sûr en nom de fichier.
        return Response(
            content=data,
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="{name}.zip"'
            },
        )

    @router.get("/reports/{name}/alto.zip")
    def get_alto_archive(name: str) -> Response:
        """Télécharge les **exports ALTO XML** du run (un fichier par document),
        empaquetés en ZIP — la forme ré-importable dans un outil de relecture
        (eScriptorium, Transkribus). ``404`` si le run n'a produit aucun ALTO
        (concurrent sans l'option *Exporter l'ALTO*)."""
        try:
            resolve_report(reports_dir, name)
        except PathSecurityError as exc:
            raise HTTPException(status_code=404, detail="rapport introuvable") from exc
        data = alto_store.archive(name) if alto_store is not None else None
        if data is None:
            raise HTTPException(
                status_code=404, detail="aucun export ALTO pour ce run"
            )
        # ``name`` est validé (resolve_report) → sûr en nom de fichier.
        return Response(
            content=data,
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="{name}-alto.zip"'
            },
        )

    return router


__all__ = ["build_reports_router"]
