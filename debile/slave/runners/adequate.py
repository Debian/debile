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

from debile.slave.wrappers.adequate import parse_adequate
from schroot import schroot

import os


def adequate(chroot_name, target, package_name, analysis):
    with schroot(chroot_name) as chroot:
        chroot.copy(target, "/tmp")

        out, err, ret = chroot.run([
            'apt-get', 'install', '-y', 'adequate'
        ], user='root')

        os.environ['DEBIAN_FRONTEND'] = 'noninteractive'
        out, err, ret = chroot.run([
            'dpkg', '-i',
            "/tmp/%s" % target
        ], user='root', return_codes=(0, 1), preserve_environment=True)

        out, err, ret = chroot.run([
            'apt-get', 'install', '-y', '-f'
        ], user='root', preserve_environment=True)

        out, err, ret = chroot.run(['adequate', package_name])

        failed = False
        for issue in parse_adequate(out.splitlines()):
            failed = True
            analysis.results.append(issue)

        return (analysis, out, failed, None, None)


def version():
    #TODO
    return ('adequate', 'n/a')
