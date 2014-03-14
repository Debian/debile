# Copyright (c) 2012-2013 Paul Tagliamonte <paultag@debian.org>
# Copyright (c) 2014      Jon Severinsson <jon@severinsson.net>
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

from debian.deb822 import _gpg_multivalued
from debian.deb822 import Changes as Changes_
import hashlib
import os


# Copy of debian.deb822.Dsc with Package-List: support added.
class Dsc(_gpg_multivalued):
    _multivalued_fields = {
        "package-list": ["name", "type", "section", "priority"],
        "files": ["md5sum", "size", "name"],
        "checksums-sha1": ["sha1", "size", "name"],
        "checksums-sha256": ["sha256", "size", "name"],
    }


# Extention to debian.deb822.Changes with add_file() support
# Also useful for Debile *.dud files.
class Changes(Changes_):
    def add_file(self, fp):
        statinfo = os.stat(fp)
        size = statinfo.st_size

        algos = {
            "Files": "md5",
            "Checksums-Sha1": "sha1",
            "Checksums-Sha256": "sha256",
        }

        for key, algo in algos.items():
            if key not in self:
                self[key] = []

            m = hashlib.new(algo)
            with open(fp, "rb") as fd:
                for chunk in iter((lambda: fd.read(128 * m.block_size)), b''):
                    m.update(chunk)

            if key != "Files":
                self[key].append({
                    algo: m.hexdigest(),
                    "size": size,
                    "name": fp
                })
            else:
                self[key].append({
                    "md5sum": m.hexdigest(),
                    "size": size,
                    "section": 'debile',
                    "priority": 'debile',
                    "name": fp
                })
