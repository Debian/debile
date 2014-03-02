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

from debian.deb822 import Packages
from debile.utils.dsc2 import Dsc2
from debile.utils.aget import dget, find_dsc
from StringIO import StringIO
from gzip import GzipFile
import requests
import os

def find_debs(archive, suite, component, arch, source, version):
    url = find_dsc(archive, suite, component, source, version)
    if url[:7] == "http://":
        dsc = Dsc2(StringIO(requests.get(url).content))
    else:
        dsc = Dsc2(filename=url)

    components = [component]
    for line in dsc['Package-List']:
        if "/" in line['section']:
            component, _ = line['section'].split("/")
            if component not in components:
                components.append(component)

    filenames = []
    for component in components:
        url = "{archive}/dists/{suite}/{component}/binary-{arch}/Packages.gz".format(
            archive=archive,
            suite=suite,
            component=component,
            arch=arch,
        )
        if url[:7] == "http://":
            packages = GzipFile(fileobj=StringIO(requests.get(url).content))
        else:
            packages = GzipFile(filename=url)

        for entry in Packages.iter_paragraphs(packages):
            name = entry['Source'] if 'Source' in entry else entry['Package']
            if (name == source and entry['Version'] == version) or (name == "%s (%s)" % (source, version)):
                filenames.append(entry['Filename'])

    if filenames == []:
        raise Exception("Damnit, no such packages?")

    ret = []
    for filename in filenames:
        url = "{archive}/{filename}".format(
            archive=archive,
            filename=filename
        )
        ret.append(url)

    return ret

def bget(archive, suite, component, arch, source, version):
    debs = find_debs(archive, suite, component, arch, source, version)
    for deb in debs:
        dget(deb)
    return [os.path.basename(url) for url in debs]

def main():
    import sys
    return bget(*sys.argv[1:])
