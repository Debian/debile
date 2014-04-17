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
from debile.slave.core import config
from debile.slave.utils import tdir, cd, upload
from debile.utils.commands import safe_run
from debile.utils.log import start_logging
from debile.utils.xmlrpc import get_proxy
from debile.utils.deb822 import Changes

from contextlib import contextmanager
from firehose.model import (Analysis, Generator, Metadata,
                            DebianBinary, DebianSource)

import logging
import time

proxy = get_proxy(config)


class IDidNothingException(Exception):
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
    logger.debug("Checking for new jobs")

    job = proxy.get_next_job(suites, components, arches, capabilities)
    if job is None:
        logger.info("Nothing to do for now")
        raise IDidNothingException

    logger.info(
        "Acquired job id=%s (%s %s) for %s",
        job['id'],
        job['source'],
        job['name'],
        job['suite'],
    )

    try:
        yield job
    except (SystemExit, KeyboardInterrupt):
        logger.info("Forfeiting the job because of shutdown request")
        proxy.forfeit_job(job['id'])
        raise
    except:
        logger.warn("Forfeiting the job because of internal exception", exc_info=True)
        proxy.forfeit_job(job['id'])
        raise
    else:
        logger.info("Successfully closing the job")
        proxy.close_job(job['id'], job['failed'])


def run_job(job):
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


def main(args):
    start_logging(args)

    # Reset the logging config in python-dput and use the global config instead
    dputlog = logging.getLogger('dput')
    dputlog.propagate = True
    dputlog.setLevel(logging.NOTSET)
    while len(dputlog.handlers) > 0:
        dputlog.removeHandler(dputlog.handlers[-1])

    suites = config['suites']
    components = config['components']
    arches = config['arches']
    checks = config.get('checks', list(PLUGINS.keys()))

    while True:
        try:
            with workon(suites, components, arches, checks) as job:
                run_job(job)
        except KeyboardInterrupt:
            raise SystemExit(1)
        except SystemExit:
            raise
        except:
            time.sleep(60)
