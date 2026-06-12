"""Section significativité inter-moteurs : rend ``RunResult.cross_engine`` au design.

Pour chaque ``vue:métrique``, la p-value d'une différence entre pipelines
(Wilcoxon / Friedman) + un **verdict factuel** (significatif si p < 0,05). Le
verdict est une **fonction auditable** de la p-value — une étiquette, pas de la
prose (narratif supprimé, ``CLAUDE.md`` §6). ``None`` si inapplicable (aucun
résultat inter-moteurs, ou sous le plancher de puissance).

Sous le tableau des p-values, la section **lit** (sans recalculer) les payloads
``inference`` de ``RunResult.analyses`` : rangs moyens, distance critique de
Nemenyi (correction multi-comparaisons), groupes statistiquement
indiscernables, et IC bootstrap à 95 % par pipeline. Puis les payloads
``inter_engine`` : complémentarité oracle (borne **supérieure** bag-of-words,
documentée comme telle — anti-surinterprétation) et divergence Jensen-Shannon
des profils d'erreurs.
"""

from __future__ import annotations

from collections.abc import Mapping

from xerocr.evaluation.analysis import (
    InferencePayload,
    InterEngineComplementarity,
    InterEngineDivergence,
    InterEnginePayload,
)
from xerocr.evaluation.result import RunResult
from xerocr.reports.engine_badges import engine_cell, engine_order
from xerocr.reports.html import escape
from xerocr.reports.section import Html, SectionContext


def _format_p(value: float | None) -> str:
    return "—" if value is None else f"{value:.4f}"


def _split_key(key: str) -> tuple[str, str]:
    """``"text:cer:significance_p"`` → ``("text", "cer")`` ; sinon (clé, "")."""
    parts = key.split(":")
    if len(parts) >= 2:
        return parts[0], parts[1]
    return key, ""


def _verdict(value: float | None) -> tuple[str, str]:
    """(libellé, classe CSS) — significatif si p < 0,05 ; ``None`` → tiret."""
    if value is None:
        return "—", ""
    if value < 0.05:
        return "significatif", " sig"
    return "non sig.", ""


def _inference_block(
    view: str, payload: InferencePayload, order: Mapping[str, int]
) -> str:
    """Rendu d'un payload ``inference`` : rangs, Nemenyi, IC bootstrap."""
    rows: list[str] = []
    intervals = {item.pipeline: item for item in payload.intervals}
    for rank in payload.mean_ranks:
        interval = intervals.get(rank.pipeline)
        ic = (
            f"[{interval.lower:.4f} ; {interval.upper:.4f}]"
            if interval is not None
            else "—"
        )
        mean = f"{interval.mean:.4f}" if interval is not None else "—"
        badge = engine_cell(rank.pipeline, order.get(rank.pipeline, 0))
        rows.append(
            f'<tr><td class="eng-cell">{badge}</td>'
            f'<td class="disp">{rank.mean_rank:.3f}</td>'
            f'<td class="disp">{mean}</td>'
            f'<td class="disp">{ic}</td></tr>'
        )
    if payload.critical_distance is not None:
        groups = " · ".join(
            "{" + ", ".join(escape(name) for name in group) + "}"
            for group in payload.tied_groups
        )
        extrapolated = " (q extrapolé)" if payload.q_alpha_extrapolated else ""
        nemenyi = (
            f'<p class="muted">Nemenyi (α={payload.alpha:g}) : distance '
            f"critique CD = {payload.critical_distance:.4f}{extrapolated} ; "
            f"groupes indiscernables : {groups}.</p>\n"
        )
    else:
        nemenyi = (
            '<p class="muted">2 pipelines : le verdict apparié est la p-value '
            "Wilcoxon ci-dessus (pas de post-hoc).</p>\n"
        )
    return (
        f"<h3>{escape(view)} · {escape(payload.metric)} — rangs &amp; IC "
        f"(n={payload.n_documents})</h3>\n"
        + nemenyi
        + '<table class="data">\n'
        "<thead><tr><th>Pipeline</th>"
        '<th class="num-cell">rang moyen</th>'
        '<th class="num-cell">moyenne</th>'
        '<th class="num-cell">IC 95 % (bootstrap)</th></tr></thead>\n'
        f"<tbody>{''.join(rows)}</tbody>\n</table>\n"
    )


def _complementarity_block(
    view: str, comp: InterEngineComplementarity, order: Mapping[str, int]
) -> str:
    """Rendu du bloc complémentarité : rappel par moteur seul vs oracle."""
    rows: list[str] = []
    for item in comp.per_engine_recall:
        badge = engine_cell(item.pipeline, order.get(item.pipeline, 0))
        best = " (meilleur seul)" if item.pipeline == comp.best_engine else ""
        rows.append(
            f'<tr><td class="eng-cell">{badge}{best}</td>'
            f'<td class="disp">{item.recall:.1%}</td></tr>'
        )
    rows.append(
        f'<tr><td class="eng-cell">oracle (union des '
        f"{len(comp.per_engine_recall)} moteurs)</td>"
        f'<td class="disp">{comp.oracle_recall:.1%}</td></tr>'
    )
    gap_documents = [d for d in comp.per_document if d.absolute_gap > 0]
    documents = ""
    if gap_documents:
        document_rows = "".join(
            f'<tr><td class="eng-cell">{escape(d.document_id)}</td>'
            f'<td class="disp">{d.oracle_recall:.1%}</td>'
            f'<td class="disp">{d.best_single_recall:.1%}</td>'
            f'<td class="disp">{d.absolute_gap:.1%}</td></tr>'
            for d in gap_documents
        )
        documents = (
            '<p class="muted">Documents au plus fort écart oracle − meilleur '
            "(échantillon borné) :</p>\n"
            '<table class="data">\n<thead><tr><th>Document</th>'
            '<th class="num-cell">oracle</th>'
            '<th class="num-cell">meilleur seul</th>'
            '<th class="num-cell">écart</th></tr></thead>\n'
            f"<tbody>{document_rows}</tbody>\n</table>\n"
        )
    return (
        f"<h3>{escape(view)} — complémentarité des moteurs "
        f"(oracle, n={comp.n_documents} documents)</h3>\n"
        '<p class="muted">Rappel des tokens de la GT (multiset) par moteur '
        "seul, contre l'<strong>oracle</strong> : l'union des moteurs où "
        "chaque token est rattrapé par le meilleur moteur sur ce token. "
        "<strong>Borne supérieure</strong> optimiste, en sac de mots — "
        "l'<strong>ordre est ignoré</strong> ; un vote séquentiel réel ferait "
        "au mieux autant, en général moins. À lire comme un plafond de gain "
        "d'ensemble, pas une prédiction.</p>\n"
        '<table class="data">\n<thead><tr><th>Pipeline</th>'
        '<th class="num-cell">rappel tokens</th></tr></thead>\n'
        f"<tbody>{''.join(rows)}</tbody>\n</table>\n"
        f'<p class="muted">Écart absolu oracle − meilleur '
        f"({escape(comp.best_engine)}) : {comp.absolute_gap:.1%} ; écart "
        f"relatif : {comp.relative_gap:.1%} des erreurs du meilleur moteur "
        "théoriquement rattrapables par un ensemble.</p>\n"
        + documents
    )


def _divergence_block(
    view: str, divergence: InterEngineDivergence, order: Mapping[str, int]
) -> str:
    """Rendu du bloc divergence : JS paire-à-paire sur les profils d'erreurs."""
    rows = "".join(
        f'<tr><td class="eng-cell">'
        f"{engine_cell(pair.a, order.get(pair.a, 0))} · "
        f"{engine_cell(pair.b, order.get(pair.b, 0))}</td>"
        f'<td class="disp">{pair.divergence:.4f}</td></tr>'
        for pair in divergence.pairs
    )
    if divergence.max_pair is not None:
        max_pair = (
            f'<p class="muted">Paire la plus divergente : '
            f"{escape(divergence.max_pair.a)} · {escape(divergence.max_pair.b)} "
            f"({divergence.max_pair.divergence:.4f} bit).</p>\n"
        )
    else:
        max_pair = (
            '<p class="muted">Profils d\'erreurs identiques : aucune paire '
            "divergente.</p>\n"
        )
    return (
        f"<h3>{escape(view)} — divergence des profils d'erreurs "
        "(Jensen-Shannon)</h3>\n"
        '<p class="muted">Divergence JS en bits ([0 ; 1]) entre les '
        "distributions de classes d'erreurs (taxonomie) des moteurs : 0 = "
        "mêmes natures d'erreurs, 1 = profils disjoints. Une paire divergente "
        "se trompe différemment — candidate naturelle à un ensemble.</p>\n"
        '<table class="data">\n<thead><tr><th>Paire</th>'
        '<th class="num-cell">JS (bits)</th></tr></thead>\n'
        f"<tbody>{rows}</tbody>\n</table>\n"
        + max_pair
    )


def _inter_engine_blocks(result: RunResult, order: Mapping[str, int]) -> str:
    """Blocs complémentarité + divergence de chaque payload ``inter_engine``."""
    blocks: list[str] = []
    for analysis in result.analyses:
        payload = analysis.payload
        if not isinstance(payload, InterEnginePayload):
            continue
        if payload.complementarity is not None:
            blocks.append(
                _complementarity_block(
                    analysis.view, payload.complementarity, order
                )
            )
        if payload.taxonomy_divergence is not None:
            blocks.append(
                _divergence_block(
                    analysis.view, payload.taxonomy_divergence, order
                )
            )
    return "".join(blocks)


class CrossEngineSection:
    """P-values de différence inter-moteurs (Wilcoxon / Friedman) + verdict."""

    name = "cross_engine"
    requires: tuple[str, ...] = ()

    def render(self, result: RunResult, ctx: SectionContext) -> Html | None:
        order = engine_order(p.pipeline for p in result.pipelines)
        inter_engine = _inter_engine_blocks(result, order)
        if not result.cross_engine and not inter_engine:
            return None
        significance = ""
        if result.cross_engine:
            body: list[str] = []
            for score in result.cross_engine:
                view, metric = _split_key(score.metric)
                label, css = _verdict(score.value)
                body.append(
                    f'<tr><td class="eng-cell">{escape(view)}</td>'
                    f'<td class="eng-cell">{escape(metric)}</td>'
                    f'<td class="disp">{_format_p(score.value)}</td>'
                    f'<td class="disp">{score.support}</td>'
                    f'<td class="verdict{css}">{label}</td></tr>'
                )
            significance = (
                '<p class="muted">p-value d\'une différence entre pipelines '
                "(Wilcoxon / Friedman) ; significatif si p &lt; 0,05.</p>\n"
                '<table class="data">\n'
                "<thead><tr><th>Vue</th><th>Métrique</th>"
                '<th class="num-cell">p-value</th><th class="num-cell">n</th>'
                "<th>verdict</th></tr></thead>\n"
                f"<tbody>{''.join(body)}</tbody>\n</table>\n"
            )
        blocks = "".join(
            _inference_block(analysis.view, analysis.payload, order)
            for analysis in result.analyses
            if isinstance(analysis.payload, InferencePayload)
        )
        return Html(
            "<h2>Significativité inter-moteurs</h2>\n"
            + significance
            + blocks
            + inter_engine
        )


__all__ = ["CrossEngineSection"]
