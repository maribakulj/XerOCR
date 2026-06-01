# design/ — spec visuelle de l'UI XerOCR

Export du **Claude Design** travaillé par le mainteneur. **C'est une spec
visuelle, PAS du code livré.** XerOCR sert une UI **rendue serveur** (Jinja2 +
CSS + JS léger) ; ces `.jsx` React servent de **référence de rendu** qu'on
reproduit à l'identique côté serveur. Rien ici n'est importé par le paquet
`xerocr/`.

> Provenance : conçu sous le nom « Picarones » → **rebrand XerOCR** (trivial).
> Itérations : v1 « sharp » → v2 « rounded » → v3 « final » (cf. `screenshots/`).

## Contenu

| Chemin | Rôle |
|---|---|
| `tokens.css` | Système de design : palette gris chaud (`--paper`/`--ink`…), accents `oklch` **fern/slate/clay/butter**, rayons, ombres, familles de police. |
| `picarones.css` | Styles de composants : chrome pilule, `view-hero`, `sec`, `readout`, `tag`/`eng-id`, `table.data` + *data-bars*, `diff`, `doc-card`, sous-nav… |
| `*.jsx`, `js/*.jsx` | Les vues (référence) : `view-by-engine`, `view-by-document`, `view-crosses`, `view-synthesis`, `js/view-benchmark` (le **lanceur**), `chrome`, `components`, `i18n`, `data`. |
| `mockups/*.html` | Maquettes HTML autonomes (dont `type-studies` pour la typo). |
| `screenshots/*.png` | Rendus de référence (v2/v3). |
| `fonts/` | **FluxischElse** (titres) + `jgs` (font ASCII du schéma *fig.1*) + licences. |

## Typographie — DÉCISION (source de vérité)

- **Titres → FluxischElse** (fournie dans `fonts/`, licence jointe).
- **Corps / reste → OCR-A** — **à sourcer** : non incluse ici ; prendre une
  webfont libre (p. ex. OFL « OCRA »). ⚠️ OCR-A en corps long est très typé →
  **valider la lisibilité au build** (option : OCR-B, ou OCR-A réservée
  labels/données + compagnon lisible pour la prose).
- ⚠️ `tokens.css` hérité référence encore **Bricolage Grotesque / IBM Plex** :
  **à remplacer** par FluxischElse / OCR-A au portage. Les variables
  `--display` / `--sans` / `--mono` / `--serif` sont les points à modifier.

## Couverture & manque

Vues couvertes : **lanceur** (Banc d'essai) + rapport (overview, by-engine,
by-document, crosses, synthesis). **Manque : la segmentation / mise en page**
(pas d'écran) → à concevoir ; correspond à l'axe **structure (T5)**, déjà
réservé côté domaine par `ArtifactType.LAYOUT`. Place à réserver dans la nav.

Plan d'exécution : [`../PLAN_SPACE_INTERACTIF.md`](../PLAN_SPACE_INTERACTIF.md).
