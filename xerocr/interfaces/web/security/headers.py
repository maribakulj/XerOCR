"""En-têtes de sécurité HTTP (couche 8).

CSP **stricte** : on bloque tout par défaut (``default-src 'none'``) et on
n'ouvre que le strict nécessaire, **toujours en `self`** (aucun CDN). Le
**rapport** reste autonome (``<style>`` inline + images self/data — cf.
``reports/html.py``). La **coquille** sert sa feuille de style et ses polices
auto-hébergées (``style-src``/``font-src 'self'``) ; depuis le lanceur
interactif (TU2.f), elle sert aussi un **JS auto-hébergé** (``script-src
'self'`` — jamais ``'unsafe-inline'``, jamais d'externe) qui parle aux API et
s'abonne au SSE (``connect-src 'self'``). ``form-action 'none'`` (on pilote en
``fetch``, pas en soumission de formulaire). Tout le reste tombe sur
``default-src 'none'`` — un script inline ou une origine tierce serait bloqué,
c'est volontaire : la CSP est un contrat.

**Adaptation HuggingFace Space.** Un Space est servi dans une ``<iframe>`` côté
``huggingface.co`` / ``*.hf.space``. Or ``frame-ancestors 'none'`` +
``X-Frame-Options: DENY`` y rendent la vitrine **invisible** (page blanche bien
que le serveur réponde ``200`` — c'est exactement le « ne peut pas afficher la
page dans un cadre » des navigateurs). On détecte le Space via ``SPACE_ID``
(injecté par HF) et on bascule ``frame-ancestors`` sur les origines du Hub, en
**omettant** ``X-Frame-Options`` (qui a priorité absolue sur ``frame-ancestors``
dans les vieux navigateurs → annulerait la permission d'embed). Hors Space
(local / institutionnel), on garde le **verrou total** : ``'none'`` + ``DENY``.
"""

from __future__ import annotations

import os

from starlette.responses import Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

#: CSP de base — tout sauf ``frame-ancestors`` (composée dynamiquement selon le
#: déploiement par :func:`get_csp_policy`). ``style-src 'unsafe-inline'`` est
#: requis par le CSS inline du rapport (le seul inline toléré) ; tout le reste
#: (``script``/``object``/``base``) tombe sur ``default-src 'none'``, verrouillé.
_CSP_BASE = (
    "default-src 'none'; "
    "script-src 'self'; "
    "style-src 'self' 'unsafe-inline'; "
    "font-src 'self'; "
    "img-src 'self' data:; "
    "connect-src 'self'; "
    "base-uri 'none'; "
    "form-action 'none'"
)

#: Origines autorisées à embarquer la vitrine quand on tourne dans un HF Space.
#: ``huggingface.co`` rend la page parente ; ``*.hf.space`` expose le conteneur
#: (rendus directs / liens partageables).
_HF_FRAME_ANCESTORS = "'self' https://huggingface.co https://*.hf.space"


def is_huggingface_space() -> bool:
    """Vrai si l'instance tourne dans un HuggingFace Space.

    HF injecte ``SPACE_ID`` (au format ``user/space``) dans l'environnement du
    conteneur — marqueur canonique documenté, présent quel que soit le SDK
    (Docker ici). On l'utilise pour adapter ``frame-ancestors`` : sans ça, la
    vitrine est invisible dans l'iframe du Hub.
    """
    return bool(os.environ.get("SPACE_ID", "").strip())


def _frame_ancestors_directive() -> str:
    """Directive ``frame-ancestors`` adaptée au déploiement détecté.

    - Local / institutionnel : ``'none'`` (aucun embed possible).
    - HuggingFace Space : autorise ``huggingface.co`` et ``*.hf.space`` pour que
      la vitrine s'affiche dans l'iframe du Space sans tomber en page blanche.
    """
    if is_huggingface_space():
        return f"frame-ancestors {_HF_FRAME_ANCESTORS}"
    return "frame-ancestors 'none'"


#: CSP locale/institutionnelle (verrou total anti-cadrage). Exposée comme valeur
#: par défaut et attendue **hors** Space ; en Space, :func:`get_csp_policy` la
#: recompose avec un ``frame-ancestors`` permissif.
CONTENT_SECURITY_POLICY = f"{_CSP_BASE}; frame-ancestors 'none'"


def get_csp_policy() -> str:
    """CSP à appliquer : base + ``frame-ancestors`` selon l'environnement."""
    return f"{_CSP_BASE}; {_frame_ancestors_directive()}"


def security_headers() -> dict[str, str]:
    """En-têtes de sécurité de la réponse, **calculés selon le déploiement**.

    ``X-Frame-Options: DENY`` est sciemment **omis sur HF Space** : ce header a
    priorité absolue sur ``frame-ancestors`` (et sert de fallback quand le
    navigateur ignore la CSP), donc un ``DENY`` annulerait la permission d'embed
    du Hub. Le contrôle d'embed est alors entièrement délégué à
    ``frame-ancestors``.
    """
    headers = {
        "Content-Security-Policy": get_csp_policy(),
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "no-referrer",
        "Cross-Origin-Opener-Policy": "same-origin",
    }
    if not is_huggingface_space():
        headers["X-Frame-Options"] = "DENY"
    return headers


class SecurityHeadersMiddleware:
    """Ajoute les en-têtes de sécurité à chaque réponse (ASGI pur, sans état)."""

    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                raw = list(message.get("headers", []))
                for key, value in security_headers().items():
                    raw.append((key.encode("latin-1"), value.encode("latin-1")))
                message = {**message, "headers": raw}
            await send(message)

        await self._app(scope, receive, send_with_headers)


def apply_security_headers(response: Response) -> Response:
    """Variante utilitaire (tests / réponses construites à la main)."""
    for key, value in security_headers().items():
        response.headers[key] = value
    return response


__all__ = [
    "CONTENT_SECURITY_POLICY",
    "SecurityHeadersMiddleware",
    "apply_security_headers",
    "get_csp_policy",
    "is_huggingface_space",
    "security_headers",
]
