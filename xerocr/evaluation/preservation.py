"""Moteur partagé de **préservation d'un sous-ensemble de caractères** (couche 3).

``mufi_err``, ``diacritic_err`` et ``hcpr`` mesurent tous la même chose sur des
sous-ensembles différents : parmi les caractères-cibles **de la référence**,
combien survivent à l'alignement caractère. Un seul moteur les sert — il rend les
deux comptes bruts ``(n_total, n_wrong)`` et chaque métrique en dérive sa lecture :

- ``diacritic_err`` / ``mufi_err`` exposent le **taux d'erreur** ``n_wrong / n_total`` ;
- ``hcpr`` expose le **taux de préservation** ``(n_total − n_wrong) / n_total``.

Même alignement que la source historique (``rapidfuzz`` ``editops``, opérations
``replace``/``delete`` sur les positions de la référence) : la factorisation est
**à valeur constante** — les métriques existantes ne bougent pas d'un ULP (parité
prouvée par ``test_preservation``). ``air``, lui, mesure l'inverse côté **sortie**
(sur-historicisation) et vit dans :mod:`xerocr.evaluation.archaic`.
"""

from __future__ import annotations

from collections.abc import Callable

from rapidfuzz.distance import Levenshtein


def preservation_counts(
    reference: str, hypothesis: str, is_target: Callable[[str], bool]
) -> tuple[int, int] | None:
    """``(n_total, n_wrong)`` pour les caractères-cibles de la **référence**.

    ``n_total`` = nombre de caractères de ``reference`` satisfaisant ``is_target`` ;
    ``n_wrong`` = ceux mal restitués (substitués ou supprimés dans l'alignement
    ``editops`` GT↔hypothèse). ``None`` si la référence n'en porte aucun (non
    applicable — le runner exclut ce cas de l'agrégat).
    """
    targets = [i for i, char in enumerate(reference) if is_target(char)]
    if not targets:
        return None
    wrong = {
        op.src_pos
        for op in Levenshtein.editops(reference, hypothesis)
        if op.tag in ("replace", "delete")
    }
    n_wrong = sum(1 for i in targets if i in wrong)
    return len(targets), n_wrong


__all__ = ["preservation_counts"]
