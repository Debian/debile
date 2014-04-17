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

import os
import sys
import logging
import traceback


class DebileFormatter(logging.Formatter):
    def __init__(self, fmt=None, datefmt="%Y-%m-%d %H:%M:%S", traceback=False):
        logging.Formatter.__init__(self, fmt=fmt, datefmt=datefmt)
        self._traceback = traceback

    def format(self, record):
        if not record.exc_info:
            return logging.Formatter.format(self, record)

        record.exc_text = self.formatException(record.exc_info)
        ret = logging.Formatter.format(self, record)
        record.exc_text = None
        return ret

    def formatException(self, exc_info):
        type, value, tb = exc_info
        if self._traceback:
            return "".join(traceback.format_exception(type, value, tb))
        return traceback.format_exception_only(type, value)[-1]


def start_logging(args):
    prog = os.path.basename(sys.argv[0])
    pid = os.getpid()

    logging.getLogger('').setLevel(logging.DEBUG)

    if args.syslog:
        handler = logging.handlers.SysLogHandler(address="/dev/log")
        handler.setLevel(logging.INFO)
        handler.setFormatter(
            DebileFormatter(
                fmt="{prog}[{pid}]: %(levelname)s - %(message)s".format(prog=prog, pid=pid),
                traceback=False,
            )
        )
        logging.getLogger('').addHandler(handler)

    if args.debug or not args.syslog:
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG if args.debug else logging.INFO)
        handler.setFormatter(
            DebileFormatter(
                fmt="%(asctime)s [{prog}] %(levelname)8s - %(message)s".format(prog=prog),
                traceback=args.debug,
            )
        )
        logging.getLogger('').addHandler(handler)

    logger = logging.getLogger('debile')
    logger.info("Booting {prog} daemon".format(prog=prog))
