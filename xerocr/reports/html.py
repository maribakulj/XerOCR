"""Assemblage HTML **autonome** au design + échappement (couche 7).

Produit un document autonome (**CSS inline**, aucune dépendance CDN/JS), donc
hébergeable tel quel **et déterministe** (cf. plan §Cibles de distribution). Le
style reprend le **design** (gris chaud, chrome pilule, cartes ``sec``, tables
tabulaires) ; les **polices du design** — titres *Mona Sans*, corps *IBM Plex
Sans*, données *IBM Plex Mono*, accents *Fluxisch Else*, logo *OCR-A* — sont
**incorporées en data-URI** (``_style.font_face_css``) pour garder
l'identité typographique **et** l'autonomie (S4.b.1a, option (a) — cf. D-019). Les
**données** sont échappées via ``escape`` ; la **structure** est de l'``Html`` de
confiance.
"""

from __future__ import annotations

import html as _html

from xerocr.reports._style import font_face_css
from xerocr.reports.section import Html

#: CSS du rapport au design (sous-ensemble de ``design/tokens.css``). Les
#: ``@font-face`` (Mona/IBM Plex/Fluxisch/OCR-A, data-URI) sont préfixés au rendu par
#: ``font_face_css()``. Statique → le rapport reste octet-stable.
_CSS = (
    ":root{--paper:#EBE8E0;--surface:#F4F1EA;--raised:#FBFAF6;--g-50:#E4E0D7;"
    "--g-100:#D6D2C8;--g-300:#8D8879;--g-400:#6F6B60;--g-500:#54514A;"
    "--g-700:#26241F;--ink:#1A1917;--fern:oklch(0.50 0.07 145);"
    "--r-md:14px;--r-lg:20px;--r-pill:999px;"
    "--display:'Mona Sans VF','IBM Plex Sans',system-ui,sans-serif;"
    "--sans:'IBM Plex Sans',system-ui,sans-serif;"
    "--mono:'IBM Plex Mono',ui-monospace,monospace;"
    "--accent:'Fluxisch Else',Georgia,serif;"
    "--ocr:'OCRA','IBM Plex Mono',ui-monospace,monospace;}"
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
    ".report-chrome .wm-name{font-family:var(--ocr);font-weight:400;"
    "font-size:18px;letter-spacing:0.01em;}"
    ".report-chrome .wm-sep{width:1px;height:16px;background:rgba(239,237,232,0.2);}"
    ".report-chrome .wm-sub{font-family:var(--mono);font-size:11px;"
    "letter-spacing:0.04em;color:rgba(239,237,232,0.6);}"
    ".report-main{display:flex;flex-direction:column;gap:14px;}"
    ".sec{background:var(--raised);border-radius:var(--r-lg);padding:22px 26px 24px;}"
    ".sec h1{font-family:var(--display);font-size:24px;font-weight:800;"
    "font-optical-sizing:auto;letter-spacing:0;"
    "margin-bottom:6px;}"
    ".sec h2{font-family:var(--display);font-size:18px;font-weight:800;"
    "font-optical-sizing:auto;letter-spacing:0;"
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
    # Readouts (portée du corpus) + tables data-bars
    ".readouts{display:grid;grid-template-columns:repeat(auto-fit,minmax(116px,1fr));"
    "gap:10px;margin:14px 0 6px;}"
    ".readout{background:var(--surface);border-radius:var(--r-md);padding:14px 16px;"
    "display:flex;flex-direction:column;gap:6px;}"
    ".readout .r-label{font-size:10px;font-weight:500;letter-spacing:0.06em;"
    "text-transform:uppercase;color:var(--g-400);}"
    ".readout .r-value{font-family:var(--display);font-size:30px;"
    "font-weight:800;font-optical-sizing:auto;letter-spacing:0;"
    "font-variant-numeric:tabular-nums;"
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
    "table.data td.verdict{padding:11px 14px;font-family:var(--sans);font-size:11.5px;"
    "color:var(--g-400);border-bottom:1px solid var(--g-50);}"
    "table.data td.verdict.sig{color:var(--fern);font-weight:600;}"
    ".muted{color:var(--g-400);}"
    "::selection{background:var(--ink);color:var(--paper);}"
    # Sommaire deeplinkable (ancres natives) + régions de section ancrées.
    ".report-toc{display:flex;flex-wrap:wrap;gap:6px;margin:0 0 16px;}"
    ".report-toc a{font-family:var(--mono);font-size:11px;text-decoration:none;"
    "color:var(--g-500);background:var(--surface);border-radius:var(--r-pill);"
    "padding:6px 13px;}"
    ".report-toc a:hover{color:var(--ink);background:var(--g-50);}"
    ".r-block{scroll-margin-top:18px;}"
    # Badge moteur (lettre + accent cyclique) — identité stable entre sections.
    ".eng-badge{display:inline-flex;align-items:center;justify-content:center;"
    "width:18px;height:18px;border-radius:5px;background:var(--badge,var(--ink));"
    "color:var(--paper);font-family:var(--mono);font-size:10px;font-weight:600;"
    "margin-right:8px;vertical-align:middle;}"
    # Widget « comparer un run » (client-side) — bouton + bandeau sticky des deltas.
    ".compare-bar{display:flex;justify-content:flex-end;margin-top:2px;}"
    ".compare-btn{font-family:var(--mono);font-size:12px;background:var(--ink);"
    "color:var(--paper);border:none;border-radius:var(--r-pill);"
    "padding:8px 16px;cursor:pointer;}"
    ".compare-banner{position:fixed;left:22px;right:22px;bottom:14px;"
    "background:var(--ink);color:var(--paper);border-radius:var(--r-md);"
    "padding:12px 16px;display:flex;flex-wrap:wrap;gap:8px 18px;align-items:center;"
    "font-family:var(--mono);font-size:12px;box-shadow:0 6px 24px rgba(0,0,0,0.25);"
    "z-index:50;}"
    ".compare-banner.empty{justify-content:center;color:var(--g-100);}"
    ".compare-banner .cb-title{font-weight:600;letter-spacing:0.02em;}"
    ".compare-banner .cb-row{display:inline-flex;gap:6px;align-items:baseline;}"
    ".compare-banner .cb-row .cb-delta{font-variant-numeric:tabular-nums;}"
    ".compare-banner .cb-row.worse .cb-delta{color:#E59A8A;}"
    ".compare-banner .cb-row.better .cb-delta{color:#9FC3A0;}"
)


def escape(text: str) -> str:
    """Échappe une donnée pour insertion sûre dans le HTML."""
    return _html.escape(text, quote=True)


def render_document(title: str, body: Html, *, footer: Html | None = None) -> str:
    """Assemble un document HTML autonome, au design, et déterministe.

    ``footer`` (optionnel) : HTML inséré en fin de ``<body>``, après le contenu
    principal — p. ex. le widget « comparer un run » (client-side). Absent → rien
    n'est ajouté (le rapport reste identique au squelette, ex. la voie
    ``compare`` server-side qui n'embarque pas le widget)."""
    safe_title = escape(title)
    tail = f"{footer}" if footer is not None else ""
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
        f"{tail}"
        "</body>\n"
        "</html>\n"
    )


__all__ = ["escape", "render_document"]
