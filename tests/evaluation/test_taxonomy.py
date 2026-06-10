"""Taxonomie : classification par règles — valeurs dérivées **à la main** (§5.8b)."""

from __future__ import annotations

from xerocr.evaluation.taxonomy import (
    TaxonomyCollector,
    classify_texts,
    classify_word_pair,
)


def test_case_only_difference() -> None:
    assert classify_word_pair("Chat", "chat") == "case"


def test_diacritic_only_difference() -> None:
    assert classify_word_pair("été", "ete") == "diacritic"
    assert classify_word_pair("a", "à") == "diacritic"


def test_ligature_expansion() -> None:
    assert classify_word_pair("cœur", "coeur") == "ligature"


def test_visual_confusions() -> None:
    # rn lu m : « main » → « rnain » ; l lu 1 ; s long.
    assert classify_word_pair("main", "rnain") == "visual"
    assert classify_word_pair("il", "i1") == "visual"
    assert classify_word_pair("estre", "eſtre") == "visual"


def test_residual_substitution_is_other() -> None:
    assert classify_word_pair("chat", "lion") == "other"


def test_segmentation_fusion_and_fragmentation() -> None:
    # « bonjour » fragmenté en « bon jour » : 2 mots produits.
    counts = classify_texts("le bonjour gris", "le bon jour gris")
    assert counts["segmentation"] == 2
    counts = classify_texts("le bon jour gris", "le bonjour gris")
    assert counts["segmentation"] == 2


def test_lacuna_and_insertion() -> None:
    counts = classify_texts("un chat noir", "un chat")
    assert counts["lacuna"] == 1
    counts = classify_texts("un chat", "un chat noir")
    assert counts["insertion"] == 1


def test_mixed_text_hand_tallied() -> None:
    # « Chat ete rnain » vs réf « chat été main » : case + diacritic + visual.
    counts = classify_texts("chat été main", "Chat ete rnain")
    assert counts == {"case": 1, "diacritic": 1, "visual": 1}


def test_collector_builds_canonical_order() -> None:
    collector = TaxonomyCollector()
    collector.observe("tess", "chat été main", "Chat ete rnain")
    analysis = collector.build("text")
    assert analysis is not None
    payload = analysis.payload
    assert payload.kind == "taxonomy"
    row = payload.pipelines[0]
    assert row.pipeline == "tess" and row.total_errors == 3
    assert [c.label for c in row.counts] == ["case", "diacritic", "visual"]
    # Déterminisme bit-à-bit.
    assert analysis.model_dump_json() == analysis.model_dump_json()


def test_collector_without_errors_yields_none() -> None:
    collector = TaxonomyCollector()
    collector.observe("tess", "parfait", "parfait")
    assert collector.build("text") is None
