# Changelog

Tous les changements notables de Cinoc. Format inspiré de
[Keep a Changelog](https://keepachangelog.com/fr/1.1.0/) ; versionnage SemVer.
La version est dérivée des tags git (`setuptools_scm`) ; le journal **décisionnel
granulaire** vit dans [`MIGRATION_PLAN.md`](MIGRATION_PLAN.md).

## [Non publié]

Préparation de la `1.0.0` : réécriture propre de Picarones sous le nom **Cinoc**,
architecture 8 couches, surface fonctionnelle complétée incrémentalement.

### Ajouté

- **Moteur déterministe** : pipelines OCR / HTR / VLM / OCR→LLM, exécutés via un
  orchestrateur unique (CLI **et** web), `RunManifest` reproductible, annulation
  et timeout coopératifs.
- **Métriques** : familles caractère/mot (CER/WER/MER/cMER…), philologiques
  (diacritiques, MUFI, abréviations, numéraux romains, archaïsmes), conformité
  HIPE, calibration (ECE/MCE), NER, inter-moteurs (Wilcoxon/Friedman/Nemenyi,
  oracle, Jensen-Shannon), distribution par ligne, longitudinal (OLS + Pettitt),
  qualité d'image, données structurées, bilan de correction.
- **Moteurs first-party** : Tesseract, Kraken, Pero, Calamari, Mistral OCR,
  Google Vision, Azure Document Intelligence (OCR/HTR) ; OpenAI, Anthropic,
  Mistral, Ollama (LLM/VLM). Jetons et coûts remontés ; tarifs datés.
- **Segmentation** : segmenteur local PP-DocLayout **et** segmenteur distant
  (endpoint object-detection HuggingFace, interchangeable sans réinstallation).
- **Rapport HTML autonome et interactif** : 4 onglets, graphes SVG serveur
  (zéro JS de calcul), tables triables, drill-in moteur/document, comparaison de
  2 runs côté client, glossaire, **bilingue FR/EN** (nombres localisés à
  l'affichage, couches machine en point).
- **Saveurs de rapport** : fichier unique (images inline), dossier/ZIP (images
  séparées), références IIIF/HF (images chargées depuis HuggingFace).
- **Bibliothèque de corpus** : upload ZIP, imports IIIF / Gallica /
  eScriptorium / HuggingFace, datasets curés Cinoc (import + découverte
  automatique par compte + tag).
- **Interface web / Space** : lanceur de benchmark (SSE), historique
  longitudinal, page de segmentation, mode public *fail-closed*.
- **Extensibilité** : point d'extension unique (briques de pipeline) via
  entry-points `cinoc.modules`, découverte runtime, fail-closed en mode public.
- **CLI** : `demo`, `run`, `compare`, `serve`, `history` ; export JSON/CSV ;
  export JSONL conforme HIPE-OCRepair.

### Sécurité

- XML durci (`safe_parse_xml` : pas de DTD/DOCTYPE/entité externe ni réseau),
  validation systématique des chemins (anti-traversal), garde anti-SSRF sur les
  appels distants, plafonds d'upload, mode public sans secrets.
