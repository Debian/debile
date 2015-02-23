# Copyright (c) 2012-2013 Paul Tagliamonte <paultag@debian.org>
# Copyright (c) 2013      Leo Cavaille <leo@cavaille.net>
# Copyright (c) 2014      Jon Severinsson <jon@severinsson.net>
# Copyright (c) 2014-2015 Clement Schreiner <clement@mux.me>
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

from SimpleXMLRPCServer import SimpleXMLRPCServer
from SimpleXMLRPCServer import SimpleXMLRPCRequestHandler
from sqlalchemy.sql import exists

from debile.utils.log import start_logging
from debile.master.utils import session
from debile.master.orm import Person, Builder, Job
from debile.master.interface import NAMESPACE, DebileMasterInterface

import SocketServer
import signal
import hashlib
import logging
import logging.handlers
import os.path
import ssl


def check_shutdown():
    with session() as s:
        shutdown = not s.query(exists().where(
            (Job.assigned_at != None) & (Job.finished_at == None))
        ).scalar()
        if shutdown:
            raise SystemExit(0)


class DebileMasterAuthMixIn(SimpleXMLRPCRequestHandler):
    def authenticate(self):
        cert = self.connection.getpeercert(True)
        fingerprint = hashlib.sha1(cert).hexdigest().upper()

        NAMESPACE.machine = NAMESPACE.session.query(Builder).filter_by(
            ssl=fingerprint
        ).first()
        NAMESPACE.user = NAMESPACE.session.query(Person).filter_by(
            ssl=fingerprint
        ).first()

        return NAMESPACE.machine or NAMESPACE.user

    def parse_request(self, *args):
        if SimpleXMLRPCRequestHandler.parse_request(self, *args):
            if self.authenticate():
                return True
            else:
                self.send_error(401, 'Authentication failed')
        return False

    def handle_one_request(self):
        try:
            with session() as s:
                NAMESPACE.session = s
                SimpleXMLRPCRequestHandler.handle_one_request(self)
        finally:
            NAMESPACE.session = None
            NAMESPACE.machine = None
            NAMESPACE.user = None

        if DebileMasterInterface.shutdown_request:
            check_shutdown()

class DebileMasterSimpleAuthMixIn(SimpleXMLRPCRequestHandler):
    def authenticate(self):
        client_address, _ = self.client_address
        NAMESPACE.machine = NAMESPACE.session.query(Builder).filter_by(
            ip=client_address
        ).first()

        NAMESPACE.user = NAMESPACE.session.query(Person).filter_by(
            ip=client_address
        ).first()

        return NAMESPACE.machine or NAMESPACE.user

    def parse_request(self, *args):
        if SimpleXMLRPCRequestHandler.parse_request(self, *args):
            if self.authenticate():
                return True
            else:
                self.send_error(401, 'Authentication failed')
        return False

    def handle_one_request(self):
        try:
            with session() as s:
                NAMESPACE.session = s
                SimpleXMLRPCRequestHandler.handle_one_request(self)
        finally:
            NAMESPACE.session = None
            NAMESPACE.machine = None
            NAMESPACE.user = None

        if DebileMasterInterface.shutdown_request:
            check_shutdown()


class SimpleAsyncXMLRPCServer(SocketServer.ThreadingMixIn,
                             DebileMasterSimpleAuthMixIn):
    pass


class AsyncXMLRPCServer(SocketServer.ThreadingMixIn, DebileMasterAuthMixIn):
    pass


class SimpleAuthXMLRPCServer(SimpleXMLRPCServer):
    def __init__(self, addr,
                 requestHandler=SimpleXMLRPCRequestHandler,
                 bind_and_activate=True,
                 allow_none=False):
        SimpleXMLRPCServer.__init__(self, addr,
                                    requestHandler=requestHandler,
                                    bind_and_activate=bind_and_activate,
                                    allow_none=allow_none)



class SecureXMLRPCServer(SimpleXMLRPCServer):
    def __init__(
        self, addr, keyfile, certfile, ca_certs,
        requestHandler=SimpleXMLRPCRequestHandler, logRequests=True,
        allow_none=False, encoding=None, bind_and_activate=True
    ):
        SimpleXMLRPCServer.__init__(self, addr,
                                    requestHandler=requestHandler,
                                    logRequests=logRequests,
                                    allow_none=allow_none,
                                    encoding=encoding,
                                    bind_and_activate=False)

        cert_reqs = (ssl.CERT_NONE if ca_certs is None
                     else ssl.CERT_REQUIRED)
        self.socket = ssl.wrap_socket(self.socket,
                                      keyfile=keyfile, certfile=certfile,
                                      ca_certs=ca_certs, cert_reqs=cert_reqs,
                                      ssl_version=ssl.PROTOCOL_TLSv1)

        if bind_and_activate:
            self.server_bind()
            self.server_activate()


def serve(server_addr, port, auth_method,
          keyfile=None, certfile=None, ssl_keyring=None, pgp_keyring=None):
    logger = logging.getLogger('debile')
    logger.info("Serving on `{server_addr}' on port `{port}'".format(**locals()))
    logger.info("Authentication method: {0}".format(auth_method))
    if auth_method == 'ssl':
        logger.info("Using keyfile=`{keyfile}', certfile=`{certfile}', "
                    "ssl_keyring=`{ssl_keyring}'".format(**locals()))
    logger.info("Using pgp_keyring=`{pgp_keyring}'".format(**locals()))

    server = None
    if auth_method == 'simple':
        server = SimpleAuthXMLRPCServer((server_addr, port),
                                   requestHandler=SimpleAsyncXMLRPCServer,
                                   allow_none=True)

    else:
        server = SecureXMLRPCServer((server_addr, port), keyfile, certfile,
                                ca_certs=ssl_keyring,
                                requestHandler=AsyncXMLRPCServer,
                                allow_none=True)

    server.register_introspection_functions()
    server.register_instance(DebileMasterInterface(ssl_keyring, pgp_keyring))
    server.serve_forever()

def system_exit_handler(signum, frame):
    raise SystemExit(1)


def shutdown_request_handler(signum, frame):
    DebileMasterInterface.shutdown_request = True
    check_shutdown()


def main(args, config):
    start_logging(args)

    signal.signal(signal.SIGQUIT, system_exit_handler)
    signal.signal(signal.SIGABRT, system_exit_handler)
    signal.signal(signal.SIGTERM, system_exit_handler)

    signal.signal(signal.SIGHUP,  signal.SIG_IGN)
    signal.signal(signal.SIGUSR1, shutdown_request_handler)

    logger = logging.getLogger('debile')

    if not os.path.isfile(config['keyrings']['pgp']):
        logger.info("Can not find pgp keyring `{file}'".format(file=config['keyrings']['pgp']))

    if args.auth_method == 'ssl':
        if not os.path.isfile(config['xmlrpc']['keyfile']):
            logger.error("Can not find ssl keyfile `{file}'".format(file=config['xmlrpc']['keyfile']))
        if not os.path.isfile(config['xmlrpc']['certfile']):
            logger.error("Can not find ssl certfile `{file}'".format(file=config['xmlrpc']['certfile']))
        if not os.path.isfile(config['keyrings']['ssl']):
            logger.error("Can not find ssl keyring `{file}'".format(file=config['keyrings']['ssl']))

    serve(config['xmlrpc']['addr'], config['xmlrpc']['port'],
          args.auth_method,
          config['xmlrpc'].get('keyfile'),
          config['xmlrpc'].get('certfile'),
          config['keyrings'].get('ssl'),
          config["keyrings"].get('pgp'))
