"""Garde-fou anti-dérive du statut (`CLAUDE.md §0` ⇄ roll-up `MIGRATION_PLAN.md`).

**Pourquoi ce test existe.** `CLAUDE.md §0` est resté gelé à l'ère T1
(« ~158 tests », « Prochaine étape = T2 ») longtemps **après** que T2→T4e furent
livrés ; cette consigne périmée s'est ensuite **propagée** dans les plans UI. La
cause : un statut **dupliqué** dans `§0` au lieu d'être **délégué** au roll-up
(la `rituel de réconciliation` du projet exige de mettre à jour les docs dans le
même commit que le code — ce qui n'a pas été tenu pour `§0`).

Ce test verrouille les trois travers **mécaniques** de cette dérive :

1. `§0` **délègue** au roll-up (référence `MIGRATION_PLAN.md`) ;
2. `§0` ne **fige pas** un compte de tests (la dérive « 158 → 356 ») ;
3. `§0` ne désigne **jamais** comme « Prochaine étape » une tranche que le
   roll-up marque déjà « ✅ fait » (le bug exact : « = T2 » alors que « T2 …
   ✅ fait »).
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _status_section() -> str:
    """Le bloc « ## 0. Statut actuel » de ``CLAUDE.md`` (jusqu'au titre suivant)."""
    text = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    start = text.index("## 0. Statut actuel")
    rest = text[start + 1 :]  # +1 : sauter le 1er '#' pour trouver le titre suivant
    return rest[: rest.index("\n## ")]


def _done_tranches() -> set[str]:
    """Tranches marquées « ✅ … fait » dans le roll-up — les deux axes ``T#``/``S#``
    (ex. ``{T1, T2, T3, T4, S1}``)."""
    plan = (ROOT / "MIGRATION_PLAN.md").read_text(encoding="utf-8")
    done: set[str] = set()
    for line in plan.splitlines():
        if "✅" in line and "fait" in line:
            done.update(re.findall(r"\b[TS]\d\b", line))
    return done


def test_status_section_delegates_to_rollup() -> None:
    assert "MIGRATION_PLAN.md" in _status_section(), (
        "CLAUDE.md §0 doit déléguer le détail au roll-up de MIGRATION_PLAN.md."
    )


def test_status_section_has_no_hardcoded_test_count() -> None:
    assert not re.search(r"\d+\s*tests", _status_section(), re.IGNORECASE), (
        "CLAUDE.md §0 ne doit pas figer un compte de tests (il se périme) — "
        "déléguer au roll-up."
    )


def test_next_step_is_not_an_already_done_tranche() -> None:
    match = re.search(r"Prochaine étape\s*=\s*([TS]U?\d[a-z]?)", _status_section())
    assert match, "CLAUDE.md §0 doit nommer une « Prochaine étape = T…/S… »."
    next_step = match.group(1)
    done = _done_tranches()
    assert next_step not in done, (
        f"CLAUDE.md §0 désigne « {next_step} » comme prochaine étape, mais le "
        f"roll-up de MIGRATION_PLAN.md la marque déjà faite ({sorted(done)}). "
        "Réconcilie le statut."
    )


def _next_session() -> str:
    return (ROOT / "NEXT_SESSION.md").read_text(encoding="utf-8")


def test_next_session_delegates_to_rollup() -> None:
    # Même dérive que CLAUDE.md §0, même verrou : NEXT_SESSION.md est resté gelé
    # à l'ère T1/TU2 (« prochaine = T2 », récaps de tranches livrées) longtemps
    # après T5→T7. Il doit pointer, pas recopier.
    assert "MIGRATION_PLAN.md" in _next_session(), (
        "NEXT_SESSION.md doit déléguer le statut au roll-up de MIGRATION_PLAN.md."
    )


def test_next_session_has_no_hardcoded_test_count() -> None:
    assert not re.search(
        r"\d+\s*(?:tests|verts)\b", _next_session(), re.IGNORECASE
    ), (
        "NEXT_SESSION.md ne doit pas figer un compte de tests (il se périme) — "
        "déléguer au roll-up."
    )


def test_next_session_does_not_recap_delivered_tranches() -> None:
    # Un titre « ## TU2.x — fait » (récap de tranche livrée) est exactement la
    # duplication de statut qui a pourri ce fichier : le détail vit dans le
    # roll-up et les DoD de couche, pas ici.
    assert not re.search(
        r"^##.*\b[TS]U?\d.*fait", _next_session(), re.MULTILINE
    ), (
        "NEXT_SESSION.md ne doit pas porter de récap « tranche — fait » : "
        "déléguer au roll-up de MIGRATION_PLAN.md."
    )
