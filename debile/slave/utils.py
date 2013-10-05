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

from debile.slave.error import EthelError
from debile.slave.core import config

from contextlib import contextmanager
from schroot import schroot
from debian import deb822
import subprocess
import tempfile
import shutil
import shlex
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


def run_command(command, stdin=None):
    if not isinstance(command, list):
        command = shlex.split(command)
    try:
        pipe = subprocess.Popen(command, shell=False,
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
    except OSError:
        return (None, None, -1)

    kwargs = {}
    if stdin:
        kwargs['input'] = stdin.read()

    (output, stderr) = pipe.communicate(**kwargs)
    output, stderr = (c.decode('utf-8',
                               errors='ignore') for c in (output, stderr))
    return (output, stderr, pipe.returncode)


def safe_run(cmd, expected=0):
    if not isinstance(expected, tuple):
        expected = (expected, )

    out, err, ret = run_command(cmd)

    if not ret in expected:
        print(err)
        e = EthelSubprocessError(out, err, ret, cmd)
        raise e

    return out, err


def dget(url):
    # TODO : add some logging here, useful to setup correctly the
    # "pool_url" parameter in debile-master
    safe_run(["dget", "-u", "-d", url])


class EthelSubprocessError(EthelError):
    def __init__(self, out, err, ret, cmd):
        super(EthelError, self).__init__()
        self.out = out
        self.err = err
        self.ret = ret
        self.cmd = cmd


def jobize(path, job):
    f = open(path, 'r')
    obj = deb822.Deb822(f)
    obj['X-Debile-Job'] = str(job['id'])
    obj.dump(fd=open(path, 'wb'))
    return obj


def prepare_binary_for_upload(changes, job):
    jobize(changes, job)
    gpg = config.get('gpg', None)
    if gpg is None:
        raise Exception("No GPG in config YAML")

    out, err, ret = run_command(['debsign', '-k%s' % (gpg), changes])
    if ret != 0:
        print(out)
        print(err)
        raise Exception("bad debsign")


def upload(changes, job, package):
    """
    This is called when we need to upload a binary to debile pool after
    a build job.
    """

    prepare_binary_for_upload(changes, job)
    # Find the dput target we need
    dput_target = "%s-%s" % (package['user']['login'], job['subtype'])

    out, err, ret = run_command([
        'dput',
        dput_target,
        changes
    ])
    if ret != 0:
        print(out)
        print(err)
        raise Exception("dput sux")
