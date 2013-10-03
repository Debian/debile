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

from base64 import b64decode
import datetime as dt
import SocketServer
import os.path
import os
import logging


class DebileMasterInterface(object):

    def get_server_info(self):
        """
        """
        return


class DebileMasterAuthMixIn(SimpleXMLRPCRequestHandler):
    def authenticate(self):
        (basic, _, encoded) = self.headers.get('Authorization').partition(' ')
        if basic.lower() != 'basic':
            self.send_error(401, 'Only allowed basic type thing')
        entity, password = b64decode(encoded.encode()).decode().split(":", 1)
        actor_type = self.headers.get('ActorType')  # Server or Machine
        actor_auth_methods = {
            "user": self.authenticate_user,
            "machine": self.authenticate_machine,
        }
        return actor_auth_methods[actor_type](entity, password)

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
    serve("0.0.0.0", 20017)


if __name__ == "__main__":
    main()
