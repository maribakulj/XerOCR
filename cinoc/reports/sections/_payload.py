"""Squelette des sections « une famille de payload → des blocs par vue » (couche 7).

~16 sections répétaient le **même** enchaînement de contrôle : détecter le
multi-vues, construire un bloc par analyse du type de payload voulu (avec le
préfixe de vue), renvoyer ``None`` si aucun, sinon un titre ``<h2>`` suivi des
blocs. On mutualise ce **flux** (pas le HTML des blocs, propre à chaque section)
→ sortie **identique** (les tests de section restent verts), boilerplate en moins.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from cinoc.evaluation.result import RunResult
from cinoc.reports.html import view_prefix
from cinoc.reports.section import Html, SectionContext

P = TypeVar("P")


def render_payload_section(
    result: RunResult,
    ctx: SectionContext,
    *,
    payload_type: type[P],
    title: str,
    block: Callable[[str, P], str],
) -> Html | None:
    """Rend une section pilotée par un type de payload.

    ``block(view_prefix, payload) -> html`` construit le bloc d'**une** analyse
    (la section y referme ``lang``/ordre moteur/etc. par closure). ``view_prefix``
    est vide en mono-vue, préfixé sinon. ``None`` si aucune analyse du type voulu.
    """
    multi = len({a.view for a in result.analyses}) > 1
    blocks = [
        block(view_prefix(a.view, ctx.lang, multi=multi), a.payload)
        for a in result.analyses
        if isinstance(a.payload, payload_type)
    ]
    if not blocks:
        return None
    return Html(f"<h2>{title}</h2>\n" + "".join(blocks))


__all__ = ["render_payload_section"]
