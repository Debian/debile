HOSTNAME=$(shell hostname --fqdn)
IMAGE_ID=debile-slave-ursae-private
CURRENT_ID = $(shell docker.io images -q $(IMAGE_ID))
IMAGE_BUILD = docker.io build \
		          --no-cache=true \
		          --rm=true \
		          -t $(IMAGE_ID) \
		          .

all: build


config.tar.gz:
	../../../debian/bin/debile-generate-slave-keys $(HOSTNAME)
	mv $(HOSTNAME).tar.gz config.tar.gz


build: config.tar.gz
ifeq ($(CURRENT_ID),)
	$(IMAGE_BUILD)
else
	@echo "$(IMAGE_ID) is tag $(CURRENT_ID)"
endif

rebuild:
	$(IMAGE_BUILD)

clean:
	docker.io rmi $(CURRENT_ID)
