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
        "sys_status": "Système",
        "sys_version": "Version",
        "sys_mode": "Mode",
        "sys_mode_value": "vitrine · lecture seule",
        "sys_active_job": "Tâche active",
        "sys_idle": "au repos",
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
        "sys_status": "System",
        "sys_version": "Version",
        "sys_mode": "Mode",
        "sys_mode_value": "showcase · read-only",
        "sys_active_job": "Active job",
        "sys_idle": "idle",
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
