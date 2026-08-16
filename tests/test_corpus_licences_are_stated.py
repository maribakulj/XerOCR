"""Un corpus sans licence énoncée est un corpus que personne ne peut
rediffuser — nous compris.

Cette garde arrive de `saknussemm` le 2026-08-16, avec les corpus qu'elle
gardait. Elle y avait un sens tant que les corpus y vivaient ; l'y laisser
l'aurait rendue verte et vide, ce qui est la façon dont une garde cesse de
garder sans que personne s'en aperçoive.

Elle est délibérément faible sur la forme et forte sur l'absence : elle ne
juge pas une licence, elle refuse qu'il n'y en ait pas d'écrite. Trancher
un droit de rediffusion est un travail humain ; constater qu'il n'a pas été
tranché ne l'est pas.
"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_CORPUS = _REPO_ROOT / "corpus"


def _corpus_dirs() -> list[Path]:
    if not _CORPUS.is_dir():
        return []
    return sorted(p for p in _CORPUS.iterdir() if p.is_dir())


def test_there_are_corpora_to_check() -> None:
    """Vert par vacuité ressemblerait exactement à vert.

    Si les corpus repartent un jour, ce test doit tomber et forcer la
    question — plutôt que de laisser la garde passer sur rien.
    """
    assert _corpus_dirs(), (
        f"aucun corpus sous {_CORPUS}. S'ils ont déménagé, cette garde les "
        "suit ; s'ils ont disparu, supprimez-la plutôt que de la laisser "
        "verte sur un dossier vide."
    )


def test_every_corpus_states_its_licence() -> None:
    missing: list[str] = []
    unsettled: list[str] = []
    for directory in _corpus_dirs():
        readme = directory / "README.md"
        if not readme.is_file():
            missing.append(directory.name)
            continue
        text = readme.read_text(encoding="utf-8").lower()
        if "licence" not in text and "license" not in text and "cc0" not in text:
            missing.append(directory.name)
        if "à vérifier" in text or "to verify" in text:
            unsettled.append(directory.name)

    assert not missing, (
        f"corpus sans licence énoncée : {missing}. Écrivez la déclaration "
        "de la source, ou retirez le corpus — un corpus qu'on ne peut pas "
        "rediffuser n'a rien à faire dans un dépôt public."
    )
    assert not unsettled, (
        f"corpus dont la licence est marquée à vérifier : {unsettled}. "
        "Une réserve non levée est une réserve, pas une licence."
    )
