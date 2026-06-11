"""Glossaire pédagogique : loader YAML (FR/EN) + section de rapport."""

from __future__ import annotations

from datetime import UTC, datetime

from xerocr.domain.run import RunManifest
from xerocr.evaluation.result import MetricScore, PipelineResult, RunResult
from xerocr.reports.glossary import load_glossary
from xerocr.reports.section import SectionContext
from xerocr.reports.sections.glossary import GlossarySection

FIXED = datetime(2026, 1, 1, tzinfo=UTC)

#: Métriques réellement calculées par le moteur → chacune doit avoir une entrée.
REAL_METRICS = (
    "cer",
    "cer_diplo",
    "wer",
    "mer",
    "del_rate",
    "ins_rate",
    "diacritic_err",
    "mufi_err",
    "hallucination",
    "searchability",
    "region_cer",
    "region_detection",
    "significance_p",
    "ece",
    "mce",
)


def _result(metric: str = "cer") -> RunResult:
    manifest = RunManifest(
        run_id="r",
        corpus_name="demo",
        n_documents=1,
        code_version="1.0",
        started_at=FIXED,
        completed_at=FIXED,
    )
    return RunResult(
        manifest=manifest,
        pipelines=(
            PipelineResult(
                pipeline="p",
                view="text",
                aggregate=(MetricScore(metric=metric, value=0.1, support=1),),
            ),
        ),
    )


def test_load_fr_and_en_cover_every_real_metric() -> None:
    for lang in ("fr", "en"):
        gloss = load_glossary(lang)
        for metric in REAL_METRICS:
            assert metric in gloss, f"{metric} absent du glossaire {lang}"
            entry = gloss[metric]
            assert entry.get("title")
            assert entry.get("definition")


def test_unknown_lang_falls_back_to_fr() -> None:
    assert load_glossary("zz") == load_glossary("fr")


def test_cache_returns_same_object() -> None:
    assert load_glossary("fr") is load_glossary("fr")


def test_section_renders_only_present_metrics() -> None:
    html = GlossarySection().render(_result("cer"), SectionContext())
    assert html is not None
    assert "<h2>Glossaire</h2>" in html
    assert "CER — taux d" in html  # titre de l'entrée cer (apostrophe échappée)
    assert "erreur caractère" in html
    assert 'class="gl-item"' in html
    assert "<details" in html  # disclosure natif, zéro JS
    # une métrique non présente dans le run n'apparaît pas
    assert "erreur mot" not in html  # le titre WER est absent


def test_section_english_lang() -> None:
    html = GlossarySection().render(_result("wer"), SectionContext(lang="en"))
    assert html is not None
    assert "<h2>Glossary</h2>" in html
    assert "WER — word error rate" in html
    assert "What it measures" in html  # libellé de champ EN


def test_section_absent_when_metric_has_no_entry() -> None:
    # Une métrique sans entrée de glossaire → section omise (pas d'erreur).
    assert GlossarySection().render(_result("unknown_metric"), SectionContext()) is None


def test_section_absent_when_no_pipeline() -> None:
    manifest = RunManifest(
        run_id="r",
        corpus_name="demo",
        n_documents=0,
        code_version="1.0",
        started_at=FIXED,
        completed_at=FIXED,
    )
    empty = RunResult(manifest=manifest, pipelines=())
    assert GlossarySection().render(empty, SectionContext()) is None


def test_section_output_is_deterministic() -> None:
    a = GlossarySection().render(_result("cer"), SectionContext())
    b = GlossarySection().render(_result("cer"), SectionContext())
    assert a == b
