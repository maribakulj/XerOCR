"""Format ALTO XML (v2/v3/v4) : types, parser tolérant, writer déterministe."""

from __future__ import annotations

from xerocr.formats.alto.parser import AltoParseError, parse_alto
from xerocr.formats.alto.types import (
    AltoBBox,
    AltoBlock,
    AltoComposedBlock,
    AltoDocument,
    AltoGraphicalElement,
    AltoIllustration,
    AltoLine,
    AltoPage,
    AltoString,
    AltoTextBlock,
)
from xerocr.formats.alto.writer import AltoWriteError, write_alto

__all__ = [
    "AltoBBox",
    "AltoString",
    "AltoLine",
    "AltoTextBlock",
    "AltoComposedBlock",
    "AltoIllustration",
    "AltoGraphicalElement",
    "AltoBlock",
    "AltoPage",
    "AltoDocument",
    "parse_alto",
    "AltoParseError",
    "write_alto",
    "AltoWriteError",
]
