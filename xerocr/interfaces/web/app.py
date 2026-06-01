"""Factory de l'application web (couche 8) — ``create_app()``.

L'app FastAPI est construite **à la demande**, jamais à l'import : pas de
``app = FastAPI()`` au niveau module (interdit par ``no_side_effect_imports`` —
``FastAPI``/``APIRouter`` sont des fabriques à effet de bord). uvicorn et le
HF Space reçoivent la **factory** (``--factory`` / callable), jamais un singleton
de module. Conséquence d'archi : un routeur est une **fonction qui construit et
renvoie un ``APIRouter``** (l'appel ``APIRouter()`` vit dans la fonction), montée
par ``create_app`` — voir les sous-tranches T4b+.

T4a pose la coquille : la factory + une route de santé. La surface (routers
benchmark/corpus, package ``security/``, SSE, annulation) se remplit ensuite,
une sous-tranche à la fois.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from xerocr.adapters.storage import JobStore
from xerocr.app import resolve_code_version
from xerocr.app.corpus_upload import CorpusStore
from xerocr.app.engines import engine_statuses
from xerocr.app.jobs import JobRunner
from xerocr.app.modules.registry import ModuleRegistry, register_default_modules
from xerocr.interfaces.web.routers.corpus import build_corpus_router
from xerocr.interfaces.web.routers.engines import build_engines_router
from xerocr.interfaces.web.routers.home import build_home_router
from xerocr.interfaces.web.routers.reports import build_reports_router
from xerocr.interfaces.web.routers.runs import build_runs_router
from xerocr.interfaces.web.security import (
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
)

#: Assets de la coquille (CSS + polices auto-hébergées) et gabarits Jinja2,
#: livrés **dans le paquet** (cf. ``[tool.setuptools.package-data]``) pour être
#: présents aussi bien en source qu'une fois ``pip install``é (Space/CI).
_WEB_DIR = Path(__file__).resolve().parent
_STATIC_DIR = _WEB_DIR / "static"
_TEMPLATES_DIR = _WEB_DIR / "templates"

#: Version du **contrat de transport HTTP** (évolue indépendamment du code métier ;
#: le déterminisme produit (§12) vit dans ``RunResult``, pas dans l'API).
API_VERSION = "0"

#: Dossier des rapports (``RunResult`` JSON) servis par la vitrine, surchargé par
#: ce var d'env (utile au Space) si ``create_app(reports_dir=...)`` ne le fixe pas.
REPORTS_DIR_ENV = "XEROCR_REPORTS_DIR"

#: Mode public (exposition sans secrets) : refuse les moteurs cloud porteurs de
#: clé. Activé par cet env (truthy) si ``create_app(public_mode=...)`` ne tranche pas.
PUBLIC_MODE_ENV = "XEROCR_PUBLIC_MODE"


def _resolve_reports_dir(reports_dir: Path | str | None) -> Path:
    """Argument explicite > variable d'env > défaut ``./reports``."""
    if reports_dir is not None:
        return Path(reports_dir)
    env = os.environ.get(REPORTS_DIR_ENV)
    return Path(env) if env else Path("reports")


def _resolve_uploads_dir(uploads_dir: Path | str | None) -> Path:
    """Dossier des corpus uploadés : argument explicite > dossier temporaire neuf.

    Éphémère par défaut (entrées de travail ; la persistance des résultats = TU3).
    """
    if uploads_dir is not None:
        return Path(uploads_dir)
    return Path(tempfile.mkdtemp(prefix="xerocr-uploads-"))


def _resolve_public_mode(public_mode: bool | None) -> bool:
    """Argument explicite > env (``1``/``true``/``yes``) > défaut ``False``."""
    if public_mode is not None:
        return public_mode
    return os.environ.get(PUBLIC_MODE_ENV, "").strip().lower() in {"1", "true", "yes"}


def create_app(
    *,
    reports_dir: Path | str | None = None,
    uploads_dir: Path | str | None = None,
    rate_limit: int = 60,
    public_mode: bool | None = None,
) -> FastAPI:
    """Construit une **nouvelle** application web XerOCR.

    Appelée explicitement (CLI ``serve``, tests, Space) — jamais au chargement du
    module. Chaque appel renvoie une instance neuve (aucun état partagé global).
    Les routeurs sont des **fonctions builder** montées ici (jamais d'``APIRouter``
    au niveau module — gate ``no_side_effect_imports``). Toute réponse porte les
    en-têtes de sécurité (CSP stricte) ; le débit par IP est borné (``429``). Le
    **lanceur** (``/api/runs``) exécute les runs en arrière-plan via un
    ``JobRunner`` ; en ``public_mode`` les moteurs cloud sont refusés.
    """
    if rate_limit < 1:
        raise ValueError("create_app : rate_limit doit être >= 1.")
    catalog_dir = _resolve_reports_dir(reports_dir)
    is_public = _resolve_public_mode(public_mode)
    app = FastAPI(title="XerOCR", version=API_VERSION)
    # Ordre : le limiteur (ajouté en dernier) s'exécute en premier → il borne
    # avant tout traitement ; les en-têtes habillent la réponse qui remonte.
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RateLimitMiddleware, max_requests=rate_limit)

    @app.get("/health")
    def health() -> dict[str, str]:
        """Sonde de vivacité (orchestrateurs / Space). Aucune donnée sensible."""
        return {"status": "ok"}

    # Assets servis depuis notre origine (``font-src``/``style-src 'self'``) —
    # aucune dépendance CDN en prod (cf. CSP, ``security/headers.py``).
    app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")
    templates = Jinja2Templates(directory=_TEMPLATES_DIR)

    # Lanceur : un registre + un store + un runner par application (état du
    # processus serveur, pas un singleton de module → factory respectée).
    registry = ModuleRegistry()
    register_default_modules(registry)
    runner = JobRunner(
        store=JobStore(),
        registry=registry,
        reports_dir=catalog_dir,
        code_version=resolve_code_version(),
    )
    corpus_store = CorpusStore(_resolve_uploads_dir(uploads_dir))

    app.include_router(build_home_router(catalog_dir, templates))
    app.include_router(build_reports_router(catalog_dir))
    app.include_router(build_runs_router(runner, public_mode=is_public))
    app.include_router(
        build_engines_router(lambda: engine_statuses(public_mode=is_public))
    )
    app.include_router(build_corpus_router(corpus_store))
    return app


__all__ = ["API_VERSION", "PUBLIC_MODE_ENV", "REPORTS_DIR_ENV", "create_app"]
