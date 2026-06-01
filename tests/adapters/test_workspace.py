"""``workspace_artifact_path`` : stem injectif, sans séparateur de chemin."""

from __future__ import annotations

from pathlib import Path

from xerocr.adapters._workspace import safe_document_stem, workspace_artifact_path


def test_stem_is_filesystem_safe() -> None:
    assert "/" not in safe_document_stem("vol1/page1")


def test_stem_is_injective_on_slash_vs_underscore() -> None:
    # le bug classique : "a/b" et "a_b" ne doivent PAS produire le même stem
    # (sinon deux documents distincts s'écrasent dans le workspace).
    assert safe_document_stem("a/b") != safe_document_stem("a_b")


def test_stem_is_injective_on_adjacent_slash_underscore() -> None:
    # cas limite qu'un échappement maison "_→__ puis /→_" collisionnerait
    # (les deux donneraient "a___b") : l'encodage réversible les sépare.
    assert safe_document_stem("a/_b") != safe_document_stem("a_/b")


def test_common_ids_stay_readable() -> None:
    assert safe_document_stem("folio_001") == "folio_001"  # rien à encoder


def test_path_layout() -> None:
    assert workspace_artifact_path("/ws", "doc1", "fra", "txt") == Path(
        "/ws/doc1.fra.txt"
    )


def test_path_collision_free_for_munged_ids() -> None:
    p1 = workspace_artifact_path("/ws", "a/b", "fra", "txt")
    p2 = workspace_artifact_path("/ws", "a_b", "fra", "txt")
    assert p1 != p2
