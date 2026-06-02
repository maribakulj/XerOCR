# Mini-corpus de référence — BNL (presse historique luxembourgeoise)

**Source** : Bibliothèque nationale de Luxembourg (BNL), **données ouvertes**
(réutilisation libre — cf. portail open data BNL). Presse historique numérisée
(XIXᵉ s.), multilingue (allemand **Fraktur** ; possiblement français/luxembourgeois
selon les pages). 10 documents.

**Attribution** : Bibliothèque nationale de Luxembourg.

## Contenu (niveau texte, déterministe)

| Fichier | Rôle |
|---|---|
| `00NN.gt.txt` | **Vérité-terrain**, extraite de l'ALTO v4 BNL (transcription de référence) via le parser ALTO de XerOCR. |
| `00NN.frk.txt` | Sortie OCR **figée** de Tesseract 5.3.4 `-l frk` (Fraktur), `--psm 3`. |
| `00NN.deu.txt` | Sortie OCR **figée** de Tesseract 5.3.4 `-l deu` (allemand moderne), `--psm 3`. |

Les sorties OCR sont **capturées une seule fois** puis figées : le benchmark est
**reproductible sans Tesseract en CI** (adapter `precomputed`, comme la démo).
Régénération = relancer Tesseract 5.3.4 sur les images BNL d'origine.

## Non committé ici (volontairement)

- **Images source PNG** + **ALTO d'origine** : exclus (poids ; ~12 Mo d'images).
  Disponibles dans le set BNL d'origine. Nécessaires uniquement pour un run OCR
  **live** (test `live`) ou le travail de mise en page (T5 — coordonnées en `mm10`).

Consommé par `tests/interfaces/test_real_corpus_bnl.py` (premier benchmark XerOCR
sur **données réelles** : CER/WER/MER + significativité inter-moteurs vivante,
n=10 ≥ plancher 6).
