"""Surface T5 élargie : reconnaisseur **par bloc** OCR réel **ou** VLM zero-shot.

Le slot de fan-out accepte tout moteur ``IMAGE → RAW_TEXT`` — donc « segmenteur
→ Mistral OCR par bloc → ALTO » et « segmenteur → VLM par bloc → ALTO ». Ces
tests verrouillent (1) le nom d'adapter + kwargs construits par moteur, (2) le
rejet d'un reconnaisseur inconnu, (3) le catalogue offert à l'UI (OCR + VLM).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cinoc.app.engines import EngineStatus
from cinoc.app.run_planning import RunPlanningError
from cinoc.app.structure_planning import (
    hybrid_recognizer_catalog,
    plan_hybrid_run,
)
from cinoc.domain.corpus import CorpusSpec


def _recognize_step(ocr: str, **kw: object):
    run_spec = plan_hybrid_run(
        CorpusSpec(name="c", documents=()),
        "r",
        segmenter="precomputed_layout",
        ocr=ocr,
        **kw,  # type: ignore[arg-type]
    )(Path("/unused"))
    _segment, recognize, _assemble = run_spec.pipelines[0].steps
    return recognize, run_spec.adapter_kwargs


def test_mistral_ocr_is_a_valid_per_block_recognizer() -> None:
    recognize, kwargs = _recognize_step("mistral_ocr")
    assert recognize.adapter_name == "mistral_ocr:hybrid"
    assert recognize.fanout is True
    assert recognize.crop is True  # OCR cloud par bloc → découpe l'image
    assert kwargs["mistral_ocr:hybrid"] == {"label": "hybrid", "lang": "fra"}


def test_vlm_per_block_runs_zero_shot_with_prompt() -> None:
    recognize, kwargs = _recognize_step(
        "openai", model="gpt-4o", prompt="Transcris fidèlement ce bloc."
    )
    assert recognize.adapter_name == "openai:hybrid"
    assert recognize.crop is True
    # Un VLM par bloc transcrit l'image en rôle zero_shot (prompt optionnel).
    assert kwargs["openai:hybrid"] == {
        "label": "hybrid",
        "role": "zero_shot",
        "model": "gpt-4o",
        "prompt": "Transcris fidèlement ce bloc.",
    }


def test_ocr_model_passes_through_for_engines_that_need_it() -> None:
    _recognize, kwargs = _recognize_step("kraken", model="/m.mlmodel", lang="lat")
    assert kwargs["kraken:hybrid"] == {
        "label": "hybrid",
        "lang": "lat",
        "model": "/m.mlmodel",
    }


def test_unknown_recognizer_is_refused() -> None:
    with pytest.raises(RunPlanningError, match="reconnaisseur par région inconnu"):
        plan_hybrid_run(
            CorpusSpec(name="c", documents=()),
            "r",
            segmenter="precomputed_layout",
            ocr="not_a_real_engine",
        )(Path("/unused"))


def test_catalog_lists_ocr_and_vlm_with_availability() -> None:
    statuses = (
        EngineStatus(kind="tesseract", label="Tesseract", available=True, detail=""),
        EngineStatus(
            kind="mistral_ocr", label="Mistral OCR", available=False, detail="no key"
        ),
        EngineStatus(kind="openai", label="OpenAI", available=True, detail=""),
    )
    catalog = hybrid_recognizer_catalog(statuses)
    by_kind = {entry["kind"]: entry for entry in catalog}
    assert by_kind["tesseract"] == {
        "kind": "tesseract",
        "label": "Tesseract",
        "available": True,
        "vlm": False,
    }
    assert by_kind["mistral_ocr"]["available"] is False
    assert by_kind["mistral_ocr"]["vlm"] is False  # OCR clé-en-main, pas VLM ici
    assert by_kind["openai"]["vlm"] is True  # VLM (transcription zero-shot par bloc)
    # precomputed_region (démo) n'est jamais offert à l'UI.
    assert "precomputed_region" not in by_kind
