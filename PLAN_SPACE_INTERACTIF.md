# Plan — application interactive dans le Space (calcul → vitrine)

> **Statut** : enveloppe **PROVISOIRE** (à confirmer au build, cf. `CLAUDE.md` §9).
> Mémoire durable d'une décision de cap : la vitrine lecture seule devient une
> **application complète qui calcule dans le Space**, puis bascule en vitrine
> publique. Construire **par tranches verticales**, jamais tout d'un coup.

## 1. Le modèle en deux phases

| Phase | Visibilité | Clés | Ce qui tourne |
|---|---|---|---|
| **A — calcul privé** | Space **privé** | clés du mainteneur en **secrets HF** | l'appli **complète** = local : modules OCR/HTR, post-correction LLM, génération de rapports |
| **B — vitrine publique** | Space **public** | secrets **retirés** | consultation des rapports accumulés (les moteurs à clé deviennent « indisponibles ») |

## 2. Décisions verrouillées

| Sujet | Décision | Pourquoi |
|---|---|---|
| **Stack UI** | **Rendu serveur** (Jinja2 + tokens/polices du design + JS léger htmx/Alpine). Le design React = **spec visuelle**, pas de SPA livrée. | Conforme à « pas de SPA lourde » (D-β) ; 1 seule stack ; réutilise le backend ; le look reste identique. |
| **Persistance des rapports** | **Push vers le dépôt GitHub** (ou Dataset HF) après chaque run. | HF Space = disque **éphémère** ; le push survit aux redémarrages **et** alimente la Phase B via `deploy-space.yml`. |
| **Moteurs** | **API cloud + Tesseract = disponibles** (légers, clés en secrets) ; **Pero/Kraken/Calamari = listés mais indisponibles**. | Pero & co = PyTorch + modèles + **GPU payant** → hors Space gratuit (cf. §6). |
| **Typographie** | **Titres = FluxischElse · corps = OCR-A.** | Remplace `tokens.css` hérité. FluxischElse = OFL 1.1. OCR-A = **John Sauter, domaine public** (`.pfa` à convertir en woff2) ; les OCR-A BT Bitstream sont écartées (propriétaires). Lisibilité à valider. |

## 3. Le pivot d'archi (assumé)

La vitrine actuelle est **délibérément** lecture seule, sans clé, sans moteur —
verrouillé par `tests/deploy/test_packaging.py::test_requirements_embark_no_engine`
et par le différé de T4f. Le nouveau cap **inverse** ça. Ce que ça implique :

- `deploy/requirements.txt` + ce test : **à faire évoluer** (la vitrine embarque
  maintenant Tesseract + SDK cloud ; toujours **pas** de moteur lourd).
- Écrire le **chemin d'écriture** (POST run → exécution → `RunResult` → rapport),
  absent de la vitrine read-only.
- **Sécurité d'un Space porteur de clés** : rester **privé** en Phase A ; avant
  toute exposition, brancher le « mode public » (cf. §7).

## 4. Réutilisable depuis Picarones (inventaire fait)

À **porter** dans l'archi propre de XerOCR (couche 8 + app/adapters), pas à recopier tel quel :

- **Lanceur** : `POST /api/benchmark/run` + statut + `cancel` + **SSE** (`stream`)
  ; worker threadé ; `JobStore` SQLite (reprise via `Last-Event-ID`).
- **Corpus** : upload **ZIP** (validation image Pillow, anti-traversal, dédup basenames).
- **Onglet Moteurs** : détection runtime **disponible/indisponible** + langues Tesseract.
- **Importeurs** : IIIF · Gallica · eScriptorium · HTR-United · HuggingFace (1/sous-tranche).
- **Sécurité produit** : mode public (bloque moteurs cloud), rate-limit/IP, quotas upload, CSRF, SSRF.
- À **éviter** : `web-app.js` 3000+ lignes (fragile) → on fait léger (htmx/Alpine) ;
  persistance par volume docker-compose (**ne marche pas** sur HF) → on push au dépôt.

## 5. Design

Spec dans [`design/`](design/) (+ `design/README.md`). Système : gris chaud +
accents `oklch` fern/slate/clay/butter, chrome pilule, hero éditorial, tables à
*data-bars*, diff philologique. Vues : lanceur + by-engine/by-document/crosses/
synthesis. **Manque : segmentation** (cf. §8).

## 6. Roadmap par tranches (proposée)

| Tranche | Livre | Note |
|---|---|---|
| **TU1 — Coquille / design shell** | tokens + polices (FluxischElse/OCR-A) + chrome (rail, hero, panneau système) appliqués à l'app **actuelle** (read-only), **déployé**. Réserve les emplacements de nav : Bibliothèque · Banc d'essai · Rapports · **Segmentation** · Historique · Moteurs. | fine, pleine profondeur, faible risque ; valide l'approche design-en-Jinja2 |
| **TU2 — Lanceur « Banc d'essai »** (cœur Phase A) | POST run + upload corpus + **SSE** progression + onglet Moteurs (dispo/indispo) ; clés depuis secrets ; écrit un `RunResult` | la grosse tranche ; sécurité d'exécution. **TU2.a fait** : walking skeleton `POST/GET/cancel /api/runs` → run de fond annulable (`JobRunner`+`JobStore`) → `RunResult` écrit (démo `precomputed`), **CSRF** + **gate mode public**. **TU2.b fait** : onglet Moteurs — `GET /api/engines`. **TU2.c fait** : upload corpus ZIP (`/api/corpus`) — ingestion durcie. **TU2.d fait** : `POST /api/runs {engine, corpus_id}` — sélection moteur + gardes HTTP (422/403/404/409). **TU2.e fait** : SSE (`/events` + `Last-Event-ID`). **TU2.f.1 fait** : page `/benchmark` interactive (rendu serveur + JS auto-hébergé : lance la démo, suit en SSE, lien rapport ; CSP ouverte `script/connect 'self'`). Reste : **TU2.f.2** page Moteurs + UI upload/sélection au design ; run tesseract réel = test `live`. |
| **TU3 — Persistance** | push `RunResult`(+HTML) vers dépôt/Dataset après run (token en secret) | rend durable + alimente Phase B |
| **TU4 — Vues rapport** | overview/by-engine/by-document/crosses/synthesis au design | consomme `RunResult`, zéro data-layer |
| **TU5 — Importeurs** | IIIF→Gallica→eScriptorium→HTR-United→HF, 1 par sous-tranche | sortie unique `Corpus` |
| **TU6 — Sécurité publique** | mode public + rate-limit + quotas + CSRF | **avant** toute exposition publique |
| **TU7 — Segmentation (T5)** | surface UI + fan-out région | quand l'axe structure démarre (cf. §8) |

## 7. Sécurité — rappels

- Phase A : Space **privé** ; secrets injectés au conteneur seulement.
- Avant public : soit retirer les secrets (Phase B), soit activer le **mode
  public** (moteurs cloud bloqués) + CSRF + rate-limit. Ne jamais exposer un
  Space **public ET porteur de clés** sans barrière.

## 8. À concevoir — segmentation (signalé par le mainteneur)

Le design ne prévoit **pas** d'écran segmentation/mise en page. Or c'est une
**ambition réservée** de XerOCR (axe structure **T5** ; `ArtifactType.LAYOUT` +
`region_id` réservés en couche 1 depuis T1). Donc : **réserver sa place dans la
nav dès TU1**, concevoir l'écran (régions, ordre de lecture, métriques
structurelles) quand TU7/T5 démarre. Le backend est dimensionné ; il manque la
surface.

## 9. Garde-fous (inchangés)

Tranches fines de pleine profondeur · budgets `<400 LOC` · zéro shim · tests
d'archi · « pas de consommateur = supprimé » · docs durables committées · **ne
pas tout faire dans une seule conversation**.

## 10. Rapport avec la migration T1–T7 (ne pas confondre les numéros)

`CLAUDE.md` décrit la **migration du moteur** (bibliothèque/CLI) par tranches
**T1→T7**, bâties **intérieur → extérieur** (couches 1→8) ; statut réel :
**T1→T4e faits** (tesseract réel, CER/WER/MER, stats, OCR→LLM, `serve`/vitrine
read-only). **Le calcul est déjà débloqué côté bibliothèque** — il reste à
l'exposer dans le web (T4f). ⚠️ Une version périmée de ce plan disait « prochaine
= T2 » (recopiée d'un `CLAUDE.md §0` non réconcilié) : **T2/T3 sont faits**.

Les **TU1→TU7** de ce plan sont l'autre extrémité : **couche 8 (interfaces) +
déploiement** — l'app web du Space. Donc :

- **TU1 (coquille au design)** est **indépendante du moteur** : présentation
  pure sur l'interface existante (read-only) → avance sans toucher à la migration.
- **TU2+ (lancer un run, calculer)** **consomment** les moteurs livrés par la
  migration : un vrai OCR dans le Space **suppose T2+ faits** (tesseract, puis
  cloud). Pas de calcul réel tant que le moteur correspondant n'existe pas.
- **Numérotation** : `T#` = migration moteur ; `TU#` = tranches UI/interfaces.

**Décidé (mainteneur)** : **TU1 d'abord** (coquille au design, indépendante du
moteur) — **fait**. T2/T3 étant déjà livrés, le calcul est débloqué côté
bibliothèque → **prochaine = TU2 (= T4f)** : le lanceur web qui exécute un run
dans le Space.
