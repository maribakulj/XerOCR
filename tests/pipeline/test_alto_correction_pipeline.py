"""Bout-en-bout : ``ALTO → LAYOUT → correction`` par le **vrai exécuteur**.

Les briques étaient vérifiées une par une ; ce test vérifie qu'elles se
composent — c'est-à-dire la seule chose qu'aucun test unitaire ne peut dire.

Il verrouille surtout le choix de conception qui a évité d'inventer un type
d'artefact ``CORRECTED_LAYOUT`` : le pool de l'exécuteur étant indexé **par
type**, le second ``LAYOUT`` écrase le premier, et c'est voulu — le plus abouti
gagne. Ce qui manquerait alors au bilan de correction (un ``RAW_TEXT`` **et** un
``CORRECTED_TEXT``) est fourni par deux étapes distinctes.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cinoc.app.modules.registry import ModuleRegistry, register_default_modules
from cinoc.domain.artifacts import Artifact, ArtifactType
from cinoc.domain.pipeline import INITIAL_STEP_ID, PipelineSpec, PipelineStep
from cinoc.pipeline.executor import PipelineExecutor

pytest.importorskip("saknussemm")

_NS = 'xmlns="http://www.loc.gov/standards/alto/ns-v4#"'

#: Le ``ſ`` long est l'une des trois substitutions des règles françaises par
#: défaut : sans lui, le test ne saurait pas distinguer « rien à corriger » de
#: « la chaîne ne corrige rien ».
_ALTO = (
    f'<alto {_NS}><Layout><Page ID="P1" WIDTH="600" HEIGHT="400"><PrintSpace>'
    '<TextBlock ID="B1">'
    '<TextLine ID="L1" HPOS="10" VPOS="10" WIDTH="300" HEIGHT="30">'
    '<String CONTENT="le" WC="0.9"/><SP/><String CONTENT="ſoleil"/></TextLine>'
    '<TextLine ID="L2" HPOS="10" VPOS="50" WIDTH="300" HEIGHT="30">'
    '<String CONTENT="rien"/><SP/><String CONTENT="ici"/></TextLine>'
    "</TextBlock></PrintSpace></Page></Layout></alto>"
).encode()


def _spec() -> PipelineSpec:
    return PipelineSpec(
        name="alto→saknussemm",
        initial_inputs=(ArtifactType.IMAGE,),
        steps=(
            PipelineStep(
                id="source",
                kind="layout_source",
                adapter_name="alto_source",
                input_types=(ArtifactType.IMAGE,),
                output_types=(ArtifactType.LAYOUT,),
                inputs_from={ArtifactType.IMAGE: INITIAL_STEP_ID},
            ),
            PipelineStep(
                id="brut",
                kind="projection",
                adapter_name="layout_to_text:brut",
                input_types=(ArtifactType.LAYOUT,),
                output_types=(ArtifactType.RAW_TEXT,),
                inputs_from={ArtifactType.LAYOUT: "source"},
            ),
            PipelineStep(
                id="corr",
                kind="post_correction",
                adapter_name="saknussemm:regles",
                input_types=(ArtifactType.LAYOUT,),
                output_types=(ArtifactType.LAYOUT, ArtifactType.CORRECTED_TEXT),
                # Explicitement la sortie de ``source`` : le pool porterait
                # sinon le LAYOUT le plus récent, qui est celui d'après.
                inputs_from={ArtifactType.LAYOUT: "source"},
            ),
        ),
    )


def _run(tmp_path: Path):
    (tmp_path / "p.png").write_bytes(b"pas une vraie image")
    (tmp_path / "p.xml").write_bytes(_ALTO)
    registry = ModuleRegistry()
    register_default_modules(registry)
    modules = {
        "alto_source": registry.build("alto_source", {}),
        "layout_to_text:brut": registry.build("layout_to_text:brut", {"label": "brut"}),
        "saknussemm:regles": registry.build("saknussemm:regles", {"label": "regles"}),
    }
    return PipelineExecutor(code_version="test").execute_document(
        _spec(),
        modules,
        {
            ArtifactType.IMAGE: Artifact(
                id="i",
                document_id="doc1",
                type=ArtifactType.IMAGE,
                uri=str(tmp_path / "p.png"),
                content_hash="0" * 64,
            )
        },
        document_id="doc1",
        workspace_uri=str(tmp_path / "ws"),
    )


def test_the_three_steps_compose(tmp_path: Path) -> None:
    result = _run(tmp_path)
    attendus = {
        ArtifactType.LAYOUT,
        ArtifactType.RAW_TEXT,
        ArtifactType.CORRECTED_TEXT,
    }
    assert attendus <= set(result.artifacts)


def test_the_correction_stage_owns_the_final_layout(tmp_path: Path) -> None:
    """Le pool est indexé par type : le ``LAYOUT`` d'arrivée est le corrigé."""
    result = _run(tmp_path)
    assert result.artifacts[ArtifactType.LAYOUT].produced_by_step == "corr"
    assert result.artifacts[ArtifactType.RAW_TEXT].produced_by_step == "brut"
    assert result.artifacts[ArtifactType.CORRECTED_TEXT].produced_by_step == "corr"


def test_the_two_texts_are_what_the_correction_balance_needs(tmp_path: Path) -> None:
    """``RAW_TEXT`` et ``CORRECTED_TEXT`` se correspondent ligne pour ligne.

    C'est ce qui permet au bilan de correction de fonctionner **sans être
    modifié**. Un décalage d'une seule ligne fausserait tout l'appariement sans
    rien casser de visible.
    """
    result = _run(tmp_path)
    brut = Path(result.artifacts[ArtifactType.RAW_TEXT].uri).read_text(encoding="utf-8")
    corrige = Path(result.artifacts[ArtifactType.CORRECTED_TEXT].uri).read_text(
        encoding="utf-8"
    )
    assert brut.splitlines() == ["le ſoleil", "rien ici"]
    assert corrige.splitlines() == ["le soleil", "rien ici"]
