"""Section philologie : rendu lecture seule du payload ``philology``."""

from __future__ import annotations

from datetime import UTC, datetime

from xerocr.domain.artifacts import ArtifactType
from xerocr.domain.pipeline import PipelineSpec
from xerocr.domain.run import RunManifest
from xerocr.evaluation.analysis import (
    Analysis,
    MarkerPreservation,
    PhilologyPayload,
    PipelinePhilology,
    PipelineRomanNumerals,
    RomanNumeralsPayload,
)
from xerocr.evaluation.result import RunResult
from xerocr.reports.section import SectionContext
from xerocr.reports.sections.philology import PhilologySection

FIXED = datetime(2026, 1, 1, tzinfo=UTC)


def _result(analyses: tuple[Analysis, ...]) -> RunResult:
    manifest = RunManifest(
        run_id="r",
        corpus_name="c",
        n_documents=1,
        pipeline_specs=(
            PipelineSpec(name="eng", initial_inputs=(ArtifactType.IMAGE,)),
        ),
        code_version="1.0",
        started_at=FIXED,
        completed_at=FIXED,
    )
    return RunResult(manifest=manifest, analyses=analyses)


def test_renders_family_and_signs() -> None:
    payload = PhilologyPayload(
        pipelines=(
            PipelinePhilology(
                pipeline="eng",
                family="abbreviations",
                n_total=3,
                n_strict=1,
                n_expansion=3,
                markers=(
                    MarkerPreservation(sign="ꝑ", n_total=2, n_strict=1, n_expansion=2),
                    MarkerPreservation(sign="ꝓ", n_total=1, n_strict=0, n_expansion=1),
                ),
            ),
        )
    )
    html = PhilologySection().render(
        _result((Analysis(scope="corpus", view="text", payload=payload),)),
        SectionContext(),
    )
    assert html is not None
    assert "Philologie" in html
    assert "abréviations médiévales" in html
    assert "ꝑ" in html and "ꝓ" in html
    assert "33.3%" in html  # strict global 1/3
    assert "100.0%" in html  # expansion global 3/3


def test_renders_positional_early_modern() -> None:
    payload = PhilologyPayload(
        pipelines=(
            PipelinePhilology(
                pipeline="eng",
                family="early_modern",
                n_total=4,
                n_strict=3,
                n_expansion=3,
                markers=(
                    MarkerPreservation(
                        sign="long_s", n_total=2, n_strict=1, n_expansion=1
                    ),
                    MarkerPreservation(
                        sign="ligatures", n_total=2, n_strict=2, n_expansion=2
                    ),
                ),
            ),
        )
    )
    html = PhilologySection().render(
        _result((Analysis(scope="corpus", view="text", payload=payload),)),
        SectionContext(),
    )
    assert html is not None
    assert "imprimé ancien" in html  # libellé de famille
    assert "préservé" in html  # lentille positionnelle
    assert "avec dév." not in html  # pas la colonne strict/expansion containment
    assert "s long (ſ)" in html  # libellé de catégorie
    assert "75.0%" in html  # préservation globale 3/4
    assert "50.0%" in html  # long_s 1/2


def test_renders_modern_archives_with_category_labels() -> None:
    payload = PhilologyPayload(
        pipelines=(
            PipelinePhilology(
                pipeline="eng",
                family="modern_archives",
                n_total=4,
                n_strict=3,
                n_expansion=4,
                markers=(
                    MarkerPreservation(
                        sign="civility_titles", n_total=2, n_strict=2, n_expansion=2
                    ),
                    MarkerPreservation(
                        sign="currency", n_total=2, n_strict=1, n_expansion=2
                    ),
                ),
            ),
        )
    )
    html = PhilologySection().render(
        _result((Analysis(scope="corpus", view="text", payload=payload),)),
        SectionContext(),
    )
    assert html is not None
    assert "archives modernes" in html
    assert "titres de civilité (Mme, Dr)" in html  # libellé de catégorie
    assert "avec dév." in html  # lentille strict/expansion (containment)
    assert "<th>catégorie</th>" in html  # en-tête catégorie, pas « signe »
    assert "75.0%" in html  # strict global 3/4
    assert "50.0%" in html  # currency strict 1/2


def test_renders_roman_numerals() -> None:
    payload = RomanNumeralsPayload(
        pipelines=(
            PipelineRomanNumerals(
                pipeline="eng",
                n_total=4,
                strict_preserved=1,
                case_changed=1,
                j_dropped=0,
                converted_to_arabic=1,
                lost=1,
                lost_samples=("XII",),
            ),
        )
    )
    html = PhilologySection().render(
        _result((Analysis(scope="corpus", view="text", payload=payload),)),
        SectionContext(),
    )
    assert html is not None
    assert "numéraux romains" in html
    assert "converti en arabe" in html  # libellé de statut
    assert "25.0%" in html  # strict 1/4
    assert "75.0%" in html  # valeur préservée (4-1)/4


def test_without_payload_renders_nothing() -> None:
    assert PhilologySection().render(_result(()), SectionContext()) is None


def test_renders_english_labels() -> None:
    philology = PhilologyPayload(
        pipelines=(
            PipelinePhilology(
                pipeline="eng",
                family="abbreviations",
                n_total=3,
                n_strict=1,
                n_expansion=3,
                markers=(
                    MarkerPreservation(sign="ꝑ", n_total=2, n_strict=1, n_expansion=2),
                ),
            ),
        )
    )
    roman = RomanNumeralsPayload(
        pipelines=(
            PipelineRomanNumerals(
                pipeline="eng",
                n_total=4,
                strict_preserved=1,
                case_changed=1,
                j_dropped=0,
                converted_to_arabic=1,
                lost=1,
                lost_samples=("XII",),
            ),
        )
    )
    html = PhilologySection().render(
        _result(
            (
                Analysis(scope="corpus", view="text", payload=philology),
                Analysis(scope="corpus", view="text", payload=roman),
            )
        ),
        SectionContext(lang="en"),
    )
    assert html is not None
    # libellés EN introduits…
    assert "Philology" in html
    assert "philological markers" in html
    assert "medieval abbreviations" in html
    assert "with expansion" in html
    assert "Roman numerals" in html
    assert "converted to Arabic" in html
    # … et leurs équivalents FR absents
    assert "Philologie" not in html
    assert "marqueurs philologiques" not in html
    assert "abréviations médiévales" not in html
    assert "avec développement" not in html
    assert "numéraux romains" not in html
    assert "converti en arabe" not in html
    # signe verbatim conservé (donnée, pas traduite)
    assert "ꝑ" in html
