"""Profils ``hipe``/``heritage`` : sensibilité Unicode de la ``norm()`` HIPE.

Cas dérivés à la main depuis SPEC_HIPE §4.3 (la table du scorer officiel) —
jamais en exécutant le scorer (il reste l'oracle *exécuté* du golden, pas la
source des attendus écrits).
"""

from __future__ import annotations

import pytest

from xerocr.formats.text import get_builtin_profile

HIPE = get_builtin_profile("hipe")
HERITAGE = get_builtin_profile("heritage")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Œuvre", "oeuvre"),  # œ → oe (+ casse pliée)
        ("Cæsar", "caesar"),  # æ → ae
        ("Straße", "strasse"),  # ß → ss
        ("veꝛbum", "verbum"),  # r rotunda → r
        ("haͤuser", "häuser"),  # aͤ (décomposé) → ä (précomposé)
        ("schoͤn", "schön"),  # oͤ → ö
        ("Zei—\nle", "zeile"),  # césure DTA (tiret cadratin + saut)
        ("Zei¬\nle", "zeile"),  # césure DTA (¬ + saut)
        ("a,b!  c", "a b c"),  # non-mot → espace, espaces compactés
        ("a_b", "a b"),  # underscore → espace
        ("l'an 1515.", "l an 1515"),  # ponctuation → espace, bords rognés
        ("ligne1\nligne2", "ligne1 ligne2"),  # saut de ligne = non-mot
    ],
)
def test_hipe_profile_hand_cases(raw: str, expected: str) -> None:
    assert HIPE.normalize(raw) == expected


def test_hipe_profile_idempotent() -> None:
    witness = "Œuvre, Straße — haͤuser ; veꝛbum_l'an  1515 !"
    once = HIPE.normalize(witness)
    assert HIPE.normalize(once) == once


def test_heritage_preserves_patrimonial_forms() -> None:
    """``heritage`` plie casse/ponctuation comme ``hipe`` mais garde œ/æ/ꝛ."""
    assert HERITAGE.normalize("Œuvre, Cæsar !") == "œuvre cæsar"
    assert HERITAGE.normalize("veꝛbum") == "veꝛbum"
    # Césures et underscore restent traités (socle commun des deux profils).
    assert HERITAGE.normalize("Zei—\nle_x") == "zeile x"


def test_heritage_documented_limits() -> None:
    """Limites documentées du delta heritage : ß reste plié (casefold Python),
    et les umlauts décomposés restent recomposés (sinon ``\\W`` — fidèle au
    scorer — détruirait la marque combinante isolée)."""
    assert HERITAGE.normalize("Straße") == "strasse"
    assert HERITAGE.normalize("haͤuser") == "häuser"


def test_profiles_registered() -> None:
    assert HIPE.name == "hipe" and HERITAGE.name == "heritage"
    assert HIPE.as_dict()["non_word_to_space"] is True
