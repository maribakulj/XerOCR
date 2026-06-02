# Mini-corpus de référence — BNL (presse historique luxembourgeoise)

**Source** : Bibliothèque nationale de Luxembourg (BNL), **données ouvertes**
(réutilisation libre — portail open data BNL). Presse historique numérisée
(XIXᵉ s.), **multilingue** : allemand **Fraktur** + **français** (Luxembourg).
**30 documents** (ids `0000`–`0009`, `0011`–`0030`).

**Attribution** : Bibliothèque nationale de Luxembourg.

## Contenu (niveau texte, déterministe) — **5 moteurs**

| Fichier | Rôle |
|---|---|
| `<id>.gt.txt` | **Vérité-terrain**, extraite des **ALTO v4 BNL** via le parser ALTO de XerOCR. |
| `<id>.frk.txt` | Tesseract 5.3.4 `-l frk` — Fraktur legacy, `--psm 3`. |
| `<id>.deu.txt` | Tesseract 5.3.4 `-l deu` — allemand moderne. |
| `<id>.fra.txt` | Tesseract 5.3.4 `-l fra` — français. |
| `<id>.deu_latf.txt` | Tesseract 5.3.4 `-l deu_latf` — Fraktur LSTM « best » (tessdata_best). |
| `<id>.easyocr.txt` | **EasyOCR** (de+fr, CPU) — deep-learning, **autre architecture** (bon en français, faible en Fraktur). |

Sorties OCR **capturées une fois** puis **figées** → benchmark **reproductible sans
Tesseract ni EasyOCR en CI** (adapter `precomputed`).

## Non committé ici (volontairement)
- **Images PNG** + **ALTO d'origine** : exclus (poids ~25 Mo). Requis seulement pour
  un run OCR **live** ou la mise en page (T5 — coordonnées en `mm10`).

## Moteurs : ce qui passe la politique réseau
Seuls **apt / PyPI / GitHub** sont joignables. **Tesseract** (apt + tessdata_best) ✓
et **EasyOCR** ✓ (modèles sur GitHub). **Pero** (Google Drive), **Kraken** (Zenodo),
**docTR** (HuggingFace) : paquets installables mais **poids 403** → exclus.

Consommé par `tests/interfaces/test_real_corpus_bnl.py` (métriques réelles +
significativité inter-moteurs **significative** à 5 moteurs, n=30 ≥ plancher 6).
