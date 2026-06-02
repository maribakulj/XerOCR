"""Section by-document : le détail **par-document** de ``RunResult`` rendu en
tables au design — une par vue, documents groupés, data-bars. Couche 7.

Surface une donnée **réelle déjà calculée** (``RunResult.documents``) jusqu'ici
**sans consommateur** dans le rapport ; aucune métrique inventée (note d'archi
S4.b). Génériques : affiche les métriques par-doc présentes, quelles qu'elles
soient.
"""

from __future__ import annotations

from xerocr.evaluation.result import RunDocumentResult, RunResult
from xerocr.reports.html import escape
from xerocr.reports.section import Html, SectionContext
from xerocr.reports.sections._tables import bar_cell, col_max, ordered_unique


class DocumentSection:
    """Détail par-document : une table par vue (document × pipeline × métriques)."""

    name = "by_document"
    requires: tuple[str, ...] = ()  # générique ; absent si aucun détail par-doc

    def render(self, result: RunResult, ctx: SectionContext) -> Html | None:
        if not result.documents:
            return None
        parts: list[str] = ["<h2>Par document</h2>"]
        for view_name in ordered_unique(d.view for d in result.documents):
            parts.append(_table_for_view(result.documents, view_name))
        return Html("\n".join(parts) + "\n")


def _table_for_view(
    documents: tuple[RunDocumentResult, ...], view_name: str
) -> str:
    rows = [d for d in documents if d.view == view_name]
    metrics = tuple(score.metric for score in rows[0].scores)
    header = "".join(f'<th class="num-cell">{escape(m)}</th>' for m in metrics)
    maxes = [col_max([d.scores for d in rows], i) for i in range(len(metrics))]
    body: list[str] = []
    for doc_id in ordered_unique(d.document_id for d in rows):
        doc_rows = [d for d in rows if d.document_id == doc_id]
        for offset, doc in enumerate(doc_rows):
            label = escape(doc_id) if offset == 0 else ""  # groupé : nom 1×
            cells = "".join(
                bar_cell(score, maxes[i]) for i, score in enumerate(doc.scores)
            )
            body.append(
                f'<tr><td class="eng-cell">{label}</td>'
                f'<td class="eng-cell">{escape(doc.pipeline)}</td>{cells}</tr>'
            )
    return (
        f"<h2>Vue : {escape(view_name)}</h2>\n"
        f'<table class="data">\n'
        f"<thead><tr><th>Document</th><th>Pipeline</th>{header}</tr></thead>\n"
        f"<tbody>{''.join(body)}</tbody>\n</table>"
    )


__all__ = ["DocumentSection"]
