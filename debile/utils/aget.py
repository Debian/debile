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

from debian.deb822 import Sources
from debile.utils import run_command
import StringIO
import requests
import gzip
import os

def dget(path):
    out, err, ret = run_command(["dget", "-u", path])
    if ret != 0:
        print ret, err
        raise Exception("dget failed to download package")

def find_dsc(archive, suite, component, source, version):
    url = "{archive}/dists/{suite}/{component}/source/Sources.gz".format(
        archive=archive,
        suite=suite,
        component=component
    )

    for entry in Sources.iter_paragraphs(gzip.GzipFile(
            fileobj=StringIO.StringIO(requests.get(url).content))):
        if entry['Package'] == source and entry['Version'] == version:
            dsc = None
            for line in entry['Files']:
                if line['name'].endswith(".dsc"):
                    dsc = line['name']
            return "{archive}/{path}/{dsc}".format(
                archive=archive,
                path=entry['Directory'],
                dsc=dsc,
            )

    raise Exception("Package not found in Sources.gz")


def aget(archive, suite, component, source, version):
    url = find_dsc(archive, suite, component, source, version)
    dget(url)
    return os.path.basename(url)


def main():
    import sys
    return aget(*sys.argv[1:])
