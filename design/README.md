# design/ — spec visuelle **unique** de l'UI XerOCR

Référence de rendu que l'UI **rendue serveur** (Jinja2 + CSS + JS léger) et le
**rapport autonome** (`xerocr/reports/`) reproduisent. **C'est une spec visuelle,
PAS du code livré** : rien ici n'est importé par le paquet `xerocr/`.

> ⚠️ **Une seule source de vérité.** Ce dossier a connu 3 générations —
> ① base *Claude Design* (polices CDN : Bricolage / IBM Plex / Apfel Grotezk),
> ② ère *Picarones* (branding « Picarones »), ③ **spec XerOCR** (la bonne).
> Les couches ① et ② ont été **purgées** : plus de CDN, plus de « Picarones »,
> plus de mockups divergents, plus de canvas d'édition. Ce qui reste **est** ③.

## Décisions verrouillées (③ — autorité)

| Sujet | Décision | Où c'est câblé |
|---|---|---|
| **Titres** | **Fluxisch Else** (OFL 1.1) | `tokens.css` `--display` + `@font-face` |
| **Corps + données** | **OCR-A** (John Sauter, domaine public) | `tokens.css` `--sans`/`--mono`/`--serif` + `@font-face` |
| **Polices** | **self-hosted** (woff2 dans `fonts/`), **zéro CDN** | `tokens.css` (source **unique** des `@font-face`) |
| **Fond** | trame de points **Xerox halftone** (data-URI SVG) | `tokens.css` `.report-board` · `picarones.css` `html,body` |
| **Branding** | **XerOCR** / pastille « X » | `chrome.jsx`, `js/app.jsx` |

> **Changer la typo = trivial** : déposer le woff2 dans `fonts/`, éditer le `src`
> du `@font-face` + la variable (`--display`/`--sans`/…) dans **`tokens.css`
> seulement**. `picarones.css` n'(re)définit plus aucune police : il hérite.
> (Le rapport autonome `reports/html.py` a son propre bloc police inline —
> contrainte d'autonomie — calqué sur les mêmes variables.)

## Contenu

| Chemin | Rôle |
|---|---|
| `tokens.css` | Système de design **+ source unique des polices** (`@font-face` + `--display`/`--sans`/`--mono`/`--serif`). |
| `picarones.css` | Styles de composants : chrome pilule, `view-hero`, `sec`, `readout`, `tag`/`eng-id`, `table.data` + *data-bars*, `diff`, `doc-card`, sous-nav… Hérite des polices de `tokens.css`. |
| `chrome.jsx` · `data.jsx` | Chrome partagé du rapport (`ReportChrome`, `HeroBand`, `ReportApp`) + données de démonstration. |
| `view-synthesis.jsx` · `view-by-engine.jsx` · `view-by-document.jsx` · `view-crosses.jsx` | Les 4 **vues rapport** (référence pour la couche 7). |
| `js/*.jsx` · `tweaks-panel.jsx` | App **lanceur** (« Banc d'essai ») — référence pour la coquille web. |
| `fonts/` | **Fluxisch Else** (woff2 + otf) · **OCR-A** (woff2 + source `.pfa`) · `jgs` (schéma fig.1) + licences. |
| `render/` | **Harnais de rendu offline** : régénère `screenshots/` depuis la source. |
| `screenshots/*.png` | Rendus de référence, **régénérés** depuis la source (avec trame + Fluxisch Else + OCR-A). |

## Régénérer les screenshots (le « moyen de le faire »)

Les `.jsx` étant du React, on les monte avec React + `@babel/standalone` et on
capture avec un Chromium **déjà présent** — **zéro réseau** au rendu (les polices
et la trame sont self-hosted). Seul `npm install` (React/Babel) touche le réseau.

```bash
cd design/render
./regenerate.sh                      # npm install + rend les 4 vues -> ../screenshots/
# Chromium custom : CHROMIUM_PATH=/usr/bin/chromium ./regenerate.sh
```

Chaque vue rendue = `ReportApp initialTab=<vue>` sur les **vrais** `tokens.css`
+ `picarones.css` + `*.jsx`. Si un rendu est faux, **c'est la source qui est
fausse**, pas le harnais (aucune surcharge police/branding n'y vit).

## Couverture & manque

Vues couvertes : **lanceur** (Banc d'essai, `js/`) + **rapport** (overview,
by-engine, by-document, crosses). **Manque : la segmentation / mise en page**
(pas d'écran) → axe **structure (T5)**, déjà réservé côté domaine par
`ArtifactType.LAYOUT`. Place à réserver dans la nav.

Plan d'exécution : [`../PLAN_SPACE_INTERACTIF.md`](../PLAN_SPACE_INTERACTIF.md).
