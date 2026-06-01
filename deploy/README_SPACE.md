---
title: XerOCR — Vitrine
emoji: 📜
colorFrom: indigo
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
license: apache-2.0
---

# XerOCR — vitrine des rapports

Banc d'essai **déterministe** de pipelines de transcription (OCR / HTR / VLM).
Ce Space sert, **en lecture seule et sans aucune clé API**, des rapports
`RunResult` pré-calculés (CER/WER/MER + tests statistiques inter-moteurs),
rendus en HTML autonome.

- `/` — liste des rapports disponibles
- `/reports/<nom>` — un rapport rendu en HTML
- `/health` — sonde de vivacité

Les calculs sont faits **hors ligne** (CLI `xerocr run`, avec vos clés et vos
moteurs) ; seuls les rapports figés sont publiés ici. Aucun secret n'est requis
ni stocké par la vitrine.

> Ce fichier est l'en-tête de configuration du Space Hugging Face (`sdk: docker`).
> Au déploiement, il devient le `README.md` racine du dépôt du Space ; le
> `Dockerfile` et `requirements.txt` vivent dans `deploy/`.
