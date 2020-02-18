# Tools

PYTHON ?= python3
FLAKE8 ?= flake8
PYTEST ?= py.test-3

CHGLOG ?= git-chglog

# Variables

PYTHONPATH ?= .
ARGS ?=

PYTEST_OPTIONS+=-s
PYTEST_COVERAGE_OPTIONS+=--cov-report=term-missing

# Rules

.PHONY: all
all:

.PHONY: lint
lint:
	$(FLAKE8) -v --format=pylint --exclude=grapi/backend/caldav,grapi/backend/imap ./grapi

.PHONY: test
test:
	PYTHONPATH=${PYTHONPATH} ${PYTEST} ${PYTEST_OPTIONS} test/unit

.PHONY: test-backend-kopano
test-backend-kopano:
	PYTHONPATH=${PYTHONPATH} ${PYTEST} ${PYTEST_OPTIONS} ${ARGS} test/integration/backend.kopano

.PHONY: test-backend-kopano-cov
test-backend-kopano-cov: ARGS = --cov=grapi.backend.kopano --cov-report=html:test/coverage/integration/backend.kopano
test-backend-kopano-cov: test-backend-kopano

.PHONY: changelog
changelog: ; $(info updating changelog ...)
	$(CHGLOG) --output CHANGELOG.md $(ARGS) v0.1.0..

# CI

.PHONY: test-backend-kopano-ci
test-backend-kopano-ci: ARGS = --cov=grapi.backend.kopano --junit-xml=test/coverage/integration/backend.kopano/integration.xml --cov-report=html:test/coverage/integration/backend.kopano -p no:cacheprovider
test-backend-kopano-ci: test-backend-kopano

# Dev helpers

.PHONY: start-mfr
start-mfr:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) grapi/mfr/__init__.py $(ARGS)

.PHONY: start-devrunner
start-devrunner:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) scripts/devrunner.py $(ARGS)
