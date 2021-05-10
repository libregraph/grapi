DOCKERCOMPOSE ?= docker-compose
DOCKERCOMPOSE_UP_ARGS ?=
DOCKERCOMPOSE_EXEC_ARGS ?=
DOCKERCOMPOSE_LOGS_ARGS ?=
EXTRA_LOCAL_ADMIN_USER ?=

BUILD_TAG ?= $(shell date +%s)

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

.PHONY: test-backend-kopano-ci-run
test-backend-kopano-ci-run:
	$(DOCKERCOMPOSE) up -d $(DOCKERCOMPOSE_UP_ARGS)
	$(DOCKERCOMPOSE) exec $(DOCKERCOMPOSE_EXEC_ARGS) kopano_grapi_test /workspace/test/starttest.sh

.PHONY: test-backend-kopano-ci-logs
test-backend-kopano-ci-logs:
	$(DOCKERCOMPOSE) logs $(DOCKERCOMPOSE_LOGS_ARGS)

.PHONY: test-backend-kopano-ci-clean
test-backend-kopano-ci-clean:
	$(DOCKERCOMPOSE) down -v --rmi local || true
