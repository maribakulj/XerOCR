"""``AltoLayoutSource`` : faire entrer un ALTO existant sans l'aplatir.

Le banc savait produire une mise en page et savait en consommer une ; il ne
savait pas **lire celle qui accompagne déjà le corpus**. Un ALTO patrimonial ne
pouvait donc entrer qu'en texte plat — en y perdant l'identité de ligne, la
géométrie et la césure, c'est-à-dire tout ce qui distingue une mise en page
d'une chaîne de caractères.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cinoc.adapters.layout.alto_source import AltoLayoutSource
from cinoc.domain.artifacts import Artifact, ArtifactType
from cinoc.domain.errors import AdapterStepError
from cinoc.domain.layout import CanonicalLayout
from cinoc.pipeline.run_control import RunControl
from cinoc.pipeline.types import RunContext

_NS = 'xmlns="http://www.loc.gov/standards/alto/ns-v4#"'


def _alto(lines: str) -> bytes:
    return (
        f'<alto {_NS}><Layout><Page ID="P1" WIDTH="600" HEIGHT="400">'
        f'<PrintSpace><TextBlock ID="B1">{lines}</TextBlock>'
        f"</PrintSpace></Page></Layout></alto>"
    ).encode()


_ONE_LINE = _alto(
    '<TextLine ID="L1" HPOS="10" VPOS="20" WIDTH="300" HEIGHT="40">'
    '<String CONTENT="Bonjour" WC="0.9"/><SP/>'
    '<String CONTENT="tra" SUBS_TYPE="HypPart1" SUBS_CONTENT="travailleurs"/>'
    "<HYP/></TextLine>"
)


def _run(tmp_path: Path, *, alto: bytes = _ONE_LINE, stem: str = "page") -> Artifact:
    (tmp_path / f"{stem}.png").write_bytes(b"pas une vraie image")
    (tmp_path / f"{stem}.xml").write_bytes(alto)
    out = AltoLayoutSource().execute(
        {
            ArtifactType.IMAGE: Artifact(
                id="img",
                document_id="doc1",
                type=ArtifactType.IMAGE,
                uri=str(tmp_path / f"{stem}.png"),
                content_hash="0" * 64,
            )
        },
        {},
        RunContext(
            document_id="doc1",
            code_version="1.0",
            pipeline_name="p",
            workspace_uri=str(tmp_path / "ws"),
        ),
        RunControl(),
    )
    return out.artifacts[ArtifactType.LAYOUT]


def test_reads_the_alto_next_to_the_image(tmp_path: Path) -> None:
    art = _run(tmp_path)
    layout = CanonicalLayout.model_validate_json(Path(art.uri).read_bytes())
    line = layout.pages[0].regions[0].lines[0]

    assert line.id == "L1"  # l'identité, pas un rang
    assert line.text == "Bonjour tra-"  # SP et HYP compris
    assert line.geometry is not None and line.geometry.bbox is not None
    assert line.words[-1].subs_content == "travailleurs"


def test_line_confidence_survives(tmp_path: Path) -> None:
    """La confiance du moteur d'origine est une donnée, pas du décor : elle
    dit quelles lignes méritent qu'on les regarde."""
    art = _run(tmp_path)
    layout = CanonicalLayout.model_validate_json(Path(art.uri).read_bytes())
    assert layout.pages[0].regions[0].lines[0].words[0].confidence == 0.9


def test_missing_alto_names_what_it_looked_for(tmp_path: Path) -> None:
    (tmp_path / "seule.png").write_bytes(b"x")
    with pytest.raises(AdapterStepError, match="aucun ALTO"):
        AltoLayoutSource().execute(
            {
                ArtifactType.IMAGE: Artifact(
                    id="img",
                    document_id="d",
                    type=ArtifactType.IMAGE,
                    uri=str(tmp_path / "seule.png"),
                    content_hash="0" * 64,
                )
            },
            {},
            RunContext(document_id="d", code_version="1.0", pipeline_name="p"),
            RunControl(),
        )


def test_a_line_without_id_is_refused(tmp_path: Path) -> None:
    """Sans identifiant, une ligne n'a pas d'identité d'un artefact à l'autre.

    Refusé **ici** plutôt qu'en aval : l'étape suivante échouerait sur une
    cause qui n'est pas la sienne.
    """
    anonyme = _alto('<TextLine><String CONTENT="sans identifiant"/></TextLine>')
    with pytest.raises(AdapterStepError, match="sans attribut ID"):
        _run(tmp_path, alto=anonyme)


def test_registered_under_its_own_kind() -> None:
    """Le module est résolvable par le registre, comme n'importe quelle brique."""
    from cinoc.app.modules.registry import ModuleRegistry, register_default_modules

    registry = ModuleRegistry()
    register_default_modules(registry)
    module = registry.build("alto_source", {})
    assert module.input_types == frozenset({ArtifactType.IMAGE})
    assert module.output_types == frozenset({ArtifactType.LAYOUT})
