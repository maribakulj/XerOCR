"""Garde-fou contre la croissance silencieuse des fichiers (`CLAUDE.md` §5).

Tout fichier de ``xerocr/`` qui atteint le seuil doit avoir une entrée
**justifiée** dans :data:`FILE_BUDGETS`. Sinon le test échoue et force un choix
conscient :

1. **Refactor** pour rentrer sous le seuil (extraire un sous-module, élaguer).
2. **Relever le budget délibérément** : ajouter une entrée ici, justifiée dans le
   message de commit. La hausse devient un acte conscient, pas une dérive.

XerOCR démarre avec une table **vide** : aucun fichier ≥ 600 LOC aujourd'hui. La
table se remplira au fil des tranches, chaque entrée portant sa justification.
"""

from __future__ import annotations

from pathlib import Path

import pytest

XEROCR = Path(__file__).resolve().parents[2] / "xerocr"

#: Seuil de surveillance. Sous ce seuil, la couverture suffit ; au-dessus, une
#: entrée justifiée est obligatoire. (Détendu de 400 → 600 : changement de règle.)
THRESHOLD = 600

#: Chemin relatif (depuis ``xerocr/``) → budget en lignes. Vide au démarrage.
FILE_BUDGETS: dict[str, int] = {
    # Hub des payloads ``analyses`` : une **union discriminée** unique (un
    # membre par famille de métriques) + ses sous-modèles. La cohésion du
    # contrat prime sur l'éclatement (CLAUDE.md §5.2) — on ne fragmente pas
    # ``AnalysisPayload``. Le fichier grandit **par construction** d'un membre
    # par famille (axe 2). Budget relevé à la tranche 4f (15ᵉ payload ``ner`` :
    # 942 LOC) + ~15 %.
    "evaluation/analysis.py": 1083,
}


def _line_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").splitlines())


@pytest.mark.parametrize(("rel_path", "budget"), sorted(FILE_BUDGETS.items()))
def test_file_size_within_budget(rel_path: str, budget: int) -> None:
    path = XEROCR / rel_path
    assert path.exists(), (
        f"Fichier disparu : {rel_path}. Retire l'entrée de FILE_BUDGETS."
    )
    actual = _line_count(path)
    assert actual <= budget, (
        f"\n{rel_path} a {actual} lignes (budget {budget}).\n"
        "Refactor pour rentrer dans le budget, ou relève-le consciemment ici "
        "avec une justification dans le message de commit."
    )


def test_no_orphaned_budget_entries() -> None:
    missing = [p for p in FILE_BUDGETS if not (XEROCR / p).exists()]
    assert not missing, f"Entrées orphelines dans FILE_BUDGETS : {missing}."


def test_budget_table_covers_all_large_files() -> None:
    """Tout fichier ≥ THRESHOLD lignes doit avoir une entrée justifiée.

    Empêche un fichier nouveau ou subitement gros d'échapper à la surveillance.
    """
    untracked: list[tuple[str, int]] = []
    for path in XEROCR.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        rel = path.relative_to(XEROCR).as_posix()
        if rel in FILE_BUDGETS:
            continue
        count = _line_count(path)
        if count >= THRESHOLD:
            untracked.append((rel, count))
    assert not untracked, (
        f"\nFichiers ≥ {THRESHOLD} lignes non surveillés :\n"
        + "\n".join(f"  {p} ({n} lignes)" for p, n in sorted(untracked))
        + "\n\nAjoute-les à FILE_BUDGETS avec budget = current + ~15 %, "
        "ou splitte-les."
    )
