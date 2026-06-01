"""En-têtes de sécurité HTTP (couche 8).

CSP **stricte** taillée pour le rapport XerOCR : le HTML est **autonome** et ne
porte qu'un ``<style>`` inline — **aucun script, aucune ressource externe** (cf.
``reports/html.py``). Donc on bloque tout par défaut (``default-src 'none'``) et
on n'autorise que le style inline et les images self/data. Si un futur rapport
introduisait du script, **cette politique le casserait** — c'est volontaire : la
CSP est un contrat, pas un confort.
"""

from __future__ import annotations

from starlette.responses import Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

#: Politique de sécurité du contenu. ``frame-ancestors 'none'`` = anti-clickjacking ;
#: ``style-src 'unsafe-inline'`` est requis par le CSS inline du rapport (le seul
#: inline toléré) ; tout le reste (``script``/``object``/``base``) est verrouillé.
CONTENT_SECURITY_POLICY = (
    "default-src 'none'; "
    "style-src 'unsafe-inline'; "
    "img-src 'self' data:; "
    "base-uri 'none'; "
    "form-action 'none'; "
    "frame-ancestors 'none'"
)

#: En-têtes appliqués à **toute** réponse. Durcissement standard, sans état.
_HEADERS = {
    "Content-Security-Policy": CONTENT_SECURITY_POLICY,
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cross-Origin-Opener-Policy": "same-origin",
}


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
                for key, value in _HEADERS.items():
                    raw.append((key.encode("latin-1"), value.encode("latin-1")))
                message = {**message, "headers": raw}
            await send(message)

        await self._app(scope, receive, send_with_headers)


def apply_security_headers(response: Response) -> Response:
    """Variante utilitaire (tests / réponses construites à la main)."""
    for key, value in _HEADERS.items():
        response.headers[key] = value
    return response


__all__ = [
    "CONTENT_SECURITY_POLICY",
    "SecurityHeadersMiddleware",
    "apply_security_headers",
]
