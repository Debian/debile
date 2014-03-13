# Copyright (c) 2012-2013 Paul Tagliamonte <paultag@debian.org>
# Copyright (c) 2013      Leo Cavaille <leo@cavaille.net>
# Copyright (c) 2014      Jon Severinsson <jon@severinsson.net>
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

from sqlalchemy.orm import sessionmaker

import debile.master.core
from debile.master.core import config
from debile.master.orm import Person, Builder

from logging.handlers import SysLogHandler
import SocketServer
import threading
import hashlib
import logging
import ssl

NAMESPACE = threading.local()


def get_builder():
    if NAMESPACE.machine is None:
        raise KeyError("What the shit, doing something you can't do")
    return NAMESPACE.machine


def builder_method(fn):
    def _(*args, **kwargs):
        try:
            get_builder()
            return fn(*args, **kwargs)
        except KeyError:
            raise Exception("You can't do that")
    return _


def get_user():
    if NAMESPACE.user is None:
        raise KeyError("What the shit, doing something you can't do")
    return NAMESPACE.user


def user_method(fn):
    def _(*args, **kwargs):
        try:
            get_user()
            return fn(*args, **kwargs)
        except KeyError:
            raise Exception("You can't do that")
    return _


def set_session():
    Session = sessionmaker(bind=debile.master.core.engine)
    session = Session()
    NAMESPACE.session = session


class DebileMasterAuthMixIn(SimpleXMLRPCRequestHandler):
    def authenticate(self):

        NAMESPACE.machine = None
        NAMESPACE.user = None
        if not hasattr(NAMESPACE, 'session'):
            set_session()

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


class AsyncXMLRPCServer(SocketServer.ThreadingMixIn, DebileMasterAuthMixIn):
    pass


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

        cert_reqs = ssl.CERT_NONE if ca_certs is None else ssl.CERT_OPTIONAL
        self.socket = ssl.wrap_socket(self.socket,
                                      keyfile=keyfile, certfile=certfile,
                                      ca_certs=ca_certs, cert_reqs=cert_reqs)

        if bind_and_activate:
            self.server_bind()
            self.server_activate()


def serve(server, port, keyfile, certfile, ca_certs):
    # Don't move the stuff below above; it would cause a circular
    # import; since it needs some of our kruft. I know it's bad form
    # but I'm tired of it.
    from debile.master.interface import DebileMasterInterface
    logger = logging.getLogger('debile')
    logger.info("Serving on `{server}' on port `{port}'".format(**locals()))
    server = SecureXMLRPCServer((server, port), keyfile, certfile, ca_certs,
                                requestHandler=AsyncXMLRPCServer,
                                allow_none=True)
    server.register_introspection_functions()
    server.register_instance(DebileMasterInterface())
    server.serve_forever()


def main():
    xml = config["xmlrpc"]
    keyrings = config["keyrings"]

    logger = logging.getLogger('debile')
    logger.setLevel(logging.DEBUG)
    syslog = SysLogHandler(address='/dev/log')
    formatter = logging.Formatter(
        '[debile-master] %(levelname)7s - %(message)s'
    )
    syslog.setFormatter(formatter)
    logger.addHandler(syslog)

    logger.info("Booting debile-masterd daemon")
    serve(xml["addr"], xml["port"], xml["keyfile"],
          xml["certfile"], keyrings["ssl"])


if __name__ == "__main__":
    main()
