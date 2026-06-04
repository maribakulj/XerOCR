"""Import IIIF **réel** de bout en bout — **opt-in strict** (réseau externe).

Couvre ce que les mocks masquent (finding F9/R-7) : le vrai fetch du manifeste, le
parsing du schéma servi, le téléchargement d'une vraie image et la fabrication du
``CorpusSpec``. Cible le **IIIF Cookbook** officiel (stable, public).

⚠️ **Skip par défaut** (comme les tests `live` BNL) : un test qui frappe un hôte
externe est non déterministe et n'a pas sa place dans la CI. Il ne s'exécute que si
``XEROCR_LIVE_IIIF`` est défini. La couverture transport déterministe vit dans
``test_iiif_local_server.py`` (loopback réel, en CI).
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from xerocr.adapters.corpus.iiif import IIIFImporter
from xerocr.app.corpus_import import import_iiif_corpus

pytestmark = [pytest.mark.network, pytest.mark.live]

MANIFEST = "https://iiif.io/api/cookbook/recipe/0001-mvm-image/manifest.json"


def _skip_unless_opted_in() -> None:
    if not os.environ.get("XEROCR_LIVE_IIIF"):
        pytest.skip("XEROCR_LIVE_IIIF non défini (test réseau externe opt-in).")


def test_fetch_real_manifest_images() -> None:
    _skip_unless_opted_in()
    images = IIIFImporter().fetch_images(MANIFEST)
    assert len(images) >= 1
    # le Cookbook sert des URLs http:// ou https:// selon les recettes
    assert images[0].image_url.startswith(("http://", "https://"))


def test_import_real_corpus(tmp_path: Path) -> None:
    _skip_unless_opted_in()
    spec = import_iiif_corpus(MANIFEST, tmp_path, name="cookbook", limit=1)
    assert len(spec.documents) == 1
    image_path = Path(spec.documents[0].image_uri)
    assert image_path.exists() and image_path.stat().st_size > 0
    assert spec.documents[0].ground_truths == ()
