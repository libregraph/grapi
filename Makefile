# Tools

PYTHON ?= python3
PYLINT ?= pylint
PYTEST ?= py.test-3

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
	PYTHONPATH=${PYTHONPATH} ${PYTEST}

.PHONE: changelog
changelog: ; $(info updating changelog ...)
	$(CHGLOG) --output CHANGELOG.md v0.1.0..

# Dev helpers

.PHONY: start-mfr
start-mfr:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) grapi/mfr/__init__.py $(ARGS)

.PHONY: start-devrunner
start-devrunner:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) scripts/devrunner.py $(ARGS)
