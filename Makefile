.PHONY: install lint type test cov check check-fast ci

# Flags de coverage : injectés UNIQUEMENT par le gate (cov/ci), jamais dans
# addopts — sinon chaque run local (y compris un sous-ensemble) paierait ×3,4.
COV := --cov=xerocr --cov-report=term-missing --cov-fail-under=85
# Parallélisme : pytest-xdist répartit la suite sur tous les cœurs (gate ~3× plus
# court). pytest-cov agrège la couverture des workers → le seuil 85 % tient.
PAR := -n auto

install:
	pip install -e ".[dev]"

lint:
	ruff check xerocr/ tests/

type:
	python -m mypy -p xerocr

# Boucle locale : suite SANS coverage (~3× plus rapide). Itérer là-dessus
# (ou sur un sous-ensemble ciblé) ; le gate complet ne tourne qu'avant push.
test:
	python -m pytest -q $(PAR)

# Suite COMPLÈTE avec coverage + seuil 85 % : le gate (CLAUDE.md §11).
cov:
	python -m pytest -q $(PAR) $(COV)

check: lint type cov

# Pré-push LOCAL : ruff + mypy + **toute** la suite, SANS coverage (parallèle).
# Le seuil de coverage 85 % est le concern du **gate PR** (GitHub Actions
# `ci.yml`), pas de chaque push local → itération rapide sans le payer ×N.
# (Tous les tests tournent : ce n'est PAS un sous-ensemble, cf. CLAUDE.md §11.)
check-fast: lint type test

# `make ci` = gate complet local (avec coverage), utile ponctuellement ;
# le gate **autoritaire** reste GitHub Actions sur la PR.
ci: check

