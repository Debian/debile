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

from debile.slave.commands import PLUGINS, load_module
from debile.slave.client import get_proxy
from contextlib import contextmanager
from debile.slave.core import config
from debile.slave.utils import tdir, cd, upload
from debile.utils.aget import aget
from debile.utils.bget import bget
from debile.utils.dud import Dud_
from dput.exceptions import DputError, DcutError

from firehose.model import (Analysis, Generator, Metadata,
                            DebianBinary, DebianSource)

import logging
from logging.handlers import SysLogHandler
import glob
import time

proxy = get_proxy()


class IDidNothingError(Exception):
    pass


def listize(entry):
    items = [x.strip() for x in entry.split(",")]
    return [None if x == "null" else x for x in items]


def generate_sut_from_source(package):
    name = package['name']
    version = package['version']
    local = None
    if "-" in version:
        version, local = version.rsplit("-", 1)
    return DebianSource(name, version, local)


def generate_sut_from_binary(package):
    name = package['name']
    version = package['version']
    arch = package['arch']
    local = None
    if "-" in version:
        version, local = version.rsplit("-", 1)
    return DebianBinary(name, version, local, arch)


def create_firehose(package, version_getter):
    logger = logging.getLogger('debile')
    logger.info("Initializing empty firehose report")
    sut = {
        "source": generate_sut_from_source,
        "binary": generate_sut_from_binary
    }[package['type']](package)

    gname_, gversion = version_getter()
    gname = "debile/%s" % gname_

    return Analysis(metadata=Metadata(
        generator=Generator(name=gname, version=gversion),
        sut=sut, file_=None, stats=None), results=[])


@contextmanager
def checkout(job, package):
    with tdir() as path:
        with cd(path):
            src = package['source']
            archive = proxy.get_archive_location(src['group'])
            if package['type'] == "source":
                yield aget(archive, src['suite'], 'main',
                           src['name'], src['version'])
            elif package['type'] == "binary":
                arch = job['arch']
                if arch == 'all':
                    arch = 'amd64'  # XXX: THIS IS A HACK. FIX THIS.
                yield bget(archive, src['suite'], 'main',
                           arch, src['name'], src['version'])
            else:
                raise Exception


@contextmanager
def workon(suites, arches, capabilities):
    logger = logging.getLogger('debile')
    job = proxy.get_next_job(suites, arches, capabilities)
    if job is None:
        yield
    else:
        logger.info("Acquired job id=%s (%s) for %s/%s",
                     job['id'], job['name'], job['suite'], job['arch'])
        try:
            yield job
        except:
            logger.warn("Forfeiting the job because of internal exception")
            proxy.forfeit_job(job['id'])
            raise
        else:
            logger.info("Successfully closing the job")
            proxy.close_job(job['id'], job['failed'])


def iterate():
    arches = config['arches']
    suites = config['suites']
    checks = config.get('checks', list(PLUGINS.keys()))

    # job is a serialized dictionary from debile-master ORM
    with workon(suites, arches, checks) as job:
        if job is None:
            raise IDidNothingError("No more jobs")

        source = proxy.get_source(job['source_id'])

        package = {
            "name": source['name'],
            "version": source['version'],
            "type": "source",
            "arch": "all",
            "source": source,
            "binary": None,
        }

        if job['binary_id']:
            binary = proxy.get_binary(job['binary_id'])
            package = {
                "name": binary['name'],
                "version": binary['version'],
                "type": "binary",
                "arch": binary['arch'],
                "source": source,
                "binary": binary,
            }

        with checkout(job, package) as check:
            run, version = load_module(job['name'])
            firehose = create_firehose(package, version)

            type_ = package['type']
            if type_ == "source":
                target = check  # Only get one.
            elif type_ == "binary":
                target = check  # tons and tons
            else:
                raise Exception("Unknown type")

            firehose, log, failed, changes = run(
                target, package, job, firehose)

            prefix = "%s" % (str(job['id']))

            dudf = "{prefix}.dud".format(prefix=prefix)
            dud = Dud_()
            dud['Created-By'] = "Dummy Entry <dummy@example.com>"
            dud['Source'] = package['source']['name']
            dud['Version'] = package['source']['version']
            dud['Architecture'] = package['arch']
            dud['X-Debile-Failed'] = "Yes" if failed else "No"
            if type_ == 'binary':
                dud['Binary'] = package['binary']['name']

            job['failed'] = failed

            with open('{prefix}.firehose.xml'.format(
                    prefix=prefix), 'wb') as fd:
                fd.write(firehose.to_xml_bytes())

            dud.add_file('{prefix}.firehose.xml'.format(prefix=prefix))

            with open('{prefix}.log'.format(prefix=prefix), 'wb') as fd:
                fd.write(log.encode('utf-8'))

            dud.add_file('{prefix}.log'.format(prefix=prefix))

            with open(dudf, 'w') as fd:
                dud.dump(fd=fd)

            if changes:
                upload(changes, job, package)
            upload(dudf, job, package)


def main():
    logging.basicConfig(
        format='%(asctime)s - %(levelname)8s - [debile-master] %(message)s',
        level=logging.DEBUG
    )

    #logger = logging.getLogger('debile')
    #logger.setLevel(logging.DEBUG)
    #syslog = SysLogHandler(address='/dev/log')
    #formatter = logging.Formatter('[debile-slave] %(levelname)7s - %(message)s')
    #syslog.setFormatter(formatter)
    #logger.addHandler(syslog)
    #logger.info("Booting debile-slave daemon")

    logger = logging
    logger.info("Booting debile-masterd daemon")

    while True:
        try:
            logger.debug("Checking for new jobs")
            iterate()
        except IDidNothingError:
            logger.debug("Nothing to do for now, sleeping 30s")
            time.sleep(30)
        except (DputError, DcutError, Exception) as e:
            logger.warning(
                "Er, we got a fatal error: %s. Restarting in a minute" % (
                    str(e)
            ))

            import traceback
            logger.warning(traceback.format_exc())

            time.sleep(60)
