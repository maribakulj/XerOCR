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

## Activer un moteur cloud (Mistral) sur un Space — ⚠️ Space PRIVÉ uniquement

Par défaut, un Space tourne en **mode public** : les moteurs cloud sont **masqués**
(personne ne peut dépenser de clé). Pour exécuter des runs **OCR → Mistral** sur
votre propre Space :

> 🔴 **Sécurité** : en mode ouvert, **n'importe quel visiteur du Space peut lancer
> un run et donc dépenser VOTRE clé Mistral**. Ne faites ceci que sur un Space dont
> la visibilité est **Private** (Settings → Visibility → Private). Sur un Space
> public, votre crédit Mistral est exposé à tous.

1. **Rendre le Space privé** (Settings → Visibility → **Private**).
2. **Secret** : `MISTRAL_API_KEY` = votre clé (Settings → Variables and secrets →
   *New secret*).
3. **Variable** : `XEROCR_PUBLIC_MODE` = `false` (même écran, *New variable*) — sans
   ça, le Space reste verrouillé et Mistral masqué.
4. Le SDK `mistralai` est déjà inclus dans `requirements.txt`. Redéployez/rebuild.

Le menu déroulant « Modèle » du Banc d'essai se remplira alors directement depuis
l'API Mistral (`models.list`), et les prompts sont éditables par concurrent.

> Ce fichier est l'en-tête de configuration du Space Hugging Face (`sdk: docker`).
> Au déploiement, il devient le `README.md` racine du dépôt du Space ; le
> `Dockerfile` et `requirements.txt` vivent dans `deploy/`.
