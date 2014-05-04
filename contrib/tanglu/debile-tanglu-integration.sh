#!/bin/bash
# This is a helper script. It is only useful within the Tanglu
# infrastructure. If you're not from Tanglu, just ignore it.
source /var/archive-kit/debile/ENV/bin/activate
python /var/archive-kit/debile/contrib/tanglu/debile-tanglu-integration.py $@
