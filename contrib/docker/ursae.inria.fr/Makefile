CURRENT_ID = $(shell docker.io images -q debile-slave-ursae)
IMAGE_BUILD = docker.io build \
		          --no-cache=true \
		          --rm=true \
		          -t debile-slave-ursae \
		          .

build:
ifeq ($(CURRENT_ID),)
	$(IMAGE_BUILD)
else
	@echo "debile-slave-ursae is tag $(CURRENT_ID)"
endif

rebuild:
	$(IMAGE_BUILD)

clean:
	docker.io rmi $(CURRENT_ID)
