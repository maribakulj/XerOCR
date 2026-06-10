"""Section diagnostic : confusions, pires lignes, documents difficiles (couche 7).

Rend les payloads ``diagnostics`` de ``RunResult.analyses`` en **lecture
seule** : « voir où ça casse », texte à l'appui. Les extraits sont verbatim du
``RunResult`` (chargés et normalisés au scoring) — aucun recalcul au rendu.
"""

from __future__ import annotations

from xerocr.evaluation.analysis import DiagnosticsPayload
from xerocr.evaluation.result import RunResult
from xerocr.reports.html import escape
from xerocr.reports.section import Html, SectionContext


def _confusion_table(payload: DiagnosticsPayload) -> str:
    if not payload.confusions:
        return ""
    rows: list[str] = []
    for block in payload.confusions:
        for pair in block.pairs:
            rows.append(
                f'<tr><td class="eng-cell">{escape(block.pipeline)}</td>'
                f'<td class="disp">{escape(pair.expected)} → '
                f"{escape(pair.observed)}</td>"
                f'<td class="disp">{pair.count}</td></tr>'
            )
    return (
        "<h4>Confusions de caractères récurrentes</h4>\n"
        '<table class="data">\n<thead><tr><th>Pipeline</th>'
        '<th class="num-cell">attendu → produit</th>'
        '<th class="num-cell">occurrences</th></tr></thead>\n'
        f"<tbody>{''.join(rows)}</tbody>\n</table>\n"
    )


def _worst_lines_table(payload: DiagnosticsPayload) -> str:
    if not payload.worst_lines:
        return ""
    rows = "".join(
        f'<tr><td class="eng-cell">{escape(line.pipeline)}</td>'
        f'<td class="eng-cell">{escape(line.document_id)}</td>'
        f'<td class="disp">{line.line_index}</td>'
        f'<td class="disp">{line.cer:.4f}</td>'
        f'<td class="disp">{escape(line.reference)}</td>'
        f'<td class="disp">{escape(line.hypothesis)}</td></tr>'
        for line in payload.worst_lines
    )
    return (
        "<h4>Pires lignes du corpus</h4>\n"
        '<table class="data">\n<thead><tr><th>Pipeline</th><th>Document</th>'
        '<th class="num-cell">ligne</th><th class="num-cell">CER</th>'
        "<th>référence</th><th>hypothèse</th></tr></thead>\n"
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
                _confusion_table(payload)
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
