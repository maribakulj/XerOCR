# NEXT_SESSION.md — démarrage de la prochaine session

> Point d'entrée **vivant** pour reprendre dans une **session fraîche**. **UN
> SEUL plan ordonné + autorité de statut = `MIGRATION_PLAN.md`** (le web = **T4**,
> sous-tranches T4a–i ; les `TU#` ne sont que des **alias historiques** —
> `PLAN_SPACE_INTERACTIF.md` = spec UX, sans roadmap).
>
> **Fait** : T1→T3 ✅ ; **T4a–e** (vitrine read-only) ✅ ; **T4f** (habillage
> design + lanceur : run de fond/SSE/Moteurs/upload/gardes HTTP) ✅ — **mergé dans
> `main` (PR #17)**, CI verte. **Prochaine = T4f.2** : page **Moteurs** + UI
> **upload**/sélection au design (réutilise `/api/engines`, `/api/corpus`,
> `/api/runs`). Ensuite **T4g** (persistance) → **T4h** (vues rapport) → **T4i**
> (durcissement public) → **T5** (structure). Détail : roll-up + §3-T4 du plan.

## TU2.f.1 — fait (page « Banc d'essai » interactive)
`GET /benchmark` : page rendue serveur (base Jinja partagée `base.html` +
`home.html`/`benchmark.html`) **+ JS léger auto-hébergé** (`static/js/benchmark.js`,
vanilla, sans dépendance) qui **lance la démo** (`fetch` POST `/api/runs` + en-tête
CSRF) puis **suit la progression en direct** via `EventSource` sur le SSE, et
propose le **lien du rapport** produit. La nav devient vivante pour **Banc d'essai
+ Rapports** (les autres restent « à venir »). **CSP ouverte** au 1ᵉʳ consommateur
navigateur : `script-src 'self'` + `connect-src 'self'` (jamais d'inline ni
d'externe ; `form-action 'none'` conservé — on pilote en `fetch`). Fichiers :
`templates/base.html|home.html|benchmark.html`, `static/js/benchmark.js`,
`static/css/shell.css` (+ `.btn`/launcher), `routers/home.py` (route `/benchmark`
+ nav 3 états), `security/headers.py` (CSP), `pyproject` (`static/js/*.js` packagé).

> ⚠️ **Comportement navigateur non exécuté en CI** (pas de navigateur, cf. TU1) :
> on teste la **surface serveur** (page, JS lié/servi, nav, CSP) + `node --check`
> (syntaxe JS) + les API sous-jacentes (déjà testées). Rendu visuel & interaction
> à confirmer au déploiement.

## TU2.e — fait (SSE de progression + reprise Last-Event-ID)
`GET /api/runs/{id}/events` (`text/event-stream`, read-only) diffuse le **journal**
du job — un événement par transition d'état (`pending→running→done/failed/
cancelled`), id monotone — et **rejoue depuis `Last-Event-ID`** à la reconnexion.
L'événementiel est réabsorbé dans le `JobStore` (`_history` + `history_since`),
ce qui **lève la réserve R-10** d'`ANALYSE_COUCHE_5`. Diffusion par *polling* du
journal (transitions rares), `idle_timeout` borne un job qui ne finit pas. Rejeu
**déterministe** même après la fin du job. Fichiers : `adapters/storage/job_store.py`
(journal), `interfaces/web/routers/runs.py` (`_sse_stream`, `/events`). ⚠️ La **CSP
n'est pas encore touchée** (pas de consommateur navigateur : zéro JS) — l'EventSource
arrive en TU2.f avec `connect-src 'self'`.

## TU2.d — fait (sélection de moteur au lancement + gardes HTTP)
`POST /api/runs` accepte un corps optionnel `{engine, corpus_id}`. **Ordre de
garde (sécurité d'abord)** : moteur inconnu → 422 ; **moteur cloud en mode public
→ 403** (le chemin sécurité, désormais HTTP) ; LLM autonome (openai/ollama, sans
chaîne OCR→LLM) → 422 ; `corpus_id` introuvable → 404 ; moteur indisponible
(binaire/SDK/clé) → 409 ; puis build : `precomputed` = démo (refuse un corpus),
`tesseract` = run OCR **sur le corpus uploadé** (corpus requis). Sans corps → démo
(rétro-compat TU2.a). Gardes **toutes testées en HTTP** (TestClient + uvicorn réel).
Le run tesseract **réel** (binaire + vraies images) = test `live` opt-in (absent
de la CI/vitrine). Fichiers : `interfaces/web/routers/runs.py` (`LaunchRequest`,
`_spec_builder`, `_tesseract_spec`), `create_app` (corpus_store + statuses au routeur).

## TU2.c — fait (upload de corpus ZIP, ingestion durcie)
`POST /api/corpus` (multipart, **CSRF**) → `CorpusStore` (couche 6) qui valide et
matérialise l'archive, `GET /api/corpus/{id}` en donne le résumé. **Sécurité
d'ingestion** (concept de la tranche, tout testé) : **anti-traversal**
(aplatissement au basename + `validated_path`), **anti-zip-bomb** (octets
**réellement** décompressés plafonnés par fichier et au total — pas de confiance
au header), **quotas** (taille archive/fichier, nombre d'entrées), **dédup** de
basename, **liste blanche** d'extensions + **magic bytes** des images, **noms**
restreints (→ `DocumentRef.id` valide). Sortie : `CorpusSpec` (images appariées à
leur `.txt` par radical). Fichiers : `app/corpus_upload.py`,
`interfaces/web/routers/corpus.py` ; `python-multipart` ajouté (serve/dev +
`deploy/requirements.txt`). Le corpus uploadé est la **cible du run** en TU2.d.

## TU2.b — fait (onglet « Moteurs » : disponibilité runtime)
`GET /api/engines` (read-only) restitue, pour chaque kind du socle (`precomputed`,
`tesseract`, `openai`, `ollama`), s'il est **utilisable ici** et *pourquoi pas* :
sondes **bon marché et sans effet de bord** — binaire (`shutil.which`), SDK
(`importlib.util.find_spec`, **sans importer**), clé d'API (env). Le **mode public**
masque les moteurs cloud. Sondes **injectables** → détection déterministe en test,
indépendante de la CI. Fichiers : `app/engines.py` (`engine_statuses`,
`EngineStatus`), `interfaces/web/routers/engines.py`. La **page** Moteurs au design
(rendu) arrive avec les formulaires UI (TU2.f) ; ici c'est la capacité backend.

## TU2.a — fait (lanceur, walking skeleton)
Le calcul tourne **dans le web**, de bout en bout : `POST /api/runs` lance le run
de démonstration (`precomputed`, sans clé) en arrière-plan via `JobRunner`
(couche 6, thread + **annulation coopérative** `RunControl`) ; `GET /api/runs/{id}`
suit l'état ; `POST .../cancel` interrompt. État dans `JobStore` (couche 5, en
mémoire, thread-safe). Le `RunResult` produit est écrit dans le dossier de la
vitrine → **listé et rendu** par les routes read-only existantes (preuve
bout-en-bout). **Sécurité d'abord** : écritures **CSRF** (en-tête custom
`X-XeroCR-CSRF`) ; **mode public** (`XEROCR_PUBLIC_MODE`) refuse les kinds cloud
(`blocked_cloud_kinds`, démo `precomputed` = safe). Fichiers : `adapters/storage/`
(`job_store.py`), `app/jobs.py`, `app/versioning.py` (version unifiée),
`interfaces/web/routers/runs.py`, `interfaces/web/security/csrf.py`,
`interfaces/demo.py` (corpus démo partagé CLI⇄web) ; `orchestrator.run(control=…)`.
Suite : **379 verts**, archi + deploy gate verts, fumé via vrai uvicorn.

> **Hors TU2.a (volontaire)** : SSE/progression fine, upload de corpus, sélection
> de moteur (et donc le **403 cloud au niveau HTTP**), persistance (HF éphémère),
> formulaire « Banc d'essai » au design. La gate mode-public est **unit-testée**
> pour le blocage cloud ; son chemin HTTP arrive avec la sélection de moteur (TU2.b).

## TU1 — fait (coquille au design)
Livré sur la branche de session : coquille rendue **serveur** (Jinja2 + CSS, JS
zéro) au design, **polices auto-hébergées** (Fluxisch Else en woff2 ; OCR-A
converti de `OCRA.pfa` → woff2), servies sous `/static` (aucun CDN). Nav avec
**tous** les emplacements réservés — Bibliothèque · Banc d'essai · Rapports ·
**Segmentation** · Historique · Moteurs (placeholders « à venir » honnêtes, seul
Rapports actif). Bascule **FR/EN** via `?lang=`. CSP durcie (`style-src`/
`font-src 'self'`, toujours zéro script). Gate `test_requirements_embark_no_engine`
**vert** (aucun moteur ajouté). Suite complète verte (356) + archi + `serve`
fumé via uvicorn. Détails de fichiers : `xerocr/interfaces/web/` (`i18n.py`,
`templates/shell.html`, `static/{css,fonts}`), `app.py`, `routers/home.py`,
`security/headers.py` ; `pyproject.toml` (extra `serve` + `package-data`) ;
`deploy/requirements.txt`.

> Reste hors TU1 (volontaire) : capture pixel vs `design/screenshots/` non faite
> faute de navigateur dans l'environnement (vérif. structurelle uniquement :
> en-têtes, assets servis, nav, FR/EN). À confirmer visuellement au déploiement.

## 0. À lire en premier (dans l'ordre)
1. `CLAUDE.md` — garde-fous, architecture en couches, workflow (chargé auto).
2. `PLAN_SPACE_INTERACTIF.md` — le cap, les décisions verrouillées, la roadmap.
3. `design/README.md` + le dossier `design/` — la spec visuelle.
4. *(contexte)* `MIGRATION_PLAN.md` et les analyses existantes si besoin.

## 1. Où on en est
- La **vitrine lecture seule** est déployée (Space) — état stable.
- **Décision de cap** : elle devient une **application interactive qui calcule
  dans le Space** (Phase A **privée**, clés en secrets) puis rebascule en
  **vitrine publique** (Phase B). Détails : `PLAN_SPACE_INTERACTIF.md`.
- **Stack** : **rendu serveur** (Jinja2 + tokens du design + JS léger).
  **Pas de SPA React** — le design `.jsx` est une **spec visuelle** à
  reproduire, pas du code à livrer.
- **Design** sauvegardé dans `design/`. **Typo** : titres **FluxischElse**
  (incluse), corps **OCR-A** (⚠️ à sourcer en version LIBRE — cf. §4).
- **Migration moteur** : à **T1** (squelette), prochaine = **T2**. **TU1 en est
  indépendant** ; le calcul réel (TU2+) suppose T2+ livrés — cf.
  `PLAN_SPACE_INTERACTIF.md §10`.
- **Branche de dev** : celle désignée pour la session. Commits clairs.
  **Pas de PR sauf demande explicite.**

## 2. Ta tâche : TU1 — la coquille au design
**But** : habiller l'app **actuelle** (read-only) avec le design, **sans rien
casser au déploiement**. Tranche **fine mais de bout en bout** (templates →
déployé, visible).

Périmètre :
- Porter `design/tokens.css` en variables CSS de prod ; **self-host les
  polices** en `@font-face` (FluxischElse + OCR-A) et **retirer l'`@import`
  Google Fonts** de tokens.css (pas de CDN en prod).
- Reproduire le **chrome** : rail/nav pilule, hero éditorial, panneau
  « système », d'après `design/` + `design/screenshots/`.
- **Réserver tous les emplacements de nav**, même vides : **Bibliothèque ·
  Banc d'essai · Rapports · Segmentation · Historique · Moteurs** (placeholders
  honnêtes, pas de fausses données).
- Préserver l'**i18n FR/EN** (`design/js/i18n.jsx`) et le **focus-visible** /
  les contrastes (accessibilité de base).

## 3. Définition de « terminé » (TU1) — état
- [x] Templates rendus au design (chrome + tokens + polices self-hosted).
- [x] Nav avec **tous** les emplacements (dont **Segmentation** en placeholder).
- [x] FR/EN fonctionnels ; focus-visible OK.
- [x] **Tous les tests verts**, dont les tests d'**archi** et le gate
      `tests/deploy/test_packaging.py`.
- [~] **Space déployé** : artefacts prêts (wheel embarque les assets, gate vert,
      smoke `serve` OK) ; conformité pixel aux captures à confirmer au déploiement
      (pas de navigateur dans l'environnement de build).
- [x] Diff sous budget (~90 LOC Python) ; aucun code mort.

## 4. Garde-fous — NE PAS se tromper
- **Tranches fines, pleine profondeur.** Faire **TU1 seulement**, puis
  s'arrêter. Ne pas anticiper TU2+.
- **Zéro shim / zéro couche de compat / zéro hack.** Pas de consommateur =
  supprimé.
- **Respecter l'archi en couches** (dépendances vers le bas) ; les **tests
  d'archi restent verts**.
- **Ne pas casser le gate deploy** : `test_requirements_embark_no_engine`
  interdit les moteurs lourds dans la vitrine. TU1 **ne touche pas aux
  moteurs** → il doit rester vert. *(Son évolution = TU2.)*
- **Polices = licence.** FluxischElse = OFL 1.1 (libre). **OCR-A = résolu** :
  OCR-A de **John Sauter, domaine public** (`design/fonts/OCRA.pfa` +
  `OCRA-LICENSE.txt`). En `.pfa` (Type 1) → **convertir en woff2/otf** pour le
  `@font-face` (tâche TU1). **NE PAS** utiliser les OCR-A BT Bitstream
  (propriétaires) testées avant.
- **HF = disque éphémère** : ne jamais compter sur l'écriture locale pour
  persister (ça, c'est TU3 = push au dépôt).
- **Ne pas recopier** `web-app.js` de Picarones (3000+ lignes, fragile) :
  rester **léger** (htmx/Alpine si nécessaire).
- **Tester avant d'affirmer** : lancer les tests + vérifier rendu/déploiement ;
  rapporter fidèlement (si un test échoue, le dire).

## 5. Hors périmètre TU1 (autres tranches)
Moteurs OCR/HTR · upload corpus · SSE · exécution d'un run · post-correction
LLM · persistance · importeurs · mode public/sécurité d'exposition · **écran de
segmentation**. → roadmap `PLAN_SPACE_INTERACTIF.md §6`.
