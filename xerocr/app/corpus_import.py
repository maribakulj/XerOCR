"""Matérialisation d'un corpus IIIF en ``CorpusSpec`` (couche 6).

Sépare **localiser** (l'adapter ``IIIFImporter`` parle IIIF) de **matérialiser**
(ici : télécharger les images sous ``dest`` validé, fabriquer le ``CorpusSpec``).
Sortie **unique** : un ``CorpusSpec`` (jamais un dict-manifeste), prêt pour un run.

Images seules → ``DocumentRef`` sans vérité-terrain : le corpus est OCR-able mais
non scoré tant qu'une GT n'est pas appariée (cf. ``adapters/corpus/iiif.py``).

``importer`` et ``download`` sont **injectables** → le chemin de matérialisation
se teste sans réseau ; le test ``live`` couvre le vrai fetch IIIF.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlsplit

from xerocr.adapters.corpus import _http
from xerocr.adapters.corpus.escriptorium import DEFAULT_LAYER, EScriptoriumImporter
from xerocr.adapters.corpus.iiif import IIIFImage, IIIFImporter
from xerocr.app.security import validated_path
from xerocr.domain.artifacts import ArtifactType
from xerocr.domain.corpus import CorpusSpec
from xerocr.domain.documents import DocumentRef, GroundTruthRef
from xerocr.domain.errors import XerOCRError

logger = logging.getLogger(__name__)

#: Extensions d'image reconnues pour nommer le fichier téléchargé.
_IMAGE_EXT = frozenset({".png", ".jpg", ".jpeg", ".tif", ".tiff", ".jp2"})
_DEFAULT_EXT = ".jpg"

ImageFetcher = Callable[[str], "tuple[IIIFImage, ...]"]
Downloader = Callable[[str, Path], None]


class CorpusImportError(XerOCRError):
    """L'import d'un corpus distant n'a produit aucune page exploitable."""


def _image_ext(image_url: str) -> str:
    suffix = Path(urlsplit(image_url).path).suffix.lower()
    return suffix if suffix in _IMAGE_EXT else _DEFAULT_EXT


def import_iiif_corpus(
    manifest_url: str,
    dest: str | Path,
    *,
    name: str,
    limit: int | None = None,
    importer: IIIFImporter | None = None,
    download: Downloader | None = None,
) -> CorpusSpec:
    """Importe un manifeste IIIF → images téléchargées sous ``dest`` → ``CorpusSpec``.

    ``limit`` borne le nombre de pages (les premières). ``dest`` est créé au besoin ;
    chaque fichier passe par ``validated_path`` (anti-traversal).
    """
    fetch_images: ImageFetcher = (importer or IIIFImporter()).fetch_images
    fetch_bytes: Downloader = download or _http.download
    dest_dir = Path(dest)
    dest_dir.mkdir(parents=True, exist_ok=True)

    images = fetch_images(manifest_url)
    if limit is not None:
        images = images[:limit]
    if not images:
        raise CorpusImportError(
            f"aucune image exploitable dans le manifeste {manifest_url!r}."
        )

    documents: list[DocumentRef] = []
    for index, image in enumerate(images, start=1):
        doc_id = f"page_{index:04d}"
        target = validated_path(f"{doc_id}{_image_ext(image.image_url)}", dest_dir)
        fetch_bytes(image.image_url, target)
        documents.append(
            DocumentRef(id=doc_id, image_uri=str(target), ground_truths=())
        )

    return CorpusSpec(
        name=name,
        documents=tuple(documents),
        metadata={"source": "iiif", "manifest_url": manifest_url},
    )


def import_escriptorium_corpus(
    base_url: str,
    token: str,
    doc_pk: int,
    dest: str | Path,
    *,
    name: str | None = None,
    layer: str = DEFAULT_LAYER,
    limit: int | None = None,
    importer: EScriptoriumImporter | None = None,
    download: Downloader | None = None,
) -> CorpusSpec:
    """Importe un document eScriptorium → corpus **scorable** sous ``dest``.

    Pour chaque page : télécharge l'image et écrit le texte de la couche ``layer``
    comme vérité-terrain (``.gt.txt`` → ``GroundTruthRef`` ``RAW_TEXT``). Une page
    sans texte reste image-seule ; une page sans image est ignorée (avertie).
    """
    imp = importer or EScriptoriumImporter(base_url, token, layer=layer)
    fetch_bytes: Downloader = download or _http.download
    dest_dir = Path(dest)
    dest_dir.mkdir(parents=True, exist_ok=True)

    pages = imp.fetch_pages(doc_pk)
    if limit is not None:
        pages = pages[:limit]

    documents: list[DocumentRef] = []
    for page in pages:
        if not page.image_url:
            logger.warning("[escriptorium] part %s sans image — ignorée.", page.pk)
            continue
        doc_id = f"part_{page.pk:05d}"
        image_target = validated_path(f"{doc_id}{_image_ext(page.image_url)}", dest_dir)
        fetch_bytes(page.image_url, image_target)
        ground_truths: tuple[GroundTruthRef, ...] = ()
        if page.gt_text.strip():
            gt_target = validated_path(f"{doc_id}.gt.txt", dest_dir)
            gt_target.write_text(page.gt_text, encoding="utf-8")
            ground_truths = (
                GroundTruthRef(type=ArtifactType.RAW_TEXT, uri=str(gt_target)),
            )
        documents.append(
            DocumentRef(
                id=doc_id, image_uri=str(image_target), ground_truths=ground_truths
            )
        )

    if not documents:
        raise CorpusImportError(
            f"document eScriptorium {doc_pk} : aucune page avec image exploitable."
        )
    return CorpusSpec(
        name=name or f"escriptorium-{doc_pk}",
        documents=tuple(documents),
        metadata={
            "source": "escriptorium",
            "base_url": base_url.rstrip("/"),
            "doc_pk": str(doc_pk),
            "layer": layer,
        },
    )


__all__ = [
    "CorpusImportError",
    "import_escriptorium_corpus",
    "import_iiif_corpus",
]
