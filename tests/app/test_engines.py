"""Détection de disponibilité des moteurs : sondes injectées → déterministe."""

from __future__ import annotations

from xerocr.app.engines import engine_statuses


def _statuses(**kw: object) -> dict[str, tuple[bool, str]]:
    out = engine_statuses(**kw)  # type: ignore[arg-type]
    return {s.kind: (s.available, s.detail) for s in out}


def test_precomputed_always_available() -> None:
    st = _statuses(
        public_mode=False,
        has_binary=lambda _n: None,
        has_module=lambda _n: False,
        get_env=lambda _n: None,
    )
    assert st["precomputed"][0] is True


def test_tesseract_needs_binary_and_module() -> None:
    common = {"public_mode": False, "get_env": lambda _n: None}
    # ni binaire ni module
    st = _statuses(has_binary=lambda _n: None, has_module=lambda _n: False, **common)
    assert st["tesseract"][0] is False and "binaire" in st["tesseract"][1]
    # binaire présent mais pytesseract absent
    st = _statuses(
        has_binary=lambda _n: "/usr/bin/tesseract",
        has_module=lambda _n: False,
        **common,
    )
    assert st["tesseract"][0] is False and "pytesseract" in st["tesseract"][1]
    # les deux présents
    st = _statuses(
        has_binary=lambda _n: "/usr/bin/tesseract",
        has_module=lambda _n: True,
        **common,
    )
    assert st["tesseract"][0] is True


def test_openai_disabled_in_public_mode() -> None:
    st = _statuses(
        public_mode=True,
        has_binary=lambda _n: None,
        has_module=lambda _n: True,
        get_env=lambda _n: "sk-xxx",
    )
    assert st["openai"][0] is False and "public" in st["openai"][1]


def test_openai_needs_module_and_key_in_private() -> None:
    base = {"public_mode": False, "has_binary": lambda _n: None}
    # SDK absent
    st = _statuses(has_module=lambda _n: False, get_env=lambda _n: "sk", **base)
    assert st["openai"][0] is False and "SDK" in st["openai"][1]
    # SDK présent, clé absente
    st = _statuses(has_module=lambda _n: True, get_env=lambda _n: None, **base)
    assert st["openai"][0] is False and "OPENAI_API_KEY" in st["openai"][1]
    # SDK + clé
    st = _statuses(has_module=lambda _n: True, get_env=lambda _n: "sk", **base)
    assert st["openai"][0] is True


def test_mistral_cloud_gated_in_public_then_needs_sdk_and_key() -> None:
    # cloud → refusé en mode public
    pub = _statuses(
        public_mode=True, has_binary=lambda _n: None,
        has_module=lambda _n: True, get_env=lambda _n: "key",
    )
    assert pub["mistral"][0] is False and "public" in pub["mistral"][1]
    base = {"public_mode": False, "has_binary": lambda _n: None}
    # SDK absent
    st = _statuses(has_module=lambda _n: False, get_env=lambda _n: "k", **base)
    assert st["mistral"][0] is False and "SDK" in st["mistral"][1]
    # SDK présent, clé absente
    st = _statuses(has_module=lambda _n: True, get_env=lambda _n: None, **base)
    assert st["mistral"][0] is False and "MISTRAL_API_KEY" in st["mistral"][1]
    # SDK + clé
    st = _statuses(has_module=lambda _n: True, get_env=lambda _n: "k", **base)
    assert st["mistral"][0] is True


def test_ollama_needs_httpx() -> None:
    common = {
        "public_mode": False,
        "has_binary": lambda _n: None,
        "get_env": lambda _n: None,
    }
    assert _statuses(has_module=lambda _n: False, **common)["ollama"][0] is False
    assert _statuses(has_module=lambda _n: True, **common)["ollama"][0] is True


def test_default_probes_run_without_error() -> None:
    # sondes réelles (env de CI) : ne lève pas, precomputed reste dispo.
    statuses = engine_statuses(public_mode=False)
    kinds = {s.kind for s in statuses}
    assert kinds == {"precomputed", "tesseract", "openai", "mistral", "ollama"}
    assert next(s for s in statuses if s.kind == "precomputed").available
