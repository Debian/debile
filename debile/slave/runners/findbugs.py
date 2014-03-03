# Copyright (c) 2012-2013 Paul Tagliamonte <paultag@debian.org>
# Copyright (c) 2013 Leo Cavaille <leo@cavaille.net>
# Copyright (c) 2013 Sylvestre Ledru <sylvestre@debian.org>
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

from debile.slave.wrappers.findbugs import parse_findbugs
from debile.slave.utils import cd
from debile.utils.commands import run_command


def findbugs(deb, analysis):
    run_command(["dpkg", "-x", deb, "binary"])
    with cd('binary'):
        out, err, ret = run_command([
            'fb', 'analyze', '-effort:max', '-xml:withMessages', '.'
        ])

        xmlbytes = out.encode("utf-8")

        failed = False
#        if err.strip() == '':
#            return (analysis, err, failed)

        for issue in parse_findbugs(xmlbytes):
            analysis.results.append(issue)
            if not failed and issue.severity in [
                'performance', 'portability', 'error', 'warning'
            ]:
                failed = True

        return (analysis, err, failed, None)


def version():
    out, err, ret = run_command([
        'fb', '-version'
    ])
    if ret != 0:
        raise Exception("findbugs is not installed")
    name, version = out.split(" ")
    return (name, version.strip())
