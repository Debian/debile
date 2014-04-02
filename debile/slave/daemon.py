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
from contextlib import contextmanager
from debile.slave.core import config
from debile.slave.utils import tdir, cd, upload
from debile.utils.commands import safe_run
from debile.utils.xmlrpc import get_proxy
from debile.utils.deb822 import Changes
from dput.exceptions import DputError, DcutError

from firehose.model import (Analysis, Generator, Metadata,
                            DebianBinary, DebianSource)

import logging
# from logging.handlers import SysLogHandler
import time

proxy = get_proxy(config)


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
def checkout(package):
    with tdir() as path:
        with cd(path):
            if package['type'] == "source":
                safe_run(["dget", "-u", "-d", package['source']['dsc_url']])
                yield package['source']['dsc_filename']
            elif package['type'] == "binary":
                files = []
                for deb in package['binary']['debs']:
                    files += [deb['filename']]
                    safe_run(["dget", "-u", "-d", deb['url']])
                yield files
            else:
                raise Exception


@contextmanager
def workon(suites, components, arches, capabilities):
    logger = logging.getLogger('debile')
    job = proxy.get_next_job(suites, components, arches, capabilities)
    if job is None:
        yield
    else:
        logger.info(
            "Acquired job id=%s (%s) for %s/%s",
            job['id'],
            job['name'],
            job['suite'],
            job['arch']
        )
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
    components = config['components']
    checks = config.get('checks', list(PLUGINS.keys()))

    # job is a serialized dictionary from debile-master ORM
    with workon(suites, components, arches, checks) as job:
        if job is None:
            raise IDidNothingError("No more jobs")

        group = job['group_obj']
        source = job['source_obj']
        binary = job['binary_obj']

        package = {
            "name": source['name'],
            "version": source['version'],
            "type": "source" if binary is None else "binary",
            "arch": job['arch'],
            "suite": source['suite'],
            "component": source['component'],
            "group": group,
            "source": source,
            "binary": binary,
        }

        with checkout(package) as target:
            run, version = load_module(job['check'])
            firehose = create_firehose(package, version)

            firehose, log, failed, changes = run(
                target, package, job, firehose)

            _, _, v = source['version'].rpartition(":")
            prefix = "%s_%s_%s.%d" % (source['name'], v, job['arch'], job['id'])

            dudf = "{prefix}.dud".format(prefix=prefix)
            dud = Changes()
            dud['Created-By'] = "Dummy Entry <dummy@example.com>"
            dud['Source'] = package['source']['name']
            dud['Version'] = package['source']['version']
            dud['Architecture'] = package['arch']
            dud['X-Debile-Failed'] = "Yes" if failed else "No"
            if package['type'] == 'binary':
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
        format='%(asctime)s - %(levelname)8s - [debile-slave] %(message)s',
        level=logging.DEBUG
    )

    #logger = logging.getLogger('debile')
    #logger.setLevel(logging.DEBUG)
    #syslog = SysLogHandler(address='/dev/log')
    #formatter = logging.Formatter(
    #                '[debile-slave] %(levelname)7s - %(message)s')
    #syslog.setFormatter(formatter)
    #logger.addHandler(syslog)
    #logger.info("Booting debile-slave daemon")

    logger = logging
    logger.info("Booting debile-slave daemon")

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
                    str(e)))

            import traceback
            logger.warning(traceback.format_exc())

            time.sleep(60)
