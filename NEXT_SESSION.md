# NEXT_SESSION.md — démarrage de la prochaine session

> Point d'entrée **vivant** pour reprendre dans une **session fraîche**, mis à
> jour à chaque tranche. **TU1 (coquille au design) faite ✅.** T1→T4e + T2/T3
> **déjà faits** (moteur texte, OCR→LLM, vitrine read-only) → **prochaine = TU2
> (= T4f)** : le lanceur web (POST run + upload + SSE + Moteurs + mode public).
> Cf. `PLAN_SPACE_INTERACTIF.md §10` + `xerocr/interfaces/ANALYSE_COUCHE_8.md`.

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
