"""Standardise un corpus brut (images + PAGE XML) en **layout dataset canonique
Cinoc**, prêt à publier sur Hugging Face (couche 6, outil de build déterministe).

Le layout assemble des **standards existants** (≠ norme inventée) :

```
<out>/
├── README.md                       carte HF (front-matter YAML + attribution)
├── corpus.json                     mapping mince → types domain (documents + strates)
├── ground_truth/<id>.gt.txt        vérité-terrain texte (RAW_TEXT, pour le scoring)
├── ground_truth/<id>.page.xml      PAGE XML source (verbatim)
└── iiif/<id>/
    ├── info.json                   IIIF Image API 3, profile level0 (statique)
    └── full/{max,1600,,400,}/0/default.jpg
```

Réutilise ``formats.pagexml`` (lecture GT) et ``adapters.images`` (dérivés). La
**publication** (upload ``huggingface_hub``, token write) est hors couche : un
script déclenché à la main (l'environnement de build n'a pas le secret).
"""

from __future__ import annotations

import json
import logging
import shutil
from dataclasses import dataclass
from pathlib import Path

from cinoc.adapters.images import iiif_derivative
from cinoc.domain.errors import CinocError
from cinoc.formats.pagexml import parse_pagexml
from cinoc.formats.pagexml.types import PagePage, PageRegion

logger = logging.getLogger(__name__)

#: Largeurs des dérivés IIIF (vignette galerie + medium drill-in). Pas de
#: deep-zoom (décision rapport) → deux tailles suffisent, plus l'original ``max``.
THUMBNAIL_WIDTH = 400
MEDIUM_WIDTH = 1600
_IIIF_IMAGE_CONTEXT = "http://iiif.io/api/image/3/context.json"
#: caractères autorisés dans un ``DocumentRef.id`` (cf. domain) — on s'y conforme.
_SAFE_ID = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-")


class DatasetStandardizeError(CinocError):
    """Échec de standardisation d'un corpus brut en layout dataset."""


@dataclass(frozen=True)
class StandardizeConfig:
    """Paramètres de curation d'un corpus (métadonnées + droits + strate)."""

    name: str
    stratum: str
    language: str
    transcription_license: str  # slug HF, ex. "cc-by-nc-sa-4.0"
    image_rights: str  # ex. "Public Domain Mark (SLUB Dresden)"
    attribution: str
    #: préfixe URL du dataset publié (résout l'``id`` IIIF) ; finalisé au publish.
    base_url: str = ""


def _doc_id(stem: str) -> str:
    """Identifiant de document sûr (cf. ``DocumentRef``) dérivé d'un nom de page.

    Les noms SLUB portent une espace (``Mscr.Dresd.K80 177``) → underscore. Tout
    autre caractère hors charset ``DocumentRef`` est rejeté (pas de mapping muet)."""
    candidate = stem.strip().replace(" ", "_")
    if not candidate or any(c not in _SAFE_ID for c in candidate):
        raise DatasetStandardizeError(
            f"nom de page non convertible en id de document : {stem!r}"
        )
    return candidate


def _region_lines(region: PageRegion) -> list[str]:
    """Lignes de texte d'une région (récursif sur sous-régions ; texte seul)."""
    lines: list[str] = []
    if region.kind == "text":
        lines.extend(line.text for line in region.text_lines)
        for sub in region.regions:
            lines.extend(_region_lines(sub))
    return lines


def _page_text(page: PagePage) -> str:
    """Vérité-terrain texte d'une page : lignes jointes par ``\\n`` (ordre du XML)."""
    lines: list[str] = []
    for region in page.regions:
        lines.extend(_region_lines(region))
    return "\n".join(lines).strip()


def _write_json(path: Path, payload: object) -> None:
    """Écrit du JSON déterministe (clés triées, UTF-8 lisible, newline final)."""
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _iiif_info(doc_id: str, width: int, height: int, sizes: list[dict[str, int]],
               base_url: str) -> dict[str, object]:
    """Document ``info.json`` IIIF Image API 3.0, ``profile`` level0 (statique)."""
    rel = f"iiif/{doc_id}"
    service_id = f"{base_url.rstrip('/')}/{rel}" if base_url else rel
    return {
        "@context": _IIIF_IMAGE_CONTEXT,
        "id": service_id,
        "type": "ImageService3",
        "protocol": "http://iiif.io/api/image",
        "profile": "level0",
        "width": width,
        "height": height,
        "sizes": sizes,
        "preferredFormats": ["jpg"],
    }


def _standardize_page(
    xml_path: Path, jpg_path: Path, out_dir: Path, config: StandardizeConfig
) -> dict[str, str]:
    """Traite une page : GT + dérivés IIIF + info.json → entrée ``corpus.json``."""
    doc_id = _doc_id(xml_path.stem)
    document = parse_pagexml(xml_path.read_bytes())
    if not document.pages:
        raise DatasetStandardizeError(f"PAGE sans page : {xml_path.name}")
    page = document.pages[0]
    if page.image_width is None or page.image_height is None:
        raise DatasetStandardizeError(
            f"PAGE sans dimensions image : {xml_path.name} (requis pour info.json)"
        )

    gt_dir = out_dir / "ground_truth"
    gt_dir.mkdir(parents=True, exist_ok=True)
    (gt_dir / f"{doc_id}.gt.txt").write_text(_page_text(page), encoding="utf-8")
    shutil.copyfile(xml_path, gt_dir / f"{doc_id}.page.xml")

    svc = out_dir / "iiif" / doc_id
    max_dest = svc / "full" / "max" / "0" / "default.jpg"
    max_dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(jpg_path, max_dest)

    sizes: list[dict[str, int]] = []
    for width in (THUMBNAIL_WIDTH, MEDIUM_WIDTH):
        dest = svc / "full" / f"{width}," / "0" / "default.jpg"
        produced = iiif_derivative(jpg_path, dest, width=width)
        if produced is None:
            raise DatasetStandardizeError(
                f"dérivé IIIF {width}px impossible pour {jpg_path.name} "
                "(Pillow requis : installer l'extra ``[images]``)"
            )
        sizes.append({"width": produced[0], "height": produced[1]})
    _write_json(
        svc / "info.json",
        _iiif_info(doc_id, page.image_width, page.image_height, sizes, config.base_url),
    )

    return {
        "id": doc_id,
        "image": f"iiif/{doc_id}/full/{MEDIUM_WIDTH},/0/default.jpg",
        "thumbnail": f"iiif/{doc_id}/full/{THUMBNAIL_WIDTH},/0/default.jpg",
        "ground_truth": f"ground_truth/{doc_id}.gt.txt",
        "page_xml": f"ground_truth/{doc_id}.page.xml",
        "stratum": config.stratum,
    }


def _dataset_card(config: StandardizeConfig, n_docs: int) -> str:
    """Carte HF : front-matter YAML (license/langue/tags) + provenance + droits."""
    return (
        "---\n"
        f"license: {config.transcription_license}\n"
        "language:\n"
        f"- {config.language}\n"
        f"pretty_name: {config.name}\n"
        "tags:\n"
        "- htr\n- ocr\n- handwritten-text-recognition\n- ground-truth\n- iiif\n"
        "---\n\n"
        f"# {config.name}\n\n"
        f"{n_docs} pages de vérité-terrain, standardisées pour Cinoc "
        "(IIIF statique + PAGE XML + texte).\n\n"
        f"- **Transcription** : {config.transcription_license}\n"
        f"- **Images** : {config.image_rights}\n"
        f"- **Strate** : `{config.stratum}`\n"
        f"- **Attribution** : {config.attribution}\n\n"
        "Layout : `corpus.json` (mapping documents), `ground_truth/` (`.gt.txt` "
        "+ `.page.xml`), `iiif/<id>/` (Image API 3, level0 statique).\n"
    )


def standardize_corpus(
    raw_dir: str | Path, out_dir: str | Path, config: StandardizeConfig
) -> Path:
    """Standardise ``raw_dir`` (sous-dossiers ``page/`` + ``jpg/``) → ``out_dir``.

    Apparie chaque ``page/<nom>.xml`` (hors ``METS.xml``) à ``jpg/<nom>.jpg``,
    produit GT + dérivés IIIF + ``info.json``, puis ``corpus.json`` (mapping →
    domain) et ``README.md`` (carte HF). Déterministe. Renvoie ``out_dir``."""
    raw = Path(raw_dir)
    page_dir, jpg_dir = raw / "page", raw / "jpg"
    if not page_dir.is_dir() or not jpg_dir.is_dir():
        raise DatasetStandardizeError(
            f"layout brut attendu : {raw}/page/ + {raw}/jpg/ (introuvables)"
        )
    xml_files = sorted(
        p for p in page_dir.glob("*.xml") if p.name.lower() != "mets.xml"
    )
    if not xml_files:
        raise DatasetStandardizeError(f"aucune page PAGE dans {page_dir}")

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    documents: list[dict[str, str]] = []
    for xml_path in xml_files:
        jpg_path = jpg_dir / f"{xml_path.stem}.jpg"
        if not jpg_path.is_file():
            raise DatasetStandardizeError(
                f"image absente pour {xml_path.name} : {jpg_path.name} attendu"
            )
        documents.append(_standardize_page(xml_path, jpg_path, out, config))

    _write_json(
        out / "corpus.json",
        {
            "name": config.name,
            "license": {
                "transcription": config.transcription_license,
                "images": config.image_rights,
            },
            "attribution": config.attribution,
            "documents": documents,
        },
    )
    (out / "README.md").write_text(
        _dataset_card(config, len(documents)), encoding="utf-8"
    )
    logger.info("[dataset] %d pages standardisées → %s", len(documents), out)
    return out


__all__ = ["StandardizeConfig", "DatasetStandardizeError", "standardize_corpus"]
