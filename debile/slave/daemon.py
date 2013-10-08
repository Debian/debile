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
from debile.utils.dud import Dud

from firehose.model import (Analysis, Generator, Metadata,
                            DebianBinary, DebianSource)

import logging
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
    logging.info("Initializing empty firehose report")
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
            if package['type'] == "source":
                server_info = proxy.get_info()
                src = package['source']
                archive = "{url}/{group}".format(
                    url=server_info['repo']['base'],
                    group=src['group'],
                )
                aget(archive, src['suite'], 'main', src['name'], src['version'])
                yield
            elif package['type'] == "binary":
                raise NotImplemented
            else:
                raise Exception


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

        with checkout(job, package):
            run, version = load_module(job['name'])
            firehose = create_firehose(package, version)

            type_ = package['type']
            if type_ == "source":
                target = glob.glob("*dsc")[0]
            elif type_ == "binary":
                target = glob.glob("*deb")
            else:
                raise Exception("Unknown type")

            firehose, log, job['failed'], changes = run(
                target, package, job, firehose)

            if changes:
                upload(changes, job, package)

            print package
            prefix = "%s" % (str(job['id']))
            dud = Dud()
            dud['Created-By'] = "Dummy Entry <dummy@example.com>"
            dud['Source'] = package['source']['name']
            dud['Version'] = package['source']['version']
            dud['Architecture'] = package['arch']
            dudf = "{prefix}.dud".format(prefix=prefix)

            open('{prefix}-firehose.xml'.format(prefix=prefix), 'wb').write(
                firehose.to_xml_bytes())
            open('{prefix}-log'.format(prefix=prefix), 'wb').write(log)

            dud.add_file('{prefix}-firehose.xml'.format(prefix=prefix))
            dud.add_file('{prefix}-log'.format(prefix=prefix))

            dud.write_dud(dudf)
            upload(dudf, job, package)



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
