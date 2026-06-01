"""Sécurité HTTP (couche 8) — un seul package (≠ 7 modules épars de la source).

T4c (vitrine en ligne, lecture seule) n'a besoin que de deux protections : des
**en-têtes de sécurité** (CSP/anti-sniff/anti-cadrage) et un **limiteur de débit**.
CSRF, quotas d'upload et **mode public** (barrière au code tiers in-process)
arrivent **avec leur consommateur** — le lanceur BYO-key (T4d) — pas avant.
"""

from __future__ import annotations

from xerocr.interfaces.web.security.headers import (
    CONTENT_SECURITY_POLICY,
    SecurityHeadersMiddleware,
)
from xerocr.interfaces.web.security.rate_limit import RateLimitMiddleware

__all__ = [
    "CONTENT_SECURITY_POLICY",
    "RateLimitMiddleware",
    "SecurityHeadersMiddleware",
]
