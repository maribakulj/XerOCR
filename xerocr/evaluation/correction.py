"""Bilan de **correction** : que vaut l'étage LLM d'un pipeline ? (couche 3)

Fonction d'analyse par vue (pattern ``calibration_analysis``) : pour chaque
pipeline **2 étages** (au moins un ``CORRECTED_TEXT`` produit), charge les
textes GT / brut / corrigé, les prépare **comme au scoring** (même
``prepare_text`` que le runner), et mesure sur les paires alignées :

- **triplet de non-régression** (signe de Δcmer par document, égalités
  strictes) + ``pref = improvement − regression`` + taux catastrophique ;
- **pcis** (SPEC §4.2 — non borné : macro + médiane + comptage |pcis| > 1) ;
- **ampleur d'intervention** (Koynov 2025) : CCR = MER(brut ↔ corrigé),
  ``change_ratio``, ``length_ratio``, drapeaux ``overedited`` ;
- **volume inséré** : ``char_ins_ratio`` = I/(H+S+D+I) sur (GT, corrigé) ;
- **absorption d'erreurs** (multiset de mots) : corrigées / introduites /
  conservées — le gain net ;
- **sur-normalisation** (positionnelle, mots) : mots OCR-justes dégradés ;
- **éditions consécutives** (R-2.6) : médiane/max/part des éditions en
  longues séquences — la signature d'une réécriture de passage.

R-1.8 : un étage absent est **matérialisé vide** (erreur maximale) + warning
et compté — jamais d'exclusion silencieuse. Un pipeline mono-étage n'a pas de
bilan (absence ≠ zéro muet).
"""

from __future__ import annotations

import logging
from collections import Counter
from collections.abc import Mapping
from statistics import fmean, median

from rapidfuzz.distance import Levenshtein

from xerocr.domain.artifacts import Artifact, ArtifactType
from xerocr.domain.corpus import CorpusSpec
from xerocr.domain.documents import DocumentRef
from xerocr.domain.evaluation import EvaluationView
from xerocr.evaluation.analysis import (
    Analysis,
    CorrectionPayload,
    OverNormalizedWord,
    PipelineCorrection,
    RegressionSample,
)
from xerocr.evaluation.representations import load_representation, prepare_text

logger = logging.getLogger(__name__)

#: Δcmer au-delà duquel une régression est « catastrophique » (R-2.3).
_CATASTROPHIC_THRESHOLD = 0.10
#: ``change_ratio`` au-delà duquel le correcteur a sur-édité (R-1.9).
_OVEREDIT_THRESHOLD = 2.0
#: Part d'insertions au-delà de laquelle un document est « hallucination
#: lourde » (R-1.3).
_HEAVY_INSERTION_THRESHOLD = 0.10
#: Longueur de séquence d'éditions au-delà de laquelle on parle de passage
#: réécrit (R-2.6).
_EDIT_RUN_THRESHOLD = 20
#: Plafonds d'échantillons embarqués (payload borné).
_MAX_TOKEN_SAMPLES = 12
_MAX_WORD_SAMPLES = 12
_MAX_REGRESSIONS = 10

_Outputs = Mapping[str, Mapping[str, Mapping[ArtifactType, Artifact]]]


def _counts(reference: str, hypothesis: str) -> tuple[int, int, int]:
    """(substitutions, suppressions, insertions) de l'alignement caractère."""
    substitutions = deletions = insertions = 0
    for op in Levenshtein.editops(reference, hypothesis):
        if op.tag == "replace":
            substitutions += 1
        elif op.tag == "delete":
            deletions += 1
        else:
            insertions += 1
    return substitutions, deletions, insertions


def _cmer(reference: str, hypothesis: str) -> tuple[float, int, int]:
    """``(cmer, edits, dénominateur)`` — dénominateur = H+S+D+I = len(ref)+I."""
    s, d, i = _counts(reference, hypothesis)
    total = len(reference) + i
    edits = s + d + i
    return (edits / total if total else 0.0), edits, total


def _edit_runs(reference: str, hypothesis: str) -> list[int]:
    """Longueurs des séquences d'éditions **consécutives** (blocs non-``equal``
    contigus de l'alignement) — une suppression suivie d'une insertion forme
    une seule séquence."""
    runs: list[int] = []
    current = 0
    for op in Levenshtein.opcodes(reference, hypothesis):
        if op.tag == "equal":
            if current:
                runs.append(current)
                current = 0
            continue
        current += max(op.src_end - op.src_start, op.dest_end - op.dest_start)
    if current:
        runs.append(current)
    return runs


def _missing(reference_words: list[str], words: list[str]) -> Counter[str]:
    """Occurrences de mots GT absentes de ``words`` (multiset, par mot)."""
    counts = Counter(words)
    out: Counter[str] = Counter()
    for word, n_ref in Counter(reference_words).items():
        lacking = n_ref - counts.get(word, 0)
        if lacking > 0:
            out[word] = lacking
    return out


def _aligned_words(
    reference_words: list[str], words: list[str]
) -> list[str | None]:
    """Mot aligné sur chaque mot GT (``None`` = supprimé) — blocs ``equal`` /
    ``replace`` mappés positionnellement (mécanique des pires lignes F15)."""
    aligned: list[str | None] = [None] * len(reference_words)
    for op in Levenshtein.opcodes(reference_words, words):
        if op.tag in ("equal", "replace"):
            for offset in range(op.src_end - op.src_start):
                aligned[op.src_start + offset] = words[op.dest_start + offset]
    return aligned


def _text_of(
    outputs: _Outputs,
    pipeline: str,
    document_id: str,
    kind: ArtifactType,
    view: EvaluationView,
) -> str | None:
    artifact = outputs.get(pipeline, {}).get(document_id, {}).get(kind)
    if artifact is None or artifact.uri is None:
        return None
    return prepare_text(str(load_representation(artifact.uri, kind)), view)


def _ground_truth(document: DocumentRef, view: EvaluationView) -> str | None:
    reference = document.gt_for(ArtifactType.RAW_TEXT)
    if reference is None:
        return None
    return prepare_text(
        str(load_representation(reference.uri, ArtifactType.RAW_TEXT)), view
    )


def _two_stage_pipelines(outputs: _Outputs) -> list[str]:
    return [
        pipeline
        for pipeline, by_document in outputs.items()
        if any(
            ArtifactType.CORRECTED_TEXT in artifacts
            for artifacts in by_document.values()
        )
    ]


def _safe_ratio(numerator: float, denominator: float) -> float | None:
    return numerator / denominator if denominator else None


def _pipeline_correction(
    pipeline: str, corpus: CorpusSpec, outputs: _Outputs, view: EvaluationView
) -> PipelineCorrection | None:
    n_missing_raw = n_missing_corrected = 0
    improvement = regression = no_change = n_catastrophic = 0
    pcis_values: list[float] = []
    ccr_edits = ccr_total = 0
    n_overedited = 0
    sys_insertions = sys_total = 0
    n_heavy = 0
    corrected_len = reference_len = 0
    errors_before = errors_after = n_corrected = n_introduced = n_kept = 0
    corrected_tokens: set[str] = set()
    introduced_tokens: set[str] = set()
    n_correct_ocr = n_over_normalized = 0
    over_samples: list[OverNormalizedWord] = []
    runs: list[int] = []
    regressions: list[RegressionSample] = []
    n_documents = 0
    raw_edits = raw_total = 0

    for document in corpus.documents:
        reference = _ground_truth(document, view)
        if reference is None:
            continue
        raw = _text_of(outputs, pipeline, document.id, ArtifactType.RAW_TEXT, view)
        corrected = _text_of(
            outputs, pipeline, document.id, ArtifactType.CORRECTED_TEXT, view
        )
        if raw is None:
            n_missing_raw += 1
            logger.warning(
                "[correction] %s · %s : étage brut absent — matérialisé vide "
                "(R-1.8).",
                pipeline,
                document.id,
            )
            raw = ""
        if corrected is None:
            n_missing_corrected += 1
            logger.warning(
                "[correction] %s · %s : étage corrigé absent — matérialisé "
                "vide (R-1.8).",
                pipeline,
                document.id,
            )
            corrected = ""
        n_documents += 1

        cmer_raw, raw_doc_edits, raw_doc_total = _cmer(reference, raw)
        raw_edits += raw_doc_edits
        raw_total += raw_doc_total
        s, d, i = _counts(reference, corrected)
        sys_edits, sys_denom = s + d + i, len(reference) + i
        cmer_corrected = sys_edits / sys_denom if sys_denom else 0.0
        sys_insertions += i
        sys_total += sys_denom
        if sys_denom and i / sys_denom > _HEAVY_INSERTION_THRESHOLD:
            n_heavy += 1
        corrected_len += len(corrected)
        reference_len += len(reference)

        delta = cmer_corrected - cmer_raw
        if delta < 0:
            improvement += 1
        elif delta > 0:
            regression += 1
            regressions.append(
                RegressionSample(
                    document_id=document.id,
                    cmer_raw=cmer_raw,
                    cmer_corrected=cmer_corrected,
                    delta=delta,
                )
            )
        else:
            no_change += 1
        if delta > _CATASTROPHIC_THRESHOLD:
            n_catastrophic += 1

        # pcis (SPEC §4.2) : qualité q = 1 − cmer ; q_brut nul → clamp.
        q_raw, q_sys = 1.0 - cmer_raw, 1.0 - cmer_corrected
        pcis_values.append(
            max(-1.0, min(1.0, q_sys)) if q_raw == 0 else (q_sys - q_raw) / q_raw
        )

        ccr_doc, edits, total = _cmer(raw, corrected)
        ccr_edits += edits
        ccr_total += total
        if cmer_raw > 0 and ccr_doc / cmer_raw > _OVEREDIT_THRESHOLD:
            n_overedited += 1

        reference_words = reference.split()
        raw_words, corrected_words = raw.split(), corrected.split()
        missing_before = _missing(reference_words, raw_words)
        missing_after = _missing(reference_words, corrected_words)
        errors_before += sum(missing_before.values())
        errors_after += sum(missing_after.values())
        for word in set(missing_before) | set(missing_after):
            before, after = missing_before.get(word, 0), missing_after.get(word, 0)
            n_kept += min(before, after)
            if before > after:
                n_corrected += before - after
                corrected_tokens.add(word)
            elif after > before:
                n_introduced += after - before
                introduced_tokens.add(word)

        aligned_raw = _aligned_words(reference_words, raw_words)
        aligned_corrected = _aligned_words(reference_words, corrected_words)
        for index, word in enumerate(reference_words):
            if aligned_raw[index] != word:
                continue
            n_correct_ocr += 1
            if aligned_corrected[index] != word:
                n_over_normalized += 1
                if len(over_samples) < _MAX_WORD_SAMPLES:
                    over_samples.append(
                        OverNormalizedWord(
                            document_id=document.id,
                            reference=word[:64],
                            corrected=(aligned_corrected[index] or "∅")[:64],
                        )
                    )
        runs.extend(_edit_runs(reference, corrected))

    if n_documents == 0:
        return None
    cmer_raw_micro = _safe_ratio(raw_edits, raw_total)
    ccr_micro = _safe_ratio(ccr_edits, ccr_total)
    big_runs = sum(r for r in runs if r > _EDIT_RUN_THRESHOLD)
    return PipelineCorrection(
        pipeline=pipeline,
        n_documents=n_documents,
        n_missing_raw=n_missing_raw,
        n_missing_corrected=n_missing_corrected,
        improvement_rate=improvement / n_documents,
        regression_rate=regression / n_documents,
        no_change_rate=no_change / n_documents,
        pref_score=(improvement - regression) / n_documents,
        n_catastrophic=n_catastrophic,
        catastrophic_rate=n_catastrophic / n_documents,
        pcis_macro=fmean(pcis_values) if pcis_values else None,
        pcis_median=median(pcis_values) if pcis_values else None,
        n_pcis_extreme=sum(1 for value in pcis_values if abs(value) > 1),
        ccr=ccr_micro,
        change_ratio=(
            ccr_micro / cmer_raw_micro
            if ccr_micro is not None and cmer_raw_micro
            else None
        ),
        length_ratio=_safe_ratio(corrected_len, reference_len),
        n_overedited=n_overedited,
        char_ins_ratio=_safe_ratio(sys_insertions, sys_total),
        n_hallucination_heavy=n_heavy,
        errors_before=errors_before,
        errors_after=errors_after,
        corrected=n_corrected,
        introduced=n_introduced,
        kept_wrong=n_kept,
        correction_rate=_safe_ratio(n_corrected, errors_before),
        introduction_rate=_safe_ratio(n_introduced, errors_after),
        net_improvement=n_corrected - n_introduced,
        corrected_samples=tuple(sorted(corrected_tokens)[:_MAX_TOKEN_SAMPLES]),
        introduced_samples=tuple(sorted(introduced_tokens)[:_MAX_TOKEN_SAMPLES]),
        n_correct_ocr_words=n_correct_ocr,
        n_over_normalized=n_over_normalized,
        over_normalization=_safe_ratio(n_over_normalized, n_correct_ocr),
        over_normalized_samples=tuple(over_samples),
        edit_run_median=float(median(runs)) if runs else None,
        edit_run_max=max(runs, default=0),
        edit_run_share=_safe_ratio(big_runs, sum(runs)),
        worst_regressions=tuple(
            sorted(regressions, key=lambda r: (-r.delta, r.document_id))[
                :_MAX_REGRESSIONS
            ]
        ),
    )


def correction_analysis(
    view: EvaluationView, corpus: CorpusSpec, outputs: _Outputs
) -> Analysis | None:
    """Payload ``correction`` de la vue, ou ``None`` sans pipeline 2 étages."""
    rows = [
        row
        for pipeline in _two_stage_pipelines(outputs)
        if (row := _pipeline_correction(pipeline, corpus, outputs, view))
        is not None
    ]
    if not rows:
        return None
    return Analysis(
        scope="corpus",
        view=view.name,
        payload=CorrectionPayload(
            metric="cmer",
            catastrophic_threshold=_CATASTROPHIC_THRESHOLD,
            overedit_threshold=_OVEREDIT_THRESHOLD,
            insertion_threshold=_HEAVY_INSERTION_THRESHOLD,
            edit_run_threshold=_EDIT_RUN_THRESHOLD,
            pipelines=tuple(rows),
        ),
    )


__all__ = ["correction_analysis"]
