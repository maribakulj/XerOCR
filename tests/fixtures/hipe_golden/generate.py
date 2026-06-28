"""Génère la fixture golden HIPE depuis le scorer officiel (Python ≥ 3.12).

Usage (poste Python ≥ 3.12) :
    pip install "hipe-ocrepair-scorer==0.9.9"
    python tests/fixtures/hipe_golden/generate.py
→ (ré)écrit ``input.jsonl`` + ``expected.json`` dans ce dossier. La parité de
notre chemin (profil ``hipe`` + ``cmer``) est ensuite vérifiée à 1e-9 par
``tests/evaluation/test_hipe_golden.py`` (qui tourne, lui, sur n'importe quel
Python — il recalcule, il n'exécute pas le scorer).

Le scorer officiel ne distribue **pas** de corpus d'exemple (seulement un schéma
JSON) : on score donc un **corpus synthétique contrôlé** (l'oracle reste le vrai
scorer v0.9.9 ; seules les entrées sont curées). Un seul ``primary_dataset_name``
→ ``averaged_scores`` = micro/macro globaux. Il couvre les comportements
documentés de ``norm()`` (§4.3) : diacritiques préservées, ligatures œ/æ/ß, ꝛ,
umlaut décomposé aͤ, césure DTA ``—\\n``, ponctuation → espace, casse, compactage,
+ cas dégénérés (réf vide, sortie vide).
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from hipe_ocrepair_scorer.ocrepair_eval import Evaluation

FIX = Path(__file__).resolve().parent  # tests/fixtures/hipe_golden/

# (document_id, ground_truth brut, ocr_hypothesis brut, ocr_postcorrection brut)
# La sortie « système » scorée = ocr_postcorrection_output.
CORPUS: list[tuple[str, str, str, str]] = [
    ("doc01_diacritic", "Le café est bon.", "Le caf3 est bon", "Le cafe est bon."),
    ("doc02_ligature_oe", "Œuvre complète", "Oeuvre complete", "Oeuvre complete"),
    ("doc03_eszett_umlaut", "Daß Wörter", "Dass Worter", "Dass Worter"),
    ("doc04_dta_hyphen", "Wört—\ner brisé", "Wort er brise", "Wört—\ner brisé"),
    ("doc05_punctuation", "a, b; c! (d)", "a b c d", "a b c d"),
    ("doc06_empty_output", "texte présent", "texte", ""),
    ("doc07_empty_gt", "", "abc", "abc"),
    ("doc08_archaic_r", "heꝛr Doctoꝛ", "herr Doctor", "herr Doctor"),
    ("doc09_decomposed", "Maͤnner koͤnig", "Manner konig", "Männer König"),
    ("doc10_multi_error", "Bonjour le monde", "B0nj0ur l3 m0nde", "Bonjur le mnde"),
    ("doc11_case_ws", "  PLEINE   Lune  ", "pleine lune", "Pleine Lune"),
    ("doc12_clean", "Stadt und Land", "Stadt und Land", "Stadt und Land"),
]


def _record(doc_id: str, gt: str, hyp: str, sysout: str) -> dict:
    """Enregistrement §4.8 valide (champs requis du schéma renseignés)."""
    return {
        "document_metadata": {
            "primary_dataset_name": "cinoc_golden",
            "primary_dataset_version": "1.0",
            "primary_dataset_license": "CC0",
            "benchmark_dataset_name": "cinoc_golden",
            "benchmark_dataset_split": "test",
            "document_type": "synthetic",
            "document_id": doc_id,
            "date": "2026-01-01",
            "language": "mul",
            "transcription_unit_scope": "page",
        },
        "ground_truth": {
            "transcription_unit": gt,
            "num_tokens": len(gt.split()),
            "num_chars": len(gt),
        },
        "ocr_hypothesis": {
            "transcription_unit": hyp,
            "num_tokens": len(hyp.split()),
            "num_chars": len(hyp),
        },
        "ocr_postcorrection_output": {
            "transcription_unit": sysout,
            "num_tokens": len(sysout.split()),
            "num_chars": len(sysout),
        },
    }


def main() -> None:
    records = [_record(d, gt, hyp, s) for d, gt, hyp, s in CORPUS]

    # Scorer officiel — passer un deepcopy (il mute les records : _normalized keys).
    evaluation = Evaluation(deepcopy(records))
    results = evaluation.score_over_datasets(normalize=True)
    averaged = results["averaged_scores"]
    cmer_micro = float(averaged["cmer_micro"][0])
    cmer_macro = float(averaged["cmer_macro"][0])

    FIX.mkdir(parents=True, exist_ok=True)
    with (FIX / "input.jsonl").open("w", encoding="utf-8") as fh:
        for record in records:  # originaux NON mutés
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    (FIX / "expected.json").write_text(
        json.dumps(
            {"system": {"cmer_micro": cmer_micro, "cmer_macro": cmer_macro}},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"cmer_micro = {cmer_micro!r}")
    print(f"cmer_macro = {cmer_macro!r}")
    print(f"input.jsonl: {len(records)} records → {FIX/'input.jsonl'}")


if __name__ == "__main__":
    main()
