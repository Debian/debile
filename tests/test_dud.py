# Copyright (c) Paul R. Tagliamonte, 2013 under the terms of the
#   debile package.

from debile.utils.dud import Dud
from debile.slave.utils import cd  # XXX: Fix this


def test_dud():
    with cd("resources"):
        d = Dud()
        d.add_file("file1")
        d.add_file("file2")
        d['Created-By'] = "Test <test@example.com>"
        d['Source'] = "fnord"
        d['Version'] = "1.0"
        d['Architecture'] = "all"

        assert ["file1", "file2"] == list(d.files())

        d.write_dud("test.dud")
