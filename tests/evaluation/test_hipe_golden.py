"""Golden de conformité HIPE : nos scores vs le scorer officiel, à 1e-9.

Protocole (SPEC_HIPE §11) — **fixture vendorée**, pas d'exécution du scorer en
CI ordinaire :

1. Sur un poste **Python ≥ 3.12** : ``pip install xerocr[hipe-oracle]``
   (``hipe-ocrepair-scorer==0.9.9`` épinglé) ;
2. scorer le corpus d'exemple du dépôt officiel et vendorer la paire
   ``tests/fixtures/hipe_golden/input.jsonl`` (les enregistrements §4.8) +
   ``tests/fixtures/hipe_golden/expected.json`` (sortie du scorer :
   ``{"<pipeline>": {"cmer_micro": …, "cmer_macro": …}}``, bootstrap désactivé) ;
3. ce test recalcule alors les scores **par notre chemin** (profil ``hipe`` +
   ``cmer`` + conventions micro/macro §4.1) et exige l'égalité à 1e-9.

Tant que la fixture n'est pas vendorée, le test **skip avec message** (réserve
ouverte au DoD — jamais un faux vert silencieux). La parité locale de la
formule, elle, tourne à chaque CI via ``jiwer`` (``test_metrics_conformity``).
"""

from __future__ import annotations

import json
from pathlib import Path
from statistics import fmean

import pytest

from xerocr.evaluation.context import DocContext
from xerocr.evaluation.metrics.conformity import cmer
from xerocr.formats.text import get_builtin_profile

_FIXTURES = Path(__file__).parent.parent / "fixtures" / "hipe_golden"
_TOLERANCE = 1e-9

pytestmark = pytest.mark.skipif(
    not (_FIXTURES / "input.jsonl").is_file()
    or not (_FIXTURES / "expected.json").is_file(),
    reason=(
        "fixture golden HIPE non vendorée (générer input.jsonl + expected.json "
        "avec le scorer officiel sur Python ≥ 3.12 — voir docstring)"
    ),
)


def test_cmer_matches_official_scorer_at_1e9() -> None:
    profile = get_builtin_profile("hipe")
    expected = json.loads((_FIXTURES / "expected.json").read_text("utf-8"))
    observations = []
    for line in (_FIXTURES / "input.jsonl").read_text("utf-8").splitlines():
        record = json.loads(line)
        reference = profile.normalize(record["ground_truth"]["transcription_unit"])
        hypothesis = profile.normalize(
            record["ocr_postcorrection_output"]["transcription_unit"]
        )
        observations.append(
            cmer.fn(
                DocContext(
                    document_id=record["document_metadata"]["document_id"],
                    reference=reference,
                    hypothesis=hypothesis,
                )
            )
        )
    weights = sum(o.weight for o in observations if o is not None)
    micro = (
        sum(o.value * o.weight for o in observations if o is not None) / weights
    )
    macro = fmean(o.value for o in observations if o is not None)
    scores = expected["system"]
    assert micro == pytest.approx(scores["cmer_micro"], abs=_TOLERANCE)
    assert macro == pytest.approx(scores["cmer_macro"], abs=_TOLERANCE)
