.PHONY: install lint type test cov check ci

# Flags de coverage : injectés UNIQUEMENT par le gate (cov/ci), jamais dans
# addopts — sinon chaque run local (y compris un sous-ensemble) paierait ×3,4.
COV := --cov=xerocr --cov-report=term-missing --cov-fail-under=85

install:
	pip install -e ".[dev]"

lint:
	ruff check xerocr/ tests/

type:
	python -m mypy -p xerocr

# Boucle locale : suite SANS coverage (~3× plus rapide). Itérer là-dessus
# (ou sur un sous-ensemble ciblé) ; le gate complet ne tourne qu'avant push.
test:
	python -m pytest -q

# Suite COMPLÈTE avec coverage + seuil 85 % : le gate (CLAUDE.md §11).
cov:
	python -m pytest -q $(COV)

check: lint type cov

# Porte unique avant push : ruff + mypy + suite COMPLÈTE.
# Règle (CLAUDE.md §11) : ne jamais rapporter « vert » sur un sous-ensemble.
ci: check

