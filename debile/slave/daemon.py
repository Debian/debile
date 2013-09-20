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

from debileslave.commands import PLUGINS, load_module
from debileslave.client import get_proxy, checkout
from contextlib import contextmanager
from debileslave.utils import tdir, cd, run_command
from debileslave.config import Config

import logging
import time
import shutil
import os

config = Config()
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
                     job['id'], job['type'], job['suite'], job['arch'])
        try:
            yield job
        except:
            logging.warn("Forfeiting the job because of internal exception")
            print job
            proxy.forfeit_job(job['id'])
            raise
        else:
            logging.info("Successfully closing the job")
            proxy.close_job(job['id'], job['failed'])


def generate_sut_from_source(package):
    name = package['name']
    local = None
    version = package['version']
    if "-" in version:
        version, local = version.rsplit("-", 1)
    return DebianSource(name, version, local)


def generate_sut_from_binary(package):
    arch = package['arch']
    name = package['name']
    local = None
    version = package['version']
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


def iterate():
    suites = listize(config.get('capabilities', 'suites'))
    arches = listize(config.get('capabilities', 'arches'))

    # job is a serialized dictionary from debile-master ORM
    with workon(suites, arches, list(PLUGINS.keys())) as job:
        if job is None:
            raise IDidNothingError("No more jobs")

        package = job['package']

        # Retrieve functions in the module to launch the command and version
        handler, version_getter = load_module(job['type'])
        # Create an empty firehose report with SUT metadata
        firehose = create_firehose(package, version_getter)

        with tdir() as fd:
            with cd(fd):
                with checkout(package) as target:
                    firehose, log, failed = handler(target, package,
                                                    job, firehose)

                    logging.info("Job worker returned, filing reports")
#                    report = proxy.submit_report(firehose.to_json(),
#                                                 job['_id'], err)

                    logging.info("Sending the XML firehose report to the pool")
                    open('firehose.xml', 'w').write(firehose.to_xml_bytes())
                    remote_firehose_path = \
                        proxy.get_write_location(job['id'])
                    remote_firehose_path = \
                        os.path.join(remote_firehose_path, 'firehose.xml')
                    cmd = config.get('master', 'copy')\
                        .format(src='firehose.xml', dest=remote_firehose_path)
                    out, err, ret = run_command(cmd)
                    ### SCANDALOUS HACK
                    ### failed contains potential scan-build report directory
                    if job['type'] == 'clanganalyzer':
                        if len(failed) == 0:
                            job['failed'] = False
                        else:
                            job['failed'] = True
                            remote_scanbuild_path = \
                                proxy.get_write_location(job['id'])
                            remote_scanbuild_path = \
                                os.path.join(
                                    remote_scanbuild_path,
                                    'scan-build')
                            cmd = config.get('master', 'copy')\
                                .format(src=failed[0],
                                        dest=remote_scanbuild_path)
                            out, err, ret = run_command(cmd)
                            shutil.rmtree(failed[0])
                    else:
                        job['failed'] = failed

                    logging.info("Sending the logs to the pool")
                    remote_log_path = proxy.get_write_location(job['id'])
                    remote_log_path = os.path.join(remote_log_path, 'log.txt')
                    open('job-log', 'wb').write(log.encode('utf-8'))
                    cmd = config.get('master', 'copy')\
                        .format(src='job-log', dest=remote_log_path)
                    out, err, ret = run_command(cmd)
                    if ret != 0:
                        print(out)
                        raise Exception("SHIT.")


def regenerate_dputcf():
    dputcf = proxy.get_dputcf()
    dputcf_file = os.path.join(os.environ['HOME'], '.dput.cf')
    with open(dputcf_file, 'w') as f:
        f.write(dputcf)


def main():
    logging.basicConfig(
        format='%(asctime)s - %(levelname)8s - [debile-slave] %(message)s',
        level=logging.DEBUG)
    logging.info("Booting debile-slave daemon")
    while True:
        try:
            logging.debug("Regenerating dput.cf")
            regenerate_dputcf()
            logging.debug("Checking for new jobs")
            iterate()
        except IDidNothingError:
            logging.debug("Nothing to do for now, sleeping 30s")
            time.sleep(30)
        except Exception as e:
            logging.warning("Er, we got a fatal error: %s. Restarting" % (
                str(e)
            ))
            time.sleep(60)
