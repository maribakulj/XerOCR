"""Renommage T4 : les métriques aux noms « chargés » (`hallucination`,
`searchability`) reçoivent un **libellé d'affichage descriptif** qui porte son
**critère**, sans prêter d'intention au modèle. Les **clés** de métrique (donc le
JSON/`RunResult`) restent inchangées — seul l'affichage change (comme `mer`)."""

from __future__ import annotations

from cinoc.reports.glossary import load_glossary
from cinoc.reports.sections._tables import _METRIC_SHORT, metric_short_label
from cinoc.reports.sections.engine_radar import _AXES


def test_glossary_titles_are_descriptive_and_carry_the_criterion() -> None:
    cases = (("fr", "Lev", "trigramme"), ("en", "Lev", "trigram"))
    for lang, recall_kw, anchor_kw in cases:
        gloss = load_glossary(lang)
        # clés inchangées (donnée stable) ...
        assert "hallucination" in gloss and "searchability" in gloss
        h, s = gloss["hallucination"], gloss["searchability"]
        # ... mais titres descriptifs, plus « Indice d'… » (vocable chargé).
        assert "Indice" not in h["title"] and "index" not in h["title"].lower()
        assert "ancr" in h["title"].lower() or "anchor" in h["title"].lower()
        assert "rappel" in s["title"].lower() or "recall" in s["title"].lower()
        # le critère exact figure dans la définition (montré, pas seulement nommé).
        assert anchor_kw in h["definition"].lower()
        assert recall_kw in s["definition"]


def test_short_labels_renamed_keys_preserved() -> None:
    # clés (données) conservées, libellés courts neutres.
    assert _METRIC_SHORT["hallucination"] == "non-ancré"
    assert _METRIC_SHORT["searchability"] == "rappel·ft"
    assert metric_short_label("hallucination") == "non-ancré"
    assert "halluc." not in _METRIC_SHORT.values()


def test_radar_axis_for_inverted_hallucination_is_anchoring() -> None:
    # L'axe radar inverse hallucination (1 − part non ancrée) : son nom honnête
    # est « Ancrage »/« Anchoring », pas « ¬Halluc ».
    axes = {key: (fr, en) for key, _inv, fr, en in _AXES}
    assert axes["hallucination"] == ("Ancrage", "Anchoring")
    assert axes["searchability"] == ("Rappel", "Recall")
    assert all("Halluc" not in fr and "Halluc" not in en for _fr, (fr, en) in
               (("k", v) for k, v in axes.items()))
