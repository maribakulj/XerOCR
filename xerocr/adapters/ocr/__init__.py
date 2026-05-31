"""Modules OCR/HTR (couche 5)."""

from __future__ import annotations

from xerocr.adapters.ocr.precomputed import PrecomputedTextAdapter
from xerocr.adapters.ocr.tesseract import TesseractAdapter

__all__ = ["PrecomputedTextAdapter", "TesseractAdapter"]
