"""Section diagnostic : confusions, pires lignes, documents difficiles (couche 7).

Rend les payloads ``diagnostics`` de ``RunResult.analyses`` en **lecture
seule** : « voir où ça casse », texte à l'appui. Les extraits sont verbatim du
``RunResult`` (chargés et normalisés au scoring) — aucun recalcul au rendu. Les
confusions sont mises en **flux de glyphes** (#8) : le glyphe attendu → produit,
prominents, barre de fréquence — « voir les symboles » et leur direction.
"""

from __future__ import annotations

from xerocr.evaluation.analysis import CharConfusion, DiagnosticsPayload, WorstLine
from xerocr.evaluation.result import RunResult
from xerocr.reports.html import escape
from xerocr.reports.section import Html, SectionContext
from xerocr.reports.text_diff import char_diff

#: Libellés bilingues du **flux de confusion** (#8). Le reste de la section,
#: antérieur à la consigne FR/EN des graphiques, reste FR (i18n rapport = jalon).
_CONFUSION_TEXT: dict[str, dict[str, str]] = {
    "fr": {
        "title": "Confusions de caractères récurrentes (attendu → produit)",
        "intro": (
            "Le glyphe attendu (vérité-terrain) → le glyphe produit par le "
            "moteur ; la barre indique la fréquence. La <strong>direction</strong> "
            "compte : « ſ → f » (long s lu f) n'est pas « f → ſ »."
        ),
    },
    "en": {
        "title": "Recurring character confusions (expected → produced)",
        "intro": (
            "The expected glyph (ground truth) → the glyph the engine produced; "
            "the bar shows frequency. <strong>Direction</strong> matters: "
            "“ſ → f” (long s read as f) is not “f → ſ”."
        ),
    },
}


def _confusion_chip(pair: CharConfusion, max_count: int) -> str:
    """Une paire de confusion : glyphes attendu → produit + barre de fréquence."""
    width = round(pair.count / max_count * 48)
    return (
        '<div class="cf-pair">'
        f'<span class="cf-glyph">{escape(pair.expected)}</span>'
        '<span class="cf-arrow">→</span>'
        f'<span class="cf-glyph">{escape(pair.observed)}</span>'
        f'<span class="cf-bar" style="width:{width}px"></span>'
        f'<span class="cf-count">{pair.count}</span></div>'
    )


def _confusion_flow(payload: DiagnosticsPayload, lang: str) -> str:
    """Flux de confusion (#8) : par moteur, glyphes attendu → produit + fréquence.

    Les glyphes sont **prominents** (le symbole *est* la donnée — on juge à l'œil) ;
    la barre est proportionnelle au compte (pairs déjà triées -count). Verbatim,
    échappés (anti-XSS) ; le slot bordé rend une espace confondue **visible**."""
    groups: list[str] = []
    for block in payload.confusions:
        if not block.pairs:
            continue
        max_count = block.pairs[0].count  # pairs triées -count → pairs[0] = max
        chips = "".join(_confusion_chip(pair, max_count) for pair in block.pairs)
        groups.append(
            f'<div class="cf-engine"><span class="cf-eng-name">'
            f"{escape(block.pipeline)}</span>"
            f'<div class="cf-grid">{chips}</div></div>'
        )
    if not groups:
        return ""
    text = _CONFUSION_TEXT.get(lang, _CONFUSION_TEXT["fr"])
    return (
        f"<h4>{text['title']}</h4>\n"
        f'<p class="muted">{text["intro"]}</p>\n' + "".join(groups)
    )


def _worst_lines_row(line: WorstLine) -> str:
    # Drill-in : GT vs hypothèse surlignées caractère à caractère (écarts visibles).
    ref_html, hyp_html = char_diff(line.reference, line.hypothesis)
    return (
        f'<tr><td class="eng-cell">{escape(line.pipeline)}</td>'
        f'<td class="eng-cell">{escape(line.document_id)}</td>'
        f'<td class="disp">{line.line_index}</td>'
        f'<td class="disp">{line.cer:.4f}</td>'
        f'<td class="diff">{ref_html}</td>'
        f'<td class="diff">{hyp_html}</td></tr>'
    )


def _worst_lines_table(payload: DiagnosticsPayload) -> str:
    if not payload.worst_lines:
        return ""
    rows = "".join(_worst_lines_row(line) for line in payload.worst_lines)
    return (
        "<h4>Pires lignes du corpus — diff GT ↔ hypothèse</h4>\n"
        '<p class="muted">Surlignage : '
        '<del class="d-del">supprimé</del> (présent en GT) · '
        '<ins class="d-ins">inséré</ins> (produit par le moteur).</p>\n'
        '<table class="data">\n<thead><tr><th>Pipeline</th><th>Document</th>'
        '<th class="num-cell">ligne</th><th class="num-cell">CER</th>'
        "<th>référence (GT)</th><th>hypothèse</th></tr></thead>\n"
        f"<tbody>{rows}</tbody>\n</table>\n"
    )


def _hardest_table(payload: DiagnosticsPayload) -> str:
    if not payload.hardest_documents:
        return ""
    rows = "".join(
        f'<tr><td class="eng-cell">{escape(doc.document_id)}</td>'
        f'<td class="disp">{doc.mean_cer:.4f}</td>'
        f'<td class="disp">{doc.n_pipelines}</td></tr>'
        for doc in payload.hardest_documents
    )
    return (
        "<h4>Documents les plus difficiles</h4>\n"
        '<table class="data">\n<thead><tr><th>Document</th>'
        f'<th class="num-cell">{escape(payload.metric)} moyen</th>'
        '<th class="num-cell">pipelines scorés</th></tr></thead>\n'
        f"<tbody>{rows}</tbody>\n</table>\n"
    )


class DiagnosticsSection:
    """Diagnostic d'erreurs : confusions, pires lignes, documents difficiles."""

    name = "diagnostics"
    requires: tuple[str, ...] = ()

    def render(self, result: RunResult, ctx: SectionContext) -> Html | None:
        blocks: list[str] = []
        for analysis in result.analyses:
            payload = analysis.payload
            if not isinstance(payload, DiagnosticsPayload):
                continue
            inner = (
                _confusion_flow(payload, ctx.lang)
                + _worst_lines_table(payload)
                + _hardest_table(payload)
            )
            if inner:
                blocks.append(
                    f"<h3>{escape(analysis.view)} — où ça casse</h3>\n" + inner
                )
        if not blocks:
            return None
        return Html("<h2>Diagnostic d'erreurs</h2>\n" + "".join(blocks))


__all__ = ["DiagnosticsSection"]
