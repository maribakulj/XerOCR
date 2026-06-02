"""Assemblage HTML **autonome** au design + échappement (couche 7).

Produit un document autonome (**CSS inline**, aucune dépendance CDN/JS), donc
hébergeable tel quel **et déterministe** (cf. plan §Cibles de distribution). Le
style reprend le **design** (gris chaud, chrome pilule, cartes ``sec``, tables
tabulaires) ; les **polices du design** — titres *Fluxisch Else*, corps + données
*OCR-A* — sont **incorporées en data-URI** (``_style.font_face_css``) pour garder
l'identité typographique **et** l'autonomie (S4.b.1a, option (a) — cf. D-019). Les
**données** sont échappées via ``escape`` ; la **structure** est de l'``Html`` de
confiance.
"""

from __future__ import annotations

import html as _html

from xerocr.reports._style import font_face_css
from xerocr.reports.section import Html

#: CSS du rapport au design (sous-ensemble de ``design/tokens.css``). Les
#: ``@font-face`` (Fluxisch Else + OCR-A, data-URI) sont préfixés au rendu par
#: ``font_face_css()``. Statique → le rapport reste octet-stable.
_CSS = (
    ":root{--paper:#EBE8E0;--surface:#F4F1EA;--raised:#FBFAF6;--g-50:#E4E0D7;"
    "--g-100:#D6D2C8;--g-300:#8D8879;--g-400:#6F6B60;--g-500:#54514A;"
    "--g-700:#26241F;--ink:#1A1917;--fern:oklch(0.50 0.07 145);"
    "--r-md:14px;--r-lg:20px;--r-pill:999px;"
    "--display:'Fluxisch Else',Georgia,serif;"
    "--sans:'OCRA',ui-monospace,monospace;"
    "--mono:'OCRA',ui-monospace,monospace;}"
    "*{box-sizing:border-box;margin:0;padding:0;}"
    "body.report-board{background-color:var(--paper);"
    "background-image:url(\"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg'"
    " width='3' height='3' viewBox='0 0 3 3'><circle cx='1' cy='1' r='0.6'"
    " fill='%231a1917' fill-opacity='0.28'/></svg>\");"
    "background-attachment:fixed;color:var(--ink);"
    "font-family:var(--sans);font-size:14px;line-height:1.5;padding:22px;"
    "display:flex;flex-direction:column;gap:18px;"
    "-webkit-font-smoothing:antialiased;}"
    ".report-chrome{display:flex;align-items:center;gap:12px;padding:12px 18px;"
    "background:var(--ink);border-radius:var(--r-pill);color:var(--paper);}"
    ".report-chrome .wm-mark{display:inline-flex;align-items:center;"
    "justify-content:center;width:24px;height:24px;border-radius:50%;"
    "background:var(--paper);color:var(--ink);font-weight:700;font-size:12px;}"
    ".report-chrome .wm-name{font-family:var(--display);font-weight:600;"
    "font-size:18px;letter-spacing:-0.02em;}"
    ".report-chrome .wm-sep{width:1px;height:16px;background:rgba(239,237,232,0.2);}"
    ".report-chrome .wm-sub{font-family:var(--mono);font-size:11px;"
    "letter-spacing:0.04em;color:rgba(239,237,232,0.6);}"
    ".report-main{display:flex;flex-direction:column;gap:14px;}"
    ".sec{background:var(--raised);border-radius:var(--r-lg);padding:22px 26px 24px;}"
    ".sec h1{font-family:var(--display);font-size:24px;letter-spacing:-0.02em;"
    "margin-bottom:6px;}"
    ".sec h2{font-family:var(--display);font-size:18px;letter-spacing:-0.015em;"
    "color:var(--ink);margin:18px 0 10px;}.sec h2:first-of-type{margin-top:0;}"
    ".sec p.muted{font-size:12.5px;color:var(--g-400);margin-bottom:10px;}"
    "table{width:100%;border-collapse:collapse;font-size:13px;margin:.4rem 0;}"
    "th{text-align:left;font-size:10.5px;letter-spacing:0.06em;"
    "text-transform:uppercase;color:var(--g-400);font-weight:500;"
    "padding:10px 14px;border-bottom:1px solid var(--g-100);}"
    "td{padding:11px 14px;border-bottom:1px solid var(--g-50);color:var(--g-700);}"
    "tr:last-child td{border-bottom:none;}"
    "td.num{text-align:right;font-family:var(--mono);"
    "font-variant-numeric:tabular-nums;color:var(--ink);}"
    # S4.b.1b — readouts (portée du corpus) + tables data-bars
    ".readouts{display:grid;grid-template-columns:repeat(auto-fit,minmax(116px,1fr));"
    "gap:10px;margin:14px 0 6px;}"
    ".readout{background:var(--surface);border-radius:var(--r-md);padding:14px 16px;"
    "display:flex;flex-direction:column;gap:6px;}"
    ".readout .r-label{font-size:10px;font-weight:500;letter-spacing:0.06em;"
    "text-transform:uppercase;color:var(--g-400);}"
    ".readout .r-value{font-family:var(--display);font-size:30px;"
    "letter-spacing:-0.03em;font-variant-numeric:tabular-nums;"
    "line-height:1;color:var(--ink);}"
    "table.data{width:100%;border-collapse:collapse;font-size:13px;margin:.4rem 0 0;}"
    "table.data th{text-align:left;font-size:10.5px;letter-spacing:0.04em;"
    "text-transform:uppercase;color:var(--g-400);font-weight:500;"
    "padding:8px 14px 10px;border-bottom:1px solid var(--g-100);}"
    "table.data th.num-cell{text-align:right;}"
    "table.data td.eng-cell{vertical-align:middle;padding:10px 14px;"
    "border-bottom:1px solid var(--g-50);color:var(--g-700);}"
    "table.data tr:last-child td{border-bottom:none;}"
    "table.data td.databar{position:relative;padding:0;font-family:var(--mono);"
    "font-variant-numeric:tabular-nums;font-size:12px;color:var(--ink);"
    "border-bottom:1px solid var(--g-50);vertical-align:middle;}"
    "table.data td.databar .db-fill{position:absolute;top:6px;bottom:6px;left:6px;"
    "border-radius:8px;background:var(--fern);opacity:0.18;z-index:0;}"
    "table.data td.databar .db-num{position:relative;z-index:1;display:block;"
    "text-align:right;padding:12px 14px;}"
    "table.data td.rank{padding:11px 8px 11px 14px;color:var(--g-400);"
    "font-family:var(--mono);font-size:11px;border-bottom:1px solid var(--g-50);}"
    "table.data td.disp{padding:11px 14px;text-align:right;font-family:var(--mono);"
    "font-size:11px;color:var(--g-500);border-bottom:1px solid var(--g-50);}"
    ".muted{color:var(--g-400);}"
    "::selection{background:var(--ink);color:var(--paper);}"
)


def escape(text: str) -> str:
    """Échappe une donnée pour insertion sûre dans le HTML."""
    return _html.escape(text, quote=True)


def render_document(title: str, body: Html) -> str:
    """Assemble un document HTML autonome, au design, et déterministe."""
    safe_title = escape(title)
    return (
        "<!DOCTYPE html>\n"
        '<html lang="fr">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{safe_title}</title>\n"
        f"<style>{font_face_css()}{_CSS}</style>\n"
        "</head>\n"
        '<body class="report-board">\n'
        '<header class="report-chrome">'
        '<span class="wm-mark">X</span><span class="wm-name">XerOCR</span>'
        '<span class="wm-sep"></span>'
        f'<span class="wm-sub">{safe_title}</span></header>\n'
        '<main class="report-main"><section class="sec">\n'
        f"{body}"
        "</section></main>\n"
        "</body>\n"
        "</html>\n"
    )


__all__ = ["escape", "render_document"]
