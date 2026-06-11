"""Routeur des **vues de la coquille** (couche 8) : accueil · Banc d'essai · Moteurs.

Rendu **serveur** (Jinja2 + tokens/polices du design) ; le Banc d'essai ajoute
un **JS léger auto-hébergé** (EventSource pour le SSE) — toujours pas de SPA. La
page « Moteurs » est, elle, **100 % rendue serveur** (aucun JS) : elle lit l'état
des moteurs (`app.engines`) côté serveur. Le rail réserve **tous** les
emplacements de nav ; les vivants sont liés, les autres restent « à venir ».
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from xerocr.adapters.corpus.htr_united import HTRUnitedCatalogue, fetch_catalogue
from xerocr.adapters.corpus.huggingface import HuggingFaceCatalogue, HuggingFaceDataset
from xerocr.adapters.storage.history_store import HistoryRecord, HistoryStore
from xerocr.app import resolve_code_version
from xerocr.app.corpus_upload import CorpusStore
from xerocr.app.engines import (
    StatusProvider,
    curated_prompts,
    installed_mistral_models,
    installed_ollama_models,
)
from xerocr.app.run_planning import benchmark_engine_catalog
from xerocr.app.segmentation import SegmentationStore
from xerocr.formats.text import NORMALIZATION_PROFILES
from xerocr.interfaces.web._cache import TTLCache
from xerocr.interfaces.web.catalog import available_reports
from xerocr.interfaces.web.i18n import normalize_lang, strings_for
from xerocr.interfaces.web.sparkline import sparkline_svg
from xerocr.reports.layout_svg import layout_to_svg

logger = logging.getLogger(__name__)

#: TTL des catalogues de découverte (F1) : la page Bibliothèque ne refetch plus
#: à chaque chargement. Fenêtre courte — la fraîcheur prime sur le cache.
_CATALOGUE_TTL_SECONDS = 300.0

#: Vues **vivantes** : id de nav → chemin.
_VIEW_PATHS = {
    "library": "/library",
    "reports": "/",
    "benchmark": "/benchmark",
    "segmentation": "/segmentation",
    "history": "/history",
    "engines": "/engines",
}
_PRIMARY_NAV_IDS = ("library", "benchmark", "reports", "history")
_SECONDARY_NAV_IDS = ("segmentation", "engines")


def _nav_items(
    ids: tuple[str, ...],
    t: dict[str, str],
    lang: str,
    active: str,
    metas: dict[str, str],
) -> list[dict[str, str]]:
    """Construit les entrées de navigation pour un groupe d'identifiants."""
    items: list[dict[str, str]] = []
    for nav_id in ids:
        items.append(
            {
                "id": nav_id,
                "label": t[f"nav_{nav_id}"],
                "state": "active" if nav_id == active else "link",
                "href": f"{_VIEW_PATHS[nav_id]}?lang={lang}",
                "meta": metas.get(nav_id, ""),
            }
        )
    return items


def _corpora_summaries(corpus_store: CorpusStore | None) -> list[dict[str, object]]:
    """Résumés des corpus enregistrés pour l'UI Bibliothèque/Benchmark."""
    if corpus_store is None:
        return []
    summaries: list[dict[str, object]] = []
    for cid, spec in corpus_store.list_corpora():
        docs = spec.documents
        summaries.append(
            {
                "id": cid,
                "name": spec.name,
                "n_documents": len(docs),
                "n_ground_truth": sum(1 for doc in docs if doc.ground_truths),
                "preview_ids": [doc.id for doc in docs[:3]],
                "source": spec.metadata.get("source", ""),
                "language": spec.metadata.get("language", ""),
            }
        )
    return summaries


def _cer_trends(
    history_store: HistoryStore, records: tuple[HistoryRecord, ...]
) -> list[dict[str, object]]:
    """Sparklines CER : une série chronologique par ``(pipeline, vue)``.

    Données réelles du store (``history``) — aucune ré-agrégation. Ordre stable
    (première apparition dans ``records``, plus récent d'abord).
    """
    seen: set[tuple[str, str]] = set()
    trends: list[dict[str, object]] = []
    for record in records:
        if record.metric != "cer":
            continue
        key = (record.pipeline, record.view)
        if key in seen:
            continue
        seen.add(key)
        series = history_store.history(record.pipeline, record.view, "cer")
        values = [s.value for s in series]
        trends.append(
            {
                "pipeline": record.pipeline,
                "view": record.view,
                "latest": values[-1] if values else None,
                "n": len(values),
                "svg": sparkline_svg(values),
            }
        )
    return trends


def build_home_router(
    reports_dir: Path,
    templates: Jinja2Templates,
    *,
    statuses: StatusProvider,
    segmenters: StatusProvider,
    history_store: HistoryStore,
    segmentation_store: SegmentationStore,
    demo_segmentation_id: str,
    corpus_store: CorpusStore | None = None,
    public_mode: bool = False,
) -> APIRouter:
    """Construit le routeur des vues de la coquille (monté par ``create_app``)."""
    router = APIRouter()
    app_version = resolve_code_version()
    # Caches TTL partagés par toutes les requêtes /library (F1) : fin du fetch
    # réseau à chaque chargement. HTR-United (index, indépendant de la requête)
    # et HuggingFace (par requête ``q``).
    htr_cache: TTLCache[str, HTRUnitedCatalogue] = TTLCache(_CATALOGUE_TTL_SECONDS)
    hf_cache: TTLCache[str, tuple[HuggingFaceDataset, ...]] = TTLCache(
        _CATALOGUE_TTL_SECONDS
    )

    def _base_context(
        lang: str, active: str, metas: dict[str, str]
    ) -> dict[str, object]:
        t = strings_for(lang)
        engine_list = tuple(statuses())
        n_ready = sum(1 for status in engine_list if status.available)
        engine_labels = [status.label for status in engine_list if status.available][:3]
        return {
            "lang": lang,
            "t": t,
            "primary_nav": _nav_items(_PRIMARY_NAV_IDS, t, lang, active, metas),
            "secondary_nav": _nav_items(_SECONDARY_NAV_IDS, t, lang, active, metas),
            "version": app_version,
            "view_path": _VIEW_PATHS[active],
            "system_pipeline": {
                "ready": n_ready,
                "total": len(engine_list),
                "labels": engine_labels,
            },
            # Les imports distants fetchent côté serveur → masqués en mode public
            # (l'endpoint les refuse de toute façon : 403).
            "public_mode": public_mode,
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
        context = _base_context(lang, "benchmark", {})
        # Catalogue moteurs par rôle (ocr/llm/vlm) : options rendues **serveur**
        # (testables) ; le composeur JS ne fait qu'assembler les concurrents.
        context["catalog"] = benchmark_engine_catalog(statuses())
        # Modèles ollama installés → menu déroulant (au lieu d'une saisie à
        # l'aveugle). Best-effort : serveur éteint → liste vide, saisie libre.
        context["ollama_models"] = installed_ollama_models()
        # Modèles Mistral disponibles pour la clé → menu déroulant dynamique.
        context["mistral_models"] = installed_mistral_models()
        # Le corpus est préparé dans la Bibliothèque ; ici on le sélectionne.
        context["corpora"] = _corpora_summaries(corpus_store)
        # Profils de normalisation lus **dynamiquement** depuis formats/text
        # (jamais figés en dur) ; le profil choisi alimente la vue d'évaluation.
        context["profiles"] = [
            {"name": p.name, "description": p.description}
            for p in NORMALIZATION_PROFILES.values()
        ]
        # Prompts curés par période (lus dynamiquement) → menu déroulant ; le
        # texte libre du formulaire reste prioritaire (résolu au plan).
        context["curated_prompts"] = list(curated_prompts())
        # Segmenteur (catégorie séparée) : son statut alimente le bouton
        # « Segmenter » — désactivé + motif si l'extra [segment] manque.
        context["segmenter"] = next(
            (s for s in segmenters() if s.kind == "pp_doclayout"), None
        )
        return templates.TemplateResponse(request, "benchmark.html", context)

    @router.get("/segmentation", response_class=HTMLResponse)
    def segmentation(request: Request, lang: str = "fr") -> HTMLResponse:
        lang = normalize_lang(lang)
        # Affiche le **run le plus récent** persisté par le sink (run réel >
        # graine de démo) ; à défaut, la démo. Même store que le runner → un
        # vrai run de segmentation apparaît ici sans second chemin.
        current_id = segmentation_store.latest() or demo_segmentation_id
        layout = segmentation_store.get_layout(current_id)
        page = layout.pages[0] if layout and layout.pages else None
        regions = page.regions if page else ()
        image_href = f"/api/segmentation/{quote(current_id, safe='')}/image"
        metas = {"segmentation": str(len(regions))}
        context = _base_context(lang, "segmentation", metas)
        context["svg"] = layout_to_svg(layout, image_href=image_href) if layout else ""
        context["regions"] = regions
        context["n_regions"] = len(regions)
        return templates.TemplateResponse(request, "segmentation.html", context)

    @router.get("/library", response_class=HTMLResponse)
    def library(request: Request, lang: str = "fr", q: str = "") -> HTMLResponse:
        lang = normalize_lang(lang)
        # Découverte best-effort : HTR-United (réseau → repli démo `is_demo`),
        # HuggingFace (socle de référence + API best-effort). Aucun blocage si
        # hors-ligne. Catalogues mis en cache TTL (F1) → pas de refetch par
        # chargement ; ``.search(q)`` de HTR-United reste en mémoire (gratuit).
        catalogue = htr_cache.get_or_compute("htr_united", fetch_catalogue)
        htr = catalogue.search(q) if q else catalogue.entries
        hf = hf_cache.get_or_compute(q, lambda: HuggingFaceCatalogue().search(q))
        corpora = _corpora_summaries(corpus_store)
        context = _base_context(lang, "library", {"library": str(len(htr) + len(hf))})
        context["query"] = q
        context["corpora"] = corpora
        context["htr_entries"] = htr
        context["htr_is_demo"] = catalogue.is_demo
        context["hf_datasets"] = hf
        context["n_corpora"] = len(corpora)
        context["n_htr"] = len(htr)
        context["n_hf"] = len(hf)
        context["n_pages"] = sum(int(c["n_documents"]) for c in corpora)  # type: ignore[call-overload]
        return templates.TemplateResponse(request, "library.html", context)

    @router.get("/history", response_class=HTMLResponse)
    def history(request: Request, lang: str = "fr") -> HTMLResponse:
        lang = normalize_lang(lang)
        try:
            records = history_store.all_records()
            # Régressions pour chaque (vue, métrique) enregistrée : lecture du
            # store, pas de ré-agrégation (cf. CLAUDE §8.3).
            pairs = sorted({(r.view, r.metric) for r in records})
            regressions = [
                reg
                for view, metric in pairs
                for reg in history_store.regressions(view, metric)
            ]
            trends = _cer_trends(history_store, records)
        except sqlite3.Error as exc:
            # Stockage indisponible (ex. dossier non inscriptible sur un Space) :
            # la page se dégrade au lieu de renvoyer une 500.
            logger.warning("[history] historique indisponible : %s", exc)
            records, regressions, trends = (), [], []
        context = _base_context(lang, "history", {"history": str(len(records))})
        context["records"] = records
        context["regressions"] = regressions
        context["trends"] = trends
        return templates.TemplateResponse(request, "history.html", context)

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
