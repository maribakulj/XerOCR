"""Assemblage HTML **autonome** + échappement (couche 7).

Produit un document autonome (CSS inline, **aucune dépendance CDN/JS**), donc
hébergeable tel quel et **déterministe** (cf. plan §Cibles de distribution). Les
**données** sont échappées via ``escape`` ; la **structure** est de l'``Html`` de
confiance.
"""

from __future__ import annotations

import html as _html

from xerocr.reports.section import Html

_CSS = (
    "body{font-family:system-ui,sans-serif;margin:2rem;color:#1a1a1a;}"
    "h1{font-size:1.4rem;}h2{font-size:1.1rem;margin-top:1.5rem;}"
    "table{border-collapse:collapse;margin:.5rem 0;}"
    "th,td{border:1px solid #ccc;padding:.3rem .6rem;text-align:left;}"
    "th{background:#f4f4f4;}"
    "td.num{text-align:right;font-variant-numeric:tabular-nums;}"
    ".muted{color:#777;}"
)


def escape(text: str) -> str:
    """Échappe une donnée pour insertion sûre dans le HTML."""
    return _html.escape(text, quote=True)


def render_document(title: str, body: Html) -> str:
    """Assemble un document HTML autonome et déterministe."""
    safe_title = escape(title)
    return (
        "<!DOCTYPE html>\n"
        '<html lang="fr">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        f"<title>{safe_title}</title>\n"
        f"<style>{_CSS}</style>\n"
        "</head>\n"
        "<body>\n"
        f"<h1>{safe_title}</h1>\n"
        f"{body}"
        "</body>\n"
        "</html>\n"
    )


__all__ = ["escape", "render_document"]
