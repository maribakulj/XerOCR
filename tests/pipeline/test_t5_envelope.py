"""Enveloppe T5 — pipeline hybride seg → reconnaissance par région → ALTO.

Les 3 briques ``precomputed_layout`` / ``precomputed_region`` / ``alto_assembler``
implémentent le contrat ``Module`` mais ne sont pas encore composées par un
planificateur : la finition T5 (le planner hybride) reste à livrer. Ce fichier
(1) **garde** qu'elles restent enregistrées au socle (anti-retrait accidentel) et
(2) **documente**, par un test ``skip`` nommé, le consommateur attendu — à
dé-skipper et réécrire quand T5 sera construit.
"""

from __future__ import annotations

import pytest

from cinoc.app.modules.registry import ModuleRegistry, register_default_modules

#: Les 3 briques de l'enveloppe hybride (cf. registry.register_default_modules).
T5_ENVELOPE = ("precomputed_layout", "precomputed_region", "alto_assembler")


def _registered_kinds() -> set[str]:
    registry = ModuleRegistry()
    register_default_modules(registry)
    return set(registry.kinds())


def test_t5_bricks_stay_registered() -> None:
    """Garde : les 3 briques de l'enveloppe hybride restent au socle.

    Elles sont injoignables par un planner aujourd'hui, mais leur retrait
    casserait la livraison T5 — ce test échoue si on les déregistre par erreur.
    """
    assert set(T5_ENVELOPE) <= _registered_kinds()


@pytest.mark.skip(
    reason="envelope T5 : le planner hybride seg→reco→ALTO n'est pas encore livré"
)
def test_hybrid_planner_composes_the_three_bricks() -> None:
    """SPEC du consommateur attendu (à implémenter puis dé-skipper en T5).

    Quand le planner hybride existera, il devra produire une ``PipelineSpec`` qui :

    1. segmente l'``IMAGE`` en ``LAYOUT`` (régions seules) — segmenteur au choix
       (``precomputed_layout`` baseline, ``pp_doclayout`` réel…) ;
    2. reconnaît **par région** via une étape ``fanout=True``
       (``LAYOUT`` + ``IMAGE`` → ``LAYOUT`` rempli) → consomme
       ``precomputed_region`` (ou un OCR réel) ;
    3. assemble le ``LAYOUT`` rempli en ``ALTO_XML`` → consomme ``alto_assembler``.

    Ce test sera alors réécrit pour asserter cette composition (et comparer le
    texte assemblé au texte brut, cf. objectif produit segmentation).
    """
    pytest.fail("non implémenté : planner hybride T5 (cf. docstring)")
