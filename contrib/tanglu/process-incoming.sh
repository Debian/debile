#!/bin/sh
# This is a helper script. It is only useful within the Tanglu
# infrastructure. If you're not from Tanglu, just ignore it.
source ENV/bin/activate
cd /pub/ftp/incoming
chmod 660 /pub/ftp/incoming/*
debile-import .
cd /tmp
