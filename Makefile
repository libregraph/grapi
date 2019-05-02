# Tools

PYTHON ?= python3
FLAKE8 ?= flake8
PYTEST ?= py.test-3
PYTEST_OPTIONS+=-s
PYTEST_COVERAGE_OPTIONS+=--cov-report=term-missing

CHGLOG ?= git-chglog

# Variables

PYTHONPATH ?= .
ARGS ?=
TESTDIR = test

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

open-backend-kopano-cov: test-integration-cov
	${BROWSER} test/coverage/integration/backend.kopano

.PHONE: changelog
changelog: ; $(info updating changelog ...)
	$(CHGLOG) --output CHANGELOG.md $(ARGS) v0.1.0..

# CI

.PHONY: pydeps
pydeps:
	grep -Ev "kopano|MAPI"  requirements.txt > jenkins_requirements.txt
	$(PYTHON) -m pip install --no-cache-dir -r jenkins_requirements.txt
	$(PYTHON) -m pip install --no-cache-dir pytest pytest-cov pylint
	@rm jenkins_requirements.txt


.PHONY: test-backend-kopano-ci
test-backend-kopano-ci: ARGS = --cov=grapi.backend.kopano --junit-xml=test/coverage/integration/backend.kopano/integration.xml --cov-report=html:test/coverage/integration/backend.kopano -p no:cacheprovider
test-backend-kopano-ci: pydeps test-backend-kopano

.PHONY: test-backend-kopano-ci-run
test-backend-kopano-ci-run:
	@$(MAKE) -C $(TESTDIR) test-backend-kopano-ci-run


# Dev helpers

.PHONY: start-mfr
start-mfr:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) grapi/mfr/__init__.py $(ARGS)

.PHONY: start-devrunner
start-devrunner:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) scripts/devrunner.py $(ARGS)
