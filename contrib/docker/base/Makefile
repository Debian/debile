NAMESPACE=paultag
IMAGE_ID=$(NAMESPACE)/debile-slave-base
CURRENT_ID = $(shell docker.io images -q $(IMAGE_ID))
IMAGE_BUILD = docker.io build \
		          --no-cache=true \
		          --rm=true \
		          -t $(IMAGE_ID) \
		          .

build:
ifeq ($(CURRENT_ID),)
	$(IMAGE_BUILD)
else
	@echo "$(IMAGE_ID) is tag $(CURRENT_ID)"
endif

rebuild:
	$(IMAGE_BUILD)

clean:
	docker.io rmi $(CURRENT_ID)
