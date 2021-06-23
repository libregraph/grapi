DOCKER := docker
IMAGE_NAME := zokradonh/kopano_ldap_demo:latest
CONTAINER_NAME  := kc-dev-ldap
NETWORK_NAME := kc-dev-network

.PHONY: build
build:
	@echo "[$(CONTAINER_NAME)] Pulling image..."
	$(DOCKER) pull $(IMAGE_NAME)

.PHONY: start
start:
ifeq ($(shell $(DOCKER) ps -a --format '{{.Names}}' --filter "name=$(CONTAINER_NAME)"), $(CONTAINER_NAME))
	@echo "[$(CONTAINER_NAME)] Starting the container...";
	$(DOCKER) start $(CONTAINER_NAME);
else
	@echo "[$(CONTAINER_NAME)] Creating a new container...";
	$(DOCKER) run --name $(CONTAINER_NAME) -p 8389:389/tcp \
		-e LDAP_ORGANISATION="Kopano Dev" \
		-e LDAP_DOMAIN="kopano-dev.local" \
		-e LDAP_BASE_DN="dc=kopano-dev,dc=local" \
		-e LDAP_ADMIN_PASSWORD="kopano-dev" \
		-e LDAP_READONLY_USER="true" \
		-e LDAP_READONLY_USER_PASSWORD="kopano-dev" \
		-e LDAP_TLS="false" \
		-d $(IMAGE_NAME) \
		--network $(NETWORK_NAME) \
		--loglevel debug --copy-service;
endif

.PHONY: clean
clean:
	@echo "[$(CONTAINER_NAME)] Removing container..."
	$(DOCKER) rm -f $(CONTAINER_NAME)
