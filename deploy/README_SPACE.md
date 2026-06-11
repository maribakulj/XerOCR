---
title: XerOCR — OCR gratuit
emoji: 📜
colorFrom: indigo
colorTo: gray
sdk: docker
app_port: 7860
pinned: false
license: apache-2.0
---

# XerOCR — banc d'essai OCR gratuit

Banc d'essai **déterministe** de pipelines de transcription (OCR / HTR / VLM).
Ce Space **exécute un vrai OCR Tesseract gratuitement** — **sans clé ni
installation** : déposez un corpus, lancez Tesseract, obtenez un rapport CER/WER/MER
réel. Il sert aussi des rapports `RunResult` pré-calculés, rendus en HTML autonome.

- `/` — liste des rapports disponibles
- `/library` — préparer un corpus (upload ZIP)
- `/benchmark` — lancer un run **Tesseract** (gratuit, local) sur un corpus
- `/reports/<nom>` — un rapport rendu en HTML
- `/health` — sonde de vivacité

En **mode public** (le défaut sur ce Space), seul le **socle gratuit** s'exécute
(Tesseract — aucun secret, aucun appel facturé). Les moteurs **cloud** (clé) et les
**plugins tiers** sont **refusés** (`403`, fail-closed) : aucun secret n'est requis
ni stocké. Pour les pipelines lourds (OCR→LLM, VLM), lancez-les **hors ligne** via la
CLI `xerocr run`, avec vos clés et vos moteurs.

## Activer les moteurs cloud (Mistral…) — ⚠️ Space PRIVÉ uniquement

Le mode public est **fail-closed** : un moteur cloud est **refusé** (`403`) sur ce
Space **même si une clé est posée** — pour qu'un visiteur ne puisse **jamais**
dépenser votre clé. Pour les ouvrir, sur **votre** Space :

> 🔴 **Sécurité** : ouvrir les moteurs cloud expose votre clé à tout visiteur.
> Rendez le Space **Private** (Settings → Visibility → Private) **avant** d'ouvrir.

1. **Rendre le Space privé** (Settings → Visibility → **Private**).
2. **Désactiver le mode public** : variable `XEROCR_PUBLIC_MODE` = `false`
   (Settings → Variables and secrets). C'est ce qui lève le verrou fail-closed sur
   les moteurs cloud **et** sur les imports distants (IIIF/Gallica/…) / plugins tiers.
3. **Secret** : `MISTRAL_API_KEY` = votre clé. Le SDK `mistralai` est déjà dans
   `requirements.txt`. Redéployez.

Le menu déroulant « Modèle » du Banc d'essai se remplit alors directement depuis
l'API Mistral (`models.list`), et les prompts sont éditables par concurrent.

> Ce fichier est l'en-tête de configuration du Space Hugging Face (`sdk: docker`).
> Au déploiement, il devient le `README.md` racine du dépôt du Space ; le
> `Dockerfile` et `requirements.txt` vivent dans `deploy/`.
