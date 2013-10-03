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

#from debile.master.orm import 

from SimpleXMLRPCServer import SimpleXMLRPCServer
from SimpleXMLRPCServer import SimpleXMLRPCRequestHandler

from sqlalchemy.orm.exc import NoResultFound

from debile.master.utils import session
from debile.master.orm import Person, Builder

from base64 import b64decode
import datetime as dt
import SocketServer
import threading
import logging
import os.path
import os

NAMESPACE = threading.local()


def machine_method(fn):
    def _(*args, **kwargs):
        try:
            get_builder()
            return fn(*args, **kwargs)
        except KeyError:
            raise Exception("You can't do that")
    return _


def user_method(fn):
    def _(*args, **kwargs):
        try:
            get_user()
            return fn(*args, **kwargs)
        except KeyError:
            raise Exception("You can't do that")
    return _


class DebileMasterInterface(object):

    def hello(self):
        return "Ohai"


class DebileMasterAuthMixIn(SimpleXMLRPCRequestHandler):
    def authenticate(self):

        NAMESPACE.machine = None
        NAMESPACE.user = None

        (basic, _, encoded) = self.headers.get('Authorization').partition(' ')
        if basic.lower() != 'basic':
            self.send_error(401, 'Only allowed basic type thing')
        entity, password = b64decode(encoded.encode()).decode().split(":", 1)

        actor_auth_methods = {
            "@": self.authenticate_user,
            "%": self.authenticate_machine,
        }

        actor_type = entity[0]
        entity = entity[1:]

        try:
            method = actor_auth_methods[actor_type]
        except KeyError:
            return False

        with session() as s:
            return method(s, entity, password)

    def authenticate_user(self, session, entity, password):
        try:
            luser = session.query(Person).filter_by(username=entity).one()
            NAMESPACE.user = luser
            return luser.validate(password)
        except NoResultFound:
            return False

    def authenticate_machine(self, session, entity, password):
        try:
            machine = session.query(Builder).filter_by(name=entity).one()
            NAMESPACE.machine = machine
            return machine.validate(password)
        except NoResultFound:
            return False

    def parse_request(self, *args):
        if SimpleXMLRPCRequestHandler.parse_request(self, *args):
            if self.authenticate():
                return True
            else:
                self.send_error(401, 'Authentication failed')
        return False


class AsyncXMLRPCServer(SocketServer.ThreadingMixIn, DebileMasterAuthMixIn):
    pass


def serve(server, port):
    print("Serving on `{server}' on port `{port}'".format(**locals()))
    server = SimpleXMLRPCServer((server, port),
                                requestHandler=AsyncXMLRPCServer,
                                allow_none=True)
    server.register_introspection_functions()
    server.register_instance(DebileMasterInterface())
    server.serve_forever()


def main():
    logging.basicConfig(
        format='%(asctime)s - %(levelname)8s - [debile-master] %(message)s',
        level=logging.DEBUG
    )
    logging.info("Booting debile-masterd daemon")
    serve("0.0.0.0", 22017)


def get_builder():
    if NAMESPACE.machine is None:
        raise KeyError("What the shit, doing something you can't do")
    return NAMESPACE.machine


def get_user():
    if NAMESPACE.user is None:
        raise KeyError("What the shit, doing something you can't do")
    return NAMESPACE.user


if __name__ == "__main__":
    main()
