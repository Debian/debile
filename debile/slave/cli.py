# Copyright (c) 2012-2013 Paul Tagliamonte <paultag@debian.org>
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


from debile.utils.config import get_config
from debile.utils.xmlrpc import get_proxy


def daemon():
    from argparse import ArgumentParser
    parser = ArgumentParser(description="Debile build slave")
    parser.add_argument("--config", action="store", dest="config", default=None,
                        help="Path to the slave.yaml config file.")
    parser.add_argument("-s", "--syslog", action="store_true", dest="syslog",
                        help="Log to syslog instead of stderr.")
    parser.add_argument("-d", "--debug", action="store_true", dest="debug",
                        help="Enable debug messages to stderr.")

    args = parser.parse_args()
    config = get_config("slave.yaml", path=args.config)
    proxy = get_proxy(config)

    from debile.slave.daemon import main
    main(args, config, proxy)
