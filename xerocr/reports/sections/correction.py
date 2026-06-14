"""Section bilan de correction : que vaut l'étage LLM ? (couche 7)

Rend le payload ``correction`` en **lecture seule** : triplet de
non-régression, pcis, ampleur d'intervention, absorption, sur-normalisation,
pires régressions. Tous les seuils affichés viennent du payload (auditable).
"""

from __future__ import annotations

from xerocr.evaluation.analysis import CorrectionPayload, PipelineCorrection
from xerocr.evaluation.result import RunResult
from xerocr.reports.html import escape, localized
from xerocr.reports.section import Html, SectionContext


def _pct(value: float | None) -> str:
    return "—" if value is None else f"{value:.1%}"


def _num(value: float | None, *, signed: bool = False) -> str:
    if value is None:
        return "—"
    return f"{value:+.4f}" if signed else f"{value:.4f}"


def _row(label: str, *cells: str) -> str:
    body = "".join(f'<td class="disp">{cell}</td>' for cell in cells)
    return f'<tr><td class="eng-cell">{escape(label)}</td>{body}</tr>'


def _pipeline_block(
    row: PipelineCorrection, payload: CorrectionPayload, lang: str
) -> str:
    missing = (
        localized(
            lang,
            f" · R-1.8 : {row.n_missing_raw} brut(s) / {row.n_missing_corrected} "
            f"corrigé(s) matérialisés vides",
            f" · R-1.8: {row.n_missing_raw} raw / {row.n_missing_corrected} "
            f"corrected materialized empty",
        )
        if row.n_missing_raw or row.n_missing_corrected
        else ""
    )
    rows = [
        _row(
            localized(
                lang,
                "Triplet (amélioration / régression / égalité)",
                "Triplet (improvement / regression / no change)",
            ),
            _pct(row.improvement_rate),
            _pct(row.regression_rate),
            _pct(row.no_change_rate),
        ),
        _row(
            localized(
                lang,
                f"pref · catastrophiques (Δ > {payload.catastrophic_threshold:g})",
                f"pref · catastrophic (Δ > {payload.catastrophic_threshold:g})",
            ),
            _num(row.pref_score, signed=True),
            f"{row.n_catastrophic} ({_pct(row.catastrophic_rate)})",
            "",
        ),
        _row(
            localized(
                lang,
                "pcis (macro · médiane · |pcis| > 1)",
                "pcis (macro · median · |pcis| > 1)",
            ),
            _num(row.pcis_macro, signed=True),
            _num(row.pcis_median, signed=True),
            str(row.n_pcis_extreme),
        ),
        _row(
            localized(
                lang,
                f"Intervention (CCR · ratio · sur-édités > "
                f"{payload.overedit_threshold:g})",
                f"Intervention (CCR · ratio · over-edited > "
                f"{payload.overedit_threshold:g})",
            ),
            _num(row.ccr),
            _num(row.change_ratio),
            str(row.n_overedited),
        ),
        _row(
            localized(
                lang,
                f"Insertions (part · lourds > {payload.insertion_threshold:g} "
                f"· longueur)",
                f"Insertions (share · heavy > {payload.insertion_threshold:g} "
                f"· length)",
            ),
            _num(row.char_ins_ratio),
            str(row.n_hallucination_heavy),
            _num(row.length_ratio),
        ),
        _row(
            localized(
                lang,
                "Absorption (corrigées · introduites · net)",
                "Absorption (corrected · introduced · net)",
            ),
            str(row.corrected),
            str(row.introduced),
            f"{row.net_improvement:+d}",
        ),
        _row(
            localized(
                lang,
                "Sur-normalisation (mots OCR-justes dégradés)",
                "Over-normalization (OCR-correct words degraded)",
            ),
            f"{row.n_over_normalized}/{row.n_correct_ocr_words}",
            _num(row.over_normalization),
            "",
        ),
        _row(
            localized(
                lang,
                f"Éditions consécutives (médiane · max · part > "
                f"{payload.edit_run_threshold})",
                f"Consecutive edits (median · max · share > "
                f"{payload.edit_run_threshold})",
            ),
            _num(row.edit_run_median),
            str(row.edit_run_max),
            _num(row.edit_run_share),
        ),
    ]
    documents_label = localized(
        lang,
        f"{row.n_documents} documents",
        f"{row.n_documents} documents",
    )
    parts = [
        f"<h4>{escape(row.pipeline)} — {documents_label}{missing}</h4>\n"
        '<table class="data">\n<tbody>' + "".join(rows) + "</tbody>\n</table>\n"
    ]
    if row.worst_regressions:
        regression_rows = "".join(
            f'<tr><td class="eng-cell">{escape(sample.document_id)}</td>'
            f'<td class="disp">{sample.cmer_raw:.4f}</td>'
            f'<td class="disp">{sample.cmer_corrected:.4f}</td>'
            f'<td class="disp">{sample.delta:+.4f}</td></tr>'
            for sample in row.worst_regressions
        )
        worst_summary = localized(
            lang,
            f"Pires régressions ({len(row.worst_regressions)})",
            f"Worst regressions ({len(row.worst_regressions)})",
        )
        th_document = localized(lang, "document", "document")
        th_cmer_raw = localized(lang, "cmer brut", "cmer raw")
        th_cmer_corrected = localized(lang, "cmer corrigé", "cmer corrected")
        parts.append(
            f'<details><summary class="muted">{worst_summary}</summary>'
            f'<table class="data">\n<thead><tr><th>{th_document}</th>'
            f'<th class="num-cell">{th_cmer_raw}</th>'
            f'<th class="num-cell">{th_cmer_corrected}</th>'
            '<th class="num-cell">Δ</th></tr></thead>\n'
            f"<tbody>{regression_rows}</tbody>\n</table></details>\n"
        )
    if row.over_normalized_samples:
        # #16 : flux mot OCR-juste → forme du correcteur (« ∅ » = supprimé).
        flows = "".join(
            f'<div class="wf-row">'
            f'<span class="wf-word wf-src">{escape(s.reference)}</span>'
            f'<span class="wf-arrow">→</span>'
            f'<span class="wf-word">{escape(s.corrected)}</span>'
            f'<span class="wf-meta">{escape(s.document_id)}</span></div>'
            for s in row.over_normalized_samples
        )
        over_summary = localized(
            lang,
            f"Mots sur-normalisés ({len(row.over_normalized_samples)} exemples "
            f"— mot OCR-juste → forme du correcteur)",
            f"Over-normalized words ({len(row.over_normalized_samples)} examples "
            f"— OCR-correct word → corrector's form)",
        )
        parts.append(
            f'<details><summary class="muted">{over_summary}</summary>\n'
            f'<div class="wflow">{flows}</div></details>\n'
        )
    return "".join(parts)


def _block(view: str, payload: CorrectionPayload, lang: str) -> str:
    head = localized(
        lang,
        f"{escape(view)} — bilan de correction",
        f"{escape(view)} — correction balance",
    )
    prose = localized(
        lang,
        '<p class="muted">Pipelines 2 étages (OCR → correcteur) : le triplet '
        "compte les documents améliorés/dégradés (jamais le pref seul) ; CCR "
        "mesure combien le correcteur a touché, indépendamment de la justesse "
        "(à qualité égale, préférer l'intervention minimale) ; l'absorption "
        "compte les mots corrigés vs introduits ; les longues séquences "
        "d'éditions signalent une réécriture de passage. Étage absent = "
        "matérialisé vide (erreur maximale), jamais exclu en silence.</p>\n",
        '<p class="muted">2-stage pipelines (OCR → corrector): the triplet '
        "counts improved/degraded documents (never pref alone); CCR "
        "measures how much the corrector touched, regardless of correctness "
        "(at equal quality, prefer minimal intervention); absorption "
        "counts corrected vs introduced words; long edit runs "
        "signal a passage rewrite. Missing stage = "
        "materialized empty (maximal error), never silently excluded.</p>\n",
    )
    return (
        f"<h3>{head}</h3>\n"
        + prose
        + "".join(_pipeline_block(row, payload, lang) for row in payload.pipelines)
    )


class CorrectionSection:
    """Bilan de l'étage de correction, par pipeline 2 étages."""

    name = "correction"
    requires: tuple[str, ...] = ()

    def render(self, result: RunResult, ctx: SectionContext) -> Html | None:
        blocks = [
            _block(analysis.view, analysis.payload, ctx.lang)
            for analysis in result.analyses
            if isinstance(analysis.payload, CorrectionPayload)
        ]
        if not blocks:
            return None
        title = localized(ctx.lang, "Bilan de correction", "Correction balance")
        return Html(f"<h2>{title}</h2>\n" + "".join(blocks))


__all__ = ["CorrectionSection"]
