"""Garde-fou : le dispatch concurrent→spec est **exhaustif**, sans retombée muette.

``plan_benchmark_run`` ne doit jamais assembler silencieusement une spec d'un
autre moteur pour un moteur/mode **non câblé** : soit la bonne spec, soit un
**refus explicite** (``RunPlanningError``). Verrou de non-régression du défaut
historique « ``mistral`` → tesseract ».
"""

from __future__ import annotations

import pytest

from xerocr.app.run_planning import (
    Competitor,
    RunPlanningError,
    plan_benchmark_run,
)
from xerocr.domain.corpus import CorpusSpec
from xerocr.domain.documents import DocumentRef


def _corpus() -> CorpusSpec:
    return CorpusSpec(
        name="t",
        documents=(DocumentRef(id="d", image_uri="d.png", ground_truths=()),),
    )


def test_uncabled_ocr_engine_is_refused() -> None:
    # 'mistral' n'est pas un moteur OCR : OCR seul (mode None) refusé, jamais
    # retombé en silence sur tesseract.
    with pytest.raises(RunPlanningError):
        plan_benchmark_run((Competitor(engine="mistral"),), _corpus(), "r-1")


def test_zero_shot_requires_vlm_engine() -> None:
    with pytest.raises(RunPlanningError):
        plan_benchmark_run(
            (Competitor(engine="tesseract", mode="zero_shot"),), _corpus(), "r-1"
        )


def test_text_only_requires_llm_provider() -> None:
    with pytest.raises(RunPlanningError):
        plan_benchmark_run(
            (Competitor(engine="tesseract", mode="text_only"),), _corpus(), "r-1"
        )


def test_text_and_image_rejects_text_only_provider() -> None:
    # ollama est text_only (pas de vision) → refusé en text_and_image.
    with pytest.raises(RunPlanningError):
        plan_benchmark_run(
            (Competitor(engine="tesseract", mode="text_and_image", llm="ollama"),),
            _corpus(),
            "r-1",
        )
