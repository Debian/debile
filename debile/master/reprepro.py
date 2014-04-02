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

from debile.utils.commands import run_command
from debian.deb822 import Sources
from gzip import GzipFile


class RepoException(Exception):
    pass


class RepoSourceAlreadyRegistered(RepoException):
    pass


class Repo(object):

    def __init__(self, root):
        self.root = root

    def add_changes(self, changes):
        dist = changes['distribution']
        self.include(dist, changes.get_changes_file())

    def _exec(self, *args):
        cmd = ["reprepro", "-Vb", self.root] + list(args)
        out, err, ret = run_command(cmd)
        if ret != 0:
            raise RepoException(ret)
        return (out, err, ret)

    def include(self, distribution, changes):
        try:
            return self._exec("include", distribution, changes)
        except RepoException as e:
            error = e.message
            if error == 254:
                raise RepoSourceAlreadyRegistered()
            raise

    def includedeb(self, distribution, deb):
        raise NotImplemented()

    def includeudeb(self, distribution, udeb):
        raise NotImplemented()

    def includedsc(self, distributions, dsc):
        raise NotImplemented()

    def list(self, distribution, name):
        raise NotImplemented()

    def clearvanished(self):
        raise NotImplemented()

    def find_dsc(self, source):
        sources = "{root}/dists/{suite}/{component}/source/Sources.gz".format(
            root=self.root,
            suite=source.suite.name,
            component=source.component.name
        )

        for entry in Sources.iter_paragraphs(GzipFile(filename=sources)):
            if entry['Package'] == source.name and entry['Version'] == source.version:
                dsc = None
                for line in entry['Files']:
                    if line['name'].endswith(".dsc"):
                        dsc = line['name']
                        break
                return (entry['Directory'], dsc)

        raise Exception("Package not found in Sources.gz")
