"""Chaînes bilingues FR/EN de la coquille web (couche 8).

Rendu **serveur**, pas de SPA : la langue est choisie par le paramètre de
requête ``?lang=`` (défaut ``fr``) et les chaînes sont injectées dans le
gabarit Jinja2. Pas d'état, pas d'effet de bord — un simple dictionnaire de
données (réf. ``design/js/i18n.jsx``, porté au strict besoin de la coquille).
"""

from __future__ import annotations

#: Langues servies. ``fr`` est la primaire (cf. spec) ; tout autre code retombe
#: dessus via :func:`normalize_lang`.
LANGUAGES: tuple[str, ...] = ("fr", "en")
DEFAULT_LANG = "fr"

_STRINGS: dict[str, dict[str, str]] = {
    "fr": {
        "nav_library": "Bibliothèque",
        "nav_benchmark": "Banc d'essai",
        "nav_reports": "Rapports",
        "nav_segmentation": "Segmentation",
        "nav_history": "Historique",
        "nav_engines": "Moteurs",
        "wordmark_sub": "OCR · HTR · VLM",
        "soon": "à venir",
        "hero_eyebrow": "Vitrine · lecture seule",
        "hero_desc": "Rapports de benchmark déterministes — "
        "OCR / HTR / VLM sur corpus patrimoniaux.",
        "stat_reports": "rapports",
        "reports_title": "Rapports générés",
        "reports_desc": "Historique des benchmarks, rendus HTML autonomes.",
        # NB : la sous-chaîne « aucun rapport » est attendue par les tests.
        "reports_empty": "aucun rapport disponible pour l'instant.",
        "open_report": "Ouvrir",
        # Banc d'essai (lanceur interactif)
        "bench_eyebrow": "Banc d'essai · démonstration",
        "bench_title": "Banc d'essai",
        "bench_desc": "Lance un run de démonstration (corpus pré-calculé, sans clé) "
        "et suis sa progression en direct.",
        "bench_run": "Lancer la démonstration",
        "bench_launching": "Lancement…",
        "bench_status": "État",
        "bench_log": "Journal",
        "bench_idle": "Prêt.",
        "bench_net_error": "Erreur réseau.",
        "bench_corpus": "Corpus (ZIP)",
        "bench_upload": "Téléverser",
        "bench_corpus_none": "aucun corpus (démo)",
        "bench_engine": "Moteur",
        "open_report_full": "Ouvrir le rapport",
        "sys_status": "Système",
        "sys_version": "Version",
        "sys_mode": "Mode",
        "sys_mode_value": "vitrine · lecture seule",
        "sys_active_job": "Tâche active",
        "sys_idle": "au repos",
        # Page « Moteurs »
        "engines_eyebrow": "Vitrine · moteurs",
        "engines_title": "Moteurs",
        "engines_desc": "Disponibilité runtime des moteurs du socle (binaire · SDK · "
        "clé). Le mode public masque les moteurs cloud.",
        "stat_ready": "prêts",
        "engines_col_engine": "Moteur",
        "engines_col_status": "État",
        "engines_col_detail": "Détail",
        "engine_available": "disponible",
        "engine_unavailable": "indisponible",
        "history_eyebrow": "Vitrine · longitudinal",
        "history_title": "Historique",
        "history_desc": "Évolution des métriques par moteur au fil des runs ; "
        "régressions signalées entre les deux derniers runs.",
        "history_stat_runs": "mesures",
        "history_regressions_title": "Régressions",
        "history_regressions_desc": "Métriques dégradées entre les deux runs les "
        "plus récents (plus bas = meilleur).",
        "history_no_regressions": "Aucune régression détectée.",
        "history_log_title": "Journal des mesures",
        "history_log_desc": "Chaque agrégat enregistré, du plus récent au plus ancien.",
        "history_empty": "Aucun run enregistré pour l'instant.",
        "history_col_run": "Run",
        "history_col_pipeline": "Moteur",
        "history_col_view": "Vue",
        "history_col_metric": "Métrique",
        "history_col_value": "Valeur",
        "history_col_change": "Évolution",
        "lang_label": "Langue",
    },
    "en": {
        "nav_library": "Library",
        "nav_benchmark": "Benchmark",
        "nav_reports": "Reports",
        "nav_segmentation": "Segmentation",
        "nav_history": "History",
        "nav_engines": "Engines",
        "wordmark_sub": "OCR · HTR · VLM",
        "soon": "soon",
        "hero_eyebrow": "Showcase · read-only",
        "hero_desc": "Deterministic benchmark reports — "
        "OCR / HTR / VLM on heritage corpora.",
        "stat_reports": "reports",
        "reports_title": "Generated reports",
        "reports_desc": "Benchmark history, standalone HTML renders.",
        "reports_empty": "no report available yet.",
        "open_report": "Open",
        "bench_eyebrow": "Benchmark · demonstration",
        "bench_title": "Benchmark",
        "bench_desc": "Launch a demonstration run (pre-computed corpus, no key) "
        "and watch its progress live.",
        "bench_run": "Run the demonstration",
        "bench_launching": "Launching…",
        "bench_status": "Status",
        "bench_log": "Log",
        "bench_idle": "Ready.",
        "bench_net_error": "Network error.",
        "bench_corpus": "Corpus (ZIP)",
        "bench_upload": "Upload",
        "bench_corpus_none": "no corpus (demo)",
        "bench_engine": "Engine",
        "open_report_full": "Open the report",
        "sys_status": "System",
        "sys_version": "Version",
        "sys_mode": "Mode",
        "sys_mode_value": "showcase · read-only",
        "sys_active_job": "Active job",
        "sys_idle": "idle",
        "engines_eyebrow": "Showcase · engines",
        "engines_title": "Engines",
        "engines_desc": "Runtime availability of the built-in engines (binary · SDK · "
        "key). Public mode hides cloud engines.",
        "stat_ready": "ready",
        "engines_col_engine": "Engine",
        "engines_col_status": "Status",
        "engines_col_detail": "Detail",
        "engine_available": "available",
        "engine_unavailable": "unavailable",
        "history_eyebrow": "Showcase · longitudinal",
        "history_title": "History",
        "history_desc": "Per-engine metric evolution across runs; regressions "
        "flagged between the two most recent runs.",
        "history_stat_runs": "records",
        "history_regressions_title": "Regressions",
        "history_regressions_desc": "Metrics that worsened between the two most "
        "recent runs (lower is better).",
        "history_no_regressions": "No regression detected.",
        "history_log_title": "Measurement log",
        "history_log_desc": "Every recorded aggregate, most recent first.",
        "history_empty": "No run recorded yet.",
        "history_col_run": "Run",
        "history_col_pipeline": "Engine",
        "history_col_view": "View",
        "history_col_metric": "Metric",
        "history_col_value": "Value",
        "history_col_change": "Change",
        "lang_label": "Language",
    },
}


def normalize_lang(raw: str | None) -> str:
    """Code de langue servi : ``raw`` s'il est connu, sinon le défaut FR."""
    return raw if raw in LANGUAGES else DEFAULT_LANG


def strings_for(lang: str) -> dict[str, str]:
    """Dictionnaire de chaînes pour ``lang`` (normalisé)."""
    return _STRINGS[normalize_lang(lang)]


__all__ = ["DEFAULT_LANG", "LANGUAGES", "normalize_lang", "strings_for"]
