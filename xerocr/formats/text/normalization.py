"""Normalisation de texte pour les métriques de similarité (CER/WER, CER diplomatique).

Un ``NormalizationProfile`` est un **objet-valeur autonome** (immuable) appliqué
**symétriquement** à la vérité-terrain et à l'hypothèse avant comparaison. La même
transformation des deux côtés mesure les erreurs « substantielles » en neutralisant
des équivalences choisies (graphies historiques, casse, ponctuation, espaces…).

Le profil ne s'applique **jamais** au niveau ``ENTITIES`` (offsets caractère) ni aux
métriques patrimoniales sur la graphie brute (MUFI, typographie) — voir le plan
couche 2.

Ordre canonique de ``normalize`` (figé, vérifié par tests) ::

    hygiène → unicode_form → casefold(si caseless) → exclude_chars
            → diplomatic_table → strip_diacritics → whitespace

Sous ``caseless`` le casefold précède la table, et les clés de table comme
l'ensemble exclu sont casefoldés pour la correspondance (sinon la casse ne serait
pas neutralisée). Le casefold pouvant dé-normaliser, on ré-applique ``unicode_form``
après lui.

La substitution diplomatique est faite en **un seul passage** (alternation regex,
clé la plus longue d'abord) : aucune cascade possible quelle que soit la table
(``{"u": "v", "v": "u"}`` sur ``"uv"`` donne ``"vu"``, pas ``"vv"``).
"""

from __future__ import annotations

import logging
import re
import unicodedata
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

logger = logging.getLogger(__name__)

UnicodeForm = Literal["none", "NFC", "NFD", "NFKC", "NFKD"]
WhitespaceMode = Literal["none", "intra_line", "flat"]
ExcludeMode = Literal["delete", "space"]

#: Caractères de contrôle conservés (pris en charge par le levier ``whitespace``).
_KEEP_CONTROL = frozenset("\t\n\r\f\v")


# ---------------------------------------------------------------------------
# Tables diplomatiques préconfigurées (données ; français + latin)
# ---------------------------------------------------------------------------

#: Français médiéval (XIIe–XVe). Appliquée des deux côtés → CER sur les classes
#: d'équivalence graphiques (quotient), non biaisé même pour u/v (non positionnel).
DIPLOMATIC_FR_MEDIEVAL: dict[str, str] = {
    "ſ": "s",
    "u": "v",
    "i": "j",
    "y": "i",
    "æ": "ae",
    "œ": "oe",
    "ꝑ": "per",
    "ꝓ": "pro",
    "&": "et",
}

#: Français imprimé ancien (XVIe–XVIIIe).
DIPLOMATIC_FR_EARLY_MODERN: dict[str, str] = {
    "ſ": "s",
    "æ": "ae",
    "œ": "oe",
    "&": "et",
    "ỹ": "yn",
}

#: Latin médiéval.
DIPLOMATIC_LATIN_MEDIEVAL: dict[str, str] = {
    "ſ": "s",
    "u": "v",
    "i": "j",
    "y": "i",
    "æ": "ae",
    "œ": "oe",
    "ꝑ": "per",
    "ꝓ": "pro",
    "ꝗ": "que",
    "&": "et",
}

#: Minimal : NFC + s long.
DIPLOMATIC_MINIMAL: dict[str, str] = {"ſ": "s"}

#: Ponctuation courante (pour le profil ``no_punctuation``).
_PUNCTUATION = ".,;:!?'’\"-–—()[]«»…"


# ---------------------------------------------------------------------------
# Helpers de transformation (purs)
# ---------------------------------------------------------------------------


def _parse_exclude_chars(value: Any) -> frozenset[str]:
    """Convertit l'entrée utilisateur en ensemble de caractères à exclure.

    - chaîne → ensemble de **ses caractères** (aucun séparateur magique) ;
    - liste/ensemble → items (chacun **un seul** codepoint) ;
    - ``None`` / vide → ensemble vide.

    Un item multi-codepoint relève de la substitution (table), pas de l'exclusion :
    il est ignoré avec un avertissement.
    """
    if not value:
        return frozenset()
    items: list[str]
    if isinstance(value, (list, tuple, set, frozenset)):
        items = [str(c) for c in value]
    else:
        items = list(str(value))
    out: set[str] = set()
    for item in items:
        if len(item) != 1:
            logger.warning(
                "[normalization] exclude_chars ignore %r (pas un caractère unique)",
                item,
            )
            continue
        out.add(item)
    return frozenset(out)


def _normalize_form(text: str, form: UnicodeForm) -> str:
    if form == "none":
        return text
    return unicodedata.normalize(form, text)


def _strip_invisible(text: str) -> str:
    """Retire les caractères invisibles : format (soft-hyphen, zero-width, BOM,
    marques directionnelles) et contrôle, en conservant ``\\t\\n\\r\\f\\v``."""
    out: list[str] = []
    for char in text:
        category = unicodedata.category(char)
        if category == "Cf":
            continue
        if category == "Cc" and char not in _KEEP_CONTROL:
            continue
        out.append(char)
    return "".join(out)


def _apply_table(text: str, table: dict[str, str]) -> str:
    """Substitution simultanée en un seul passage (clé la plus longue d'abord)."""
    if not table:
        return text
    keys = sorted(table, key=len, reverse=True)
    pattern = re.compile("|".join(re.escape(k) for k in keys))
    return pattern.sub(lambda m: table[m.group(0)], text)


def _strip_diacritics(text: str, form: UnicodeForm) -> str:
    """NFD → suppression des marques combinantes (catégorie ``Mn``) → forme cible."""
    decomposed = unicodedata.normalize("NFD", text)
    stripped = "".join(c for c in decomposed if unicodedata.category(c) != "Mn")
    return _normalize_form(stripped, form)


# ---------------------------------------------------------------------------
# Profil
# ---------------------------------------------------------------------------


class NormalizationProfile(BaseModel):
    """Stratégie de normalisation immuable, appliquée symétriquement GT/OCR."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    unicode_form: UnicodeForm = "NFC"
    caseless: bool = False
    whitespace: WhitespaceMode = "none"
    strip_diacritics: bool = False
    diplomatic_table: dict[str, str] = Field(default_factory=dict)
    exclude_chars: frozenset[str] = Field(default_factory=frozenset)
    exclude_mode: ExcludeMode = "delete"
    description: str = ""

    @field_validator("exclude_chars", mode="before")
    @classmethod
    def _coerce_exclude(cls, value: Any) -> frozenset[str]:
        return _parse_exclude_chars(value)

    @field_validator("diplomatic_table")
    @classmethod
    def _check_table(cls, value: dict[str, str]) -> dict[str, str]:
        if any(not key for key in value):
            raise ValueError("clé de table diplomatique vide interdite")
        return value

    # -- application --------------------------------------------------------

    def normalize(self, text: str) -> str:
        """Applique le profil (ordre canonique figé)."""
        text = _strip_invisible(text)
        text = _normalize_form(text, self.unicode_form)
        if self.caseless:
            text = _normalize_form(text.casefold(), self.unicode_form)
        if self.exclude_chars:
            text = self._apply_exclude(text)
        if self.diplomatic_table:
            text = _apply_table(text, self._effective_table())
        if self.strip_diacritics:
            text = _strip_diacritics(text, self.unicode_form)
        return self._apply_whitespace(text)

    def _effective_chars(self) -> frozenset[str]:
        if not self.caseless:
            return self.exclude_chars
        folded: set[str] = set()
        for char in self.exclude_chars:
            cf = char.casefold()
            if len(cf) == 1:
                folded.add(cf)
            else:
                logger.warning(
                    "[normalization] exclude %r : casefold multi-codepoint, ignoré",
                    char,
                )
        return frozenset(folded)

    def _apply_exclude(self, text: str) -> str:
        chars = self._effective_chars()
        replacement = " " if self.exclude_mode == "space" else ""
        return "".join(replacement if c in chars else c for c in text)

    def _effective_table(self) -> dict[str, str]:
        if not self.caseless:
            return self.diplomatic_table
        return {k.casefold(): v.casefold() for k, v in self.diplomatic_table.items()}

    def _apply_whitespace(self, text: str) -> str:
        if self.whitespace == "none":
            return text
        if self.whitespace == "flat":
            return re.sub(r"\s+", " ", text).strip()
        # intra_line : normalise les espaces dans chaque ligne, garde les sauts.
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        lines = [re.sub(r"\s+", " ", line).strip() for line in text.split("\n")]
        return "\n".join(lines).strip("\n")

    # -- sérialisation / construction --------------------------------------

    def as_dict(self) -> dict[str, Any]:
        """Forme sérialisée déterministe (clés et exclusions triées)."""
        return {
            "name": self.name,
            "unicode_form": self.unicode_form,
            "caseless": self.caseless,
            "whitespace": self.whitespace,
            "strip_diacritics": self.strip_diacritics,
            "diplomatic_table": dict(sorted(self.diplomatic_table.items())),
            "exclude_chars": sorted(self.exclude_chars),
            "exclude_mode": self.exclude_mode,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NormalizationProfile:
        """Construit un profil depuis un dict (clés inconnues → erreur de validation).

        Sucre rétro-compatible : ``nfc: bool`` → ``unicode_form``, et ``diplomatic``
        comme alias de ``diplomatic_table``. ``unicode_form`` explicite l'emporte.
        """
        fields = dict(data)
        nfc = fields.pop("nfc", None)
        if "unicode_form" not in fields and nfc is not None:
            fields["unicode_form"] = "NFC" if nfc else "none"
        diplomatic = fields.pop("diplomatic", None)
        if "diplomatic_table" not in fields and diplomatic is not None:
            fields["diplomatic_table"] = diplomatic
        fields.setdefault("name", "custom")
        return cls(**fields)

    @classmethod
    def from_yaml(cls, path: str | Path) -> NormalizationProfile:
        """Charge un profil depuis un fichier YAML (usage CLI/local uniquement).

        Ne jamais exposer un chemin fourni par une entrée non fiable (lecture
        de fichier arbitraire).
        """
        import yaml  # type: ignore[import-untyped]

        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        if not isinstance(raw, dict):
            raise ValueError(f"profil YAML invalide (objet attendu) : {path}")
        raw.setdefault("name", Path(path).stem)
        return cls.from_dict(raw)


# ---------------------------------------------------------------------------
# Profils préconfigurés (12) — défaut neutre ``nfc``, aucun profil privilégié
# ---------------------------------------------------------------------------

NORMALIZATION_PROFILES: dict[str, NormalizationProfile] = {
    p.name: p
    for p in (
        NormalizationProfile(name="nfc", description="NFC seul (neutre)"),
        NormalizationProfile(
            name="nfkc", unicode_form="NFKC", description="NFKC (ligatures ﬁﬂ…)"
        ),
        NormalizationProfile(
            name="caseless", caseless=True, description="NFC + insensible à la casse"
        ),
        NormalizationProfile(
            name="minimal",
            diplomatic_table=DIPLOMATIC_MINIMAL,
            description="NFC + s long",
        ),
        NormalizationProfile(
            name="no_diacritics",
            strip_diacritics=True,
            description="NFC + pliage des diacritiques (é→e)",
        ),
        NormalizationProfile(
            name="flat_text",
            whitespace="flat",
            description="NFC + comparaison à plat (espaces et sauts écrasés)",
        ),
        NormalizationProfile(
            name="keep_line_breaks",
            whitespace="intra_line",
            description="NFC + espaces normalisés, sauts de ligne conservés",
        ),
        NormalizationProfile(
            name="no_punctuation",
            exclude_chars=_PUNCTUATION,  # type: ignore[arg-type]
            exclude_mode="space",
            description="NFC + ponctuation ignorée (remplacée par une espace)",
        ),
        NormalizationProfile(
            name="no_apostrophes",
            exclude_chars="'’",  # type: ignore[arg-type]
            exclude_mode="delete",
            description="NFC + apostrophes droite (') et typographique (’) ignorées",
        ),
        NormalizationProfile(
            name="medieval_french",
            diplomatic_table=DIPLOMATIC_FR_MEDIEVAL,
            description="Français médiéval : ſ=s, u=v, i=j, æ=ae, œ=oe…",
        ),
        NormalizationProfile(
            name="early_modern_french",
            diplomatic_table=DIPLOMATIC_FR_EARLY_MODERN,
            description="Français imprimé ancien : ſ=s, æ=ae, œ=oe…",
        ),
        NormalizationProfile(
            name="medieval_latin",
            diplomatic_table=DIPLOMATIC_LATIN_MEDIEVAL,
            description="Latin médiéval : ſ=s, u=v, i=j, ꝑ=per, ꝓ=pro, ꝗ=que…",
        ),
    )
}

#: Profil par défaut : neutre, sans table culturelle.
DEFAULT_PROFILE: NormalizationProfile = NORMALIZATION_PROFILES["nfc"]


def get_builtin_profile(name: str) -> NormalizationProfile:
    """Retourne un profil préconfiguré, ou lève ``KeyError`` (message explicite)."""
    try:
        return NORMALIZATION_PROFILES[name]
    except KeyError:
        available = ", ".join(sorted(NORMALIZATION_PROFILES))
        raise KeyError(
            f"profil de normalisation inconnu : {name!r}. Disponibles : {available}"
        ) from None
