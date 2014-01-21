# This Makefile will help in creating a Debile slave image for this
# host.
#

all: image

slave.yaml:
	@echo "Copying /etc/debile/slave.yaml here."
	@echo "If you need, please edit this config."
	@cp /etc/debile/slave.yaml .


image: slave.yaml
	@echo "Creating the image"
	@docker.io build -rm=true -t debile-slave .
