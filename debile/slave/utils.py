# Copyright (c) 2012-2013 Paul Tagliamonte <paultag@debian.org>
# Copyright (c) 2013 Leo Cavaille <leo@cavaille.net>
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
import dput

from contextlib import contextmanager
from schroot import schroot
import tempfile
import shutil
import sys
import os


def upgrade(chroot):
    print("Schrooting")
    with schroot(chroot) as chroot:
        print("updating")
        out, err, ret = chroot.run([
            "apt-get", "update"
        ], user='root')
        print(out, err)
        out, err, ret = chroot.run([
            "apt-get", "upgrade", "-y"
        ], user='root')
        print(out, err)
        out, err, ret = chroot.run([
            "apt-get", "dist-upgrade", "-y"
        ], user='root')
        print(out, err)


def doupdate():
    upgrade(*sys.argv[1:])


@contextmanager
def tdir():
    fp = tempfile.mkdtemp()
    try:
        yield fp
    finally:
        shutil.rmtree(fp)


@contextmanager
def cd(where):
    ncwd = os.getcwd()
    try:
        yield os.chdir(where)
    finally:
        os.chdir(ncwd)


def sign(changes, gpg):
    if changes.endswith(".dud"):
        safe_run(['gpg', '-u', gpg, '--clearsign', changes])
        os.rename("%s.asc" % (changes), changes)
    else:
        safe_run(['debsign', '-k', gpg, changes])


def upload(changes, job, gpg, host):
    sign(changes, gpg)
    dput.upload(changes, host)
