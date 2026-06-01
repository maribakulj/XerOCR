# NEXT_SESSION.md — démarrage de la prochaine session

> Point d'entrée **vivant** pour reprendre dans une **session fraîche**, mis à
> jour à chaque tranche. **Tranche courante : TU1 — la coquille au design.**

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

## 3. Définition de « terminé » (TU1)
- [ ] Templates rendus au design (chrome + tokens + polices self-hosted).
- [ ] Nav avec **tous** les emplacements (dont **Segmentation** en placeholder).
- [ ] FR/EN fonctionnels ; focus-visible OK.
- [ ] **Tous les tests verts**, dont les tests d'**archi** et le gate
      `tests/deploy/test_packaging.py`.
- [ ] **Space déployé** et conforme aux captures `design/screenshots/`.
- [ ] Diff sous budget (~< 400 LOC) ; aucun code mort.

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
- **Polices = licence.** FluxischElse = libre (licence jointe). **OCR-A** : la
  police uploadée est **OCR-A BT © Bitstream « All rights reserved » =
  propriétaire → NE PAS committer.** Utiliser une **OCR-A libre** (domaine
  public, ex. Matthew Skala) ou OCR-B libre. *(Décision mainteneur à confirmer
  avant de figer la police.)*
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
