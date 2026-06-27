"""Formatage **localisé** des nombres *affichés* (couche 7).

Un rapport français écrit les décimales avec une **virgule** (« 12,3 % »), un
rapport anglais avec un **point** (« 12.3 % »). Ces helpers déterministes se
branchent sur ``SectionContext.lang`` et ne touchent **que l'affichage** —
jamais les coordonnées SVG (``svg.num``), les clés, ni les calculs.

Périmètre volontairement minimal : **séparateur décimal** uniquement (pas de
groupement de milliers — éviter l'ambiguïté typographique et le risque de
casser un nombre déjà rendu). Le point décimal d'un format Python devient une
virgule en français ; tout le reste est inchangé.
"""

from __future__ import annotations


def localize_decimal(text: str, lang: str) -> str:
    """Remplace le point décimal par une virgule en français (no-op sinon).

    Opère sur une chaîne **déjà formatée** : ``"12.3 %"`` → ``"12,3 %"`` (fr).
    N'introduit aucun groupement de milliers."""
    return text.replace(".", ",") if lang == "fr" else text


def fmt(value: float, lang: str, spec: str = ".2f") -> str:
    """Formate ``value`` via ``spec`` (mini-langage de format Python) puis
    localise le séparateur décimal. Ex. ``fmt(0.333, "fr", ".2f") == "0,33"``."""
    return localize_decimal(f"{value:{spec}}", lang)


def fmt_pct(
    value: float, lang: str, *, decimals: int = 1, scale: bool = True
) -> str:
    """Pourcentage affiché « X,Y % » (fr) / « X.Y % » (en).

    ``scale`` (défaut) multiplie par 100 (entrée ratio ``[0, 1]``) ; le passer à
    ``False`` si la valeur est **déjà** en points de pourcentage."""
    pct = value * 100 if scale else value
    return f"{localize_decimal(f'{pct:.{decimals}f}', lang)} %"


__all__ = ["fmt", "fmt_pct", "localize_decimal"]
