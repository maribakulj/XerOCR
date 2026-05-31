"""CLI XerOCR (couche 8). T1 : la commande ``demo``.

``argparse`` (stdlib, aucune dépendance — journal D-007). ``demo`` génère un
rapport de démonstration **déterministe** sans moteur réel : un mini-corpus
pré-calculé en mémoire → ``precomputed`` → CER → ``RunResult`` → HTML autonome.
Les verbes ``run``/``compare``/``serve`` arrivent à leurs tranches (T2/T4).
"""

from __future__ import annotations

import argparse
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from tempfile import TemporaryDirectory

from xerocr.app import run as run_orchestrator
from xerocr.app.modules.registry import ModuleRegistry, register_default_modules
from xerocr.domain.artifacts import ArtifactType
from xerocr.domain.corpus import CorpusSpec
from xerocr.domain.documents import DocumentRef, GroundTruthRef
from xerocr.domain.evaluation import EvaluationSpec, EvaluationView
from xerocr.domain.pipeline import PipelineSpec, PipelineStep
from xerocr.domain.run_spec import RunSpec
from xerocr.reports import default_report_renderer

_ENGINES = ("tesseract", "pero")

#: Mini-corpus déterministe : (id, vérité-terrain, {moteur: sortie pré-calculée}).
_DEMO_DOCS: tuple[tuple[str, str, dict[str, str]], ...] = (
    (
        "folio_001",
        "Icy commence le prologue",
        {
            "tesseract": "Icy commence le prologve",
            "pero": "Icy commence le prologue",
        },
    ),
    (
        "folio_002",
        "maistre Jehan Froissart",
        {
            "tesseract": "maistre Jehan Froissart",
            "pero": "maistre Jehan Froiſſart",
        },
    ),
    (
        "folio_003",
        "les croniques de France",
        {
            "tesseract": "les croniques de France",
            "pero": "les croniques de France",
        },
    ),
)

_TEXT_VIEW = EvaluationView(
    name="text",
    candidate_types=frozenset({ArtifactType.RAW_TEXT}),
    metric_names=("cer", "wer", "mer"),
)


def _code_version() -> str:
    try:
        return version("xerocr")
    except PackageNotFoundError:  # pragma: no cover (paquet non installé)
        from xerocr.domain._version_fallback import FALLBACK_VERSION

        return FALLBACK_VERSION


def _write_demo_corpus(root: Path) -> CorpusSpec:
    documents: list[DocumentRef] = []
    for doc_id, ground_truth, engine_texts in _DEMO_DOCS:
        (root / f"{doc_id}.gt.txt").write_text(ground_truth, encoding="utf-8")
        for label, text in engine_texts.items():
            (root / f"{doc_id}.{label}.txt").write_text(text, encoding="utf-8")
        documents.append(
            DocumentRef(
                id=doc_id,
                image_uri=str(root / f"{doc_id}.png"),
                ground_truths=(
                    GroundTruthRef(
                        type=ArtifactType.RAW_TEXT,
                        uri=str(root / f"{doc_id}.gt.txt"),
                    ),
                ),
            )
        )
    return CorpusSpec(name="demo", documents=tuple(documents))


def _demo_run_spec(corpus: CorpusSpec) -> RunSpec:
    pipelines = tuple(
        PipelineSpec(
            name=label,
            initial_inputs=(ArtifactType.IMAGE,),
            steps=(
                PipelineStep(
                    id="ocr",
                    kind="ocr",
                    adapter_name=f"precomputed:{label}",
                    input_types=(ArtifactType.IMAGE,),
                    output_types=(ArtifactType.RAW_TEXT,),
                ),
            ),
        )
        for label in _ENGINES
    )
    adapter_kwargs = {
        f"precomputed:{label}": {"source_label": label} for label in _ENGINES
    }
    return RunSpec(
        corpus=corpus,
        pipelines=pipelines,
        evaluation=EvaluationSpec(views=(_TEXT_VIEW,)),
        adapter_kwargs=adapter_kwargs,
        run_id="demo",
    )


def demo_to_html() -> str:
    """Exécute la démo et renvoie le rapport HTML (déterministe)."""
    registry = ModuleRegistry()
    register_default_modules(registry)
    with TemporaryDirectory() as tmp:
        corpus = _write_demo_corpus(Path(tmp))
        result = run_orchestrator(
            _demo_run_spec(corpus),
            registry=registry,
            code_version=_code_version(),
        )
    return default_report_renderer().render(result, title="XerOCR — démonstration")


def _run_demo(output: str) -> int:
    path = Path(output)
    path.write_text(demo_to_html(), encoding="utf-8")
    print(f"Rapport de démonstration écrit : {path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="xerocr",
        description="Banc d'essai déterministe de pipelines de transcription.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    demo = subparsers.add_parser(
        "demo",
        help="Génère un rapport de démonstration déterministe (sans moteur).",
    )
    demo.add_argument(
        "-o", "--output", default="rapport_demo.html", help="Fichier HTML de sortie."
    )
    args = parser.parse_args(argv)
    if args.command == "demo":
        return _run_demo(args.output)
    return 1  # pragma: no cover (sous-commande requise)


__all__ = ["demo_to_html", "main"]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
