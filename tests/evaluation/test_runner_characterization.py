"""Filet de caractérisation (Phase 1.1) : snapshot complet du ``RunResult``.

But : **figer la sortie observable** de ``evaluate_run`` sur un scénario réel et
déterministe, **avant** tout recâblage du runner (Phase 5). Un golden JSON est
comparé à la reconstruction live ; les flottants sont arrondis à la comparaison
pour absorber la dérive ULP inter-versions de ``scipy`` (p-values) **sans**
masquer une vraie régression métrique (ordres de grandeur ≫ 1e-6).

Ce filet ne teste **aucun** comportement nouveau : il documente l'existant pour
que la simplification du runner prouve une sortie *identique*.

Régénération **délibérée** du golden (acte conscient, jamais automatique en
test) ::

    python tests/evaluation/test_runner_characterization.py --generate
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from xerocr.domain.artifacts import Artifact, ArtifactType
from xerocr.domain.corpus import CorpusSpec
from xerocr.domain.documents import DocumentRef, GroundTruthRef
from xerocr.domain.evaluation import EvaluationSpec, EvaluationView
from xerocr.domain.pipeline import PipelineSpec
from xerocr.domain.run import RunManifest
from xerocr.evaluation.registry import MetricRegistry, register_default_metrics
from xerocr.evaluation.result import RunResult
from xerocr.evaluation.runner import evaluate_run

_FIXED = datetime(2026, 1, 1, tzinfo=UTC)
_GOLDEN = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "characterization"
    / "runner_runresult.json"
)

#: Scénario figé : 6 documents × 3 pipelines (alpha parfait, beta 2 err/doc,
#: gamma 1 err/doc), vue texte sans profil (sauts de ligne préservés). Connu pour
#: produire les 9 familles d'analyse first-party du chemin texte.
_GT_TEXTS = ("abcdefgh", "ijklmnop", "qrstuvwx", "yzabcdef", "ghijklmn", "opqrstuv")
_VIEW = EvaluationView(
    name="text",
    candidate_types=frozenset({ArtifactType.RAW_TEXT}),
    metric_names=("cer",),
)
_EXPECTED_FAMILIES = frozenset(
    {
        "inference",
        "diagnostics",
        "taxonomy",
        "document_texts",
        "document_lines",
        "textual_fidelity",
        "inter_engine",
        "lines",
        "word_errors",
    }
)


def _candidate(document_id: str, uri: Path) -> Artifact:
    return Artifact(
        id=f"{document_id}:precomputed:raw_text",
        document_id=document_id,
        type=ArtifactType.RAW_TEXT,
        uri=str(uri),
    )


def build_characterization_run(tmp_path: Path) -> RunResult:
    """Construit un ``RunResult`` déterministe depuis un corpus en mémoire."""
    documents: list[DocumentRef] = []
    outputs: dict[str, dict[str, dict[ArtifactType, Artifact]]] = {
        "alpha": {},
        "beta": {},
        "gamma": {},
    }
    for i, text in enumerate(_GT_TEXTS):
        doc_id = f"d{i}"
        gt = tmp_path / f"{doc_id}.gt.txt"
        gt.write_text(text, encoding="utf-8")
        documents.append(
            DocumentRef(
                id=doc_id,
                ground_truths=(
                    GroundTruthRef(type=ArtifactType.RAW_TEXT, uri=str(gt)),
                ),
            )
        )
        for name, hyp in (
            ("alpha", text),
            ("beta", "XY" + text[2:]),
            ("gamma", "X" + text[1:]),
        ):
            path = tmp_path / f"{doc_id}.{name}.txt"
            path.write_text(hyp, encoding="utf-8")
            outputs[name][doc_id] = {ArtifactType.RAW_TEXT: _candidate(doc_id, path)}
    manifest = RunManifest(
        run_id="char",
        corpus_name="char-corpus",
        n_documents=len(_GT_TEXTS),
        pipeline_specs=tuple(
            PipelineSpec(name=n, initial_inputs=(ArtifactType.IMAGE,))
            for n in ("alpha", "beta", "gamma")
        ),
        code_version="char-1.0",
        started_at=_FIXED,
        completed_at=_FIXED,
    )
    registry = MetricRegistry()
    register_default_metrics(registry)
    return evaluate_run(
        corpus=CorpusSpec(name="char-corpus", documents=tuple(documents)),
        evaluation=EvaluationSpec(views=(_VIEW,)),
        pipeline_outputs=outputs,
        registry=registry,
        manifest=manifest,
    )


def _round_floats(obj: Any) -> Any:
    """Arrondit récursivement les flottants (absorbe la dérive ULP de scipy)."""
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, float):
        return round(obj, 6)
    if isinstance(obj, list):
        return [_round_floats(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _round_floats(v) for k, v in obj.items()}
    return obj


def _canonical(payload: str) -> Any:
    return _round_floats(json.loads(payload))


def test_runresult_matches_golden(tmp_path: Path) -> None:
    result = build_characterization_run(tmp_path)
    dumped = result.model_dump_json()
    # Garde-fou anti-fuite : aucun chemin temporaire absolu ne doit transiter
    # dans la sortie (sinon le golden serait dépendant de l'environnement).
    assert str(tmp_path) not in dumped
    actual = _canonical(dumped)
    expected = _canonical(_GOLDEN.read_text(encoding="utf-8"))
    assert actual == expected, (
        "Le RunResult diverge du golden de caractérisation. Si le changement "
        "est VOULU, régénère puis relis le diff avant de committer :\n"
        "  python tests/evaluation/test_runner_characterization.py --generate"
    )


def test_scenario_still_covers_rich_families(tmp_path: Path) -> None:
    """Invariant sémantique (au-delà du golden brut) : les 9 familles texte.

    Si une future évolution change l'ensemble des familles produites, ce test
    le signale **indépendamment** du golden d'octets — utile pour distinguer un
    changement de *valeurs* d'un changement de *structure*.
    """
    result = build_characterization_run(tmp_path)
    kinds = {a.payload.kind for a in result.analyses}
    assert kinds == set(_EXPECTED_FAMILIES)


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as _tmp:
        _run = build_characterization_run(Path(_tmp))
    _GOLDEN.parent.mkdir(parents=True, exist_ok=True)
    _GOLDEN.write_text(_run.model_dump_json(indent=2) + "\n", encoding="utf-8")
    print(f"golden écrit : {_GOLDEN} ({len(_run.analyses)} familles d'analyse)")
