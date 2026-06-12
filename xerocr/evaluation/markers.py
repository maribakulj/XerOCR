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

Adaptatif : une famille sans aucun signe dans la GT du corpus est **absente**
du rapport (pas un zéro sur un corpus moderne). Données = **constantes du
module** (≠ surface exécutable, comme les profils de normalisation) : 11 signes
Capelli/MUFI à un seul ou deux codepoints. La famille *roman* (5 statuts) et
les marqueurs *positionnels* (imprimé ancien) arrivent à leur sous-tranche.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass

from xerocr.evaluation.analysis import (
    Analysis,
    MarkerPreservation,
    PhilologyPayload,
    PipelinePhilology,
)


@dataclass(frozen=True)
class Marker:
    """Un signe abréviatif + ses développements éditoriaux acceptés."""

    sign: str
    expansions: tuple[str, ...]


@dataclass(frozen=True)
class MarkerFamily:
    """Une famille de marqueurs partageant une stratégie d'appariement."""

    name: str
    markers: tuple[Marker, ...]


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

#: Familles actives (containment). Positionnel (imprimé ancien) ajouté à sa
#: tranche — pas de branche morte avant son consommateur.
FAMILIES: tuple[MarkerFamily, ...] = (ABBREVIATIONS,)

#: Motif « mot entier » des développements (R3 : ``\b…\b`` quelle que soit la
#: longueur), insensible à la casse — précompilé par signe au chargement.
_EXPANSION_PATTERNS: dict[str, re.Pattern[str]] = {
    marker.sign: re.compile(
        r"\b(?:" + "|".join(re.escape(e) for e in marker.expansions) + r")\b",
        re.IGNORECASE,
    )
    for family in FAMILIES
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
            for sign, counts in family_counts(family, reference, hypothesis).items():
                slot = self._sums.setdefault((pipeline, family.name, sign), [0, 0, 0])
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
    "FAMILIES",
    "Marker",
    "MarkerCollector",
    "MarkerFamily",
    "SignCounts",
    "family_counts",
]
