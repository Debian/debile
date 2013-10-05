

%:
	set -xe; \
	for fp in "setup.py" "setup.master.py" "setup.slave.py"; do \
		python $$fp $@; \
	done
