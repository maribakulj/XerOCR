"""Modules OCR/HTR (couche 5)."""

from __future__ import annotations

from cinoc.adapters.ocr.precomputed import PrecomputedTextAdapter
from cinoc.adapters.ocr.tesseract import TesseractAdapter

__all__ = ["PrecomputedTextAdapter", "TesseractAdapter"]
