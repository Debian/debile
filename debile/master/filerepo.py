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
import os
import shutil
from debile.utils.config import load_master_config

class FilesException(Exception):
    pass


class FilesAlreadyRegistered(FilesException):
    pass


class FileRepo(object):

    def __init__(self, root):
        self.root = root
        config = load_master_config()
        self._chmod_mode = config['chmod_dud_data']

    def add_dud(self, dud):
        source, version, jid = (dud[x] for x in [
            'Source', 'Version', 'X-Debile-Job'])
        self.include(source, version, jid, dud)

    def include(self, source, version, jid, dud):
        path = "{root}/{source}/{version}/{jid}".format(
            root=self.root,
            source=source,
            version=version,
            jid=jid
        )
        os.makedirs(path)

        for fp in [dud.get_filename()] + dud.get_files():
            shutil.move(fp, path)
            os.chmod("%s/%s" % (path, os.path.basename(fp)), self._chmod_mode)
