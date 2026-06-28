"""Ancrage Phase 1 — char-MER calculé à DEUX endroits doit rester d'accord.

La Phase 3 fusionnera les deux implémentations actuelles du Match Error Rate
caractère en un seul helper ``char_mer`` :

- ``evaluation.metrics.conformity.cmer`` (métrique de socle, ``Observation``) ;
- ``evaluation.correction._cmer`` (interne au collecteur de correction).

Ce test **fige les valeurs attendues à la main** sur des paires contrôlées, et
**vérifie qu'aujourd'hui les deux chemins produisent exactement les mêmes
nombres**. Après la fusion (Phase 3.1), ``char_mer`` devra reproduire ces valeurs
au bit près — sinon ce test casse et signale une dérive.

Convention (SPEC_HIPE §4.1) : ``value = (S+D+I) / (len(ref) + I)`` ; dénominateur
``H+S+D+I`` = ``weight`` ; deux textes vides → ``0.0``.
"""

from __future__ import annotations

import pytest

from cinoc.evaluation.context import DocContext
from cinoc.evaluation.correction import _cmer
from cinoc.evaluation.metrics.conformity import cmer

#: (référence, hypothèse, value attendue, dénominateur attendu, edits attendus).
#: Valeurs dérivées à la main depuis l'alignement caractère.
_CASES = [
    ("abc", "abc", 0.0, 3, 0),  # identiques
    ("abc", "abxc", 0.25, 4, 1),  # 1 insertion
    ("abc", "", 1.0, 3, 3),  # 3 suppressions
    ("ab", "abcd", 0.5, 4, 2),  # 2 insertions
    ("abc", "abd", 1 / 3, 3, 1),  # 1 substitution
    ("", "", 0.0, 0, 0),  # deux vides
]


@pytest.mark.parametrize(("ref", "hyp", "value", "denom", "edits"), _CASES)
def test_conformity_cmer_pinned(
    ref: str, hyp: str, value: float, denom: int, edits: int
) -> None:
    observation = cmer.fn(DocContext(document_id="d", reference=ref, hypothesis=hyp))
    assert observation.value == pytest.approx(value)
    assert observation.weight == denom


@pytest.mark.parametrize(("ref", "hyp", "value", "denom", "edits"), _CASES)
def test_correction_cmer_matches_conformity(
    ref: str, hyp: str, value: float, denom: int, edits: int
) -> None:
    got_value, got_edits, got_denom = _cmer(ref, hyp)
    assert got_value == pytest.approx(value)
    assert got_edits == edits
    assert got_denom == denom


@pytest.mark.parametrize(("ref", "hyp", "value", "denom", "edits"), _CASES)
def test_two_implementations_agree(
    ref: str, hyp: str, value: float, denom: int, edits: int
) -> None:
    """Le pin central : conformity.cmer et correction._cmer ne divergent pas."""
    observation = cmer.fn(DocContext(document_id="d", reference=ref, hypothesis=hyp))
    got_value, _got_edits, got_denom = _cmer(ref, hyp)
    assert observation.value == pytest.approx(got_value)
    assert observation.weight == got_denom
