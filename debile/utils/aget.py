# Copyright (c) 2012-2013 Paul Tagliamonte <paultag@debian.org>
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

from debile.utils import run_command
import deb822
import StringIO
import requests
import gzip
import os

SOURCE = "dists/{suite}/{section}/source/Sources.gz"


def dget(path):
    out, err, ret = run_command(["dget", "-u", path])
    if ret != 0:
        print ret, err
        raise Exception("DAMNIT; dget fucked us")


def aget(archive, suite, section, source, version):
    url = "{archive}/{path}".format(
        archive=archive,
        path=SOURCE.format(suite=suite, section=section
    ))

    for entry in deb822.Deb822.iter_paragraphs(gzip.GzipFile(
            fileobj=StringIO.StringIO(requests.get(url).content))):

        path = entry['Directory']

        dsc = None
        for fp in entry['Files'].splitlines():
            if fp.strip() == "":
                continue

            hash_, size, fid = fp.split()
            if fid.endswith(".dsc"):
                dsc = fid

        if entry['Package'] == source and entry['Version'] == version:
            dget("{archive}/{pool}/{dsc}".format(
                archive=archive,
                pool=path,
                dsc=dsc,
            ))
            # break
            return os.path.basename(dsc)
    else:
        print "BALLS."
        raise Exception


def main():
    import sys
    return aget(*sys.argv[1:])
