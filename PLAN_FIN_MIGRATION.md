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
| 7 | **Parité moteurs** : Google+Azure first-party (extras `[google]`/`[azure]`), Pero+Calamari plugins hors-dépôt | ✅ validé (§4) |

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

> **Note de portage — toutes les familles gardées sont OBLIGATOIRES avant 1.0.**
> Plusieurs familles « gardées » (numerical_sequences, readability, abbreviations,
> early_modern/roman, fidélité textuelle, robustness, image_quality,
> error_absorption, inter_engine, line_metrics) ne sont **pas encore** dans
> XerOCR. **Décision (cette session) : elles deviennent des tranches obligatoires
> de la route 1.0** (T19→T23), pas un backlog post-1.0. Raison : le gel de
> Picarones (§9) **ferme la fenêtre de portage** — ce qui n'est pas dans la 1.0
> est perdu. Ce n'est **pas** une dérive « surface au cas où » car (a) chaque
> famille est jugée utile/réparable sur pièces (§3 bis), (b) chacune reçoit un
> **consommateur réel** (sa section de rapport) → garde-fou « pas de consommateur »
> respecté, (c) chaque famille est construite **entièrement** (métrique + payload
> + section + tests), jamais en stub → garde-fou #5 respecté. Les familles 🔶
> sont **réparées** au portage (unification, recâblage), jamais copiées telles
> quelles.

---

## 3 bis. Verdict métrique-par-métrique (analyse sur pièces)

Synthèse des deux audits de qualité d'exécution de Picarones (lecture du code,
tests, renderers, câblage). Légende : ✅ ABOUTIE-UTILE · 🔶 BONNE-IDÉE-MAL-FAITE
(réparée au portage) · 🟡 GADGET (abandonnée). **Toute famille non 🟡 est une
tranche obligatoire** (déjà livrée en XerOCR, ou T16/T19→T23).

| Famille | Verdict | Sur pièces | Statut XerOCR / tranche |
|---|---|---|---|
| CER / WER / MER | ✅ | parité jiwer | **livré** (T2) |
| diacritic_err, del_rate, ins_rate, mufi_err | ✅ | NFD align, MUFI PUA | **livré** (T7) |
| confusion + char_scores | ✅ | Levenshtein minimal (fix F4) | **livré** (T11) |
| taxonomy cœur (7-9 classes) | ✅ | classes à sens analytique | **livré** (T13) |
| searchability | ✅ | Levenshtein≤2 (Elastic), 21 tests | **livré** (T11) |
| hallucination | 🔶 | trigrammes ; faux positifs diacritiques/multilingue | **livré** (T11), **à durcir** |
| economics | ✅ | jetons mesurés + temps réel | **livré** (T10), CO₂ exclu |
| calibration (ECE/MCE) | ✅ | Guo et al., bins | **livré** (T12, `ConfidenceToken`) |
| longitudinal | 🔶 | OLS OK ; « CUSUM » = max-diff naïf | **livré** (T7), **change-point à raffiner** (T23) |
| **numerical_sequences** | ✅ | 5 catégories, regex conservatrices, recto/verso | **T19** |
| **readability (Flesch delta)** | ✅ | formules publiées, révèle sur-normalisation LLM | **T19** |
| **abbreviations** | ✅ | 2 scores diplo/modernisant, pas de GT spéciale | **T20** |
| **early_modern + roman + modern_archives** | 🔶 | fragmenté, roman couplé à 2 entrées | **T20** (unifié) |
| **rare_tokens + lexical_mod + over_norm + equivalence** | 🔶 | câblage fragmenté | **T21** (unifié « fidélité textuelle ») |
| **robustness** | ✅ | vraies dégradations PIL + re-OCR | **T22** |
| **image_quality** | 🔶 | mesure réelle OK, constantes crues | **T22** (mesure ; `image_predictive` abandonné) |
| **error_absorption** | ✅ | multiset correct, méthodo honnête | **T23** |
| **inter_engine** | ✅ | Jensen-Shannon + oracle gap | **T23** |
| **line_metrics** | ✅ | percentiles/Gini ; alignement `\n` à fiabiliser | **T23** |
| **ner** | ⚠️→✅ | IoU solide mais découplée (silence si spaCy absent) | **T16** (extra `[ner]`, recâblée, anti-silence) |
| taxonomy intra_doc / cooccurrence / comparison | 🟡 | re-projections sans info nouvelle | **ABANDON #5** |
| pricing CO₂ | 🟡 | table statique + intensité fictive | **ABANDON #1** |
| image_predictive | 🟡 | stub, pas d'implémentation | **ABANDON #2** |
| calibration au-delà existant | 🟡 | un seul moteur fournit des confiances | **ABANDON #3** |
| levers (registre 561 LOC) | 🔶→🟡 | dépendances silencieuses | **ABANDON #4** (registre ; obs. saines → `synthesis`) |
| reliability (κ/α) | 🔶→🟡 | plafonné 2 annotateurs, jamais branché | **ABANDON #6** |
| module_policy | 🟡 | zéro module tiers, inerte | **ABANDON #7** |
| WIL | 🟡 | quasi-monotone du WER | **ABANDON #8** |

> Chaque tranche T19→T23 livre la famille **entièrement** : métrique +
> payload additif `RunResult` + **section de rapport** (le consommateur) +
> tests à **valeurs calculées main / référence externe** (jamais Picarones comme
> oracle) + câblage profil. Les 🔶 sont **réparées**, pas copiées.

---

## 4. Parité moteurs — arbitrage tranché ✅

**Le conflit (résolu).** L'objectif « parité moteurs complète avec Picarones
(Pero, Calamari, Google Vision, Azure) » contredisait une décision mergée de
XerOCR : `CLAUDE.md §8.8` (« 8+8+8 adapters → minimal ») et D-072 classaient
Pero/Google/Azure/Calamari en **plugins hors-dépôt**. La tension a été signalée
(rituel `CLAUDE.md §9`) puis **arbitrée** : on retient le partage de
réconciliation ci-dessous (parité côté utilisateur sans rouvrir l'enflure).

**Décision actée** :

| Moteur | Verdict | Justification |
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

**T17 est donc débloquée.** À reporter dans le journal de décisions du roll-up
`MIGRATION_PLAN.md` (nouvelle entrée D-0xx) au moment du build de T17.

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

#### T17 — Parité moteurs (débloquée ✅, cf. §4)

| | |
|---|---|
| **Objectif** | Atteindre la parité moteurs côté utilisateur selon l'arbitrage §4 (acté). |
| **Traverse** | 5 (adapters) · 6 (factory) · 8 (extras) |
| **Fichiers touchés** | `xerocr/adapters/ocr/google_vision.py` (**nouveau**, extra `[google]`) · `xerocr/adapters/ocr/azure_di.py` (**nouveau**, extra `[azure]`) · `xerocr/app/engines.py` (entrées factory) · `pyproject.toml` (extras `google`, `azure`) · `tests/adapters/ocr/test_google_vision.py` + `test_azure_di.py` (cassettes, valeurs main) · **Pero/Calamari** : aucun fichier in-tree (dépôts plugins `xerocr-pero`/`xerocr-calamari`) + `docs/PLUGINS.md` |
| **Dépendances** | contrat `Protocol` (✅) · découverte plugins T6 (✅) · arbitrage §4 ✅ |
| **Risques** | **Croissance de surface** → mitigée : un `Protocol`, extra-gated, un test chacun, fail-closed sans clé. Ne **jamais** réintroduire de double contrat. |
| **DoD** | Google/Azure listés ; avec clé → OCR réel sur cassette ; sans clé → indisponible propre. · Plugins Pero/Calamari : un `pip install xerocr-pero` les rend découvrables sans forker (preuve entry-points). · `make ci` vert. |

#### T18 — Vérification VLM `zero_shot` (checkpoint léger)

| | |
|---|---|
| **Objectif** | Confirmer et **documenter** que `zero_shot` (image → VLM direct, sans OCR amont) est fonctionnel de bout en bout sur les 3 VLM. |
| **Fichiers touchés** | aucun code attendu (déjà livré) · `tests/pipeline/` (assert spec zero_shot 1 étage IMAGE→RAW_TEXT) · `README`/docs (mode documenté) |
| **DoD** | Test bout-en-bout zero_shot sur fixture image + un VLM (cassette). |

#### T19 — Données structurées & lisibilité

| | |
|---|---|
| **Objectif** | `numerical_sequences` (fidélité dates/foliation/devises/romains/régnal) + `readability` (Flesch delta GT↔hyp, révèle la sur-normalisation LLM). |
| **Traverse** | 3 (2 métriques + payload additif) · 7 (section) |
| **Fichiers touchés** | `xerocr/evaluation/metrics/numerical_sequences.py` (**nouveau**) · `xerocr/evaluation/metrics/readability.py` (**nouveau**) · `xerocr/evaluation/analysis.py` (+payloads additifs) · `xerocr/evaluation/runner.py` (câblage profil) · `xerocr/reports/sections/structured_data.py` (**nouveau**, section commune) · `tests/evaluation/test_numerical_sequences.py` + `test_readability.py` (valeurs main : années 1000-2099, foliation r/v, Flesch publié) |
| **Risques** | Flesch : syllabation heuristique → **borner l'usage au delta relatif** (documenté), jamais publier un absolu. Langue : coefficients FR/EN explicites. |
| **DoD** | 5 catégories numériques testées ; delta Flesch=0 sur GT=hyp, positif sur LLM lissé ; section rendue ; `make ci` vert. |

#### T20 — Philologie étendue (abréviations + typographie ancienne)

| | |
|---|---|
| **Objectif** | `abbreviations` (scores diplomatique/modernisant) + **unification** `early_modern_typography` + `roman_numerals` + `modern_archives` sous un namespace propre (corrige la fragmentation Picarones : roman comptée deux fois). |
| **Traverse** | 3 (métriques + payload) · 7 (section, étend la vue philologie de `mufi_err`) |
| **Fichiers touchés** | `xerocr/evaluation/metrics/abbreviations.py` (**nouveau**) · `xerocr/evaluation/metrics/early_modern.py` (**nouveau** — roman + typo ancienne + archives, **un seul point d'entrée**) · `xerocr/evaluation/metrics/philology.py` (étendre la section) · `analysis.py` (payload) · `runner.py` (câblage) · `xerocr/reports/sections/` (philologie étendue) · `tests/evaluation/test_abbreviations.py` + `test_early_modern.py` (Capelli, romains IV/IX, edge cases) |
| **Risques** | **Réparation 🔶** : ne pas re-coupler roman à `numerical_sequences` ; un seul détecteur roman partagé. |
| **DoD** | 2 scores abréviation distinguent diplo/modernisant/cassé ; roman compté **une fois** ; namespace unifié ; `make ci` vert. |

#### T21 — Fidélité textuelle (modernisation / normalisation)

| | |
|---|---|
| **Objectif** | Unifier `rare_tokens` + `lexical_modernization` + `over_normalization` + `equivalence_profile` en **une famille « fidélité textuelle »** au câblage cohérent (corrige la fragmentation : rare_tokens hors hook, autres implicites). |
| **Traverse** | 3 (famille de métriques + payload) · 7 (section) |
| **Fichiers touchés** | `xerocr/evaluation/metrics/textual_fidelity.py` (**nouveau** — les 4 sous-mesures, câblage homogène) · `analysis.py` (payload) · `runner.py` (un seul point de câblage) · `xerocr/reports/sections/textual_fidelity.py` (**nouveau**) · `tests/evaluation/test_textual_fidelity.py` (hapax/dis-legomena, ſ→s, u↔v, over-norm Levenshtein minimal) |
| **Risques** | **Réparation 🔶** : décider le seuil rare (≤2) explicitement ; over_normalization sur Levenshtein minimal (pas positionnel) ; pas de silence si profil d'équivalence absent. |
| **DoD** | 4 sous-mesures sous un câblage unique ; tests valeurs main ; section rendue ; `make ci` vert. |

#### T22 — Robustesse & qualité image

| | |
|---|---|
| **Objectif** | `robustness` (dégradations PIL réelles bruit/flou/rotation/résolution/binarisation + **re-OCR réel**) + `image_quality` (netteté/bruit/contraste **mesurés**). **`image_predictive` reste abandonné** (§3 #2). |
| **Traverse** | 3 (métriques + payload) · 5 (utilise les adapters OCR pour re-run) · 7 (section) |
| **Fichiers touchés** | `xerocr/evaluation/robustness.py` (**nouveau** — dégradations PIL + projection) · `xerocr/evaluation/metrics/image_quality.py` (**nouveau** — variance laplacienne, MAD, Michelson) · `analysis.py` (payload) · `runner.py` ou CLI `robustness` (câblage du re-run) · `xerocr/reports/sections/robustness.py` (**nouveau**) · `tests/evaluation/test_robustness.py` + `test_image_quality.py` (dégradation déterministe, scores bornés) |
| **Risques** | Re-OCR = coûteux → `max_docs` borné + opt-in (comme Picarones). Constantes qualité empiriques → **validées sur fixtures patrimoniales**, documentées. Déterminisme : seed PIL fixe. |
| **DoD** | Dégradation PIL déterministe + re-OCR produit une courbe ; scores qualité bornés [0,1] ; section rendue ; `make ci` vert. |

#### T23 — Analyse inter-moteurs étendue & lignes

| | |
|---|---|
| **Objectif** | `inter_engine` (divergence Jensen-Shannon + oracle gap de complémentarité) + `error_absorption` (gain net OCR→LLM, multiset aligné) + `line_metrics` (percentiles/Gini par ligne) + **raffinement change-point** du longitudinal (remplacer le max-diff naïf par un vrai détecteur, ex. Pettitt/CUSUM). |
| **Traverse** | 3 (métriques + payload + raffinement longitudinal) · 7 (sections) |
| **Fichiers touchés** | `xerocr/evaluation/metrics/inter_engine.py` (**nouveau**) · `xerocr/evaluation/metrics/error_absorption.py` (**nouveau**) · `xerocr/evaluation/metrics/line_metrics.py` (**nouveau**) · `xerocr/evaluation/longitudinal.py` ou équivalent T7 (change-point raffiné) · `analysis.py` (payloads) · `runner.py` (câblage) · `xerocr/reports/sections/{crosses,lines}.py` (étendre/nouveau) · `tests/evaluation/` (JS divergence bornée [0,1], absorption multiset, percentiles, change-point sur série synthétique) |
| **Risques** | **Réparation 🔶** : alignement ligne-à-ligne `\n` fragile → fiabiliser (apparier par index + garde sur décalage) ; oracle gap = borne optimiste **documentée**. Change-point : tester sur série à rupture connue. |
| **DoD** | JS divergence ∈ [0,1] ; oracle gap calculé ; absorption multiset correcte ; change-point détecté sur fixture à rupture ; sections rendues ; `make ci` vert. |

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

## 6 bis. Familles métriques restantes = tranches OBLIGATOIRES

**Aucun backlog post-1.0.** Le gel de Picarones (§9) ferme la fenêtre de portage :
toute famille « gardée » non livrée dans la 1.0 est **perdue**. Les familles
gardées encore absentes de XerOCR sont donc des **tranches obligatoires** T19→T23
(plan détaillé en Phase B), chacune livrée entièrement (métrique + payload +
section + tests) :

| Tranche | Familles | Note |
|---|---|---|
| **T16** | NER | extra `[ner]`, recâblée anti-silence |
| **T19** | numerical_sequences, readability (Flesch) | ✅ copie fidèle |
| **T20** | abbreviations, early_modern + roman + modern_archives | 🔶 unifié au portage |
| **T21** | rare_tokens + lexical_mod + over_norm + equivalence | 🔶 famille « fidélité textuelle » unifiée |
| **T22** | robustness, image_quality | ✅/🔶 ; `image_predictive` abandonné |
| **T23** | inter_engine, error_absorption, line_metrics, change-point longitudinal | ✅/🔶 ; alignement ligne fiabilisé |

Seuls restent abandonnés les **8 (§3)** — jugés sans valeur même réparés, donc
aucune perte au gel.

---

## 7. Garde-fous anti-« syndrome Picarones » (appliqués à ce plan)

| Garde-fou | Comment ce plan le respecte |
|---|---|
| **1. Rupture nette, zéro shim** | Aucun pont vers un format Picarones ; `RunResult` unique. |
| **2. Budgets fichier** | Chaque nouveau fichier (ner, google_vision, azure_di, sections) sous 600 LOC ou entrée justifiée `test_file_budgets`. |
| **3. Pas de consommateur = supprimé** | Les 8 abandons (§3) sont retirés ; les familles **gardées** ne sont **pas** spéculatives — chacune reçoit son consommateur (sa section de rapport) et est livrée entièrement (T19→T23). Le gel de Picarones rend le portage-avant-1.0 nécessaire, pas « au cas où ». Pero/Calamari hors-dépôt (plugins de référence, §4). |
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
- [ ] **Parité moteurs** : Google+Azure first-party + Pero/Calamari plugins implémentés (T17, §4 acté) ; VLM zero_shot vérifié (T18).
- [ ] **Toutes les familles métriques gardées portées** (T19→T23) : numerical_sequences, readability, abbreviations, early_modern unifié, fidélité textuelle, robustness, image_quality, error_absorption, inter_engine, line_metrics, change-point longitudinal — chacune avec section + tests valeurs-main. Plus aucune famille gardée hors XerOCR.
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
B : T16 (NER) + T16-bis (jetons) → T17 (parité moteurs, §4 acté) → T18 (zero_shot)
    → T19 (num/lisibilité) → T20 (philologie) → T21 (fidélité textuelle)
    → T22 (robustesse/qualité image) → T23 (inter-moteurs/lignes)
C : S10 (rapport interactif) → S11 (galerie) → S12 (champs formulaire) → S13 (obs/a11y)
D : R1.0 (release 1.0.0) → GEL (gel Picarones)
```

**Tout est tranché, rien en attente.** Arbitrage §4 acté (Google+Azure
first-party, Pero+Calamari plugins). **Toutes les familles métriques gardées sont
des tranches obligatoires** (T19→T23) : la 1.0 est feature-complète vis-à-vis du
périmètre gardé, le gel de Picarones ne perd rien. **Point de départ : Phase A /
`S8`** (le manque n°1 — OCR réel gratuit sur le Space).
