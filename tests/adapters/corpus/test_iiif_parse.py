"""Parseur IIIF v2/v3 (pur, sans réseau) : URL d'image directe ou via service."""

from __future__ import annotations

from xerocr.adapters.corpus.iiif import parse_manifest

V2 = {
    "@context": "http://iiif.io/api/presentation/2/context.json",
    "sequences": [
        {
            "canvases": [
                {
                    "label": "f. 1",
                    "images": [{"resource": {"@id": "https://ex.org/img/1.jpg"}}],
                },
                {
                    "label": "f. 2",
                    "images": [{"resource": {"service": {"@id": "https://ex.org/iiif/2"}}}],
                },
                {"label": "f. 3 sans image", "images": []},
            ]
        }
    ],
}

V3 = {
    "@context": "http://iiif.io/api/presentation/3/context.json",
    "type": "Manifest",
    "items": [
        {
            "label": {"en": ["Page 1"]},
            "items": [
                {"items": [{"body": {"id": "https://ex.org/p1.jpg", "type": "Image"}}]}
            ],
        },
        {
            "label": {"fr": ["Page 2"]},
            "items": [
                {"items": [{"body": {"type": "Image", "service": [{"id": "https://ex.org/iiif/p2"}]}}]}
            ],
        },
    ],
}


def test_v2_direct_and_service_urls() -> None:
    images = parse_manifest(V2)
    assert len(images) == 2  # le canvas sans image est ignoré
    assert images[0].image_url == "https://ex.org/img/1.jpg"
    assert images[0].label == "f. 1"
    # via service IIIF Image API → construction de l'URL d'image
    assert images[1].image_url == "https://ex.org/iiif/2/full/max/0/default.jpg"


def test_v3_direct_and_service_and_language_map() -> None:
    images = parse_manifest(V3)
    assert len(images) == 2
    assert images[0].image_url == "https://ex.org/p1.jpg"
    assert images[0].label == "Page 1"  # map de langue v3 aplatie
    assert images[1].image_url == "https://ex.org/iiif/p2/full/max/0/default.jpg"
    assert images[1].label == "Page 2"


def test_label_fallback_when_missing() -> None:
    manifest = {
        "@context": "http://iiif.io/api/presentation/3/context.json",
        "type": "Manifest",
        "items": [
            {
                "items": [
                    {"items": [{"body": {"id": "http://e.org/x", "type": "Image"}}]}
                ]
            }
        ],
    }
    images = parse_manifest(manifest)
    assert images[0].label == "canvas_1"


def test_v3_label_nested_list_is_stringified() -> None:
    # Une map de langue dont la valeur est une liste non-str ne doit pas casser
    # le type str de IIIFImage.label (régression d'audit).
    manifest = {
        "@context": "http://iiif.io/api/presentation/3/context.json",
        "type": "Manifest",
        "items": [
            {
                "label": {"none": [42]},
                "items": [
                    {"items": [{"body": {"id": "http://e.org/x", "type": "Image"}}]}
                ],
            }
        ],
    }
    (image,) = parse_manifest(manifest)
    assert image.label == "42" and isinstance(image.label, str)


def test_empty_manifest_yields_no_images() -> None:
    assert parse_manifest({"@context": "…/presentation/3/…", "type": "Manifest"}) == ()
    assert parse_manifest({}) == ()
