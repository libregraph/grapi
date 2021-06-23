# Kopano Core.
DOCKER := docker
IMAGE_NAME := kc-test-dev
CONTAINER_NAME := $(IMAGE_NAME)
NETWORK_NAME := $(IMAGE_NAME)-network
HOST_IP := $(shell ip addr show wlp2s0 | \grep inet | head -1 | awk '{split($$2,s,"/");print s[1]}')
PYTHON_VERSION ?= '3.9'

.PHONY: build
build:
	@echo "[$(CONTAINER_NAME)] Creating image..."
	$(DOCKER) build --build-arg python_version=$(PYTHON_VERSION) -t $(IMAGE_NAME) .

.PHONY: start
start: build
ifeq ($(shell $(DOCKER) ps -a --format '{{.Names}}' --filter "name=$(CONTAINER_NAME)"), $(CONTAINER_NAME))
	@echo "[$(CONTAINER_NAME)] Starting the container...";
	$(DOCKER) start $(CONTAINER_NAME);
	$(DOCKER) exec -ti $(CONTAINER_NAME) /bin/bash;
else
	@echo "[$(CONTAINER_NAME)] Creating a new container...";
	$(DOCKER) run -ti -v ~/Workspaces/kopano/socket/:/srv/shared \
		--add-host fx:$(HOST_IP) \
		--network $(NETWORK_NAME) \
		--privileged --name $(CONTAINER_NAME) $(IMAGE_NAME);
endif

.PHONY: clean
clean: start
	@echo "[$(CONTAINER_NAME)] Removing container..."
	$(DOCKER) rm -f $(CONTAINER_NAME)
