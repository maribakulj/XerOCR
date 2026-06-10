"""Glossaire pédagogique du rapport (DONNÉE, ≠ surface exécutable) — loader YAML.

Définitions FR/EN affichées en fin de rapport pour les **seules** métriques que
le moteur calcule (un consommateur réel par entrée). Lu **dynamiquement** du
paquet (jamais une liste statique — la leçon des profils de normalisation et des
prompts) ; repli FR si la langue demandée manque, ``{}`` non bloquant si même
``fr.yaml`` est illisible (le rapport omet alors le glossaire).

``__init__`` mince : aucune lecture au moment de l'import (le cache est lazy).
"""

from __future__ import annotations

import logging
from importlib import resources

import yaml

logger = logging.getLogger(__name__)

_SUFFIX = ".yaml"
_DEFAULT_LANG = "fr"
#: Cache lazy par langue (peuplé au premier appel, jamais à l'import).
_CACHE: dict[str, dict[str, dict[str, str]]] = {}


def _parse(text: str, lang: str) -> dict[str, dict[str, str]]:
    try:
        data = yaml.safe_load(text) or {}
    except yaml.YAMLError as e:
        logger.warning("[glossary] %s illisible (YAML) : %s", lang, e)
        return {}
    if not isinstance(data, dict):
        logger.warning("[glossary] %s n'est pas un mapping — ignoré", lang)
        return {}
    return {
        str(term): {str(k): str(v) for k, v in body.items()}
        for term, body in data.items()
        if isinstance(body, dict)
    }


def load_glossary(lang: str = _DEFAULT_LANG) -> dict[str, dict[str, str]]:
    """Glossaire ``{term: {title, definition, measures, limits}}`` pour ``lang``.

    Repli sur le français si la langue n'a pas de fichier ; ``{}`` (dégradé non
    bloquant) si même le français est absent/illisible.
    """
    if lang in _CACHE:
        return _CACHE[lang]
    path = resources.files(__name__).joinpath(f"{lang}{_SUFFIX}")
    if not path.is_file():
        result = {} if lang == _DEFAULT_LANG else load_glossary(_DEFAULT_LANG)
        _CACHE[lang] = result
        return result
    _CACHE[lang] = _parse(path.read_text(encoding="utf-8"), lang)
    return _CACHE[lang]


__all__ = ["load_glossary"]
