# Tools

PYTHON ?= python3
PYLINT ?= pylint3
PYTEST ?= py.test-3
PYTEST_OPTIONS+=-s
PYTEST_COVERAGE_OPTIONS+=--cov-report=term-missing

CHGLOG ?= git-chglog

# Variables

PYTHONPATH ?= .
ARGS ?=

# Rules

.PHONY: all
all:

.PHONY: lint
lint:
	$(PYLINT) ./grapi

.PHONY: test
test:
	PYTHONPATH=${PYTHONPATH} ${PYTEST} ${PYTEST_OPTIONS} test/unit

.PHONY: test-backend-kopano
test-backend-kopano:
	PYTHONPATH=${PYTHONPATH} ${PYTEST} ${PYTEST_OPTIONS} ${ARGS} test/integration/backend.kopano

.PHONY: test-backend-kopano-cov
test-backend-kopano-cov: ARGS = --cov=grapi.backend.kopano --cov-report=html:test/coverage/integration/backend.kopano
test-backend-kopano-cov: test-backend-kopano

open-backend-kopano-cov: test-integration-cov
	${BROWSER} test/coverage/integration/backend.kopano

.PHONE: changelog
changelog: ; $(info updating changelog ...)
	$(CHGLOG) --output CHANGELOG.md $(ARGS) v0.1.0..

# Dev helpers

.PHONY: start-mfr
start-mfr:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) grapi/mfr/__init__.py $(ARGS)

.PHONY: start-devrunner
start-devrunner:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) scripts/devrunner.py $(ARGS)
