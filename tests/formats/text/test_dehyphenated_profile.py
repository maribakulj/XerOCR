"""Profil ``dehyphenated`` : ne pas punir un correcteur qui recolle.

Un post-correcteur qui réunit correctement un mot coupé en fin de ligne produit
un texte plus court que la référence ligne à ligne. **Sans normalisation, il est
pénalisé pour avoir bien fait.**

Ce que ce profil n'est pas : un moyen de faire baisser l'erreur. Appliqué des
deux côtés sur ``corpus/37-GT-BNL``, il la fait légèrement *monter* — 0,1119 →
0,1133 — parce qu'un mot recollé concentre en un seul long mot faux ce qui était
une moitié juste et une moitié fausse. C'est une **option de comparaison**,
jamais un défaut.
"""

from __future__ import annotations

import pytest

from cinoc.formats.text.normalization import DEHYPHENATE, get_builtin_profile


@pytest.fixture
def profil():
    return get_builtin_profile("dehyphenated")


def test_the_whole_break_repertoire_is_covered(profil) -> None:
    """Le tiret ASCII ne suffit pas : la Fraktur utilise ``⸗``, l'imprimé
    ancien ``¬``, et Unicode compte trois autres tirets de coupure.

    Une table qui n'en couvrirait qu'une partie recollerait certains mots et
    pas d'autres — un traitement inégal, plus trompeur que pas de traitement.
    """
    for marque in ("-", "‐", "‑", "–", "¬", "⸗"):
        assert profil.normalize(f"cou{marque}\npé") == "coupé", marque
    assert len(DEHYPHENATE) == 6


def test_the_soft_hyphen_is_out_of_reach_and_says_so(profil) -> None:
    """U+00AD ne peut **pas** être recollé ici, et la table ne prétend pas le
    faire.

    L'ordre canonique de ``normalize`` retire les invisibles *avant* la table :
    le tiret conditionnel est déjà parti quand elle passe. Une entrée pour lui
    serait morte et laisserait croire à une couverture qui n'existe pas.

    Le cas réel est couvert en amont : le parser ALTO ramène le ``<HYP>``
    U+00AD au tiret ordinaire à la lecture.
    """
    assert "\u00ad\n" not in DEHYPHENATE
    assert profil.normalize("cou\u00ad\npé") == "cou\npé"


def test_a_break_mid_line_is_left_alone(profil) -> None:
    """Un trait d'union **dans** une ligne n'est pas une coupure.

    Le recoller changerait « arc-en-ciel » en « arcenciel » : une faute
    introduite par la mesure elle-même.
    """
    assert profil.normalize("un arc-en-ciel entier") == "un arc-en-ciel entier"


def test_line_breaks_without_a_mark_survive(profil) -> None:
    assert profil.normalize("deux lignes\nsans coupure") == "deux lignes\nsans coupure"


def test_it_is_symmetric_by_construction(profil) -> None:
    """Le profil s'applique **des deux côtés** — c'est ce qui rend la
    comparaison équitable, et c'est la raison de le mettre ici plutôt que
    dans le projecteur, qui ne voit qu'un côté."""
    reference = "un mot cou-\npé ici"
    hypothese_qui_recolle = "un mot coupé ici"
    assert profil.normalize(reference) == profil.normalize(hypothese_qui_recolle)


def test_a_corrector_that_rejoins_is_no_longer_punished(profil) -> None:
    """Le cas mesuré, réduit à une phrase.

    Sans le profil, la référence et l'hypothèse diffèrent d'un caractère de
    coupure et d'un saut de ligne, alors qu'elles disent la même chose.
    """
    reference = "les tra-\nvailleurs ruraux"
    recolle = "les travailleurs ruraux"
    assert reference != recolle
    assert profil.normalize(reference) == profil.normalize(recolle)


def test_it_is_not_a_default(profil) -> None:
    """Le profil neutre ne recolle rien : activer ce traitement est un choix
    explicite, pas un effet de bord."""
    neutre = get_builtin_profile("nfc")
    assert neutre.normalize("cou-\npé") == "cou-\npé"
