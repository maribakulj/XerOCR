"""Section diagnostic : lecture seule du payload, rendu déterministe."""

from __future__ import annotations

from datetime import UTC, datetime

from xerocr.domain.run import RunManifest
from xerocr.evaluation.analysis import (
    Analysis,
    CharConfusion,
    DiagnosticsPayload,
    HardDocument,
    PipelineConfusions,
    WorstLine,
)
from xerocr.evaluation.result import RunResult
from xerocr.reports.section import Section, SectionContext
from xerocr.reports.sections.diagnostics import DiagnosticsSection

FIXED = datetime(2026, 6, 1, tzinfo=UTC)


def _result() -> RunResult:
    payload = DiagnosticsPayload(
        metric="cer",
        confusions=(
            PipelineConfusions(
                pipeline="tess",
                pairs=(CharConfusion(expected="e", observed="o", count=12),),
            ),
        ),
        worst_lines=(
            WorstLine(
                pipeline="tess",
                document_id="d7",
                line_index=3,
                cer=0.62,
                reference="le chevalier <s>preux</s>",
                hypothesis="lo chovalior preux",
            ),
        ),
        hardest_documents=(
            HardDocument(document_id="d7", mean_cer=0.41, n_pipelines=3),
        ),
    )
    manifest = RunManifest(
        run_id="r",
        corpus_name="c",
        n_documents=1,
        code_version="1.0",
        started_at=FIXED,
        completed_at=FIXED,
    )
    return RunResult(
        manifest=manifest,
        analyses=(Analysis(scope="corpus", view="text", payload=payload),),
    )


def test_satisfies_section_protocol() -> None:
    section = DiagnosticsSection()
    assert isinstance(section, Section)
    assert section.name == "diagnostics"


def test_renders_confusions_lines_and_hardest_with_escaping() -> None:
    html = DiagnosticsSection().render(_result(), SectionContext())
    assert html is not None
    assert "e → o" in html and "12" in html
    assert "0.6200" in html and "d7" in html
    # Drill-in : diff GT↔hypothèse surligné caractère à caractère.
    assert 'class="d-del"' in html  # suppressions (présentes en GT)
    assert 'class="d-ins"' in html  # insertions (produites par le moteur)
    # Les extraits verbatim restent **échappés** même découpés par le diff
    # (anti-XSS) : `<s>` n'apparaît jamais brut, seulement `&lt;s&gt;`.
    assert "<s>preux</s>" not in html and "&lt;s&gt;" in html
    assert "preux" in html  # segment identique rendu tel quel
    assert "0.4100" in html
    assert html == DiagnosticsSection().render(_result(), SectionContext())


def test_without_payload_renders_nothing() -> None:
    manifest = RunManifest(
        run_id="r", corpus_name="c", n_documents=0,
        code_version="1.0", started_at=FIXED, completed_at=FIXED,
    )
    assert (
        DiagnosticsSection().render(RunResult(manifest=manifest), SectionContext())
        is None
    )
