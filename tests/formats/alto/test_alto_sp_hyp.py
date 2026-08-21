"""``SP`` et ``HYP`` : les deux enfants de ``<TextLine>`` que le parser ignorait.

Recoller les ``String`` par une espace est faux **deux fois** en ALTO :

* l'espace est **explicite** (``<SP>``) — deux ``String`` voisins sans ``SP``
  sont collés (``L`` + ``r`` exposant + ``s`` = ``Lrs``, pas ``L r s``) ;
* le tiret de coupure est un **élément frère** (``<HYP>``) et non un suffixe du
  ``String``, donc il disparaissait — avec lui la seule trace lisible qu'une
  ligne continue sur la suivante.

Mesuré sur ``corpus/BnF-bpt6k3265015q`` avant correctif : **118 des 566 lignes**
portaient un texte faux et **205** perdaient leur rôle de césure. Sur
``corpus/37-GT-BNL``, zéro — il n'a ni ``<HYP>`` ni ``SUBS_TYPE``, et c'est
précisément pourquoi un seul corpus ne prouve rien ici.
"""

from __future__ import annotations

from cinoc.formats.alto.layout_map import alto_to_layout, layout_to_alto
from cinoc.formats.alto.parser import parse_alto

_NS = 'xmlns="http://www.loc.gov/standards/alto/ns-v4#"'


def _alto(line_children: str) -> bytes:
    return (
        f'<alto {_NS}><Layout><Page ID="P1" WIDTH="100" HEIGHT="50">'
        f'<PrintSpace><TextBlock ID="B1">'
        f'<TextLine ID="L1">{line_children}</TextLine>'
        f"</TextBlock></PrintSpace></Page></Layout></alto>"
    ).encode()


def _first_line(data: bytes):
    return alto_to_layout(parse_alto(data)).pages[0].regions[0].lines[0]


def test_sp_is_the_only_space() -> None:
    """Sans ``<SP>``, deux ``String`` voisins sont collés."""
    doc = _alto(
        '<String CONTENT="L"/><String CONTENT="r"/><String CONTENT="s"/>'
        '<SP/><String CONTENT="personnes"/>'
    )
    assert _first_line(doc).text == "Lrs personnes"


def test_hyp_restores_the_break_mark() -> None:
    """Le ``<HYP>`` frère porte le tiret que le ``String`` n'a pas."""
    doc = _alto(
        '<String CONTENT="de"/><SP/>'
        '<String CONTENT="tra" SUBS_TYPE="HypPart1" SUBS_CONTENT="travailleurs"/>'
        '<HYP CONTENT="&#173;"/>'
    )
    # U+00AD (tiret conditionnel) est ramené au tiret ordinaire : c'est ce que
    # la ligne *dit*, et ce sur quoi une heuristique de césure peut mordre.
    assert _first_line(doc).text == "de tra-"


def test_hyp_does_not_double_a_mark_already_written() -> None:
    """Un producteur qui écrit la marque dans le ``String`` **et** émet un
    ``HYP`` veut une marque, pas deux."""
    doc = _alto('<String CONTENT="Ober⸗"/><HYP CONTENT="⸗"/>')
    assert _first_line(doc).text == "Ober⸗"


def test_subs_survive_the_round_trip() -> None:
    """``SUBS_TYPE``/``SUBS_CONTENT`` traversent ``LAYOUT`` et reviennent.

    Sans eux, un post-correcteur qui recolle un mot coupé ne sait plus quelle
    ligne continue quelle autre — l'information n'est plus nulle part.
    """
    doc = _alto(
        '<String CONTENT="tra" SUBS_TYPE="HypPart1" SUBS_CONTENT="travailleurs"/>'
        "<HYP/>"
    )
    word = _first_line(doc).words[-1]
    assert (word.subs_type, word.subs_content) == ("HypPart1", "travailleurs")

    back = layout_to_alto(alto_to_layout(parse_alto(doc)))
    string = back.pages[0].blocks[0].lines[0].strings[-1]
    assert (string.subs_type, string.subs_content) == ("HypPart1", "travailleurs")


def test_handbuilt_layout_still_falls_back_to_joining() -> None:
    """Un ``AltoDocument`` construit sans parser n'a ni ``SP`` ni ``HYP`` :
    la jointure par espaces reste son repli, sinon son texte serait vide."""
    from cinoc.formats.alto import AltoLine, AltoString

    line = AltoLine(
        id="L1",
        strings=(AltoString(content="deux"), AltoString(content="mots")),
    )
    assert line.text == ""  # aucun parser n'a rempli le champ
    from cinoc.formats.alto.layout_map import _line  # noqa: PLC0415

    assert _line(line).text == "deux mots"


def test_underspecified_line_becomes_specified_then_stable() -> None:
    """Une ligne sans ``text`` ne dit pas où sont ses blancs.

    L'aller-retour la **spécifie** (blanc par défaut entre deux ``String``),
    puis devient idempotent. C'est la propriété qui compte : sans elle, écrire
    puis relire un ALTO déplacerait le texte à chaque passage.
    """
    from cinoc.formats.alto import (
        AltoDocument,
        AltoLine,
        AltoPage,
        AltoString,
        AltoTextBlock,
    )
    from cinoc.formats.alto.writer import write_alto

    doc = AltoDocument(
        pages=(
            AltoPage(
                id="P1",
                width=100,
                height=50,
                blocks=(
                    AltoTextBlock(
                        id="B1",
                        lines=(
                            AltoLine(
                                id="L1",
                                strings=(
                                    AltoString(content="hello"),
                                    AltoString(content="world"),
                                ),
                            ),
                        ),
                    ),
                ),
            ),
        )
    )
    once = parse_alto(write_alto(doc))
    assert once.pages[0].blocks[0].lines[0].text == "hello world"
    assert parse_alto(write_alto(once)) == once
