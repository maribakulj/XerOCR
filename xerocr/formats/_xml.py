"""Parsing XML sécurisé — entonnoir unique de la couche formats.

Tout XML entrant (ALTO, PAGE, manifeste…) passe par ``safe_parse_xml``. Le parseur
lxml est durci contre :

- **XXE** (entités externes) et **billion laughs** : ``resolve_entities=False`` —
  les entités ne sont jamais expansées ;
- **récupération de DTD distante** : ``no_network=True`` + ``load_dtd=False`` ;
- toute **DTD / DOCTYPE** : rejet explicite (équivalent ``forbid_dtd``).

Retourne ``None`` si le contenu n'est pas un XML bien formé, contient un DOCTYPE,
ou déclenche une protection. Le caller (parser ALTO/PAGE) lève alors son erreur.

Un parseur **neuf est créé à chaque appel** : les instances ``XMLParser`` de lxml
ne sont pas sûres en usage concurrent (le runner est multi-thread).
"""

from __future__ import annotations

from lxml import etree

__all__ = ["safe_parse_xml"]


def safe_parse_xml(data: bytes) -> etree._Element | None:
    """Parse des octets XML de façon sécurisée, ou retourne ``None``."""
    parser = etree.XMLParser(
        resolve_entities=False,
        no_network=True,
        load_dtd=False,
        dtd_validation=False,
        huge_tree=False,
    )
    try:
        root = etree.fromstring(data, parser=parser)
    except etree.XMLSyntaxError:
        return None
    if root is None:
        return None
    doctype = root.getroottree().docinfo.doctype  # type: ignore[union-attr]
    if doctype:
        return None  # DTD / DOCTYPE interdit
    return root
