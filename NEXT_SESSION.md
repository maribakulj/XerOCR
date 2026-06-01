# NEXT_SESSION.md — démarrage de la prochaine session

> Point d'entrée **vivant** pour reprendre dans une **session fraîche**, mis à
> jour à chaque tranche. **Tranche courante : TU1 — la coquille au design.**

## 0. À lire en premier (dans l'ordre)
1. `CLAUDE.md` — garde-fous, architecture en couches, workflow (chargé auto).
2. `PLAN_SPACE_INTERACTIF.md` — le cap, les décisions verrouillées, la roadmap.
3. `design/README.md` + le dossier `design/` — la spec visuelle.
4. *(contexte)* `MIGRATION_PLAN.md` et les analyses existantes si besoin.
5. **§6 ci-dessous — réalité du code (vérifié) & pièges.** **À lire AVANT de
   coder** : 3 hypothèses « naturelles » du brief sont fausses (Jinja2, i18n,
   « Space déployé »), et la CSP bloque le JS *et* les `@font-face`.

## 1. Où on en est
- La **vitrine lecture seule** est déployée (Space) — état stable.
- **Décision de cap** : elle devient une **application interactive qui calcule
  dans le Space** (Phase A **privée**, clés en secrets) puis rebascule en
  **vitrine publique** (Phase B). Détails : `PLAN_SPACE_INTERACTIF.md`.
- **Stack** : **rendu serveur léger** (FastAPI + tokens/CSS du design). Pas de
  SPA React — le design `.jsx` est une **spec visuelle** à reproduire, pas du
  code à livrer. ⚠️ **Jinja2 n'est PAS encore en place** et **le JS est bloqué
  par la CSP** → cf. §6.
- **Design** sauvegardé dans `design/`. **Typo** : titres **FluxischElse**
  (incluse), corps **OCR-A** (**résolu** : John Sauter, **domaine public** —
  cf. §4 ; `.pfa` à convertir en woff2).
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
  Google Fonts** de tokens.css (pas de CDN en prod). ⚠️ La stack n'a **ni
  Jinja2 ni service de fichiers statiques** aujourd'hui, et la **CSP bloque
  `@font-face`** : voir §6 avant de commencer.
- Reproduire le **chrome** : rail/nav pilule, hero éditorial, panneau
  « système », d'après `design/` + `design/screenshots/`.
- **Réserver tous les emplacements de nav**, même vides : **Bibliothèque ·
  Banc d'essai · Rapports · Segmentation · Historique · Moteurs** (placeholders
  honnêtes, pas de fausses données).
- **Créer** l'**i18n FR/EN côté serveur** : l'app web n'en a **aucune**
  aujourd'hui ; `design/js/i18n.jsx` est une **réf React**. Faire simple
  (`?lang=` / cookie), **sans JS** (CSP — §6). Préserver le **focus-visible** /
  les contrastes (accessibilité de base).

## 3. Définition de « terminé » (TU1)
- [ ] **Shell** rendu au design (chrome + tokens + polices self-hosted servies
      depuis `xerocr/interfaces/web/static/` — cf. §6).
- [ ] Nav avec **tous** les emplacements (dont **Segmentation** en placeholder).
- [ ] FR/EN **côté serveur** ; focus-visible OK.
- [ ] **CSP élargie au strict minimum** : `font-src 'self'` (obligatoire pour
      les polices) ; `script-src 'self'` **seulement** si un JS est réellement
      introduit — décision de sécurité consciente (§6).
- [ ] **Rapports `/reports/{name}` INCHANGÉS** (couche 7, octet-stable → leur
      mise au design = **TU4**) : ne pas toucher à `xerocr/reports/`.
- [ ] **Tous les tests verts**, dont les tests d'**archi** et le gate
      `tests/deploy/test_packaging.py`. *(Si tu ajoutes une dépendance, son
      `test_requirements_cover_core_and_serve` impose de la mettre **aussi**
      dans `deploy/requirements.txt`.)*
- [ ] **Rendu vérifié EN LOCAL** (`xerocr serve` → captures comparées à
      `design/screenshots/`). Le **Space** se déploie **après merge sur `main`**
      (`deploy-space.yml`) — hors session ; vérif visuelle finale = mainteneur.
- [ ] Diff sous budget (~< 400 LOC de **glue Python + templates**, hors
      CSS/polices vendées) ; **aucun `.py` ≥ 400 lignes** (gate
      `test_file_budgets`) ; aucun code mort.

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
- **CSP & packaging (pièges vérifiés — §6).** La CSP bloque le JS **et** les
  `@font-face` → ajouter `font-src 'self'`. `design/` n'est **pas** livré dans
  l'image → mettre les assets sous `xerocr/…/static/` **et** les déclarer en
  **package-data**.
- **Polices = licence.** FluxischElse = OFL 1.1 (libre). **OCR-A = résolu** :
  OCR-A de **John Sauter, domaine public** (`design/fonts/OCRA.pfa` +
  `OCRA-LICENSE.txt`). En `.pfa` (Type 1) → **convertir en woff2/otf** pour le
  `@font-face` (tâche TU1 ; outil : `fontforge` puis `fonttools`/`woff2` →
  **committer le `.woff2`** sous `xerocr/…/static/`, image déterministe).
  **NE PAS** utiliser les OCR-A BT Bitstream (propriétaires) testées avant.
- **HF = disque éphémère** : ne jamais compter sur l'écriture locale pour
  persister (ça, c'est TU3 = push au dépôt).
- **Ne pas recopier** `web-app.js` de Picarones (3000+ lignes, fragile) :
  rester **léger** — et **sans JS** tant que la CSP le bloque (§6).
- **Tester avant d'affirmer** : lancer les tests + vérifier le rendu en local ;
  rapporter fidèlement (si un test échoue, le dire).

## 5. Hors périmètre TU1 (autres tranches)
Moteurs OCR/HTR · upload corpus · SSE · exécution d'un run · post-correction
LLM · persistance · importeurs · mode public/sécurité d'exposition · **écran de
segmentation** · **design des vues de rapport (= TU4)**. → roadmap
`PLAN_SPACE_INTERACTIF.md §6`.

## 6. Réalité du code — hypothèses fausses & pièges (vérifié le 2026-06-01)

> Établi en **lisant le code réel** (pas le design). À lire avant de coder.

### 3 hypothèses « naturelles » mais FAUSSES

| Le brief/plan suggère… | …mais en réalité (fichier) | TU1 doit donc |
|---|---|---|
| « rendu serveur **Jinja2** », « porter `tokens.css` en Jinja2 » | **Jinja2 absent.** L'HTML est produit en **f-strings** (`web/routers/home.py::_render_home`) + par le **renderer de la couche 7** (`web/routers/reports.py` → `default_report_renderer()`). Absent de `pyproject` (`[serve] = fastapi, uvicorn`) **et** de `deploy/requirements.txt`. | **Choisir consciemment** : introduire Jinja2 — alors l'ajouter à `[serve]` **et** `deploy/requirements.txt` (sinon `test_requirements_cover_core_and_serve` casse) — **ou** rester en petits templates-string (zéro dépendance). |
| « **préserver** l'i18n FR/EN » | L'app web n'a **aucune** i18n (libellés FR en dur dans `home.py`/`reports.py`) ; `design/js/i18n.jsx` est du **React** (réf). | **Créer** l'i18n **côté serveur** (`?lang=` ou cookie + `Accept-Language`). **Sans JS** (cf. piège CSP). |
| « **Space déployé** » comme étape de la session | Le déploiement = `.github/workflows/deploy-space.yml` sur **push `main`** (+ déclenchement manuel). La session travaille sur une **branche** → elle ne déploie pas et ne voit pas le Space live. | Vérifier le rendu **en local** (`xerocr serve`) vs `design/screenshots/`. Le Space suit **au merge sur `main`**. |

### 4 pièges techniques (vérifiés)

1. **La CSP bloque le JS *et* les polices.** `web/security/headers.py` :
   `default-src 'none'; style-src 'unsafe-inline'; img-src 'self' data:; base-uri 'none'; form-action 'none'`.
   → `<style>` inline OK, mais **tout `<script>` est bloqué** et **`@font-face`
   aussi** (pas de `font-src`). ⇒ self-host des polices ⇒ **ajouter
   `font-src 'self'`** au `_CSP_BASE`. N'ajouter `script-src 'self'` **que** si
   un JS est indispensable — c'est une **modif de contrat de sécurité** (le
   fichier le dit : « la CSP est un contrat, pas un confort »).
   ⚠️ **Contradiction signalée** (CLAUDE.md §9) : `PLAN_SPACE_INTERACTIF §2`
   prévoit « JS léger htmx/Alpine » — **incompatible** avec la CSP actuelle.
   Reco TU1 : **rester sans JS** (chrome, nav et bascule de langue = liens +
   CSS pur).
2. **Les assets ne sont livrés que sous `xerocr/`.** `deploy/Dockerfile` et
   `deploy-space.yml` ne copient que `xerocr/` (+ `pyproject`, `requirements`,
   `reports`) ; **`design/` n'entre pas dans l'image**. ⇒ placer polices + CSS
   sous `xerocr/interfaces/web/static/`, les **servir** (`StaticFiles` monté
   dans `create_app`) **et** les **déclarer en package-data** dans
   `pyproject.toml` — sinon `pip install --no-deps .` n'embarque pas les
   `.woff2/.css` (→ 404 dans le Space). Idéalement : un test deploy qui asserte
   la présence des polices servies.
3. **Ne pas toucher la couche 7.** `/reports/{name}` est rendu par
   `default_report_renderer()` (`xerocr/reports/html.py`) : HTML **autonome, à
   `<style>` inline, octet-stable** (golden tests du `demo`). Le mettre au
   design = **TU4**. En TU1 on n'habille **que le shell** (accueil + nav) ; la
   page de rapport garde son rendu actuel.
4. **`serve` existe déjà.** `xerocr serve --host 127.0.0.1 --port 8000`
   (`cli.py`) ; en conteneur : `--port 7860`. Smoke-test de réf (= ce que fait
   la CI) : `uvicorn xerocr.interfaces.web.app:create_app --factory`. ⚠️ un
   `200 /health` **ne prouve pas** que la page s'affiche (cf. logique
   iframe/headers de `headers.py`) → vérifier le **HTML rendu**, pas la santé.

### Commandes locales
```
make check                                   # ruff + mypy + pytest — tout doit rester vert
xerocr serve --port 8000                     # http://127.0.0.1:8000 (vitrine locale)
python -m pytest tests/deploy tests/architecture -q
```
