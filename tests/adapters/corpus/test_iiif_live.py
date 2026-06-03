"""Import IIIF **réel** de bout en bout (opt-in : ``-m live`` / ``-m network``).

Couvre précisément ce que les mocks masquent (finding F9/R-7) : le vrai fetch du
manifeste, le parsing du schéma servi, et — pour le test complet — le téléchargement
d'une vraie image et la fabrication du ``CorpusSpec``. Cible le **IIIF Cookbook**
officiel (manifeste v3 stable, public).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from xerocr.adapters.corpus.iiif import IIIFImporter
from xerocr.app.corpus_import import import_iiif_corpus

pytestmark = [pytest.mark.network, pytest.mark.live]

MANIFEST = "https://iiif.io/api/cookbook/recipe/0001-mvm-image/manifest.json"


def test_fetch_real_manifest_images() -> None:
    images = IIIFImporter().fetch_images(MANIFEST)
    assert len(images) >= 1
    assert images[0].image_url.startswith("https://")


def test_import_real_corpus(tmp_path: Path) -> None:
    spec = import_iiif_corpus(MANIFEST, tmp_path, name="cookbook", limit=1)
    assert len(spec.documents) == 1
    image_path = Path(spec.documents[0].image_uri)
    assert image_path.exists() and image_path.stat().st_size > 0
    assert spec.documents[0].ground_truths == ()
