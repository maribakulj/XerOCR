"""Section bascule de classement : bump chart du rang moteur par métrique (couche 7).

Pour chaque métrique, on classe les moteurs (rang 1 = meilleur), puis on relie le
rang de chaque moteur d'une métrique à l'autre : une ligne qui **descend** = un
moteur fort sur une métrique mais faible sur une autre (les croisements = arbitrages
qu'un classement unique masque). Pure présentation : lit les scores d'agrégat du
``RunResult`` (aucun recalcul), rendu SVG serveur déterministe, zéro JS.
"""

from __future__ import annotations

from xerocr.evaluation.result import RunResult
from xerocr.reports.engine_badges import engine_accent, engine_letter, engine_order
from xerocr.reports.html import escape, localized
from xerocr.reports.section import Html, SectionContext
from xerocr.reports.sections._tables import ordered_unique
from xerocr.reports.svg import bump_chart

#: Métriques classées (clé, « plus bas = meilleur ? », libellé fr, libellé en).
_METRICS: tuple[tuple[str, bool, str, str], ...] = (
    ("cer", True, "CER", "CER"),
    ("wer", True, "WER", "WER"),
    ("bow_f1", False, "F1", "F1"),
    ("searchability", False, "Rech.", "Search"),
)


class RankBumpSection:
    """Bump chart : rang des moteurs métrique par métrique (carte autonome)."""

    name = "rank_bump"
    requires: tuple[str, ...] = ()

    def render(self, result: RunResult, ctx: SectionContext) -> Html | None:
        if not result.pipelines:
            return None
        view = ordered_unique(p.view for p in result.pipelines)[0]
        order = engine_order(p.pipeline for p in result.pipelines)
        pipes = sorted(
            (p for p in result.pipelines if p.view == view),
            key=lambda p: order[p.pipeline],
        )
        if len(pipes) < 2:
            return None  # un classement suppose au moins deux moteurs
        scores = {
            p.pipeline: {s.metric: s.value for s in p.aggregate if s.value is not None}
            for p in pipes
        }
        metrics = [
            m for m in _METRICS if all(m[0] in scores[p.pipeline] for p in pipes)
        ]
        if len(metrics) < 2:
            return None  # une bascule suppose au moins deux métriques
        # Rang par métrique : 1 = meilleur. Départage par ordre de badge (stable).
        ranks: dict[str, list[int]] = {p.pipeline: [] for p in pipes}
        for key, lower_better, _fr, _en in metrics:
            keyed: list[tuple[float, int, str]] = []
            for p in pipes:
                v = scores[p.pipeline][key]
                keyed.append((v if lower_better else -v, order[p.pipeline], p.pipeline))
            keyed.sort()
            for rank, (_v, _o, name) in enumerate(keyed, start=1):
                ranks[name].append(rank)
        columns = [m[2] if ctx.lang != "en" else m[3] for m in metrics]
        series = [(p.pipeline, ranks[p.pipeline]) for p in pipes]
        accents = [engine_accent(order[p.pipeline]) for p in pipes]
        svg = bump_chart(columns, series, accents=accents, n_ranks=len(pipes))
        if not svg:
            return None
        legend = " · ".join(
            f'<span class="eng-badge" style="--badge:{engine_accent(i)}">'
            f"{engine_letter(i)}</span> {escape(p.pipeline)}"
            for p in pipes
            for i in (order[p.pipeline],)
        )
        title = localized(ctx.lang, "Bascule de classement", "Ranking shift")
        intro = localized(
            ctx.lang,
            "Rang des moteurs métrique par métrique (1 = meilleur, en haut) — les "
            "lignes qui se <strong>croisent</strong> révèlent un moteur fort ici, "
            "faible là (arbitrage qu'un classement unique masque).",
            "Engine rank metric by metric (1 = best, at top) — "
            "<strong>crossing</strong> lines reveal an engine strong here, weak "
            "there (a trade-off a single ranking hides).",
        )
        return Html(
            f"<h2>{title}</h2>\n"
            f'<p class="muted">{intro}</p>\n'
            f'<div class="bump-wrap">{svg}</div>\n'
            f'<p class="muted bump-legend">{legend}</p>\n'
        )


__all__ = ["RankBumpSection"]
