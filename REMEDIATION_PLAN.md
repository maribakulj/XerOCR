# REMEDIATION_PLAN.md — durcissement post-audit (sans bricolage)

> Plan de correction issu de l'**audit impitoyable** de la session T7/S6 (cf.
> `MIGRATION_PLAN.md` journal **D-050**). Principe : chaque item est soit
> **corrigé proprement avec test** + **suite complète verte** avant push, soit
> **accepté explicitement** avec justification (jamais un silence). Tranches
> verticales, une chose à la fois.
>
> **Décisions produit actées** (utilisateur) :
> - **D1** = type domaine dédié pour l'OCR-référence (≠ GT manuelle).
> - **D2** = import HuggingFace **matérialisé**, **convention XerOCR seule** +
>   **streaming** (pas de snapshot local complet).
> - **D3** = vérification distante par **cassettes enregistrées** (rejouables, CI).

## Déjà corrigé (D-050, mergé dans `main`)
- [x] Fuite de jeton sur **redirection cross-hôte** (`_http`) — strip si l'hôte change + test.
- [x] Fuite de jeton via **`next` eScriptorium cross-hôte** — refus hors hôte.
- [x] **Décalage page Gallica** (canvas sauté) — vue lue dans l'URL `/f{n}/` + test qui échoue sur l'ancien code.
- [x] **Déterminisme régressions** — `ORDER BY …, run_id`.
- [x] `mufi_err` chevauchait `diacritic_err` (bloc combinant retiré).
- [x] `_extract_label` pouvait renvoyer non-`str`.
- [x] `materialize` testé en direct ; page `/history` bornée.

## Lots restants (ordre d'exécution)

### Lot 0 — Garde-fou process ✅ (ce commit)
- [x] `make ci` (= `make check` : ruff + mypy + **pytest complet**).
- [x] Règle écrite (`CLAUDE.md §11`) : **jamais rapporter « vert » sur un sous-ensemble** ; `make check` obligatoire avant tout push. *(Cause racine de la CI rouge non vue pendant 11 commits.)*

### Lot A — Sécurité : anti-DNS-rebinding réel (#2) ✅ (D-051)
- [x] Résoudre **une fois** → valider → **connecter à l'IP épinglée**. Implémenté par un `network_backend` `httpcore` custom (`_PinnedBackend`) : l'URL (donc `Host` + **SNI** + vérif. de certificat TLS) reste **inchangée** ; seule la cible TCP est figée sur l'IP validée. Pas d'override SNI-sur-IP fragile → le risque TLS noté ci-dessous **ne se présente pas**. Ré-épinglage par redirection (`_stream_validated`, client par saut).
- [x] Test : `getaddrinfo` mocké (public à la validation, loopback ensuite) → la connexion vise l'IP **validée** (interception de la cible réelle du transport) + une **seule** résolution DNS (`test_connection_pins_validated_ip_not_rebind`). Non-régression SSRF + redirect-auth verte.
- Risque TLS/SNI : **évité** (URL/Host/SNI préservés, seule la cible TCP change). `httpcore` ajouté à la whitelist archi adapters + aux extras (`httpx` le co-installe).

### Lot B — Robustesse transport ✅ (D-052)
- [x] **B1** `download` en **flux disque** (`.part` au fil de l'eau, cap `IMAGE_MAX_BYTES`, `os.replace` atomique, `.part` supprimé sur toute erreur → pas de fichier partiel). Plus de buffer RAM intégral (limite assumée de D-050 levée).
- [x] **B2** média eScriptorium : `download` accepte `headers` ; `import_escriptorium_corpus` ne joint le jeton qu'à un média **même-hôte** que `base_url` (règle host de D-050) — média sur hôte tiers (CDN) téléchargé sans jeton (+ `_stream_validated` strip cross-hôte sur redirection en défense en profondeur).

### Lot C — Domaine : type « OCR-référence » (D1) ✅ (D-053)
- [x] `ArtifactType.REFERENCE_TEXT` (couche 1) ; Gallica écrit `GroundTruthRef(REFERENCE_TEXT)` (+ `gt_source=gallica_ocr`).
- [x] **Évaluation** : une GT `REFERENCE_TEXT` **n'est pas scorée** par une vue par défaut (la vue `text` ne déclare pas la projection → GT ignorée, pas de faux score d'exactitude). **Matérialisé de bout en bout** (≠ type dormant) : vue *référence* dédiée (opt-in via projection `reference_text → raw_text`, projecteur `identity_text`), **construite automatiquement** par `_views_for_corpus` quand le corpus porte une GT `REFERENCE_TEXT` → **rapport distinct** (le nom de la vue porte l'avertissement « pas une vérité-terrain manuelle », rendu tel quel par le rapport).
- [x] Round-trip JSON (valeur `reference_text` stable) ; golden démo inchangé (corpus précalculé = GT manuelle `RAW_TEXT`, non concerné).

### Lot D — Import HuggingFace (D2 : convention XerOCR + streaming)
- [ ] Doc **convention XerOCR** (schéma : `image`, `ground_truth`, opt. `segmentation`).
- [ ] Adapter via lib `datasets` (**extra `[huggingface]`**, `streaming=True`) → corpus de travail page-par-page (pas de snapshot).
- [ ] Service `app.import_hf_corpus` + endpoint `/api/corpus/import/huggingface` (CSRF, **gate public 403**) ; dataset non conforme → 422 clair.
- [ ] GT d'un dataset XerOCR curé = **vraie GT** (`RAW_TEXT`).

### Lot E — Vérification cassettes (D3) + fixture Gallica réelle
- [ ] Script de capture (réseau ouvert, **hors sandbox**) → fixtures (IIIF/Gallica `texteBrut`/eScriptorium/HF).
- [ ] Transport « replay » déterministe → valide le **parsing réel** + l'hypothèse Gallica `/f{n}/`.
- ⚠️ **Dépendance** : capture impossible dans le sandbox actuel (allowlist) → nécessite un environnement réseau (ou exécution du script par l'utilisateur).

### Lot F — UX / scalabilité
- [ ] **F1** cache TTL des catalogues découverte (fin du fetch par chargement `/library`).
- [ ] **F3** atomicité import : nettoyage du dossier partiel sur échec.
- [ ] **F2** *(optionnel, gros)* import = job de fond (infra runs : annulable, SSE) si gros corpus visés.

### Lot G — Housekeeping
- [ ] Vérifier/narrower les `except Exception` de `jobs.py`.
- [ ] Accepts mineurs **documentés** : HF `results[:limit]` (#9), pk non-int + warning (#14), `errors=replace` OCR (#15), insert non compté `mufi_err` (#17).

## Contraintes honnêtes
- **Lot E** (cassettes) + toute vraie validation distante : **impossible dans ce sandbox** (allowlist réseau).
- **Lot A** : pinning IP réel si SNI propre ; sinon accept documenté (gate public).
