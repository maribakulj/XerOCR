"""Marqueurs des **archives modernes** (XIXᵉ-XXᵉ) — données + détection (couche 3).

Là où le médiéval scribal (`markers.ABBREVIATIONS`) et l'imprimé ancien
(`markers.EARLY_MODERN`) couvrent les écritures historiques, ce module couvre les
conventions d'abréviation des corpus institutionnels modernes : titres de
civilité (``Mme``, ``Dr``), ordinaux (``1ᵉʳ``, ``XIXᵉ``), monnaies, abréviations
administratives, état civil, ponctuation typographique, abréviations latines,
bibliographie, adresses. Neuf **catégories**, ~70 marqueurs.

Pourquoi un module dédié (≠ `markers.family_counts`) : ces marqueurs sont
**multi-caractères** et exigent une **frontière de mot adaptée** (``M.`` ne doit
pas matcher dans ``M.A.``, ``arr.`` pas dans ``arracher``) — un simple
``str.count`` les sur-compterait. La détection est donc **regex bornée** +
**plus-long-gagne** (``S.A.R.`` plutôt que ``S.`` + ``A.R.``).

Sémantique : **containment multiset** (comme `markers`), deux lentilles —
*strict* (la forme abrégée survit) / *expansion* (forme **ou** développement,
borne optimiste). On compte les **occurrences** (multiset), pas une simple
présence : une présence-par-occurrence gonflerait le score quand un ``Mme``
devient ``Mlle`` sans le pénaliser. Tables = **constantes de module** (donnée,
comme les profils de normalisation). Catégorie sans signe en GT → omise
(adaptatif).
"""

from __future__ import annotations

import re
from collections import Counter

#: ``(forme abrégée canonique, développements acceptés)`` par catégorie.
#: Développements insensibles à la casse ; formes abrégées sensibles à la casse.
CIVILITY_TITLES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Mme", ("Madame",)),
    ("Mlle", ("Mademoiselle",)),
    ("Mgr", ("Monseigneur",)),
    ("Dr", ("Docteur",)),
    ("Pr", ("Professeur",)),
    ("Me", ("Maître",)),
    ("M.", ("Monsieur",)),
    ("R.P.", ("Révérend Père",)),
    ("S.M.", ("Sa Majesté",)),
    ("S.A.R.", ("Son Altesse Royale",)),
    ("S.E.", ("Son Excellence",)),
    ("S.S.", ("Sa Sainteté",)),
)

ORDINALS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("1ᵉʳ", ("1er", "premier")),
    ("1ʳᵉ", ("1re", "première", "premiere")),
    ("2ᵈ", ("2d", "second")),
    ("2ᵈᵉ", ("2de", "seconde")),
    ("2ᵉ", ("2e", "deuxième", "deuxieme")),
    ("3ᵉ", ("3e", "troisième", "troisieme")),
    ("Iᵉʳ", ("Ier", "premier")),
    ("Vᵉ", ("Ve", "cinquième", "cinquieme")),
    ("XIᵉ", ("XIe", "onzième", "onzieme")),
    ("XIIᵉ", ("XIIe", "douzième", "douzieme")),
    ("XVIᵉ", ("XVIe", "seizième", "seizieme")),
    ("XVIIᵉ", ("XVIIe", "dix-septième", "dix-septieme")),
    ("XVIIIᵉ", ("XVIIIe", "dix-huitième", "dix-huitieme")),
    ("XIXᵉ", ("XIXe", "dix-neuvième", "dix-neuvieme")),
    ("XXᵉ", ("XXe", "vingtième", "vingtieme")),
)

CURRENCY: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("₶", ("livre tournois", "livres tournois")),
    ("₣", ("franc", "francs")),
    ("ƒ", ("florin", "florins")),
    ("£", ("livre", "livres", "pound", "pounds")),
    ("l.", ("livre", "livres")),
    ("s.", ("sol", "sols", "sou", "sous")),
    ("d.", ("denier", "deniers")),
)

ADMINISTRATIVE: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("arr.", ("arrondissement",)),
    ("dép.", ("département", "departement")),
    ("cant.", ("canton",)),
    ("com.", ("commune",)),
    ("reg.", ("régiment", "regiment")),
    ("prov.", ("province",)),
)

CIVIL_STATUS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("°", ("né", "née")),
    ("†", ("mort", "morte", "décédé", "décédée")),
    ("✶", ("naissance",)),
    ("⚭", ("marié", "mariée", "épousa", "epousa")),
    ("ép.", ("épouse", "époux", "epouse", "epoux")),
    ("vve", ("veuve",)),
)

TYPOGRAPHIC_PUNCTUATION: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("«", ('"',)),
    ("»", ('"',)),
    ("—", ("-", "--")),
    ("–", ("-",)),
    ("…", ("...",)),
    ("’", ("'",)),
    ("‘", ("'",)),
)

LATIN_ABBR_MODERN: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("e.g.", ("for example", "par exemple", "exempli gratia")),
    ("i.e.", ("c'est-à-dire", "id est", "that is")),
    ("etc.", ("et cetera", "et caetera")),
    ("cf.", ("confer", "voir")),
    ("ibid.", ("ibidem",)),
    ("op. cit.", ("opere citato", "opus citatum")),
    ("ad lib.", ("ad libitum",)),
    ("N.B.", ("nota bene",)),
)

BIBLIOGRAPHIC: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("vol.", ("volume",)),
    ("t.", ("tome",)),
    ("p.", ("page",)),
    ("pp.", ("pages",)),
    ("n°", ("numéro", "numero", "no")),
    ("fasc.", ("fascicule",)),
    ("éd.", ("édition", "edition")),
    ("ms.", ("manuscrit",)),
    ("f.", ("folio",)),
    ("r°", ("recto",)),
    ("v°", ("verso",)),
)

ADDRESS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("bd", ("boulevard",)),
    ("av.", ("avenue",)),
    ("r.", ("rue",)),
    ("pl.", ("place",)),
    ("imp.", ("impasse",)),
    ("fbg", ("faubourg",)),
)

#: Catégories dans l'ordre canonique de rendu (déterministe).
_CATEGORIES: dict[str, tuple[tuple[str, tuple[str, ...]], ...]] = {
    "civility_titles": CIVILITY_TITLES,
    "ordinals": ORDINALS,
    "currency": CURRENCY,
    "administrative": ADMINISTRATIVE,
    "civil_status": CIVIL_STATUS,
    "typographic_punctuation": TYPOGRAPHIC_PUNCTUATION,
    "latin_abbr_modern": LATIN_ABBR_MODERN,
    "bibliographic": BIBLIOGRAPHIC,
    "address": ADDRESS,
}

#: Ordre canonique des catégories — consommé par le collecteur pour l'affichage.
CATEGORY_ORDER: tuple[str, ...] = tuple(_CATEGORIES)

#: Tous les marqueurs (forme, développements, catégorie), triés par longueur
#: décroissante : la détection préfère le plus long (``S.A.R.`` avant ``S.``).
_ALL_MARKERS: list[tuple[str, tuple[str, ...], str]] = sorted(
    (
        (marker, expansions, category)
        for category, entries in _CATEGORIES.items()
        for marker, expansions in entries
    ),
    key=lambda triple: -len(triple[0]),
)

#: Marqueur → catégorie (un marqueur n'appartient qu'à une catégorie).
_MARKER_CATEGORY: dict[str, str] = {
    marker: category for marker, _exp, category in _ALL_MARKERS
}

# Frontières explicites pour les marqueurs à point (le ``.`` final étant non-mot,
# ``\b`` standard matcherait dans « arr.acher ») : début/fin/blanc/ponctuation.
_TRAILING_BOUNDARY = r"(?=$|[\s,;:!?\)\]\»\"'\n\r\t…])"
_LEADING_BOUNDARY = r"(?:^|(?<=[\s,;:!?\(\[\«\"'\n\r\t]))"


def _is_ascii_alnum(text: str) -> bool:
    """Vrai si tous les caractères sont alphanumériques ASCII."""
    return bool(text) and all(c.isascii() and c.isalnum() for c in text)


def _compile_marker(marker: str) -> re.Pattern[str]:
    """Pattern de détection (frontière adaptée à la composition du marqueur)."""
    escaped = re.escape(marker)
    if "." in marker:
        return re.compile(_LEADING_BOUNDARY + escaped + _TRAILING_BOUNDARY)
    if _is_ascii_alnum(marker):
        return re.compile(r"\b" + escaped + r"\b")
    # Unicode (exposants, monnaies, guillemets, croix) : littéral, pas de ``\b``.
    return re.compile(escaped)


def _compile_expansions(expansions: tuple[str, ...]) -> tuple[re.Pattern[str], ...]:
    """Patterns des développements (insensibles à la casse ; ``\\b`` si alnum)."""
    out: list[re.Pattern[str]] = []
    for exp in expansions:
        escaped = re.escape(exp)
        if _is_ascii_alnum(exp):
            out.append(re.compile(r"\b" + escaped + r"\b", re.IGNORECASE))
        else:
            out.append(re.compile(escaped, re.IGNORECASE))
    return tuple(out)


_MARKER_PATTERNS: dict[str, re.Pattern[str]] = {
    marker: _compile_marker(marker) for marker, _exp, _cat in _ALL_MARKERS
}
_EXPANSION_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    marker: _compile_expansions(expansions) for marker, expansions, _cat in _ALL_MARKERS
}


def _detect(text: str) -> list[tuple[int, str]]:
    """Marqueurs non chevauchants de ``text`` : ``[(start, marker), ...]``.

    Stratégie **plus-long-gagne** à chaque position (tri ``(start, -longueur)``).
    """
    candidates: list[tuple[int, int, str]] = []
    for marker, pattern in _MARKER_PATTERNS.items():
        for match in pattern.finditer(text):
            candidates.append((match.start(), match.end(), marker))
    candidates.sort(key=lambda c: (c[0], -(c[1] - c[0])))
    chosen: list[tuple[int, str]] = []
    last_end = -1
    for start, end, marker in candidates:
        if start < last_end:
            continue
        chosen.append((start, marker))
        last_end = end
    return chosen


def archival_counts(
    reference: str, hypothesis: str
) -> dict[str, tuple[int, int, int]]:
    """Préservation par catégorie présente dans la GT (containment multiset).

    Pour chaque catégorie présente : ``(n_total, n_strict, n_expansion)`` —
    ``n_strict = Σ min(occurrences GT, occurrences hyp)`` du signe (frontière
    adaptée) ; ``n_expansion`` ajoute les développements trouvés dans l'hyp,
    capé au total GT (borne optimiste). Catégories absentes de la GT → omises.
    """
    gt = Counter(marker for _start, marker in _detect(reference))
    if not gt:
        return {}
    hyp = Counter(marker for _start, marker in _detect(hypothesis))
    totals: dict[str, list[int]] = {}
    for marker, gt_n in gt.items():
        category = _MARKER_CATEGORY[marker]
        strict = min(gt_n, hyp.get(marker, 0))
        expansion_hits = sum(
            len(pattern.findall(hypothesis))
            for pattern in _EXPANSION_PATTERNS[marker]
        )
        expansion = min(gt_n, hyp.get(marker, 0) + expansion_hits)
        slot = totals.setdefault(category, [0, 0, 0])
        slot[0] += gt_n
        slot[1] += strict
        slot[2] += expansion
    return {cat: (t, s, e) for cat, (t, s, e) in totals.items()}


__all__ = ["CATEGORY_ORDER", "archival_counts"]
