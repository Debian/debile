IMAGES := ursae

$(IMAGES): base
	make -C $@ build

base:
	# We special-case build since we depend on it.
	make -C base build

all: $(IMAGES)

.PHONY: $(IMAGES) base
