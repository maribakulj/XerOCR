"""Garde-fou : le dispatch moteur→spec est **exhaustif**, sans retombée muette.

``runs._spec_builder`` ne doit jamais assembler silencieusement une spec
*tesseract* pour un moteur **différent**. Aujourd'hui, sélectionner ``mistral``
(moteur enregistré au registre, hors ``LLM_KINDS``) retombe sur la branche
tesseract → un run faux et silencieux. Comportement correct : soit une spec du
bon moteur, soit un **refus explicite** (``HTTPException``).

``xfail(strict)`` jusqu'à ce que ``_spec_builder`` traite ``mistral``
correctement ou le refuse.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import HTTPException

from xerocr.domain.corpus import CorpusSpec
from xerocr.domain.documents import DocumentRef
from xerocr.interfaces.web.routers.runs import _spec_builder


def _corpus() -> CorpusSpec:
    return CorpusSpec(
        name="t",
        documents=(DocumentRef(id="d", image_uri="d.png", ground_truths=()),),
    )


@pytest.mark.xfail(
    strict=True,
    reason="dispatch moteur non exhaustif : 'mistral' ne doit pas produire "
    "une spec tesseract (retombée muette).",
)
def test_non_tesseract_engine_never_silently_builds_tesseract(
    tmp_path: Path,
) -> None:
    try:
        build = _spec_builder("mistral", _corpus(), "r-1")
    except HTTPException:
        return  # refus explicite = comportement acceptable
    spec = build(tmp_path)
    adapters = {
        step.adapter_name for pipe in spec.pipelines for step in pipe.steps
    }
    assert not any(a.startswith("tesseract") for a in adapters), (
        f"'mistral' a produit une spec tesseract (retombée muette) : {adapters}"
    )
