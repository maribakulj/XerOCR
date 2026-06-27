# PLAN P3 — Dataset de référence curé (axe « banc de corpus », P3-b)

> **Statut** : design figé, **construction en cours**. Concrétise
> [`VISION_DATASET_XEROCR.md`](VISION_DATASET_XEROCR.md) et la case `[ ] P3` de
> [`PLAN_FIN_MIGRATION.md`](PLAN_FIN_MIGRATION.md). Décision cadre :
> `MIGRATION_PLAN.md` D-094 (rapport interactif, images = références).

---

## 0. Décision directrice

**On n'invente pas de norme.** P3 = **un importeur + un profil documenté**
qui assemble des **standards existants** (IIIF statique + PAGE/ALTO + dataset
Hugging Face), mappés sur les types `domain` **déjà en place**. « Spec de
standardisation » est reformulé en **« profil d'adaptation »**.

**On vise P3-b dès le départ** (et pas P3-a « GT seule sans images ») : le
livrable produit veut un **rapport léger dont les images s'affichent via des
liens HF** — c'est la **saveur « Réfs IIIF / HF »** du rapport
([`xerocr/reports/DECISION_RAPPORT_INTERACTIF.md`](xerocr/reports/DECISION_RAPPORT_INTERACTIF.md)),
qui exige des **URLs d'image résolvables** → donc du **IIIF statique publié**.

---

## 1. Corpus retenu (squelette)

**Dresdner Hofdiarium — SLUB Mscr.Dresd.K.80 (1665), « GT Sample Set »** —
10 pages (fol. 85r–89v), Kurrent saxon du XVIIe.

| Critère | Valeur | Source |
|---|---|---|
| Images | **`Public Domain Mark`** (SLUB Dresden) — *le* gate, propre | `README.txt` du set |
| GT | **`CC BY-NC-SA 4.0`**, PAGE + ALTO (eScriptorium + correction manuelle) | idem |
| Niveau | **page** (TextRegion → TextLine → Coords/Baseline/Unicode), long-s ſ préservé | inspection XML |
| Strate | allemand / XVIIe / Kurrent / journal de cour | README |
| Hôte | Zenodo (DOI, épinglable) ; rec. 1665 = `14356190` | recherche |
| Taille | 10 pages, ~13 Mo (JPG ~1,3 Mo/page) | ZIP fourni |

> ⚠️ **Caveat licence à trancher AVANT publish** : le 1665 est **NC**
> (`CC BY-NC-SA`). Les volumes **1673 (K.117)** et **1653-56 (K.113)** sont
> **`CC-BY 4.0`** (plus permissifs pour un banc de référence). Le 1665 sert de
> **corpus-preuve** (license-agnostique pour bâtir) ; le **dataset publié**
> devra choisir NC-1665 ou CC-BY-1673. **Images PD dans tous les cas.**

Alternates (épaississement ultérieur, autres strates — droits image à
**vérifier** car « non précisé » au catalogue) : Incunabula Reichenau /
Incunables sévillans (imprimé ancien) ; FONDUE-*-PRINT-* / Reichsanzeiger-GT
(presse XIXe).

---

## 2. Contrats existants que P3-b respecte (zéro nouveau format)

| Brique | Déjà là | Usage P3-b |
|---|---|---|
| `domain.DocumentRef.image_uri: str\|None` | accepte une **URL** | y mettre l'**URL IIIF** (mode réf, pas de download) |
| `domain.DocumentRef.metadata["stratum"]` | clé **conventionnelle documentée** | y mettre la strate (`de/17e/kurrent`) |
| `domain.GroundTruthRef(type, uri)` | RAW_TEXT/ALTO/PAGE | GT page → `RAW_TEXT` (ligne-jointe) au minimum |
| `domain.CorpusSpec.metadata` | dict libre | `source`, `dataset_id`, **`revision` (SHA HF)**, licences |
| `formats.pagexml.parse_pagexml` | parser PAGE tolérant | lire la GT page → texte |
| `app.corpus_import.import_hf_corpus` | **convention HF existante** (stream `{image,gt_text}` → download octets) | **étendre** : variante **réf-IIIF + strate** (PAS un parallèle) |

**Anti-double-format (§8.1)** : l'importeur HF curé est une **variante** de
`import_hf_corpus` (même sortie `CorpusSpec`), pas une seconde convention. La
différence = `image_uri` pointe une **URL IIIF** au lieu d'un fichier téléchargé,
et `metadata["stratum"]` est renseigné.

---

## 3. Layout canonique du dataset HF (le « profil d'adaptation »)

Assemble des standards existants ; rien de propriétaire sauf un `corpus.json`
mince (mapping → `domain`).

```
<dataset HF>/
├── README.md                  # carte HF : YAML (license, language, tags) + attribution SLUB + strates
├── corpus.json                # mapping mince → domain : [{id, image(iiif), gt, stratum}]
├── ground_truth/<id>.page.xml # PAGE XML (GT canonique, verbatim source)
├── ground_truth/<id>.gt.txt   # texte joint dérivé (RAW_TEXT, pour le scoring)
└── iiif/<id>/
    ├── info.json              # IIIF Image API Level 0 (statique)
    ├── full/max/0/default.jpg # original (PD)
    ├── full/400,/0/default.jpg# vignette (galerie)
    └── full/1600,/0/default.jpg# medium (drill-in ; pas de deep-zoom)
```

- **IIIF Image API Level 0** = fichiers statiques pré-générés (pas de serveur ;
  servis par le CDN HF). Tailles **vignette ~400 px + medium ~1600 px**
  uniquement (décision rapport : zoom medium, **pas** de pyramide de tuiles).
- **Manifeste Presentation** : un `manifest.json` par corpus (optionnel au
  squelette ; `corpus.json` suffit à l'importeur XerOCR).
- **Repro** : la **révision git du dataset HF → SHA** est épinglée dans
  `CorpusSpec.metadata["revision"]` → `RunManifest`.

---

## 4. Découpage en tranches (squelette ambulant d'abord)

| Tranche | Livrable | Réseau ? |
|---|---|---|
| **P3-b.1 — Standardiseur** ✅ | `app/dataset_standardize.py` : `raw (jpg+page)` → **layout canonique** (IIIF Image API 3 level0 + GT `.gt.txt`/`.page.xml` + `corpus.json` + carte HF). Réutilise `formats.pagexml` + `adapters.images.iiif_derivative`. Déterministe, 7 tests ; **vérifié sur les 10 pages Dresden réelles** (info.json 2321×3812, dérivés 400/1600 exacts, ſ préservé). | non (local) |
| **P3-b.2 — Importeur curé** ✅ | `app.corpus_import.import_curated_corpus` : lit `corpus.json` (local OU snapshot HF) → `CorpusSpec` (`image_uri` = URL IIIF si `base_url`, sinon dérivé local ; GT `RAW_TEXT` ; `metadata["stratum"]` ; `metadata["revision"]`=SHA). **Variante** de `import_hf_corpus`, pas un parallèle. Path-traversal durci (`validated_path`). 5 tests + round-trip ; **vérifié sur les 10 pages Dresden** (image_uri = URL IIIF HF, GT chargée). | non (local d'abord) |
| **P3-b.3 — Publication** | upload du layout → dépôt Dataset HF (**toi** : compte + token write ; je fournis le script). | **oui (toi)** |
| **P3-b.4 — Boucle prouvée** | run réel @SHA → rapport saveur « Réfs IIIF/HF » : images affichées via liens HF. | oui |

Placement code : **standardiseur = outil de build** hors des 8 couches (ex.
`tools/dataset/` ou `scripts/`, à confirmer au commit — il dépend de Pillow,
extra `[images]`, et n'est pas importé par le moteur). **Importeur =
`app/corpus_import`** (couche 6, là où vit `import_hf_corpus`).

---

## 5. Répartition du travail

| | Moi (ici) | Toi (hors-bande) |
|---|---|---|
| Sourcing + lecture licences | ✅ | feu vert légal **publish** (NC vs CC-BY) |
| Récupérer les images | ✅ (ZIP fourni) | déjà fait pour le 1665 |
| Standardiseur + IIIF + importeur + tests | ✅ | — |
| **Compte HF + dataset + token write** | ❌ | ✅ |
| **Push HF** (env. bloque HF/Zenodo : proxy 403) | ❌ | ✅ (script fourni) |
| Pin SHA + run + vérif rapport | ✅ (une fois public) | — |

---

## 6. Décisions ouvertes (à trancher au fil)

1. **Licence du dataset publié** : NC-1665 (preuve) ou CC-BY-1673/1653-56 (réf).
2. **GT scorée** : RAW_TEXT (ligne-jointe) au squelette ; PAGE/layout-niveau =
   épaississement (réutilise `page_to_layout` + métriques région, T5).
3. **Manifeste Presentation** : `corpus.json` suffit à l'importeur ; manifeste
   IIIF complet = nice-to-have pour visionneuses tierces.
