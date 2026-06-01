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

from fastapi import FastAPI

#: Version du **contrat de transport HTTP** (évolue indépendamment du code métier ;
#: le déterminisme produit (§12) vit dans ``RunResult``, pas dans l'API).
API_VERSION = "0"


def create_app() -> FastAPI:
    """Construit une **nouvelle** application web XerOCR.

    Appelée explicitement (CLI ``serve``, tests, Space) — jamais au chargement du
    module. Chaque appel renvoie une instance neuve (aucun état partagé global).
    """
    app = FastAPI(title="XerOCR", version=API_VERSION)

    @app.get("/health")
    def health() -> dict[str, str]:
        """Sonde de vivacité (orchestrateurs / Space). Aucune donnée sensible."""
        return {"status": "ok"}

    return app


__all__ = ["API_VERSION", "create_app"]
