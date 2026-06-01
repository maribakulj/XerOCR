"""Défense CSRF des routes mutantes (couche 8).

Stratégie **custom-header** : toute requête d'écriture (``POST``) doit porter
l'en-tête ``X-XeroCR-CSRF: 1``. Un navigateur **ne peut pas** ajouter un en-tête
personnalisé sur une requête *cross-site* « simple » (formulaire, image…) ; le
faire exige ``fetch`` + un *preflight* CORS, que la vitrine **n'autorise pas**.
Donc exiger cet en-tête bloque le forçage cross-site sans cookie ni token de
session — adapté à une API JSON same-origin (cf. OWASP CSRF, defense « custom
request header »).

Volontairement minimal pour TU2.a (lanceur same-origin). Un token signé par
session arrivera si/quand des cookies d'auth existent.
"""

from __future__ import annotations

from fastapi import HTTPException, Request

CSRF_HEADER = "X-XeroCR-CSRF"
_EXPECTED = "1"


def csrf_protect(request: Request) -> None:
    """Dépendance FastAPI : rejette (403) une écriture sans l'en-tête attendu."""
    if request.headers.get(CSRF_HEADER) != _EXPECTED:
        raise HTTPException(
            status_code=403,
            detail="en-tête CSRF requis (X-XeroCR-CSRF).",
        )


__all__ = ["CSRF_HEADER", "csrf_protect"]
