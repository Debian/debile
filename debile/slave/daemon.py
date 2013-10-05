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

from firehose.model import (Analysis, Generator, Metadata,
                            DebianBinary, DebianSource)

from debile.slave.commands import PLUGINS, load_module
from debile.slave.client import get_proxy, checkout
from contextlib import contextmanager
from debile.slave.utils import tdir, cd, run_command
from debile.slave.core import config

import logging
import time
import shutil
import os

proxy = get_proxy()


class IDidNothingError(Exception):
    pass


def listize(entry):
    items = [x.strip() for x in entry.split(",")]
    return [None if x == "null" else x for x in items]


@contextmanager
def workon(suites, arches, capabilities):
    job = proxy.get_next_job(suites, arches, capabilities)
    if job is None:
        yield
    else:
        logging.info("Acquired job id=%s (%s) for %s/%s",
                     job['id'], job['name'], job['suite'], job['arch'])
        try:
            yield job
        except:
            logging.warn("Forfeiting the job because of internal exception")
            proxy.forfeit_job(job['id'])
            raise
        else:
            logging.info("Successfully closing the job")
            proxy.close_job(job['id'], job['failed'])


def iterate():
    arches = config['arches']
    suites = config['suites']
    checks = config.get('checks', list(PLUGINS.keys()))

    # job is a serialized dictionary from debile-master ORM
    with workon(suites, arches, checks) as job:
        if job is None:
            raise IDidNothingError("No more jobs")
        raise Exception


def main():
    logging.basicConfig(
        format='%(asctime)s - %(levelname)8s - [debile-slave] %(message)s',
        level=logging.DEBUG
    )
    logging.info("Booting debile-slave daemon")
    while True:
        try:
            logging.debug("Checking for new jobs")
            iterate()
        except IDidNothingError:
            logging.debug("Nothing to do for now, sleeping 30s")
            time.sleep(30)
        except Exception as e:
            logging.warning("Er, we got a fatal error: %s. Restarting" % (
                str(e)
            ))
            raise
            time.sleep(60)
