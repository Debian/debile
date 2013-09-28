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

from debile.slave.utils import tdir, cd, dget, run_command
from debile.slave.config import Config

from contextlib import contextmanager
import xmlrpclib
import os


def get_proxy():
    config = Config()
    proxy = xmlrpclib.ServerProxy(
        "http://{user}:{password}@{host}:{port}/".format(
            user=config.get('master', 'user'),
            password=config.get('master', 'password'),
            host=config.get('master', 'host'),
            port=config.get('master', 'port')
        ), allow_none=True)
    return proxy


@contextmanager
def checkout(package):
    proxy = get_proxy()
    _type = package['type']
    if _type not in ['binary', 'source']:
        raise ValueError("type sucks")

    def source():
        url = proxy.get_dsc_url(package['source_id'])
        dsc = os.path.basename(url)
        dget(url)
        yield dsc

    def binary():
        url = proxy.get_deb_url(package['binary_id'])
        deb = os.path.basename(url)
        out, err, ret = run_command(['wget', url])
        if ret != 0:
            raise Exception("zomgwtf")
        yield deb

    with tdir() as where:
        with cd(where):
            for x in {"source": source, "binary": binary}[_type]():
                yield x
