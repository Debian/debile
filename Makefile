PYTHON := python


%:
	set -xe; \
	for fp in "setup.py" "setup.master.py" "setup.slave.py"; do \
		$(PYTHON) $$fp $@; \
	done
