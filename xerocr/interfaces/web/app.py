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
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from xerocr.interfaces.web.routers.home import build_home_router
from xerocr.interfaces.web.routers.reports import build_reports_router
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


def _resolve_reports_dir(reports_dir: Path | str | None) -> Path:
    """Argument explicite > variable d'env > défaut ``./reports``."""
    if reports_dir is not None:
        return Path(reports_dir)
    env = os.environ.get(REPORTS_DIR_ENV)
    return Path(env) if env else Path("reports")


def create_app(
    *,
    reports_dir: Path | str | None = None,
    rate_limit: int = 60,
) -> FastAPI:
    """Construit une **nouvelle** application web XerOCR.

    Appelée explicitement (CLI ``serve``, tests, Space) — jamais au chargement du
    module. Chaque appel renvoie une instance neuve (aucun état partagé global).
    Les routeurs sont des **fonctions builder** montées ici (jamais d'``APIRouter``
    au niveau module — gate ``no_side_effect_imports``). Toute réponse porte les
    en-têtes de sécurité (CSP stricte) ; le débit par IP est borné (``429``).
    """
    if rate_limit < 1:
        raise ValueError("create_app : rate_limit doit être >= 1.")
    catalog_dir = _resolve_reports_dir(reports_dir)
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

    app.include_router(build_home_router(catalog_dir, templates))
    app.include_router(build_reports_router(catalog_dir))
    return app


__all__ = ["API_VERSION", "REPORTS_DIR_ENV", "create_app"]
