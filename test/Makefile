WORKSPACE ?= /workspace
DOCKERCOMPOSE ?= docker-compose
DOCKERCOMPOSE_BUILD_ARGS ?= --parallel
DOCKERCOMPOSE_UP_ARGS ?= --build
DOCKERCOMPOSE_EXEC_ARGS ?= -T -u $(shell id -u) -e HOME=$(WORKSPACE) -e WORKSPACE=$(WORKSPACE)
DOCKERCOMPOSE_LOGS_ARGS ?=
EXTRA_LOCAL_ADMIN_USER ?= $(shell id -u)

BUILD_TAG ?= $(shell whoami || date +%s)

export COMPOSE_PROJECT_NAME=grapi-test-$(BUILD_TAG)
export EXTRA_LOCAL_ADMIN_USER

test:

# CI

.test-backend-kopano-ci-run-logger.pid:
	($(MAKE) test-backend-kopano-ci-logs DOCKERCOMPOSE_LOGS_ARGS="--follow $(DOCKERCOMPOSE_LOGS_ARGS)" & echo $$! > $@)

.PHONY: test-backend-kopano-ci-run-start-logger
test-backend-kopano-ci-run-start-logger: .test-backend-kopano-ci-run-logger.pid

.PHONY: test-backend-kopano-ci-run-stop-logger
test-backend-kopano-ci-run-stop-logger: .test-backend-kopano-ci-run-logger.pid
	@kill `cat $<` 2>/dev/null || true
	@rm $< || true

.PHONY: test-backend-kopano-ci-build
test-backend-kopano-ci-build:
	$(DOCKERCOMPOSE) build $(DOCKERCOMPOSE_BUILD_ARGS)

.PHONY: test-backend-kopano-ci-up
test-backend-kopano-ci-up:
	$(DOCKERCOMPOSE) up -d $(DOCKERCOMPOSE_UP_ARGS)

.PHONY: test-backend-kopano-ci-run
test-backend-kopano-ci-run: test-backend-kopano-ci-up
	$(DOCKERCOMPOSE) exec $(DOCKERCOMPOSE_EXEC_ARGS) kopano_grapi_test $(WORKSPACE)/test/starttest.sh

.PHONY: test-backend-kopano-ci-logs
test-backend-kopano-ci-logs:
	$(DOCKERCOMPOSE) logs $(DOCKERCOMPOSE_LOGS_ARGS)

.PHONY: test-backend-kopano-ci-clean
test-backend-kopano-ci-clean:
	$(DOCKERCOMPOSE) down -v --rmi local || true
