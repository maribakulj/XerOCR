"""Préservation de **marqueurs philologiques** : moteur + familles (couche 3).

Mesure si une convention scribale de la vérité-terrain survit dans la sortie —
*diplomatique* (la forme abrégée est reproduite telle quelle) vs *modernisante*
(elle est développée). Deux scores par marqueur, agrégés par famille :

- **strict** : le signe exact de la GT est reproduit (``ꝑ`` reste ``ꝑ``) ;
- **expansion** : le signe **ou** son développement est reproduit (``ꝑ`` →
  ``per``/``par``) — toujours ``≥ strict`` (lentille plus permissive).

Stratégie *containment* (abréviations) : appariement **multiset** sur le texte
entier ; les développements sont cherchés en **mot entier** (``\b…\b`` pour
**toutes** les longueurs — réparation R3 : ``per`` ne matche plus dans
« permettre », contrairement à la source qui ne bornait que ``≤ 2`` lettres).
L'expansion est une **borne optimiste** (un « et » du texte compte comme
développement d'un ``⁊``, capé au nombre de signes de la GT).

Deux stratégies d'appariement, déclarées par chaque famille (``MarkerFamily.
strategy``) :

- *containment* (abréviations) — la forme (ou son développement) existe quelque
  part dans l'hypothèse (multiset, insensible à l'ordre), deux scores ;
- *positional* (imprimé ancien) — le marqueur est restitué **à sa position**
  (toutes ses positions GT tombent dans un opcode ``equal`` de Levenshtein,
  cohérent CER), un seul score (préservation).

Adaptatif : une famille — et, en positionnel, une catégorie — sans aucun signe
dans la GT du corpus est **absente** du rapport (pas un zéro sur un corpus
moderne). Données = **constantes du module** (≠ surface exécutable, comme les
profils de normalisation). La famille *roman* (5 statuts) arrive à sa
sous-tranche.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from rapidfuzz.distance import Levenshtein

from xerocr.evaluation.analysis import (
    Analysis,
    MarkerPreservation,
    PhilologyPayload,
    PipelinePhilology,
)


@dataclass(frozen=True)
class Marker:
    """Membre d'une famille de marqueurs.

    - *containment* (abréviations) : ``sign`` est le signe cherché tel quel,
      ``expansions`` ses développements éditoriaux ; ``forms`` est vide.
    - *positional* (imprimé ancien) : ``sign`` est le **nom de catégorie** (clé
      d'agrégation et d'affichage), ``forms`` les graphies pré-composées qui en
      relèvent ; ``expansions`` est vide (aucune notion de développement).
    """

    sign: str
    expansions: tuple[str, ...] = ()
    forms: tuple[str, ...] = ()


@dataclass(frozen=True)
class MarkerFamily:
    """Une famille de marqueurs partageant une stratégie d'appariement.

    ``strategy`` choisit la sémantique de préservation : ``"containment"`` (la
    forme ou son développement existe dans l'hypothèse) ou ``"positional"`` (le
    marqueur est à sa position — opcode ``equal``, cohérent CER).
    """

    name: str
    markers: tuple[Marker, ...]
    strategy: Literal["containment", "positional"] = "containment"


#: Abréviations médiévales (Capelli / MUFI). ``ñ`` (U+00F1) est **exclu** : son
#: ambiguïté avec l'espagnol/le français modernes en ferait un faux positif
#: systématique (chaque « ñ » compté comme abréviation). Les signes combinants
#: ``p̃``/``q̃`` (lettre + U+0303) sont appariés en forme NFC.
ABBREVIATIONS = MarkerFamily(
    name="abbreviations",
    markers=(
        Marker("ꝑ", ("per", "par")),
        Marker("ꝓ", ("pro",)),
        Marker("ꝗ", ("qui",)),
        Marker("ꝙ", ("quia",)),
        Marker("ꝯ", ("us", "con")),
        Marker("⁊", ("et",)),
        Marker("ꝝ", ("rum",)),
        Marker("ꝫ", ("et",)),
        Marker("ꝭ", ("is",)),
        Marker("p̃", ("par", "per")),
        Marker("q̃", ("que", "qui")),
    ),
)

#: Marqueurs typographiques de l'imprimé ancien (XVIᵉ-XVIIIᵉ), **stratégie
#: positionnelle**. Cinq catégories ; chaque ``forms`` ne liste que des graphies
#: **pré-composées** (un codepoint) — les séquences décomposées voyelle + U+0303
#: sont ramenées à leur pré-composé par la normalisation NFC avant détection,
#: donc ``ã`` (a + U+0303) et ``ã`` (U+00E3) comptent pareil. ``ñ`` est inclus
#: ici (marqueur d'imprimé ancien), contrairement à la famille scribale où son
#: ambiguïté moderne le bannit.
EARLY_MODERN = MarkerFamily(
    name="early_modern",
    strategy="positional",
    markers=(
        Marker("ligatures", forms=("ﬀ", "ﬁ", "ﬂ", "ﬃ", "ﬄ", "ﬅ", "ﬆ")),
        Marker("long_s", forms=("ſ",)),
        Marker("dotless_i", forms=("ı",)),
        Marker("ampersand", forms=("&",)),
        Marker(
            "nasal_tildes",
            forms=("ã", "Ã", "ñ", "Ñ", "õ", "Õ", "ũ", "Ũ", "ẽ", "Ẽ", "ĩ", "Ĩ"),
        ),
    ),
)

#: Familles actives. ``observe`` les parcourt toutes ; une famille (ou catégorie)
#: sans signal dans la GT n'écrit rien (adaptatif).
FAMILIES: tuple[MarkerFamily, ...] = (ABBREVIATIONS, EARLY_MODERN)

#: Motif « mot entier » des développements (R3 : ``\b…\b`` quelle que soit la
#: longueur), insensible à la casse — précompilé par signe au chargement. Seules
#: les familles *containment* portent des développements.
_EXPANSION_PATTERNS: dict[str, re.Pattern[str]] = {
    marker.sign: re.compile(
        r"\b(?:" + "|".join(re.escape(e) for e in marker.expansions) + r")\b",
        re.IGNORECASE,
    )
    for family in FAMILIES
    if family.strategy == "containment"
    for marker in family.markers
}


@dataclass(frozen=True)
class SignCounts:
    """Comptes d'un signe pour une paire (GT, hypothèse)."""

    n_total: int
    n_strict: int
    n_expansion: int


def family_counts(
    family: MarkerFamily, reference: str, hypothesis: str
) -> dict[str, SignCounts]:
    """Comptes par signe **présent dans la GT** (containment, multiset).

    ``n_strict = min(n_gt, occurrences du signe dans l'hyp)`` ;
    ``n_expansion = min(n_gt, signe + développements en mot entier)`` — borne
    optimiste, capée à ``n_gt`` (jamais > le nombre d'occurrences de la GT).
    """
    ref = unicodedata.normalize("NFC", reference)
    hyp = unicodedata.normalize("NFC", hypothesis)
    out: dict[str, SignCounts] = {}
    for marker in family.markers:
        n_gt = ref.count(marker.sign)
        if n_gt == 0:
            continue
        sign_in_hyp = hyp.count(marker.sign)
        expansion_in_hyp = len(_EXPANSION_PATTERNS[marker.sign].findall(hyp))
        out[marker.sign] = SignCounts(
            n_total=n_gt,
            n_strict=min(n_gt, sign_in_hyp),
            n_expansion=min(n_gt, sign_in_hyp + expansion_in_hyp),
        )
    return out


def _char_categories(family: MarkerFamily) -> dict[str, str]:
    """Index ``graphie NFC (un codepoint) → nom de catégorie`` d'une famille."""
    return {
        unicodedata.normalize("NFC", form): marker.sign
        for marker in family.markers
        for form in marker.forms
    }


def _equal_src_positions(reference: str, hypothesis: str) -> set[int]:
    """Indices de ``reference`` couverts par un opcode ``equal`` (cohérent CER)."""
    positions: set[int] = set()
    for op in Levenshtein.opcodes(reference, hypothesis):
        if op.tag == "equal":
            positions.update(range(op.src_start, op.src_end))
    return positions


def positional_counts(
    family: MarkerFamily, reference: str, hypothesis: str
) -> dict[str, SignCounts]:
    """Préservation **positionnelle** par catégorie présente dans la GT.

    Un marqueur (un codepoint après NFC) est *préservé* si sa position GT tombe
    dans un opcode ``equal`` de l'alignement Levenshtein GT↔hypothèse — même
    critère que le CER. Score unique : ``n_strict == n_expansion == n_préservé``
    (la famille n'a pas de lentille « développement »), pour réutiliser la forme
    du payload sans rupture. Catégories absentes de la GT → omises (adaptatif).
    """
    ref = unicodedata.normalize("NFC", reference)
    hyp = unicodedata.normalize("NFC", hypothesis)
    categories = _char_categories(family)
    occurrences = [
        (i, categories[ch]) for i, ch in enumerate(ref) if ch in categories
    ]
    if not occurrences:
        return {}
    equal_positions = _equal_src_positions(ref, hyp)
    sums: dict[str, list[int]] = {}
    for position, category in occurrences:
        slot = sums.setdefault(category, [0, 0])
        slot[0] += 1
        if position in equal_positions:
            slot[1] += 1
    return {
        category: SignCounts(n_total=total, n_strict=kept, n_expansion=kept)
        for category, (total, kept) in sums.items()
    }


def _counts_for(
    family: MarkerFamily, reference: str, hypothesis: str
) -> dict[str, SignCounts]:
    """Comptes d'une famille selon sa stratégie déclarée."""
    if family.strategy == "positional":
        return positional_counts(family, reference, hypothesis)
    return family_counts(family, reference, hypothesis)


class MarkerCollector:
    """Accumule la préservation des marqueurs au fil du scoring (micro).

    Pattern ``TaxonomyCollector`` : ``observe`` par document scoré (mêmes textes
    normalisés, zéro relecture), ``build`` agrège par (pipeline × famille ×
    signe) → ``PhilologyPayload``. Familles sans signal → absentes.
    """

    def __init__(self, families: Sequence[MarkerFamily] = FAMILIES) -> None:
        self._families = tuple(families)
        #: (pipeline, family, sign) -> [n_total, n_strict, n_expansion]
        self._sums: dict[tuple[str, str, str], list[int]] = {}
        self._order: list[str] = []

    def observe(self, pipeline: str, reference: str, hypothesis: str) -> None:
        seen = False
        for family in self._families:
            for key, counts in _counts_for(family, reference, hypothesis).items():
                slot = self._sums.setdefault((pipeline, family.name, key), [0, 0, 0])
                slot[0] += counts.n_total
                slot[1] += counts.n_strict
                slot[2] += counts.n_expansion
                seen = True
        if seen and pipeline not in self._order:
            self._order.append(pipeline)

    def build(self, view: str) -> Analysis | None:
        """Payload de la vue, ``None`` si aucun marqueur dans la GT du corpus."""
        rows: list[PipelinePhilology] = []
        for pipeline in self._order:
            for family in self._families:
                signs = [
                    (marker.sign, self._sums[(pipeline, family.name, marker.sign)])
                    for marker in family.markers
                    if (pipeline, family.name, marker.sign) in self._sums
                ]
                if not signs:
                    continue
                markers = tuple(
                    MarkerPreservation(
                        sign=sign,
                        n_total=slot[0],
                        n_strict=slot[1],
                        n_expansion=slot[2],
                    )
                    for sign, slot in signs
                )
                rows.append(
                    PipelinePhilology(
                        pipeline=pipeline,
                        family=family.name,
                        n_total=sum(m.n_total for m in markers),
                        n_strict=sum(m.n_strict for m in markers),
                        n_expansion=sum(m.n_expansion for m in markers),
                        markers=markers,
                    )
                )
        if not rows:
            return None
        return Analysis(
            scope="corpus",
            view=view,
            payload=PhilologyPayload(pipelines=tuple(rows)),
        )


__all__ = [
    "ABBREVIATIONS",
    "EARLY_MODERN",
    "FAMILIES",
    "Marker",
    "MarkerCollector",
    "MarkerFamily",
    "SignCounts",
    "family_counts",
    "positional_counts",
]
