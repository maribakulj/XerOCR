"""Sélection de documents **notables** + binning de distributions (couche 7).

Socle d'un rapport **invariant d'échelle** : les sections par-document ne listent
jamais un élément par document. Elles font, toujours, l'une de deux choses — quel
que soit le nombre de documents (20 ou 6000) :

- une **distribution** (histogramme, densité 2D) qui couvre **100 %** du corpus,
  de même allure à toute échelle ;
- un ensemble de **documents notables** (les plus difficiles, les plus discordants
  entre moteurs, les plus faciles), de **cardinalité fixe** — des *exemples
  illustratifs*, pas une troncature : rien n'est masqué puisque les distributions
  représentent l'ensemble, exactement comme ``diagnostics`` montre « les 10
  confusions les plus fréquentes ».

Ni seuil, ni bascule de mode : à petit corpus, l'union des notables couvre
naturellement tous les documents (mêmes ``worst``/``best`` qui se recouvrent, puis
dé-duplication) ; à grand corpus, elle plafonne. Le **même chemin de code** sert
les deux cas.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from statistics import fmean

from xerocr.evaluation.result import RunResult

_METRIC = "cer"

#: Nombre d'exemples **par catégorie** de notables (difficiles / discordants /
#: faciles). Convention éditoriale (cf. « top 10 confusions » de diagnostics) —
#: **pas** un plafond de corpus : les distributions, elles, couvrent tout.
HIGHLIGHTS_PER_GROUP = 10


def _per_doc_cer_values(result: RunResult, view: str) -> dict[str, list[float]]:
    """``{document_id: [CER par moteur scoré]}`` pour la vue (valeurs non ``None``)."""
    values: dict[str, list[float]] = {}
    for doc in result.documents:
        if doc.view != view:
            continue
        for score in doc.scores:
            if score.metric == _METRIC and score.value is not None:
                values.setdefault(doc.document_id, []).append(score.value)
    return values


def per_doc_mean_cer(result: RunResult, view: str) -> dict[str, float]:
    """``{document_id: CER moyen sur les moteurs}`` (documents sans CER exclus)."""
    return {
        doc: fmean(vals)
        for doc, vals in _per_doc_cer_values(result, view).items()
        if vals
    }


def per_doc_cer_spread(result: RunResult, view: str) -> dict[str, float]:
    """``{document_id: écart max−min du CER inter-moteurs}`` (≥ 2 moteurs scorés).

    L'écart mesure la **discordance** : les documents où les moteurs sont le plus
    en désaccord — les exemples les plus instructifs pour comprendre *quel* moteur
    décroche *où*.
    """
    return {
        doc: max(vals) - min(vals)
        for doc, vals in _per_doc_cer_values(result, view).items()
        if len(vals) >= 2
    }


@dataclass(frozen=True)
class DocumentHighlights:
    """Documents notables d'une vue, par catégorie (identifiants, dé-dupliqués)."""

    worst: tuple[str, ...]
    best: tuple[str, ...]
    divergent: tuple[str, ...]

    @property
    def ordered_ids(self) -> tuple[str, ...]:
        """Union **déterministe sans doublon** : difficiles → discordants → faciles.

        L'ordre est stable (= ordre d'ancrage des fiches détail) : la galerie et
        les fiches itèrent cette même séquence, donc les ancres ``#doc-<idx>``
        restent alignées.
        """
        seen: dict[str, None] = {}
        for group in (self.worst, self.divergent, self.best):
            for doc in group:
                seen.setdefault(doc, None)
        return tuple(seen)

    def group_of(self, document_id: str) -> str:
        """Catégorie **primaire** d'un document (premier groupe qui le revendique :
        ``worst`` > ``divergent`` > ``best``). ``""`` si non notable."""
        if document_id in self.worst:
            return "worst"
        if document_id in self.divergent:
            return "divergent"
        if document_id in self.best:
            return "best"
        return ""


def notable_documents(
    result: RunResult, view: str, *, per_group: int = HIGHLIGHTS_PER_GROUP
) -> DocumentHighlights:
    """Documents notables de la vue : ``per_group`` plus difficiles / discordants /
    faciles, par CER moyen et écart inter-moteurs. Déterministe (tiebreak par id)."""
    means = per_doc_mean_cer(result, view)
    if not means:
        return DocumentHighlights((), (), ())
    worst = tuple(sorted(means, key=lambda d: (-means[d], d))[:per_group])
    best = tuple(sorted(means, key=lambda d: (means[d], d))[:per_group])
    spread = per_doc_cer_spread(result, view)
    divergent = tuple(sorted(spread, key=lambda d: (-spread[d], d))[:per_group])
    return DocumentHighlights(worst=worst, best=best, divergent=divergent)


def histogram(values: Sequence[float], n_bins: int) -> list[float]:
    """Comptes par classe de largeur égale sur ``[min, max]`` (``n_bins ≥ 1``).

    Invariant d'échelle : la **forme** ne dépend que de la distribution, pas du
    nombre de points (20 ou 6000 → ``n_bins`` barres). Toutes valeurs égales →
    tout dans la première classe (largeur nulle, pas de division par zéro)."""
    vals = list(values)
    if not vals or n_bins < 1:
        return []
    lo, hi = min(vals), max(vals)
    if hi <= lo:
        return [float(len(vals))] + [0.0] * (n_bins - 1)
    width = (hi - lo) / n_bins
    counts = [0.0] * n_bins
    for value in vals:
        index = int((value - lo) / width)
        counts[min(index, n_bins - 1)] += 1.0
    return counts


def density_grid(
    points: Sequence[tuple[float, float]], nx: int, ny: int
) -> list[tuple[float, float, float]]:
    """Binning 2D de points ``(x, y)`` ∈ [0,1]² en grille ``nx × ny``.

    Renvoie ``(centre_x, centre_y, compte)`` par cellule **occupée**, trié
    déterministe. Invariant d'échelle : au plus ``nx · ny`` sorties quel que soit
    le nombre de points en entrée (un nuage de 6000 points reste lisible et léger).
    """
    if nx < 1 or ny < 1:
        return []
    cells: dict[tuple[int, int], int] = {}
    for x, y in points:
        ix = min(nx - 1, max(0, int(max(0.0, min(x, 1.0)) * nx)))
        iy = min(ny - 1, max(0, int(max(0.0, min(y, 1.0)) * ny)))
        cells[(ix, iy)] = cells.get((ix, iy), 0) + 1
    return [
        ((ix + 0.5) / nx, (iy + 0.5) / ny, float(count))
        for (ix, iy), count in sorted(cells.items())
    ]


__all__ = [
    "HIGHLIGHTS_PER_GROUP",
    "DocumentHighlights",
    "density_grid",
    "histogram",
    "notable_documents",
    "per_doc_cer_spread",
    "per_doc_mean_cer",
]
