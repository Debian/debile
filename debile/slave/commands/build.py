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

from debile.slave.runners.sbuild import sbuild, version
import glob


def run(dsc, package, job, firehose):
    suite = job['suite']
    arch = job['arch']

    firehose, out, ftbfs, changes, = sbuild(dsc, suite, arch, firehose)

    # ['python-schroot_0.3-1.debian.tar.gz',
    # 'python3-schroot_0.3-1_all.deb',
    # 'python-schroot_0.3-1.dsc',
    # 'python-schroot_0.3-1_amd64.build',
    # 'python-schroot-0.3',
    # 'python-schroot_0.3-1_all.deb',
    # 'python-schroot_0.3.orig.tar.gz',
    # 'python-schroot_0.3-1_amd64.changes',
    # 'python-schroot_0.3-1_amd64-20131009-2159.build']

    version = package['version']
    if ":" in version:
        _, version = version.split(":", 1)
        # epoch. boggle.

    changes = "{source}_{version}*.changes".format(
        source=package['name'],
        version=version,
    )

    changes = list(glob.glob(changes))

    if changes == [] and not ftbfs:
        print(out)
        print(changes)
        print(list(glob.glob("*")))
        raise Exception("Um. No changes but no FTBFS.")

    if not ftbfs:
        changes = changes[0]
    else:
        changes = None

    return (firehose, out, ftbfs, changes)


def get_version():
    return version()
