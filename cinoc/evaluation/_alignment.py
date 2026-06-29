"""Primitives d'alignement caractère partagées (couche 3) — une seule source.

Le runner distribue à chaque collecteur le **même** ``(référence, hypothèse)``
normalisé ; sans ce module, plusieurs collecteurs réouvraient leur propre boucle
d'opcodes ``rapidfuzz`` pour recompter substitutions/suppressions/insertions au
**caractère** (et le char-MER en dérivait à deux endroits — ``metrics/conformity``
et ``correction``). On mutualise ici la primitive ; la **forme** (comptes S/D/I,
dénominateur ``H+S+D+I`` borné) est figée par ``tests/evaluation/test_char_mer_anchor``.
"""

from __future__ import annotations

from rapidfuzz.distance import Levenshtein


def char_counts(reference: str, hypothesis: str) -> tuple[int, int, int]:
    """``(substitutions, suppressions, insertions)`` de l'alignement caractère."""
    substitutions = deletions = insertions = 0
    for op in Levenshtein.editops(reference, hypothesis):
        if op.tag == "replace":
            substitutions += 1
        elif op.tag == "delete":
            deletions += 1
        else:
            insertions += 1
    return substitutions, deletions, insertions


def char_mer(reference: str, hypothesis: str) -> tuple[float, int, int]:
    """``(cmer, edits, dénominateur)`` — Match Error Rate caractère (SPEC_HIPE §4.1).

    ``cmer = (S+D+I) / (H+S+D+I)``, borné ``[0, 1]`` ; dénominateur
    ``H+S+D+I = len(reference) + insertions`` (l'alignement complet de la
    référence donne ``H+S+D = len(reference)``). Deux textes vides → ``(0.0, 0, 0)``.
    """
    substitutions, deletions, insertions = char_counts(reference, hypothesis)
    total = len(reference) + insertions
    edits = substitutions + deletions + insertions
    return (edits / total if total else 0.0), edits, total


__all__ = ["char_counts", "char_mer"]
