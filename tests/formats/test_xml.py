"""Tests de sécurité du parsing XML (entonnoir ``safe_parse_xml``)."""

from __future__ import annotations

import time

from xerocr.formats import safe_parse_xml

_VALID = b'<?xml version="1.0"?><root><child>salut</child></root>'

_XXE = (
    b'<?xml version="1.0"?>'
    b'<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>'
    b"<foo>&xxe;</foo>"
)

_BILLION_LAUGHS = (
    b'<?xml version="1.0"?>\n'
    b"<!DOCTYPE lolz [\n"
    b'<!ENTITY lol "lol">\n'
    b'<!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">\n'
    b'<!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">\n'
    b'<!ENTITY lol4 "&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;&lol3;">\n'
    b"]>\n"
    b"<lolz>&lol4;</lolz>"
)

_DOCTYPE_REMOTE = (
    b'<?xml version="1.0"?>'
    b'<!DOCTYPE foo SYSTEM "http://169.254.169.254/evil.dtd">'
    b"<foo/>"
)


def test_valid_xml_parses() -> None:
    root = safe_parse_xml(_VALID)
    assert root is not None
    assert root.tag == "root"


def test_rejects_xxe() -> None:
    assert safe_parse_xml(_XXE) is None


def test_rejects_billion_laughs_without_expanding() -> None:
    start = time.monotonic()
    assert safe_parse_xml(_BILLION_LAUGHS) is None
    assert time.monotonic() - start < 1.0  # pas d'explosion d'entités


def test_rejects_remote_doctype() -> None:
    assert safe_parse_xml(_DOCTYPE_REMOTE) is None


def test_rejects_malformed() -> None:
    assert safe_parse_xml(b"<root><unclosed>") is None


def test_rejects_empty() -> None:
    assert safe_parse_xml(b"") is None


def test_namespaced_xml_parses() -> None:
    data = b'<a xmlns="http://example.org/ns"><b/></a>'
    root = safe_parse_xml(data)
    assert root is not None
    assert root.tag == "{http://example.org/ns}a"
