"""Rejeu **déterministe** des cassettes réelles (Lot E) : les vrais importeurs
tournent hors-ligne sur des réponses HTTP enregistrées → on prouve le **parsing
réel** (≠ mocks), reproductible en CI.

Les cassettes vivent dans ``tests/fixtures/cassettes/`` (capturées par
``scripts/capture_cassettes.py`` contre les vraies sources).
"""

from __future__ import annotations

from pathlib import Path

from tests.adapters.corpus._cassette import replaying
from xerocr.adapters.corpus.huggingface import HuggingFaceCatalogue
from xerocr.app.corpus_import import import_iiif_corpus

#: URL exacte du manifeste enregistré dans la cassette IIIF.
_IIIF_MANIFEST = "https://iiif.io/api/cookbook/recipe/0009-book-1/manifest.json"


def test_iiif_cassette_parses_manifest_and_downloads(tmp_path: Path) -> None:
    # Manifeste IIIF v3 réel (cookbook) + 2 images → CorpusSpec à 2 pages, images
    # écrites sur disque. Le parsing du manifeste (v3) est exercé sur vraie donnée.
    with replaying("iiif"):
        spec = import_iiif_corpus(_IIIF_MANIFEST, tmp_path, name="iiif", limit=2)

    assert spec.name == "iiif"
    assert spec.metadata["source"] == "iiif"
    assert [d.id for d in spec.documents] == ["page_0001", "page_0002"]
    for doc in spec.documents:
        image = Path(doc.image_uri)
        assert image.exists() and image.stat().st_size > 0  # image téléchargée
        assert doc.ground_truths == ()  # IIIF = images seules


def test_hf_cassette_parses_discovery() -> None:
    # Réponse réelle de l'API du Hub (task image-to-text, q="manuscript") → des
    # datasets parsés avec source="api" (le parsing de la découverte est exercé).
    with replaying("hf"):
        results = HuggingFaceCatalogue().search("manuscript")

    assert results, "la cassette HF doit produire au moins un dataset"
    api = [d for d in results if d.source == "api"]
    assert api, "au moins un dataset doit venir de l'API (parsing réel)"
    assert all(d.dataset_id for d in api)  # chaque entrée API a un id non vide
