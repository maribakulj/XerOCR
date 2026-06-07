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

## Activer Mistral sur votre Space — ⚠️ Space PRIVÉ uniquement

Modèle « clé posée → ça marche » : un moteur cloud est disponible **dès que sa clé
est présente**. Donc, sur **votre** Space :

> 🔴 **Sécurité** : si la clé est présente, **n'importe quel visiteur peut lancer un
> run et donc dépenser VOTRE clé**. Mettez donc le Space en **Private** (Settings →
> Visibility → Private). Sur un Space public, **retirez la clé** (comme on faisait).

1. **Rendre le Space privé** (Settings → Visibility → **Private**).
2. **Secret** : `MISTRAL_API_KEY` = votre clé (Settings → Variables and secrets →
   *New secret*).
3. C'est tout : le SDK `mistralai` est déjà dans `requirements.txt`. Redéployez.

Le menu déroulant « Modèle » du Banc d'essai se remplit alors directement depuis
l'API Mistral (`models.list`), et les prompts sont éditables par concurrent.

> La variable `XEROCR_PUBLIC_MODE=false` n'est **plus nécessaire pour les moteurs**
> cloud. Elle ne sert plus qu'à ré-ouvrir les **imports distants** (IIIF/Gallica/…)
> et les plugins tiers, verrouillés par défaut sur un Space pour la sécurité SSRF.

> Ce fichier est l'en-tête de configuration du Space Hugging Face (`sdk: docker`).
> Au déploiement, il devient le `README.md` racine du dépôt du Space ; le
> `Dockerfile` et `requirements.txt` vivent dans `deploy/`.
