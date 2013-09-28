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

from debile.slave.wrappers.piuparts import parse_piuparts

from schroot.chroot import SchrootCommandError
from schroot import schroot

try:
    import configparser
except ImportError:
    import ConfigParser as configparser

import os
import re


LINE_INFO = re.compile(
    r"(?P<minutes>\d+)m(?P<sec>(\d(\.?))+)s (?P<severity>\w+): (?P<info>.*)")


def piuparts(chroot, target, analysis):
    cfg = configparser.ConfigParser()
    if cfg.read("/etc/schroot/chroot.d/%s" % (chroot)) == []:
        raise Exception("Shit. No such tarball")

    block = cfg[chroot]

    if "file" not in block:
        raise Exception("Chroot type isn't of tarball")

    location = block['file']
    copy_location = os.path.join("/tmp", os.path.basename(location))

    with schroot(chroot) as chroot:
        chroot.copy(location, copy_location)
        chroot.copy(target, "/tmp")

        print("[     ] Installing...")
        chroot.run(['apt-get', 'install', '-y', 'piuparts'], user='root')
        print("[     ] Piuparts installed.")

        failed = False
        try:
            print("[     ] Running Piuparts..")
            out, err, ret = chroot.run([
                'piuparts',
                '-b', copy_location,
                '/tmp/%s' % target,
                '--warn-on-debsums-errors',
                '--pedantic-purge-test',
            ], user='root')
        except SchrootCommandError as e:
            out, err = e.out, e.err
            failed = True

        for x in parse_piuparts(out.splitlines(), target):
            analysis.results.append(x)

        return analysis, out, failed


def version():
    #TODO
    return ('piuparts', 'n/a')
