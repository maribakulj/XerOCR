"""Diff **GT ↔ hypothèse** surligné (couche 7) — caractère par caractère, déterministe.

Aligne référence et hypothèse via ``difflib.SequenceMatcher`` (stdlib, déterministe)
et marque les écarts : **suppressions** (caractères de la GT absents de l'hypothèse,
``<del>``) et **insertions** (caractères de l'hypothèse absents de la GT, ``<ins>``).
Le texte est **échappé** avant marquage (les balises sont les seules non échappées,
de confiance) — frontière anti-XSS. Aucun JS : le surlignage est du HTML rendu côté
serveur, donc octet-stable.
"""

from __future__ import annotations

from difflib import SequenceMatcher

from xerocr.reports.html import escape
from xerocr.reports.section import Html


def char_diff(reference: str, hypothesis: str) -> tuple[Html, Html]:
    """``(ref_html, hyp_html)`` : écarts surlignés, alignés caractère à caractère.

    ``ref_html`` = la GT avec ses **suppressions** marquées ``<del class="d-del">`` ;
    ``hyp_html`` = l'hypothèse avec ses **insertions** marquées ``<ins class="d-ins">``.
    Les segments identiques sont rendus tels quels (échappés). Un ``replace`` est
    une suppression **et** une insertion (les deux côtés sont marqués).
    """
    matcher = SequenceMatcher(None, reference, hypothesis, autojunk=False)
    ref_parts: list[str] = []
    hyp_parts: list[str] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        ref_seg = escape(reference[i1:i2])
        hyp_seg = escape(hypothesis[j1:j2])
        if tag == "equal":
            ref_parts.append(ref_seg)
            hyp_parts.append(hyp_seg)
            continue
        if ref_seg:
            ref_parts.append(f'<del class="d-del">{ref_seg}</del>')
        if hyp_seg:
            hyp_parts.append(f'<ins class="d-ins">{hyp_seg}</ins>')
    return Html("".join(ref_parts)), Html("".join(hyp_parts))


__all__ = ["char_diff"]
