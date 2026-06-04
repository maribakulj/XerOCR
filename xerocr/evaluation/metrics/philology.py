"""Métrique philologique **MUFI** : taux d'erreur sur les caractères médiévaux
spéciaux (zone privée MUFI, abréviations latines, lettres médiévales).

Complète ``diacritic_err`` (signes combinants) sur un autre axe philologique :
les **lettres et signes médiévaux** standardisés par la MUFI (Medieval Unicode
Font Initiative) — soit dans la **zone d'usage privé** (PUA), soit des codepoints
Unicode dédiés (``ſ`` s long, ``þ`` thorn, ligatures, abréviations latines de
Latin Extended-D…). Un moteur OCR/HTR peut très bien rendre le texte courant mais
échouer précisément sur ces glyphes — c'est ce que cette métrique isole.

Même mécanique que ``diacritic_err`` : alignement caractère ``rapidfuzz``
(whitelist ``evaluation/``, C, déterministe). ``text.py`` reste sans dépendance.
"""

from __future__ import annotations

from rapidfuzz.distance import Levenshtein

from xerocr.domain.artifacts import ArtifactType
from xerocr.evaluation.context import DocContext
from xerocr.evaluation.errors import EvaluationError
from xerocr.evaluation.metric import DocumentMetric, Observation, document_metric

#: Plages Unicode où vivent les glyphes MUFI / médiévaux.
#: ⚠️ **Pas de signes combinants** ici (bloc U+1DC0–U+1DFF volontairement exclu) :
#: ils relèvent de ``diacritic_err`` (catégorie ``Mn``). ``mufi_err`` mesure des
#: **lettres/ligatures/abréviations** à codepoint propre → axe disjoint.
_MUFI_RANGES: tuple[tuple[int, int], ...] = (
    (0xE000, 0xF8FF),      # Private Use Area (zone MUFI principale)
    (0xF0000, 0xFFFFD),    # Supplementary PUA-A
    (0x100000, 0x10FFFD),  # Supplementary PUA-B
    (0xA720, 0xA7FF),      # Latin Extended-D (abréviations latines médiévales)
    (0xFB00, 0xFB06),      # Ligatures latines (ﬀ ﬁ ﬂ ﬃ ﬄ ﬅ ﬆ)
)

#: Lettres/signes médiévaux à codepoint dédié, hors plages ci-dessus.
_MUFI_EXPLICIT: frozenset[str] = frozenset("þÞðÐƿǷſæÆœŒøØƀŧđħȝȜ")


def _is_mufi(char: str) -> bool:
    """Vrai si ``char`` est un glyphe MUFI / médiéval (PUA ou codepoint dédié)."""
    cp = ord(char)
    if any(lo <= cp <= hi for lo, hi in _MUFI_RANGES):
        return True
    return char in _MUFI_EXPLICIT


@document_metric(
    name="mufi_err",
    input_types=(ArtifactType.RAW_TEXT, ArtifactType.RAW_TEXT),
    description="Taux d'erreur sur les caractères MUFI / médiévaux "
    "(PUA, abréviations latines, ſ/þ/ligatures…).",
    higher_is_better=False,
    tags=frozenset({"text", "philology", "alignment", "mufi"}),
)
def mufi_error(ctx: DocContext) -> Observation | None:
    """Parmi les caractères MUFI de la **référence**, fraction mal reconnue
    (substituée ou supprimée dans l'alignement). ``None`` si la référence n'en
    contient aucun (non applicable) — le runner exclut ce cas de l'agrégat."""
    if not isinstance(ctx.reference, str) or not isinstance(ctx.hypothesis, str):
        raise EvaluationError(
            "mufi_err : reference et hypothesis doivent être du texte."
        )
    targets = [i for i, char in enumerate(ctx.reference) if _is_mufi(char)]
    if not targets:
        return None
    wrong = {
        op.src_pos
        for op in Levenshtein.editops(ctx.reference, ctx.hypothesis)
        if op.tag in ("replace", "delete")
    }
    errors = sum(1 for i in targets if i in wrong)
    return Observation(value=errors / len(targets), weight=len(targets))


#: Métriques philologiques MUFI (dépendent de ``rapidfuzz``).
PHILOLOGY_METRICS: tuple[DocumentMetric, ...] = (mufi_error,)

__all__ = ["PHILOLOGY_METRICS", "mufi_error"]
