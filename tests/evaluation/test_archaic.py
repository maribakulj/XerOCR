"""``air``/``hcpr`` : apport net & préservation d'archaïsmes + listes/empreinte.

Valeurs **dérivées à la main** (jamais d'oracle exécuté) : la liste par défaut
``archaic_core`` est connue, les alignements sont triviaux sur des cas courts.
"""

from __future__ import annotations

import pytest

from xerocr.evaluation.archaic import (
    ARCHAIC_LISTS,
    DEFAULT_ARCHAIC_LIST,
    air_observation,
    archaic_list_hash,
    hcpr_observation,
    resolve_archaic_list,
)
from xerocr.evaluation.context import DocContext
from xerocr.evaluation.errors import EvaluationError
from xerocr.evaluation.metrics.archaic import make_air_metric, make_hcpr_metric

_CHARS = resolve_archaic_list(DEFAULT_ARCHAIC_LIST).chars
_LONG_S = "ſ"
_THORN = "þ"
_E_ABOVE = "ͤ"  # marque suscrite des formes aͤ/oͤ/uͤ


def _ctx(reference: str, hypothesis: str) -> DocContext:
    return DocContext(document_id="d", reference=reference, hypothesis=hypothesis)


# --- air : apport net (sur-historicisation) ---------------------------------


def test_air_inserted_long_s() -> None:
    # GT « messe » écrit en clair, sortie « meſſe » → 2 ſ insérés sur 2 → 1.0.
    obs = air_observation("messe", f"me{_LONG_S}{_LONG_S}e", _CHARS)
    assert obs is not None and obs.value == 1.0 and obs.weight == 2


def test_air_faithful_archaism_is_not_added() -> None:
    # La GT porte déjà les ſ, la sortie les recopie → apport net nul.
    obs = air_observation(f"me{_LONG_S}{_LONG_S}e", f"me{_LONG_S}{_LONG_S}e", _CHARS)
    assert obs is not None and obs.value == 0.0 and obs.weight == 2


def test_air_none_when_output_has_no_archaic() -> None:
    assert air_observation("messe", "messe", _CHARS) is None


def test_air_combining_mark_inserted() -> None:
    # marque suscrite ◌ͤ ajoutée (aͤ) là où la GT a « a » nu.
    obs = air_observation("a", f"a{_E_ABOVE}", _CHARS)
    assert obs is not None and obs.value == 1.0 and obs.weight == 1


# --- hcpr : préservation ----------------------------------------------------


def test_hcpr_all_lost() -> None:
    obs = hcpr_observation(f"me{_LONG_S}{_LONG_S}e", "messe", _CHARS)
    assert obs is not None and obs.value == 0.0 and obs.weight == 2


def test_hcpr_all_preserved() -> None:
    ref = f"me{_LONG_S}{_LONG_S}e"
    obs = hcpr_observation(ref, ref, _CHARS)
    assert obs is not None and obs.value == 1.0 and obs.weight == 2


def test_hcpr_partial() -> None:
    # ſ perdu, þ conservé → 1 préservé sur 2.
    obs = hcpr_observation(f"{_LONG_S}a{_THORN}", f"sa{_THORN}", _CHARS)
    assert obs is not None and obs.value == 0.5 and obs.weight == 2


def test_hcpr_none_when_gt_has_no_archaic() -> None:
    assert hcpr_observation("messe", "messe", _CHARS) is None


# --- listes nommées + empreinte (reproductibilité) --------------------------


def test_default_list_is_archaic_core() -> None:
    assert DEFAULT_ARCHAIC_LIST == "archaic_core"
    assert _LONG_S in _CHARS and _THORN in _CHARS and _E_ABOVE in _CHARS


def test_modern_ambiguous_chars_excluded_from_default() -> None:
    # œ æ ß ç et accents modernes sont langue-relatifs → hors défaut (Q4).
    for char in ("œ", "æ", "ß", "ç", "é", "à"):
        assert char not in _CHARS


def test_hash_is_deterministic_and_order_independent() -> None:
    assert archaic_list_hash("ſþ") == archaic_list_hash("þſ")
    assert archaic_list_hash(_CHARS) == archaic_list_hash(ARCHAIC_LISTS["archaic_core"])


def test_hash_differs_for_different_lists() -> None:
    assert archaic_list_hash("ſ") != archaic_list_hash("ſþ")


def test_resolve_default_and_unknown() -> None:
    resolved = resolve_archaic_list()
    assert resolved.name == "archaic_core"
    assert resolved.list_hash == archaic_list_hash(resolved.chars)
    with pytest.raises(EvaluationError):
        resolve_archaic_list("does_not_exist")


# --- fabriques de métriques (liée à une liste) ------------------------------


def test_metric_factories_bind_list() -> None:
    air = make_air_metric(_CHARS)
    hcpr = make_hcpr_metric(_CHARS)
    assert air.name == "air" and air.spec.higher_is_better is False
    assert hcpr.name == "hcpr" and hcpr.spec.higher_is_better is True
    obs = air.fn(_ctx("messe", f"me{_LONG_S}{_LONG_S}e"))
    assert obs is not None and obs.value == 1.0
