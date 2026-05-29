"""Source unique du fallback de version.

Vit dans la couche ``domain`` pour être importable depuis n'importe
quelle couche sans violer le sens des dépendances. Volontairement
minimal : aucun import, aucune logique.

``FALLBACK_VERSION`` est utilisé uniquement quand les deux sources
canoniques sont absentes :

1. ``xerocr/_version.py`` (généré au build par setuptools_scm) ;
2. ``importlib.metadata.version("xerocr")`` (paquet installé via pip).

Cohérence avec ``pyproject.toml`` : la valeur ci-dessous DOIT être
identique à ``[tool.setuptools_scm] fallback_version``. Vérifié par
``tests/architecture/test_single_version_source.py``.
"""

FALLBACK_VERSION = "0.1.0"
