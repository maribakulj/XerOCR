# PLAN_PARITE.md — porter XerOCR à parité fonctionnelle avec Picarones

> **Nature** : plan d'enveloppe + séquencement de tranches, dans la continuité de
> `MIGRATION_PLAN.md` (axes `T#`/`S#`). Il prolonge le parcours après T7/S6.
> **Autorité de statut** : le roll-up de `MIGRATION_PLAN.md` — ce fichier ne
> recopie aucun statut, il définit le *périmètre cible* et l'*ordre*.
> Basé sur une analyse code-niveau des deux dépôts (juin 2026) :
> contrats d'extension XerOCR (`@document_metric`, `@cross_engine_metric`,
> `Module` Protocol, `Section` Protocol, `RunResult` v1) × dissection des
> ~37 métriques / 7 modules statistiques / adapters de Picarones.

---

## 0. Constat de départ (résumé de l'analyse)

**Déjà à parité (ne pas re-planifier)** : ALTO/PAGE/text + 9 profils,
CER/WER/MER/`cer_diplo`/`ins`/`del`, MUFI + diacritiques, Wilcoxon/Friedman,
segmentation complète (LAYOUT, fan-out, `region_cer`, `region_detection`,
projecteur), **les 3 modes pipeline `text_only`/`text_and_image`/`zero_shot`
avec VLM OpenAI/Anthropic/Mistral** (livrés — contrairement à une idée reçue),
6 importeurs corpus, historique SQLite, plugins entry-points, 5 sections de
rapport au design, Space S1–S6.

**Manquant et visé par ce plan** : statistique inférentielle complète
(Nemenyi, bootstrap, Pareto, CDD), économie (pricing + durées + tokens),
diagnostic d'erreurs (confusion, pires lignes, hallucination, cherchabilité,
difficulté), philologie étendue, confidences + calibration, taxonomie
d'erreurs (± NER), moteurs HTR/cloud (Kraken, Mistral OCR), surfaces
(export CSV, glossaire, CLI `history`, prompts par période), reprise
partielle.

**Abandons confirmés** (ne reviendront pas — décisions actées ou prises ici) :
voir §2.

---

## 1. Les deux extensions d'enveloppe (à faire UNE fois, en tête — axe 1)

Tout le reste du plan est de la *surface* qui s'emboîte dans les contrats
existants. Exactement **deux** trous d'enveloppe ont été identifiés ; on les
ferme en premier, une fois, proprement — c'est la condition pour ne jamais
recréer le shim `BenchmarkResult↔RunResult` (~1 620 LOC chez Picarones).

### E1 — Canal « ressources » (durées + tokens)

**Problème** : `RunResult` v1 ne porte ni durée ni consommation ; or Pareto,
débit effectif et coûts en dépendent. Picarones le faisait via
`StepResult.duration_seconds` + extraction `usage.completion_tokens` dans
chaque adapter.

**Décision** : étendre le contrat `Module` **atomiquement** —
`execute()` retourne un `StepOutput(artifacts, usage: ResourceUsage | None)`
au lieu du dict nu. `ResourceUsage` (domain, frozen) :
`duration_seconds` (mesurée par l'**exécuteur**, pas par le module —
source unique), `tokens_in`/`tokens_out` (renseignés par les adapters
LLM/VLM seuls). Agrégé en `RunDocumentResult` et `PipelineResult`.

- Changement **atomique** : les ~10 builders du socle + le plugin de réf +
  l'exécuteur + fan-out, dans **le même commit**. Jamais deux signatures
  supportées en parallèle (zéro shim). À faire **avant** que l'écosystème
  de plugins tiers grossisse — c'est maintenant ou jamais.
- `schema_version` → 2, goldens refaits (octet-stables).

### E2 — Canal « analyses » (résultats non scalaires)

**Problème** : `MetricScore` est scalaire ; or l'inférentiel (matrice Nemenyi,
IC bootstrap), les fronts Pareto, les paires de confusion, les pires lignes,
les blocs hallucinés, les bins de calibration, la taxonomie et le NER sont
**structurés**. Picarones a sombré en les entassant dans des dicts non typés
(`report_data`), refaits au rendu par la data-layer.

**Décision** : un **canal unique typé** sur `RunResult` :

```python
RunResult.analyses: tuple[Analysis, ...]   # défaut ()
Analysis = frozen { name, scope: Literal["corpus","pipeline","document"],
                    view, pipeline: str|None, document_id: str|None,
                    payload: <union discriminée par name> }
```

Chaque famille ajoute son **payload Pydantic frozen** à l'union discriminée
**dans le même commit** que (a) son calcul dans `evaluation/` et (b) son
**unique consommateur** (une section de rapport ou un export). Règles dures :

1. **Les scalaires (`MetricScore`) restent la seule monnaie de classement**
   (agrégats, historique, régressions). `analyses` = contexte/diagnostic,
   jamais une 2ᵉ voie de scoring.
2. **Tout est calculé dans `evaluation/` (runner), écrit dans `RunResult`** ;
   `reports/` lit, ne calcule pas (gate archi existant — c'est l'anti
   data-layer).
3. **Payload sans consommateur = supprimé** (garde-fou §5.3 inchangé).

> E1+E2 = **tranche T8** ci-dessous. Après T8, plus aucune tranche du plan
> ne touche l'enveloppe.

---

## 2. Décisions de périmètre (garde / abandonne)

### Repris de Picarones (jugés utiles — portés par les tranches §3)

| Élément | Pourquoi | Faits d'implémentation (source) |
|---|---|---|
| Nemenyi post-hoc | Sans correction multi-comparaisons, le verdict sur-affirme | Table Tukey/√2 + interpolation, fallback Wilson-Hilferty ; `friedman_nemenyi.py`, autonome |
| Bootstrap IC | Donne l'incertitude du CER au lecteur | Percentile, `seed=42` (déterministe — compatible invariant §12) |
| Front de Pareto | « Meilleur » ≠ « meilleur au coût » | `compute_pareto_front(points, objectives=("cer","cost"))`, pur, N-dim |
| Diagramme CDD (SVG) | Visualisation standard académique du Nemenyi | rendu déterministe ; optionnel (sous-tranche) |
| Économie : `pricing.yaml` + coût/débit/coût marginal | Question institutionnelle centrale ; les pipelines OCR→LLM ont un coût **réel dès aujourd'hui** | ~40 entrées YAML datées (`valid_until`) ; conso : durées (E1) + tokens (E1) |
| Confusion de caractères | Diagnostic actionnable (choix de modèle/langue) | paires depuis le diff char, corpus-level |
| Pires lignes | Le « voir où ça casse » le plus demandé | top-N lignes par CER + diff, ~150 LOC |
| Hallucination | **Critique** pour les pipelines LLM (XerOCR en a 4) | insertion nette, ratio longueur, ancrage n-grammes, blocs ; texte pur |
| Cherchabilité (searchability) | LA question des bibliothèques numériques | recall tokens GT à distance ≤2 ; texte pur |
| Difficulté document | Contextualise les écarts | texte pur |
| Philologie étendue (abréviations, typo early-modern ; option : chiffres romains, séquences numériques) | Cœur patrimonial, fonctions doc-level simples, `None` si non applicable | autonomes |
| Confidences (`ConfidenceToken`) + calibration ECE/MCE | « Peut-on faire confiance au score du moteur ? » ; déclencheur backlog domain atteint | sidecar `*.confidences.json` ; tesseract TSV ÷100 ; ECE/MCE ~250 LOC |
| Taxonomie d'erreurs (9 classes) | Transforme un CER en diagnostic ; règles pures (pas de ML) | Levenshtein mot-à-mot + classification contextuelle |
| NER (option, extra `[ner]`) | Cherchabilité des entités ; lourd (spaCy) | alignement IoU 0,5 sur spans ; backend pluggable interne |
| Kraken (first-party, extra `[kraken]`) | Mission HTR : Tesseract seul ne couvre pas le manuscrit ; standard communautaire (eScriptorium) ; produit confidences + layout | lazy import, pattern identique tesseract |
| Mistral OCR (extra) | 1ᵉʳ moteur cloud payant → donne un sens réel à l'axe coût/Pareto | gate public 403 déjà en place |
| Export CSV | Attendu des utilisateurs tableurs ; trivial depuis `RunResult` | ~100 LOC |
| Glossaire FR/EN | Rapport lisible par des non-spécialistes | YAML statique ~880 lignes, zéro couplage ; **élaguer** les entrées des features non portées |
| Prompts de correction par période (FR/DE, texte) | Savoir-faire philologique ; `Competitor.prompt` existe déjà | données pures |
| `partial_store` (reprise fingerprintée) | Runs longs/coûteux relançables | SHA-256 + NDJSON ~350 LOC ; **différé** tant que les corpus restent petits |

### Abandonnés (décisions — à inscrire au journal `MIGRATION_PLAN.md` au merge de T8)

| Élément | Raison |
|---|---|
| Moteur narratif (20 détecteurs, arbiter, templates) | Déjà acté (CLAUDE.md §6). **Exception reprise** : la règle anti-contradiction (Nemenyi corrigé > Wilcoxon brut) et le verdict « égalité statistique » intègrent `synthesis` en T9 — 2 idées, pas le moteur. |
| Workflows CLI `diagnose`/`economics`/`edition`/`robustness` | Déjà acté. L'économie revient comme **métriques + section**, pas comme workflow. |
| Robustesse synthétique (dégradation d'images + projection) | **Nouvelle décision** : méthodologie fragile (équivalence d'échelle qualité↔dégradation supposée, interpolation linéaire), PIL-lourd, faible valeur décisionnelle. |
| Clustering d'erreurs, matrices de corrélation, Venn, reliability curves (hors calibration) | Jouets de la data-layer Picarones ; pas de question utilisateur identifiée. |
| readability, lexical_modernization, equivalence_profile, error_absorption, levers, specialization, inter_engine, baseline_comparison, module_policy, modern_archives, rare_tokens | Valeur discutable ou redondante (cherchabilité/hallucination couvrent les vrais besoins). Ré-évaluables un par un si une demande réelle émerge. |
| Pero, Google Vision, Azure DI, Calamari first-party | Hors socle ; voie **plugin out-of-tree** (T6) — Calamari = bon candidat de plugin de démonstration réel. |
| Prompts `zero_shot`/`image` anglais + profils EN | Déjà acté (profils) ; prompts EN suivent. |

---

## 3. Les tranches (axe moteur `T#`, surfaces `S#`)

Chaque tranche : **fine, pleine profondeur** (calcul → `RunResult` → section →
golden → web/CLI si pertinent), budget LOC, `make ci` complet, docs (roll-up +
DoD couche) **dans le même commit**. Ordre = dépendances réelles.

### T8 — Consolidation : hygiène + enveloppe (prérequis de tout)

*Ne livre aucune feature visible ; livre la stabilité.*

1. **Hygiène (issue de l'audit juin 2026)** :
   - ~~rate-limit `/api/engines` + imports~~ et ~~purge des IP inactives~~ :
     **faux positifs au build** (D-066) — le middleware est global et `_prune`
     existe ; les constats venaient de l'analyse de *Picarones* (couche 8) ;
   - rafraîchir `NEXT_SESSION.md` (périmé à l'ère T1/TU2) ;
     étendre `test_status_freshness` à `NEXT_SESSION.md` ;
   - purger les annotations de tranche des docstrings livrées (`Phase B`, `T2`…) — la règle existe, l'appliquer.
2. **E1 ressources** : `ResourceUsage` + `StepOutput`, exécuteur chronomètre,
   adapters LLM/VLM remontent les tokens. Changement atomique, tous builders.
3. **E2 analyses** : **contrat gravé** (docstring `result.py` + règles §1/E2) ;
   le **champ** `analyses` naît en T9 avec son 1ᵉʳ payload (`inference`) — une
   union discriminée vide n'est pas implémentable, et un champ sans payload
   serait une API sans consommateur (arbitrage D-066, rituel §4).
4. `schema_version=2`, goldens refaits, journal de décisions mis à jour
   (abandons §2).

**Gates** : `make ci` ; archi verte ; goldens octet-stables ; aucun builder
sur l'ancienne signature (grep).

### T9 — Verdict statistique complet *(dép. : T8/E2)*

- Port `nemenyi_posthoc` (+ table critique) et `bootstrap_ci` (percentile,
  seed fixe) dans `evaluation/statistics/` (nouveau sous-paquet, whitelist
  scipy/numpy déjà OK).
- Calcul dans le runner → payloads `inference` (matrice de significativité,
  groupes ex æquo, IC par pipeline) dans `analyses`.
- `CrossEngineSection` enrichie (IC affichés, matrice) ; **`synthesis`
  apprend 2 règles** : (a) anti-contradiction — si Nemenyi corrigé dit
  « égalité », il l'emporte sur Wilcoxon brut ; (b) verdict explicite
  « statistiquement indistinguables ».
- Sous-tranche optionnelle : CDD SVG (rendu déterministe, dans la section).

**Gates** : parité numérique avec Picarones sur fixtures partagées ;
déterminisme bit-à-bit du rapport ; cas dégénérés (<6 docs, 2 moteurs).

### T10 — Économie *(dép. : T8/E1, T9 pour Pareto-affichage)*

- `data/pricing.yaml` (élagué aux moteurs existants + LLM/VLM ; `valid_until`
  obligatoire → **warning automatique de péremption** dans le rapport — jamais
  un chiffre silencieusement périmé).
- Métriques : coût estimé/1000 pages (local : durée mesurée × taux horaire ;
  cloud : table + tokens mesurés), débit effectif (pages/h corrigé erreurs),
  coût marginal par erreur évitée. Scalaires → `MetricScore` ; front de
  Pareto (`cer×coût`, `cer×durée`) → payload `economics` dans `analyses`.
- Nouvelle section `economics` (Protocol existant, `requires=("cer",)` +
  présence du payload). Affichage web idem (le rapport est autonome).

**Gates** : un benchmark BNL réel OCR vs OCR→LLM produit des coûts non
triviaux ; péremption testée ; reports ne recalcule rien (gate archi).

### T11 — Diagnostic d'erreurs *(dép. : T8/E2 ; indépendant de T9/T10)*

- **Scalaires** : `hallucination_score` (ancrage), `searchability_recall`,
  `difficulty` — `@document_metric` texte standard.
- **Structurés** → `analyses` : paires de confusion (corpus), pires lignes
  (top-N + diff), blocs hallucinés.
- Section `diagnostics` (+ enrichissement by-document : lien vers pires lignes).
- Sous-tranche **philologie étendue** : abréviations + typo early-modern
  (option : chiffres romains, séquences numériques) — simples
  `@document_metric`, `None` si non applicable.

**Gates** : hallucination prouvée sur un vrai run OCR→LLM (le LLM qui
« invente » est détecté) ; pires lignes corrects sur fixture BNL.

### T12 — Confidences & calibration *(dép. : T8 ; précède Kraken pour le schéma)*

- `ConfidenceToken` en domain (déclencheur backlog atteint : 1ᵉʳ consommateur).
- Tesseract produit le sidecar `CONFIDENCES` (TSV natif ÷100) — l'`ArtifactType`
  existe déjà, il devient consommé.
- Calibration ECE/MCE (alignement confiance↔correction par token) :
  scalaires + bins (payload `calibration`) ; section reliability.

**Gates** : ECE reproductible ; métrique `None` quand le moteur ne produit
pas de confidences (pas de faux zéro).

### T13 — Taxonomie d'erreurs (± NER) *(dép. : T8/E2)*

- **T13.a Taxonomie** : 9 classes (confusion visuelle, diacritique, casse,
  ligature, abréviation, hapax, segmentation, hors-vocab, lacune) — règles
  pures Levenshtein mot-à-mot. Comptages → payload `taxonomy` ; part de
  chaque classe → scalaires. Section dédiée.
- **T13.b NER (option, extra `[ner]`)** : backend interne pluggable
  (spaCy lazy), F1 global + par catégorie (alignement IoU 0,5), entités
  hallucinées/manquées → payload `ner`. **Interne, pas un point d'extension
  tiers** (périmètre strict CLAUDE.md §3).

**Gates** : classification déterministe ; corpus sans GT entités → `None`.

### T14 — Moteurs HTR & cloud *(dép. : T12 pour les confidences Kraken ; T10 pour donner du sens au coût cloud)*

- **Kraken first-party** (extra `[kraken]`) : IMAGE → RAW_TEXT (+ CONFIDENCES,
  + LAYOUT à terme — il segmente). Builder + sonde `engine_statuses` +
  matrice CLI/web. Modèle par défaut documenté, version → `module_versions`.
- **Mistral OCR** (extra, cloud) : gate public 403 existant ; alimente le
  Pareto coût réel.
- **Calamari = plugin out-of-tree de démonstration** (dépôt séparé
  `xerocr-calamari`) : valide T6 sur un vrai moteur, sans gonfler le socle.

**Gates** : run `live` Kraken sur fixture manuscrite ; le socle reste
importable sans les extras ; `test_requirements_embark_no_engine` vert.

### S7 — Surfaces utilisateur *(dép. : faible ; peut s'intercaler dès T9)*

- **Export CSV** : agrégats + par-document depuis `RunResult` (couche
  reports, lecture pure) ; CLI `--csv` + bouton web.
- **Glossaire** FR/EN : YAML porté **élagué** (entrées des features
  réellement présentes seulement, grandit avec les tranches), bouton « ? »
  dans le rapport.
- **CLI `history`** : lecture du `HistoryStore` (séries + régressions) —
  parité avec la page web.
- **Endpoint profils de normalisation** : lus dynamiquement depuis
  `formats/text` (jamais de liste statique — leçon Picarones).
- **Prompts par période** (FR/DE, texte + image) : fichiers de données +
  sélecteur (le champ `Competitor.prompt` existe).

### T15 (différé-par-design) — Reprise partielle

`partial_store` (fingerprint SHA-256 : config moteurs + normalisation +
corpus mtime/size + code_version ; journal NDJSON). **Déclencheur** : premier
corpus > ~200 docs ou moteurs cloud facturés au volume en usage régulier.
Conforme « pas d'infra d'avance ».

---

## 4. Vue d'ensemble — dépendances et volumes

```
T8 (hygiène + E1 + E2)
 ├─→ T9  stats (Nemenyi/bootstrap/CDD)  ─→ synthesis enrichie
 ├─→ T10 économie (pricing/Pareto)      ←─ E1 (durées/tokens)
 ├─→ T11 diagnostic (+philologie)
 ├─→ T12 confidences/calibration ─→ T14 moteurs (Kraken/Mistral OCR/plugin Calamari)
 └─→ T13 taxonomie (± NER)
S7 surfaces : intercalable dès T9 (CSV, glossaire, CLI history, prompts)
T15 reprise : sur déclencheur
```

| Tranche | Port estimé (source Picarones, à adapter 15-25 %) | Touche l'enveloppe ? |
|---|---|---|
| T8 | ~300 LOC neuves (E1+E2) + hygiène | **Oui — la seule** |
| T9 | ~600 LOC (stats) + sections | Non |
| T10 | ~850 LOC + YAML | Non |
| T11 | ~700 LOC (sous-ensemble retenu) | Non |
| T12 | ~400 LOC | Non (type domain au déclencheur) |
| T13 | ~750 LOC (taxo 300 + NER 450 opt.) | Non |
| T14 | ~500 LOC (2 adapters) + plugin externe | Non |
| S7 | ~300 LOC + données (glossaire, prompts) | Non |

---

## 5. Règles anti-chaos spécifiques à ce plan

Les 5 garde-fous de `CLAUDE.md §5` restent la loi. S'y ajoutent, propres à
cette phase de parité :

1. **Monnaie unique** : tout classement/historique/régression passe par
   `MetricScore` scalaire. `analyses` ne classe jamais.
2. **Un payload `analyses` = un calcul (evaluation) + un consommateur
   (section/export) + un golden, même commit.** Pas de payload spéculatif.
3. **`reports/` lit, ne calcule pas** — le gate archi existant s'applique à
   chaque nouvelle section (c'est l'anti data-layer, cause n°2 du chaos
   Picarones).
4. **Jamais deux signatures de `Module` en vie.** E1 est le seul changement
   de contrat autorisé par ce plan, et il est atomique.
5. **Donnée datée = donnée vérifiable** : `pricing.yaml` porte
   `valid_until` ; le rapport affiche l'avertissement de péremption
   automatiquement (leçon `pricing_staleness` de Picarones, sans le moteur
   narratif).
6. **Port ≠ copie** : chaque module porté perd ses références sprint, ses
   imports legacy, et passe sous budget. La parité *numérique* avec
   Picarones est testée sur fixtures partagées quand l'algo est censé être
   identique (Nemenyi, bootstrap, ECE).
7. **Un abandon est écrit** : tout élément de la liste §2 « abandonnés »
   est inscrit au journal de décisions au merge de T8 — plus jamais de
   « statut ambigu ».
