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


def init():
    from debile.master.orm import init_db
    return init_db()


def process_incoming():
    import debile.master.incoming_changes
    import debile.master.incoming_dud
    import sys

    for mod in [debile.master.incoming_changes, debile.master.incoming_dud]:
        getattr(mod, 'process_directory')(*sys.argv[1:])


def process_incoming_changes():
    from debile.master.incoming_changes import process_directory
    import sys
    return process_directory(*sys.argv[1:])


def process_incoming_dud():
    from debile.master.incoming_dud import process_directory
    import sys
    return process_directory(*sys.argv[1:])


def import_db():
    from debile.master.dimport import import_from_yaml
    import sys
    return import_from_yaml(*sys.argv[1:])


def serve():
    from debile.master.server import main
    import sys
    return main(*sys.argv[1:])
