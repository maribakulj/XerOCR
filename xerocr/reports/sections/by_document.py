"""Section by-document : **distribution** de difficulté (tout le corpus) + table
des documents **notables** (couche 7).

Invariant d'échelle : ne liste **jamais** un document par ligne. Montre (1) la
distribution du CER moyen par document — couvre 100 % du corpus, même allure à 20
ou 6000 documents — et (2) une table des **documents notables** (les plus
difficiles, les plus discordants entre moteurs, les plus faciles), de cardinalité
fixe : des exemples, **pas** une troncature (la distribution représente
l'ensemble). Remplace l'ancienne table exhaustive, dépendante de l'échelle.
"""

from __future__ import annotations

from xerocr.evaluation.result import MetricScore, RunResult
from xerocr.reports._doc_highlights import (
    histogram,
    notable_documents,
    per_doc_mean_cer,
)
from xerocr.reports.engine_badges import engine_cell, engine_order
from xerocr.reports.html import escape, localized
from xerocr.reports.section import Html, SectionContext
from xerocr.reports.sections._tables import bar_cell, ordered_unique
from xerocr.reports.svg import bar_series

#: Nombre de classes de l'histogramme de difficulté (constant → invariant d'échelle).
_N_BINS = 24
#: Libellés de la catégorie primaire d'un document notable.
_GROUP_FR = {"worst": "difficile", "divergent": "discordant", "best": "facile"}
_GROUP_EN = {"worst": "hard", "divergent": "divergent", "best": "easy"}


class DocumentSection:
    """Distribution de la difficulté par document + table des documents notables."""

    name = "by_document"
    requires: tuple[str, ...] = ()

    def render(self, result: RunResult, ctx: SectionContext) -> Html | None:
        if not result.documents:
            return None
        view = ordered_unique(d.view for d in result.documents)[0]
        means = per_doc_mean_cer(result, view)
        if not means:
            return None  # aucun CER par document → rien à distribuer (no-orphan)
        lang = ctx.lang
        order = engine_order(p.pipeline for p in result.pipelines) or engine_order(
            d.pipeline for d in result.documents if d.view == view
        )
        return Html(
            self._distribution(means, lang)
            + self._notable_table(result, view, order, lang)
        )

    @staticmethod
    def _distribution(means: dict[str, float], lang: str) -> str:
        """Histogramme du CER moyen par document — couvre **tout** le corpus."""
        counts = histogram(list(means.values()), _N_BINS)
        n = len(means)
        lo = min(means.values()) * 100
        hi = max(means.values()) * 100
        caption = localized(
            lang,
            f'<span class="muted">{n} documents · CER moyen par document de '
            f"{lo:.1f} % à {hi:.1f} % ({_N_BINS} classes, gauche = facile)</span>",
            f'<span class="muted">{n} documents · per-document mean CER from '
            f"{lo:.1f} % to {hi:.1f} % ({_N_BINS} bins, left = easy)</span>",
        )
        title = localized(
            lang,
            "Distribution de la difficulté",
            "Difficulty distribution",
        )
        return (
            f"<h3>{title}</h3>\n"
            f'<div class="prof-chart"><div class="drill-caption">{caption}</div>'
            f'{bar_series(counts, accent="var(--ink)")}</div>\n'
        )

    def _notable_table(
        self, result: RunResult, view: str, order: dict[str, int], lang: str
    ) -> str:
        """Table des documents notables : id, catégorie, CER par moteur (data-bar)."""
        hl = notable_documents(result, view)
        ordered = hl.ordered_ids
        if not ordered:
            return ""
        engines = [n for n in sorted(order, key=lambda e: order[e])]
        # CER (MetricScore) par (document, moteur) pour la vue.
        cer: dict[tuple[str, str], MetricScore] = {}
        for doc in result.documents:
            if doc.view != view:
                continue
            for score in doc.scores:
                if score.metric == "cer":
                    cer[(doc.document_id, doc.pipeline)] = score
        col_max = max(
            (
                s.value
                for (_doc, _eng), s in cer.items()
                if _doc in set(ordered) and s.value is not None
            ),
            default=0.0,
        )
        groups = _GROUP_EN if lang == "en" else _GROUP_FR
        header = "".join(
            f'<th class="num-cell">{engine_cell(name, order.get(name, 0))}</th>'
            for name in engines
        )
        body: list[str] = []
        for doc_id in ordered:
            tag = groups.get(hl.group_of(doc_id), "")
            cells = "".join(
                bar_cell(cer[(doc_id, name)], col_max)
                if (doc_id, name) in cer and cer[(doc_id, name)].value is not None
                else '<td class="disp muted">—</td>'
                for name in engines
            )
            body.append(
                f'<tr><td class="eng-cell">{escape(doc_id)}</td>'
                f'<td class="muted">{escape(tag)}</td>{cells}</tr>'
            )
        th_doc = localized(lang, "Document", "Document")
        th_cat = localized(lang, "catégorie", "category")
        title = localized(lang, "Documents notables", "Notable documents")
        intro = localized(
            lang,
            '<p class="muted">Exemples (cardinalité fixe) : les plus '
            "<strong>difficiles</strong>, les plus <strong>discordants</strong> entre "
            "moteurs, les plus <strong>faciles</strong>. Rien n'est masqué : la "
            "distribution ci-dessus couvre tout le corpus.</p>\n",
            '<p class="muted">Examples (fixed count): <strong>hardest</strong>, most '
            "engine-<strong>divergent</strong>, <strong>easiest</strong>. Nothing is "
            "hidden: the distribution above covers the whole corpus.</p>\n",
        )
        return (
            f"<h3>{title}</h3>\n{intro}"
            f'<table class="data">\n'
            f"<thead><tr><th>{th_doc}</th><th>{th_cat}</th>{header}</tr></thead>\n"
            f"<tbody>{''.join(body)}</tbody>\n</table>\n"
        )


__all__ = ["DocumentSection"]
