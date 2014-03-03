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

from debile.utils.commands import safe_run
from debian.deb822 import Sources
from StringIO import StringIO
from gzip import GzipFile
import requests
import os


def find_dsc(archive, suite, component, source, version):
    url = "{archive}/dists/{suite}/{component}/source/Sources.gz".format(
        archive=archive,
        suite=suite,
        component=component
    )
    if url[:7] == "http://":
        sources = GzipFile(fileobj=StringIO(requests.get(url).content))
    else:
        sources = GzipFile(filename=url)

    for entry in Sources.iter_paragraphs(sources):
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
    safe_run(["dget", "-u", "-d", url])
    return os.path.basename(url)


def main():
    import sys
    return aget(*sys.argv[1:])
