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
from xerocr.adapters.corpus.gallica import GALLICA_BASE, GallicaImporter
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
OcrFetcher = Callable[[int], str]


class CorpusImportError(XerOCRError):
    """L'import d'un corpus distant n'a produit aucune page exploitable."""


def _image_ext(image_url: str) -> str:
    suffix = Path(urlsplit(image_url).path).suffix.lower()
    return suffix if suffix in _IMAGE_EXT else _DEFAULT_EXT


def _download_image(
    fetch_bytes: Downloader, image_url: str, doc_id: str, dest_dir: Path
) -> str:
    """Télécharge une image sous ``dest_dir`` (chemin validé) ; renvoie l'URI local."""
    target = validated_path(f"{doc_id}{_image_ext(image_url)}", dest_dir)
    fetch_bytes(image_url, target)
    return str(target)


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
        image_uri = _download_image(fetch_bytes, image.image_url, doc_id, dest_dir)
        documents.append(
            DocumentRef(id=doc_id, image_uri=image_uri, ground_truths=())
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
        image_uri = _download_image(fetch_bytes, page.image_url, doc_id, dest_dir)
        ground_truths: tuple[GroundTruthRef, ...] = ()
        if page.gt_text.strip():
            gt_target = validated_path(f"{doc_id}.gt.txt", dest_dir)
            gt_target.write_text(page.gt_text, encoding="utf-8")
            ground_truths = (
                GroundTruthRef(type=ArtifactType.RAW_TEXT, uri=str(gt_target)),
            )
        documents.append(
            DocumentRef(id=doc_id, image_uri=image_uri, ground_truths=ground_truths)
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


def import_gallica_corpus(
    ark: str,
    dest: str | Path,
    *,
    base_url: str = GALLICA_BASE,
    name: str | None = None,
    limit: int | None = None,
    include_ocr: bool = True,
    image_importer: IIIFImporter | None = None,
    download: Downloader | None = None,
    fetch_ocr: OcrFetcher | None = None,
) -> CorpusSpec:
    """Importe un document Gallica (ARK) → images (via IIIF) + OCR Gallica optionnel.

    Les images viennent du **manifeste IIIF** Gallica ; si ``include_ocr``, l'OCR
    brut de chaque vue (``texteBrut``) est écrit comme **référence étiquetée**
    (``gt_source=gallica_ocr`` — pas une GT manuelle). La vue en position ``i``
    (1-based) correspond directement à ``f{i}.texteBrut`` : pas d'indirection, donc
    pas de décalage de page.
    """
    gallica = GallicaImporter(ark, base_url=base_url)
    fetch_bytes: Downloader = download or _http.download
    ocr_of: OcrFetcher = fetch_ocr or gallica.fetch_ocr_text
    dest_dir = Path(dest)
    dest_dir.mkdir(parents=True, exist_ok=True)

    images = (image_importer or IIIFImporter()).fetch_images(gallica.manifest_url)
    if limit is not None:
        images = images[:limit]
    if not images:
        raise CorpusImportError(f"aucune image pour l'ARK Gallica {gallica.ark!r}.")

    documents: list[DocumentRef] = []
    has_ocr_gt = False
    for page, image in enumerate(images, start=1):
        doc_id = f"f{page:04d}"
        image_uri = _download_image(fetch_bytes, image.image_url, doc_id, dest_dir)
        ground_truths: tuple[GroundTruthRef, ...] = ()
        if include_ocr:
            text = ocr_of(page)
            if text.strip():
                gt_target = validated_path(f"{doc_id}.gallica_ocr.txt", dest_dir)
                gt_target.write_text(text, encoding="utf-8")
                ground_truths = (
                    GroundTruthRef(type=ArtifactType.RAW_TEXT, uri=str(gt_target)),
                )
                has_ocr_gt = True
        documents.append(
            DocumentRef(id=doc_id, image_uri=image_uri, ground_truths=ground_truths)
        )

    metadata = {
        "source": "gallica",
        "ark": gallica.ark,
        "manifest_url": gallica.manifest_url,
    }
    if has_ocr_gt:
        metadata["gt_source"] = "gallica_ocr"
    return CorpusSpec(
        name=name or f"gallica-{gallica.ark.split('/')[-1]}",
        documents=tuple(documents),
        metadata=metadata,
    )


__all__ = [
    "CorpusImportError",
    "import_escriptorium_corpus",
    "import_gallica_corpus",
    "import_iiif_corpus",
]
