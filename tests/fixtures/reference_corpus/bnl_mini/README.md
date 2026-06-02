# Mini-corpus de référence — BNL (presse historique luxembourgeoise)

**Source** : Bibliothèque nationale de Luxembourg (BNL), **données ouvertes**
(réutilisation libre — portail open data BNL). Presse historique numérisée
(XIXᵉ s.), **multilingue** : allemand **Fraktur** + **français** (Luxembourg).
**30 documents** (ids `0000`–`0009`, `0011`–`0030`).

**Attribution** : Bibliothèque nationale de Luxembourg.

## Contenu (niveau texte, déterministe)

| Fichier | Rôle |
|---|---|
| `<id>.gt.txt` | **Vérité-terrain**, extraite des **ALTO v4 BNL** via le parser ALTO de XerOCR. |
| `<id>.frk.txt` | Tesseract 5.3.4 `-l frk` — Fraktur legacy, `--psm 3`. |
| `<id>.deu.txt` | Tesseract 5.3.4 `-l deu` — allemand moderne. |
| `<id>.fra.txt` | Tesseract 5.3.4 `-l fra` — français. |
| `<id>.deu_latf.txt` | Tesseract 5.3.4 `-l deu_latf` — Fraktur LSTM « best » (tessdata_best). |

Sorties OCR **capturées une fois** puis **figées** → benchmark **reproductible sans
Tesseract en CI** (adapter `precomputed`). Régénération = relancer Tesseract 5.3.4
sur les images BNL d'origine.

## Non committé ici (volontairement)
- **Images PNG** + **ALTO d'origine** : exclus (poids ~25 Mo). Disponibles dans le
  set BNL. Requis seulement pour un run OCR **live** ou la mise en page (T5 —
  coordonnées en `mm10`).

## Pourquoi 4 moteurs **Tesseract** (et pas Pero/Kraken/docTR)
Sous la politique réseau de l'environnement, seuls **apt / PyPI / GitHub** passent.
Les paquets Pero-OCR, Kraken, docTR, Calamari s'**installent** (PyPI), mais leurs
**poids** sont inaccessibles ici : **Pero** → Google Drive (403), **Kraken** →
Zenodo (403), **docTR** → HuggingFace (403). Tesseract (apt + tessdata_best/GitHub)
est le seul jeu de modèles atteignable → 4 variantes couvrant la **langue** (de/fr)
et la **qualité de modèle** (Fraktur legacy vs LSTM).

Consommé par `tests/interfaces/test_real_corpus_bnl.py` (métriques réelles +
significativité inter-moteurs vivante, n=30 ≥ plancher 6).
