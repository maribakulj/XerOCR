"""Garde-fou : le dispatch moteur→spec est **exhaustif**, sans retombée muette.

``app.run_planning.plan_ocr_run`` ne doit jamais assembler silencieusement une
spec *tesseract* pour un moteur **différent**. Comportement correct : soit une
spec du bon moteur, soit un **refus explicite** (``RunPlanningError``). Verrou de
non-régression : il échoue si un moteur non câblé retombe sur tesseract.
"""

from __future__ import annotations

from pathlib import Path

from xerocr.app.run_planning import RunPlanningError, plan_ocr_run
from xerocr.domain.corpus import CorpusSpec
from xerocr.domain.documents import DocumentRef


def _corpus() -> CorpusSpec:
    return CorpusSpec(
        name="t",
        documents=(DocumentRef(id="d", image_uri="d.png", ground_truths=()),),
    )


def test_non_tesseract_engine_never_silently_builds_tesseract(
    tmp_path: Path,
) -> None:
    try:
        build = plan_ocr_run("mistral", _corpus(), "r-1")
    except RunPlanningError:
        return  # refus explicite = comportement attendu
    spec = build(tmp_path)
    adapters = {
        step.adapter_name for pipe in spec.pipelines for step in pipe.steps
    }
    assert not any(a.startswith("tesseract") for a in adapters), (
        f"'mistral' a produit une spec tesseract (retombée muette) : {adapters}"
    )
