# Copyright (c) 2012-2013 Paul Tagliamonte <paultag@debian.org>
# Copyright (c) 2013 Leo Cavaille <leo@cavaille.net>
# Copyright (c) 2014 Clement Schreiner <clement@mux.me>
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

from debile.slave.wrappers.coccinelle import parse_coccinelle
from debile.slave.utils import cd
from debile.utils.commands import run_command
import os.path
import os
import glob
import logging

logger = logging.getLogger('debile')

def list_semantic_patches():
    root = os.path.join(os.environ['HOME'], 'coccinellery/CONTRIB/firehose')
    return glob.iglob(os.path.join(root, "*/*.cocci"))


def coccinelle(dsc, analysis):
    run_command(["dpkg-source", "-x", dsc, "source"])
    os.environ['COCCI_SUT_TYPE'] = 'debian-source' # used by coccinelle firehose scripts

    with cd('source'):
        log = ""
        failed = False
        for semantic_patch in list_semantic_patches():
            logger.debug('Running patch: {0}'.format(semantic_patch))
            out, err, ret = run_command([
                "spatch",
                "-D", "firehose",
                "--cocci-file", semantic_patch,
                "--dir", ".",
                "--no-show-diff",
                "--timeout", "120",
            ])


            failed = (ret != 0) or failed
            logger.debug('Spatch output: {0}'.format(out))
            logger.debug('Spatch err: {0}'.format(err))
            parsed_results = parse_coccinelle(out)

            result_count = 0
            for result in parsed_results:
                analysis.results.append(result)
                result_count += 1

            log += "DEAL patch %s\n" % semantic_patch
            log += "  %d results\n" % result_count

    return (analysis, log, failed, None, None)


def version():
    out, err, ret = run_command(["spatch", "--version"])
    if ret != 0:
        raise Exception("spatch seems not to be installed")
    try:
        out = out.split()[2]  # we only extract the version number
    except:
        out = out.strip()

    return ('coccinelle', out)
