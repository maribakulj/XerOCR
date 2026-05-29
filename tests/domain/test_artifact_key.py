from __future__ import annotations

from xerocr.domain import ArtifactKey


def test_canonical_json_is_order_independent():
    k1 = ArtifactKey(
        adapter_name="t", step_params={"b": 1, "a": 2},
        input_hashes=(("raw_text", "h"),),
    )
    k2 = ArtifactKey(
        adapter_name="t", step_params={"a": 2, "b": 1},
        input_hashes=(("raw_text", "h"),),
    )
    assert k1.to_canonical_json() == k2.to_canonical_json()
    assert k1.hash_hex() == k2.hash_hex()


def test_hash_none_when_input_missing():
    assert ArtifactKey(input_hashes=(("raw_text", ""),)).hash_hex() is None


def test_hash_is_64_hex():
    h = ArtifactKey(input_hashes=(("raw_text", "h"),), adapter_name="x").hash_hex()
    assert h is not None
    assert len(h) == 64
    int(h, 16)  # parsable hex
