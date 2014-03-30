# -*- coding: utf-8 -*-
#
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

from debile.slave.utils import run_command

from firehose.model import Stats
import firehose.parsers.gcc as fgcc

from datetime import timedelta
from io import StringIO
import glob
import re
import os


STATS = re.compile("Build needed (?P<time>.*), (?P<space>.*) dis(c|k) space")
VERSION = re.compile("sbuild \(Debian sbuild\) (?P<version>)")


def parse_sbuild_log(log, sut):
    gccversion = None
    stats = None

    for line in log.splitlines():
        flag = "Toolchain package versions: "
        stat = STATS.match(line)
        if stat:
            info = stat.groupdict()
            hours, minutes, seconds = [int(x) for x in info['time'].split(":")]
            timed = timedelta(hours=hours, minutes=minutes, seconds=seconds)
            stats = Stats(timed.total_seconds())
        if line.startswith(flag):
            line = line[len(flag):].strip()
            packages = line.split(" ")
            versions = {}
            for package in packages:
                if "_" not in package:
                    continue
                b, bv = package.split("_", 1)
                versions[b] = bv
            vs = list(filter(lambda x: x.startswith("gcc"), versions))
            if vs == []:
                continue
            vs = vs[0]
            gccversion = versions[vs]

    obj = fgcc.parse_file(
        StringIO(log),
        sut=sut,
        gccversion=gccversion,
        stats=stats
    )

    return obj


def ensure_chroot_sanity(chroot_name):
    out, ret, err = run_command(['schroot', '-l'])
    for chroot in out.splitlines():
        chroot = chroot.strip()
        chroots = [
            chroot,
            "chroot:%s" % (chroot)
        ]
        if chroot in chroots:
            return True
    raise ValueError("No such schroot (%s) found." % (chroot_name))


def sbuild(package, suite, arch, affinity, analysis):
    chroot_name = "{suite}-{affinity}".format(suite=suite, affinity=affinity)

    ensure_chroot_sanity(chroot_name)

    if not package.endswith('.dsc'):
        raise ValueError("WTF")

    out, err, ret = run_command([
        "sbuild",
        "--dist={suite}".format(suite=suite),
        "--arch={affinity}".format(affinity=affinity),
        "--chroot={chroot_name}".format(chroot_name=chroot_name),
        ("--arch-all" if arch == 'all' else '--no-arch-all'),
        "-v",
        "-j", "8",
        package,
    ])

    statusline = None
    summary = False
    for line in out.splitlines():
        if line == u"│ Summary                                                                      │":
            summary = True
        if summary and line.startswith("Status: "):
            statusline = line
            break

    if not statusline or statusline == "Status: failed":
        raise Exception("sbuild failed to run")

    ftbfs = ret != 0 or statusline != "Status: successful"
    base, _ = os.path.basename(package).rsplit(".", 1)
    changes = glob.glob("{base}_*.changes".format(base=base))

    return (analysis, out, ftbfs, changes)


def version():
    out, err, ret = run_command([
        "sbuild", '--version'
    ])
    if ret != 0:
        raise Exception("sbuild is not installed")
    vline = out.splitlines()[0]
    v = VERSION.match(vline)
    vdict = v.groupdict()
    return ('sbuild', vdict['version'])
