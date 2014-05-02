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


from argparse import ArgumentParser
from debile.master.utils import init_master


def init():
    parser = ArgumentParser(description="Debile master database initialization")
    parser.add_argument("--config", action="store", dest="config", default=None,
                        help="Path to the master.yaml config file.")
    parser.add_argument("--force", action="store_true", dest="force", default=False,
                        help="Force initialization even if sanity checks fail.")
    parser.add_argument("file", action="store",
                        help="Yaml file with initial database.")

    args = parser.parse_args()
    config = init_master(args.config)

    from debile.master.dimport import main
    main(args, config)


def process_incoming():
    parser = ArgumentParser(description="Debile master incoming handling")
    parser.add_argument("--config", action="store", dest="config", default=None,
                        help="Path to the master.yaml config file.")
    parser.add_argument("--group", action="store", dest="group", default="default",
                        help="Group to use for uploads without a X-Debile-Group field")
    parser.add_argument("--no-dud", action="store_false", dest="dud",
                        help="Do not process *.dud files.")
    parser.add_argument("--no-changes", action="store_false", dest="changes",
                        help="Do not process *.changes files.")
    parser.add_argument("directory", action="store",
                        help="Directry to process.")

    args = parser.parse_args()
    config = init_master(args.config)

    from debile.master.incoming import main
    main(args, config)


def server():
    parser = ArgumentParser(description="Debile master daemon")
    parser.add_argument("--config", action="store", dest="config", default=None,
                        help="Path to the master.yaml config file.")
    parser.add_argument("-s", "--syslog", action="store_true", dest="syslog",
                        help="Log to syslog instead of stderr.")
    parser.add_argument("-d", "--debug", action="store_true", dest="debug",
                        help="Enable debug messages to stderr.")

    args = parser.parse_args()
    config = init_master(args.config)

    from debile.master.server import main
    main(args, config)
