# Copyright (c) Sylvestre Ledru, 2013 under the terms of the
#   debile package.
from debile.slave.runners.findbugs import findbugs
from debile.slave.utils import cd
import firehose.model
import os
import urllib

def test_findbugs():
    with cd("tmp"):
        report=firehose.model.Analysis.from_xml(
            open("/home/sylvestre/incoming/1.firehose.xml", 'r'))

        urllib.urlretrieve("http://snapshot.debian.org/archive/debian/20130527T160533Z/pool/main/libj/libjlatexmath-java/libjlatexmath-fop-java_1.0.2-1_all.deb", "libjlatexmath-fop-java_1.0.2-1_all.deb")
        assert os.path.isfile("libjlatexmath-fop-java_1.0.2-1_all.deb")

        analysis = findbugs("libjlatexmath-fop-java_1.0.2-1_all.deb",report)

#        assert ["file1", "file2"] == list(d.files())

