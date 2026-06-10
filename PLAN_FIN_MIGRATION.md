# PLAN_FIN_MIGRATION.md — Route vers `1.0.0` et gel de Picarones

> **Nature de ce fichier.** Plan **prospectif** de la dernière ligne droite. Il
> décrit le **scope décidé**, l'**ordre des tranches**, les **fichiers touchés**,
> les **risques** et la **DoD** de chaque étape jusqu'à `1.0.0`.
>
> **Autorité de statut = roll-up de [`MIGRATION_PLAN.md`](MIGRATION_PLAN.md).**
> Ce fichier ne *déclare* aucun statut « fait » : toutes les tranches ci-dessous
> sont **PLANIFIÉES — non livrées**. Quand une tranche est livrée, on met à jour
> le roll-up **dans le même commit que le code** (rituel de réconciliation), pas
> ici.

---

## 0. Constat d'entrée — où en est XerOCR (juin 2026)

Le cadrage initial sous-estimait l'avancement. État réel vérifié sur le code :

| Bloc | État réel | Détail |
|---|---|---|
| **Moteur T1→T15** | ✅ livré | domain/formats/evaluation/pipeline complets ; Nemenyi + bootstrap, économie, diagnostics, calibration, taxonomie, reprise SHA-256 |
| **Space S1→S6, S7.a** | ✅ livré | coquille design, lanceur SSE+`Last-Event-ID`, persistance, sécurité publique, importeurs distants, `/history`, `/library`, `/segmentation`, export CSV |
| **OCR/HTR socle** | ✅ | Tesseract, Kraken, Mistral OCR, Precomputed |
| **LLM/VLM socle** | ✅ | OpenAI, Anthropic, Mistral (texte **+ vision**), Ollama |
| **VLM `zero_shot`** | ✅ | image → VLM direct, déjà câblé (openai/anthropic/mistral vision) |
| **Segmentation** | ✅ moteur | `CanonicalLayout`, fan-out région, PP-DocLayout maison, `region_cer`/`region_detection` |
| **Économie** | ✅ **mesurée** | coûts = jetons réels (E1) + temps wall-clock réel × tarif unitaire daté (`pricing.json`). **Pas d'estimation, pas de CO₂.** |
| **Importeurs** | ✅ | IIIF, eScriptorium, Gallica, HuggingFace, HTR-United |

**Les vrais manques vers 1.0** (ce que ce plan adresse) :

1. **Le Space public n'exécute aucun moteur** — c'est une **vitrine lecture seule**
   (rapports baké, `deploy/Dockerfile` sans binaire OCR). Le visiteur ne peut pas
   lancer un vrai OCR gratuitement. **C'est le manque n°1.**
2. **NER** non implémentée (enveloppe `RunResult` prête, métrique absente).
3. **Parité moteurs** Pero/Calamari/Google/Azure (tension à arbitrer, §4).
4. **Surface UX du rapport/web** : éléments Picarones non encore portés (§6).
5. **Release `1.0.0` + gel de Picarones** non faits.

---

## 1. Décisions actées (cette session)

| # | Décision | Statut |
|---|---|---|
| 1 | **8 abandons définitifs** (§3) | ✅ validé |
| 2 | **NER = extra optionnel `[ner]`** (option B), jamais de silence | ✅ validé |
| 3 | **Économie = coûts mesurés réels** | ✅ déjà l'état du code |
| 4 | **Ordonnancement = « socle déployé d'abord »** | ✅ validé |
| 5 | **Cible = `1.0.0` puis gel immédiat de Picarones** | ✅ validé |
| 6 | **Fiabilité = références externes + cas calculés à la main** (jamais Picarones comme source de vérité) | ✅ principe maintenu |
| 7 | **Parité moteurs** — tension archi à trancher | ⚠️ recommandation §4, nod attendu |

---

## 2. Méthode — fidélité & anti-régression

- **Picarones n'est jamais l'oracle.** Toute valeur attendue d'un test vient
  d'une **référence externe** (jiwer, formule publiée, q-table Tukey, cassette
  HTTP réelle) ou d'un **cas calculé à la main**. On ne valide jamais une sortie
  XerOCR contre une sortie Picarones.
- **`make ci` complet avant tout push** (jamais un sous-ensemble — cf. D-049/050).
- **Chaque tranche = enveloppe figée + surface minimale**, dans un budget fichier,
  en élaguant. On n'empile pas.

---

## 3. Les 8 abandons définitifs

Décision **irréversible**, validée. Ce qui était dans Picarones et **ne sera pas
porté** dans XerOCR :

| # | Famille | Ce que ça faisait | Pourquoi on abandonne |
|---|---|---|---|
| 1 | **Estimation CO₂** | g CO₂/1000 pages = kWh inventé × intensité carbone conventionnelle | Aucun chiffre mesuré ; produit un nombre d'apparence scientifique sans donnée d'entrée auditable → viole l'invariant anti-hallucination. Mesurer exigerait un wattmètre/RAPL, hors scope. |
| 2 | **`image_predictive`** | « prédire » le CER depuis la qualité image | Pas d'implémentation réelle (stub) ; une vraie régression demanderait un jeu d'entraînement par moteur/type. `image_quality` (mesure réelle netteté/bruit/contraste) reste, **si** un consommateur la réclame. |
| 3 | **Calibration au-delà de l'existant** | ECE/MCE sur 10 bins de confiance | XerOCR a déjà `ConfidenceToken` + ECE/MCE (T12) branchés sur le sidecar Tesseract. Aucun 2ᵉ moteur ne fournit de confidences → rien à étendre tant que ce n'est pas le cas. |
| 4 | **Registre `levers` (561 LOC)** | infra à registre de « leviers d'amélioration » | 561 LOC pour 5 détecteurs, moitié dépendants de pré-métriques optionnelles qui **se taisent en silence** si absentes (pattern « moteur narratif », déjà supprimé §6). Les 2-3 observations saines (concentration Pareto, classe récupérable dominante) sont repliées dans `synthesis` en fonctions directes, avec message explicite si dépendance manquante. |
| 5 | **`taxonomy_intra_doc` + `_cooccurrence` + `_comparison`** | 3 re-projections de la taxonomy cœur | Aucune information nouvelle (re-groupements du même classement), tests quasi absents, 3 renderers SVG à maintenir pour des vues dont rien ne prouve l'usage. La **taxonomy cœur est gardée** (T13). |
| 6 | **`reliability` (Cohen κ / Krippendorff α)** | accord inter-annotateurs de la GT | Plafonné à 2 annotateurs, aucun loader multi-GT, jamais branché au runner ; outillage de **campagne d'annotation**, pas de benchmark de moteurs. La stabilité multi-runs LLM, elle, pourra revenir comme option `--repeat N` (autre design). |
| 7 | **`module_policy`** | audit de manifeste de modules tiers | Zéro module tiers n'a jamais existé ; XerOCR résout déjà mieux via `Protocol` unique + entry-points + fail-closed (T6). Le porter = doublon. |
| 8 | **WIL (Word Information Lost)** | variante d'erreur mot | XerOCR a CER/WER/MER (parité jiwer). WIL est quasi-monotone du WER : zéro décision différente, une colonne de plus partout. |

**Tout le reste est gardé ou amélioré** : searchability, numerical_sequences,
readability, abbreviations/MUFI, confusion/char_scores, taxonomy cœur,
error_absorption, inter_engine, line_metrics, robustness, hallucination,
image_quality, fidélité textuelle, longitudinal, économie (déjà mesurée).

> **Note de portage.** Plusieurs de ces familles « gardées » (searchability,
> numerical_sequences, readability, abbreviations, robustness, inter_engine,
> line_metrics, error_absorption) ne sont **pas encore** dans XerOCR — elles sont
> **additives** sur l'enveloppe `RunResult` et s'ajoutent **à la demande d'un
> consommateur** (garde-fou « pas de consommateur = supprimé »). Elles ne sont
> donc pas des tranches obligatoires de la route 1.0 ; ce plan les laisse en
> backlog additif explicite (§6 bis), priorisables une par une après 1.0.

---

## 4. ⚠️ Tension à arbitrer — parité moteurs

**Le conflit.** L'objectif « parité moteurs complète avec Picarones (Pero,
Calamari, Google Vision, Azure) » **contredit** une décision mergée de XerOCR :
`CLAUDE.md §8.8` (« 8+8+8 adapters → minimal ») et D-072 classent
Pero/Google/Azure/Calamari en **plugins hors-dépôt**, précisément pour ne pas
reproduire l'enflure de Picarones. Les deux ne peuvent être vrais simultanément —
je le signale au lieu de le trancher en douce (rituel `CLAUDE.md §9`).

**Recommandation de réconciliation** (donne la parité côté utilisateur sans
rouvrir l'enflure) :

| Moteur | Verdict recommandé | Justification |
|---|---|---|
| **Google Vision** | **First-party, extra `[google]`** | Client cloud léger (pas de dép lourde), valeur de parité réelle, enveloppé par le **contrat `Protocol` unique** (≠ double contrat Picarones). Un fichier adapter + une entrée factory + un test. |
| **Azure Document Intelligence** | **First-party, extra `[azure]`** | Idem : client cloud léger, parité réelle, un adapter + factory + test. |
| **VLM `zero_shot`** | **Déjà fait** | openai/anthropic/mistral vision livrés (T3/T14). À vérifier/documenter seulement (T18). |
| **Pero** | **Plugin de référence hors-dépôt** (`xerocr-pero`) | Dép lourde et fragile (modèles, torch) ; la garder hors du socle évite le dependency-hell in-tree **et** prouve le chemin entry-points (objectif produit T6). |
| **Calamari** | **Plugin de référence hors-dépôt** (`xerocr-calamari`) | Idem ; déjà désigné plugin de référence (D-072). |

> **Pourquoi ce partage est « sain » et non « Picarones ».** Le péché de Picarones
> n'était pas *d'avoir* des adapters cloud, c'était le **double contrat**
> (`BaseOCRAdapter` emballé dans `BaseModule`) et l'empilement « au cas où ».
> Ici : **un seul `Protocol`**, **extra-gated**, **un test chacun**, **fail-closed
> sans clé** (listé mais indisponible, jamais de crash). C'est la couche 5 dans
> son rôle légitime.

**Ce qu'il te reste à confirmer (une phrase suffit)** : OK pour Google+Azure
first-party / Pero+Calamari plugins ? Ou veux-tu Pero et/ou Calamari **aussi**
in-tree (j'ajoute alors les extras `[pero]`/`[calamari]` et j'assume le poids des
deps) ? **Tant que tu n'as pas tranché, la tranche T17 reste bloquée ; tout le
reste du plan (Phase A surtout) avance sans elle.**

---

## 5. Tranches ordonnancées — « socle déployé d'abord »

Quatre phases. **Phase A en premier** (valeur publique visible tôt) ; chaque
phase s'appuie sur un socle déjà déployé.

Gabarit de chaque tranche : **Objectif · Traverse · Fichiers touchés ·
Dépendances · Risques · DoD**.

---

### PHASE A — Socle déployé (le Space exécute un OCR réel gratuit)

#### S8 — Space exécutable Tesseract (clé de voûte)

| | |
|---|---|
| **Objectif** | Le Space HF public **exécute réellement Tesseract gratuitement**. Aujourd'hui : vitrine lecture seule, zéro moteur baké → le visiteur ne peut rien benchmarker. Cible : upload corpus → run Tesseract → vrai rapport CER, **sans clé, sans installation**. |
| **Traverse** | déploiement (`deploy/`) · interfaces/web (mode public **autorise l'exécution first-party**) · app (statut moteur exposé) |
| **Fichiers touchés** | `deploy/Dockerfile.engine` (**nouveau** — image moteur ≠ image vitrine) : `apt-get install tesseract-ocr tesseract-ocr-fra tesseract-ocr-lat tesseract-ocr-eng`, `pip install .[serve,tesseract]`, `ENV TESSDATA_PREFIX=/usr/share/tesseract-ocr/*/tessdata`, **`ENV OMP_THREAD_LIMIT=1`**, **smoke-test build** (`tesseract --version` + `--list-langs | grep -qx fra` + OCR d'une PBM générée), `USER` non-root 1000 · `deploy/requirements.txt` (+`pytesseract` ; binaire via apt, pas pip) · `.github/workflows/deploy-space.yml` (build image moteur, **smoke OCR réel** post-déploiement en plus du `/health`) · `xerocr/interfaces/web/app.py` + `security/` (mode public : exécution **uniquement** des modules first-party gratuits ; plugins/cloud gated) · `xerocr/app/engines.py` (Tesseract = disponible dans le Space) |
| **Dépendances** | adapter `tesseract` (T2 ✅) · `JobRunner`+SSE (S2 ✅) · durcissement public (S5 ✅) · leçons Picarones (incident OpenMP 2026-05-16, `fra` apt, `TESSDATA_PREFIX`, smoke fail-fast) |
| **Risques** | **(R1) Cold-start / 2 vCPU free-tier** : `OMP_THREAD_LIMIT=1` **obligatoire** (sans lui Tesseract deadlock OpenMP — incident documenté Picarones). **(R2) Abus public** : conserver rate-limit (S5), caps upload (413/422), sémaphore jobs, `Deadline`/timeout coopératifs. **(R3) Surface d'exécution** : en mode public, **seul** le socle first-party gratuit (tesseract) s'exécute ; plugins désactivés (fail-closed T6), moteurs cloud listés mais **indisponibles sans clé**. **(R4) Déterminisme** : version binaire Tesseract épinglée dans l'image → tracée dans `RunManifest`. |
| **DoD** | Build Docker **échoue** si tesseract/`fra` absent ou OCR > timeout (smoke). · Test `live` : un visiteur upload un petit ZIP → run tesseract → reçoit un rapport CER réel sur le Space public, sans clé. · Test mode-public : tesseract exécutable, plugins + cloud **gated**. · `make ci` vert · workflow déploiement vert · `/health` < 50 ms. |

#### S9 — Segmenteur réel sur le Space (T2.5 PaddleX) — **conditionnel**

| | |
|---|---|
| **Objectif** | `/segmentation` exécute un **vrai** PP-DocLayout sur le Space (aujourd'hui : « segmenteur indisponible » en dégradé gracieux si poids absents). |
| **Traverse** | déploiement (`deploy/`) · app (statut segmenteur) |
| **Fichiers touchés** | `deploy/Dockerfile.engine` (+`paddlex`, poids via Git-LFS **ou** download au build) · `.github/workflows/deploy-space.yml` (LFS poids, taille image) · `xerocr/app/engines.py` (segmenteur disponible) |
| **Dépendances** | **S8 déployé d'abord** (mesurer le cold-start Tesseract avant d'alourdir) · adapter `pp_doclayout` (T5 ✅) |
| **Risques** | **PaddleX + poids = lourd** (centaines de Mo) → cold-start free-tier potentiellement rédhibitoire (D-064, différé opérationnel). |
| **DoD / décision** | Mesurer le cold-start avec l'image S8 **puis** trancher : (a) baker PaddleX si le free-tier tient ; (b) rester en **dégradé gracieux** (« segmenteur indisponible », le moteur tourne en local/CI) ; (c) **upgrade de tier** (décision budget — **à toi**). Aucune des trois ne bloque 1.0 : le dégradé gracieux est déjà livré. |

---

### PHASE B — Surface fonctionnelle restante

#### T16 — NER en extra `[ner]`

| | |
|---|---|
| **Objectif** | Mesurer la **préservation des entités nommées** (F1 par catégorie, manquées/hallucinées, appariement IoU 0.5 — standard CoNLL/HIPE) quand la GT fournit un sidecar `.entities.json`. **Derrière l'extra `[ner]`** ; GT entités présente + extra absent → **message explicite** « installer `xerocr[ner]` », **jamais de silence** (correction du défaut Picarones). |
| **Traverse** | 3 (loader entités GT + métrique `ner` + `NerPayload` additif) · 5 (extracteur spaCy lazy) · 7 (section) · 8 (extra) |
| **Fichiers touchés** | `pyproject.toml` (**extra `ner = ["spacy"]`** ; modèles documentés, pas en dép) · `xerocr/adapters/ner/spacy_extractor.py` (**nouveau** — import lazy, fail-closed) · `xerocr/evaluation/metrics/ner.py` (**nouveau** — IoU greedy F1) · `xerocr/evaluation/analysis.py` (+`NerPayload`, additif) · `xerocr/evaluation/runner.py` (branchement : GT entités + extra dispo → calcul ; sinon payload « indisponible ») · `xerocr/reports/sections/ner.py` (**nouveau**) · loader sidecar `.entities.json` (`xerocr/adapters/corpus/` ou `app/corpus_import.py`) · `tests/evaluation/test_ner.py` (fixture entités, F1 calculé **à la main**) |
| **Dépendances** | enveloppe `RunResult` (✅) · `Protocol Section` (✅) · `RunManifest.deps` (✅, trace version modèle spaCy) |
| **Risques** | spaCy lourd → **strictement extra** (jamais en base — respecte `CLAUDE.md §3`). · Déterminisme : version modèle spaCy → `RunManifest`. · **Anti-silence** : test dédié qui vérifie le message explicite quand l'extra manque. |
| **DoD** | Avec extra + modèle → F1 conforme à un cas calculé main sur fixture. · Sans extra → message explicite, pas de crash, pas de silence. · `make ci` vert (tests NER skip propre sans extra). |

#### T16-bis — Vérification « économie mesurée » (micro)

| | |
|---|---|
| **Objectif** | Garantir que **tous** les adapters cloud remontent `tokens_in`/`tokens_out` (E1) — le calcul économique est déjà mesuré, reste à fermer les trous éventuels. |
| **Fichiers touchés** | `xerocr/adapters/llm/{openai,anthropic,mistral}.py` (vérifier la remontée `ResourceUsage`) · `tests/adapters/llm/` (assert tokens non-`None` sur cassette) |
| **Risques** | Un adapter qui ne remonte pas les jetons → coût `None` + motif `basis` (déjà géré, jamais de zéro silencieux) ; on veut juste éviter le `None` évitable. |
| **DoD** | Chaque adapter cloud testé : `tokens_in/out` peuplés sur réponse réelle (cassette). |

#### T17 — Parité moteurs (**bloquée sur §4**)

| | |
|---|---|
| **Objectif** | Atteindre la parité moteurs côté utilisateur selon l'arbitrage §4. |
| **Traverse** | 5 (adapters) · 6 (factory) · 8 (extras) |
| **Fichiers touchés** (recommandation §4) | `xerocr/adapters/ocr/google_vision.py` (**nouveau**, extra `[google]`) · `xerocr/adapters/ocr/azure_di.py` (**nouveau**, extra `[azure]`) · `xerocr/app/engines.py` (entrées factory) · `pyproject.toml` (extras `google`, `azure`) · `tests/adapters/ocr/test_google_vision.py` + `test_azure_di.py` (cassettes, valeurs main) · **Pero/Calamari** : aucun fichier in-tree (dépôts plugins `xerocr-pero`/`xerocr-calamari`) + `docs/PLUGINS.md` |
| **Dépendances** | contrat `Protocol` (✅) · découverte plugins T6 (✅) · **arbitrage §4 confirmé** |
| **Risques** | **Croissance de surface** → mitigée : un `Protocol`, extra-gated, un test chacun, fail-closed sans clé. Ne **jamais** réintroduire de double contrat. |
| **DoD** | Google/Azure listés ; avec clé → OCR réel sur cassette ; sans clé → indisponible propre. · Plugins Pero/Calamari : un `pip install xerocr-pero` les rend découvrables sans forker (preuve entry-points). · `make ci` vert. |

#### T18 — Vérification VLM `zero_shot` (checkpoint léger)

| | |
|---|---|
| **Objectif** | Confirmer et **documenter** que `zero_shot` (image → VLM direct, sans OCR amont) est fonctionnel de bout en bout sur les 3 VLM. |
| **Fichiers touchés** | aucun code attendu (déjà livré) · `tests/pipeline/` (assert spec zero_shot 1 étage IMAGE→RAW_TEXT) · `README`/docs (mode documenté) |
| **DoD** | Test bout-en-bout zero_shot sur fixture image + un VLM (cassette). |

---

### PHASE C — Parité UX (web + rapport)

> Le web et le rapport XerOCR portent déjà **beaucoup** (benchmark, SSE
> `Last-Event-ID`, library, history, segmentation, importeurs, CSRF, rate-limit,
> i18n FR/EN). Cette phase **comble le delta** avec Picarones (inventaire §6). Les
> verdicts « porter / déjà fait / adapter » sont **à confirmer au build** (le
> contact du code corrige souvent l'analyse — convention XerOCR).

#### S10 — Rapport autonome interactif (parité interaction)

| | |
|---|---|
| **Objectif** | Porter les interactions client-side du rapport Picarones manquantes. |
| **Fichiers touchés** | `xerocr/reports/` (templates + JS embarqué) : **compare 2 runs client-side** (`FileReader`+`JSON.parse`, 0 réseau, plafond 50 Mo, bandeau sticky deltas — la logique server-side `reports/compare.py` reste pour `xerocr compare`) · **badges moteur A→E** (helper unique, cf. convention Picarones `engine_badges`) · **hash-router** vues + deeplinks + navigation clavier (ARIA tablist) · **i18n formatage nombres** (séparateurs localisés FR/EN) · **palette daltonien** (toggle `?palette=`) |
| **Risques** | Tout reste **déterministe** et **sans LLM** (invariant anti-hallucination). JS client = lecture seule, aucune fuite réseau. |
| **DoD** | Compare 2 runs hors-ligne fonctionnel ; deeplinks + clavier ; nombres localisés ; golden rapport octet-stable inchangé. |

#### S11 — Galerie documents & drill-in

| | |
|---|---|
| **Objectif** | Galerie de documents avec **miniatures lazy-load** (IntersectionObserver) + drill-in **image + diff caractère/mot surligné** GT vs hypothèse. |
| **Fichiers touchés** | `xerocr/reports/` (section galerie + template drill-in + JS lazy) · réutilise `_diff` (à porter si absent : diff char/mot déterministe) |
| **Risques** | Poids des images → lazy obligatoire ; plafond résolution configurable. |
| **DoD** | Galerie affiche miniatures à la demande ; drill-in montre diff coloré ; aucun appel réseau hors images. |

#### S12 — Surfaces formulaire (parité champs `RunSpec`)

| | |
|---|---|
| **Objectif** | Exposer dans le Banc d'essai les champs encore absents, pour la **parité CLI/web**. |
| **Fichiers touchés** | `xerocr/interfaces/web/routers/` + templates : **preview profil de normalisation** (endpoint validation YAML custom, sans persistance) · **config save/load** (JSON téléchargeable, schema_version) · **`/api/models/{provider}`** (modèles + capacités text/vision, fallback liste canonique) · sélecteurs `char_exclude`, profil métrique, toggle expose-ALTO (si pertinent) |
| **Risques** | Garder `interfaces` **mince** (garde-fou `test_interfaces_thin`) : la construction de spec vit en `app/run_planning`. · Validation chemins/SSRF maintenue. |
| **DoD** | Tous les champs `RunSpec` atteignables en web ; preview normalisation sans persistance ; config round-trip. |

#### S13 — Observabilité & accessibilité (finitions)

| | |
|---|---|
| **Objectif** | `/metrics` Prometheus **opt-in**, sélecteur de langue `/api/lang`, tooltips/ARIA, feedback dropzone, spinner/progress. |
| **Fichiers touchés** | `xerocr/interfaces/web/routers/` (system endpoints) · templates (a11y) |
| **Risques** | `/metrics` strictement opt-in (variable d'env), pas d'effet de bord. |
| **DoD** | `/metrics` exposé si activé ; navigation a11y au clavier ; aucun endpoint nouveau non testé. |

---

### PHASE D — Release `1.0.0` & gel de Picarones

#### R1.0 — Release `1.0.0`

| | |
|---|---|
| **Objectif** | Publier `1.0.0` : l'enveloppe 8 couches est remplie au niveau « parité utile », le Space exécute un OCR réel gratuit, la surface est élaguée. |
| **Fichiers touchés** | tag `v1.0.0` (setuptools_scm) · `README.md` (positionnement 1.0, matrice moteurs/extras, mode Space) · `CHANGELOG.md` (**minimal**, pas un 97-sprints) · `pricing.json` (`valid_until` rafraîchi) · `MIGRATION_PLAN.md` roll-up (réconcilié au même commit) |
| **DoD** | `make ci` vert sur 3 OS × Python 3.11/3.12 · Space public déployé et exécutant Tesseract · couverture ≥ 85 % · checklist §7 cochée. |

#### GEL — Gel de Picarones

| | |
|---|---|
| **Objectif** | Figer Picarones en lecture seule, rediriger vers XerOCR. |
| **Étapes** | Bannière `README` Picarones → « Projet figé, successeur : XerOCR » · archivage du dépôt GitHub (read-only) · note de dépréciation sur le Space HF Picarones (lien vers Space XerOCR) · dernier commit de gel, plus aucun développement. |
| **DoD** | Dépôt Picarones archivé ; pointeurs en place ; XerOCR `1.0.0` est l'unique cible active. |

---

## 6. Inventaire UX Picarones — verdict par élément

Verdicts **PROVISOIRES — à confirmer au build**. Légende : **DÉJÀ FAIT** (présent
dans XerOCR) · **PORTER** (à ajouter) · **ADAPTER** (présent partiellement) ·
**ABANDONNER**.

### Banc d'essai / run

| Élément | Verdict | Tranche |
|---|---|---|
| Sélection corpus + hero stats | DÉJÀ FAIT | — |
| Upload ZIP drag&drop + validation + dédup basename | DÉJÀ FAIT | — |
| Purge RGPD des uploads | ADAPTER (vérifier purge) | S12 |
| Composition OCR / OCR→LLM / post-correction | DÉJÀ FAIT | — |
| `pipeline_mode` strict (`zero_shot`/`text_only`/`text_and_image`) | DÉJÀ FAIT | — |
| Sélecteur profil métrique (minimal/standard/full) | ADAPTER | S12 |
| `char_exclude`, entity extractor path, output JSON | PORTER (champs) | S12 |
| Toggle expose-ALTO (Tesseract) | PORTER (si pertinent) | S12 |
| SSE progression + `Last-Event-ID` + keepalive | DÉJÀ FAIT | — |
| Annulation job + sémaphore + rate-limit | DÉJÀ FAIT | — |
| Config save/load JSON | PORTER | S12 |
| Preview profil normalisation (YAML custom) | PORTER | S12 |
| `/api/models/{provider}` capacités | PORTER | S12 |

### Bibliothèque / corpus

| Élément | Verdict | Tranche |
|---|---|---|
| Upload + listing + suppression corpus | DÉJÀ FAIT | — |
| Import IIIF (preview manifeste) | DÉJÀ FAIT | — |
| Recherche + import Gallica | DÉJÀ FAIT | — |
| Catalogue HTR-United (+ mode démo) | DÉJÀ FAIT | — |
| Recherche + import HuggingFace | DÉJÀ FAIT | — |
| Import eScriptorium (token non loggé) | DÉJÀ FAIT | — |

### Historique

| Élément | Verdict | Tranche |
|---|---|---|
| Listing runs + filtres SQLite | DÉJÀ FAIT | — |
| Courbes/sparklines CER par moteur | ADAPTER (vérifier sparklines) | S11 |
| Détection régression (seuil Δ) | DÉJÀ FAIT | — |

### Rapport HTML

| Élément | Verdict | Tranche |
|---|---|---|
| Onglets Overview/Engines/Documents/Crosses | DÉJÀ FAIT (sections) | — |
| Synthèse factuelle déterministe (0 LLM) | DÉJÀ FAIT (`synthesis`) | — |
| Badges moteur A→E | PORTER | S10 |
| Galerie documents + miniatures lazy | PORTER | S11 |
| Diff caractère/mot drill-in | PORTER | S11 |
| Compare 2 runs client-side (FileReader) | PORTER | S10 |
| Hash-router + deeplinks + clavier | PORTER | S10 |
| Palette daltonien | PORTER | S10 |
| i18n formatage nombres | PORTER | S10 |
| Export JSON/CSV | DÉJÀ FAIT (CSV) ; JSON ADAPTER | S12 |
| Heatmap confusion Unicode | DÉJÀ FAIT (diagnostics) | — |
| Pareto coût/vitesse | DÉJÀ FAIT (economics) | — |
| Onglet CO₂ Pareto | **ABANDONNER** | §3 #1 |
| 20 détecteurs narratifs | **ABANDONNER** (déjà acté §6 CLAUDE) | — |

### Système / sécurité

| Élément | Verdict | Tranche |
|---|---|---|
| `/health`, CSRF, CSP, rate-limit, path-traversal, ZIP-bomb, image streaming | DÉJÀ FAIT | — |
| `/metrics` Prometheus opt-in | PORTER | S13 |
| i18n FR/EN interface | DÉJÀ FAIT | — |

### Notable « faciles à oublier » (à porter dans S10/S11/S12)

Lazy images (IntersectionObserver) · bandeau compare sticky non-intrusif ·
palette daltonien partageable par URL · keepalive SSE 30 s · CSRF double-submit ·
formatage nombres localisé · détection corpus-mismatch au compare · dédup
basename à l'upload · message explicite « modèle hors table » (jamais zéro
silencieux) · token API jamais loggé.

---

## 6 bis. Backlog additif (post-1.0, à la demande d'un consommateur)

Familles « gardées » non bloquantes pour 1.0, ajoutables une par une **quand un
consommateur réel les réclame** (jamais « au cas où ») : searchability,
numerical_sequences, readability, abbreviations/MUFI (au-delà de `mufi_err`),
error_absorption, inter_engine (divergence + oracle gap), line_metrics
(percentiles/Gini), robustness (dégradations PIL + re-run), image_quality.

---

## 7. Garde-fous anti-« syndrome Picarones » (appliqués à ce plan)

| Garde-fou | Comment ce plan le respecte |
|---|---|
| **1. Rupture nette, zéro shim** | Aucun pont vers un format Picarones ; `RunResult` unique. |
| **2. Budgets fichier** | Chaque nouveau fichier (ner, google_vision, azure_di, sections) sous 600 LOC ou entrée justifiée `test_file_budgets`. |
| **3. Pas de consommateur = supprimé** | Les 8 abandons (§3) ; familles « gardées » mises en **backlog additif** (§6 bis), pas implémentées d'avance. Pero/Calamari hors-dépôt tant que pas réclamés in-tree. |
| **4. Tests d'archi jour 1** | Inchangés et bloquants ; toute tranche passe `layer_dependencies`, `no_broad_except`, `file_budgets`, `status_freshness`, etc. |
| **5. Une feature entière, dans un budget, en élaguant** | Google/Azure = 1 adapter + 1 factory + 1 test chacun ; NER = métrique + extracteur + section + extra, rien de plus. |
| **Anti-silence** | NER et coûts : message explicite si dépendance/tarif manquant, jamais de `[]`/`0` muet. |
| **Anti-hallucination** | Rapport interactif (S10/S11) reste déterministe, 0 LLM, diff/compare calculés client-side sur données d'entrée. |

---

## 8. Définition de « `1.0.0` prête » (checklist)

- [ ] **Space public exécute Tesseract gratuitement** (S8), build fail-fast, OMP borné, `fra` présent.
- [ ] Segmenteur Space : tranché S9 (baké **ou** dégradé gracieux **ou** tier supérieur).
- [ ] **NER** livrée en extra `[ner]`, message explicite sans l'extra (T16).
- [ ] Économie : tous adapters cloud remontent les jetons (T16-bis).
- [ ] **Parité moteurs** : arbitrage §4 confirmé et implémenté (T17) ; VLM zero_shot vérifié (T18).
- [ ] **Parité UX** : compare client-side, galerie lazy, badges A→E, i18n nombres, config, preview normalisation (S10–S13).
- [ ] `make ci` vert (3 OS × 3.11/3.12), couverture ≥ 85 %, tous garde-fous d'archi verts.
- [ ] Roll-up `MIGRATION_PLAN.md` réconcilié au même commit que chaque livraison.
- [ ] `README`/`CHANGELOG` à jour, `pricing.json` daté.

## 9. Gel de Picarones (post-`1.0.0`)

- [ ] Bannière `README` Picarones → successeur XerOCR.
- [ ] Dépôt GitHub Picarones archivé (read-only).
- [ ] Note de dépréciation sur le Space HF Picarones (lien Space XerOCR).
- [ ] Plus aucun commit Picarones ; XerOCR `1.0.0` = unique cible active.

---

## Ordre d'exécution résumé

```
A : S8 (Space Tesseract) → S9 (Space segmenteur, conditionnel)
B : T16 (NER) + T16-bis (jetons) → [arbitrage §4] → T17 (parité moteurs) → T18 (zero_shot)
C : S10 (rapport interactif) → S11 (galerie) → S12 (champs formulaire) → S13 (obs/a11y)
D : R1.0 (release 1.0.0) → GEL (gel Picarones)
```

**Seule action requise de ta part pour débloquer la suite : l'arbitrage §4
(parité moteurs).** La Phase A (le manque n°1 — OCR réel gratuit sur le Space) ne
dépend d'aucun arbitrage et peut démarrer immédiatement.
