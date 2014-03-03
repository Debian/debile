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

import sys
import shlex
import subprocess

if sys.hexversion < 0x03000000:
    unicode_type = unicode
    binary_type = str
else:
    unicode_type = str
    binary_type = bytes


class SubprocessError(Exception):
    def __init__(self, out, err, ret, cmd):
        self.out = out
        self.err = err
        self.ret = ret
        self.cmd = cmd


# Input may be a byte string, a unicode string, or a file-like object
def run_command(command, input=None):
    if not isinstance(command, list):
        command = shlex.split(command)

    if not input:
        input = None
    elif isinstance(input, unicode_type):
        input = input.encode('utf-8')
    elif not isinstance(input, binary_type):
        input = input.read()

    try:
        pipe = subprocess.Popen(command,
                                shell=False,
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                )
    except OSError:
        return (None, None, -1)

    (output, stderr) = pipe.communicate(input=input)
    (output, stderr) = (c.decode('utf-8', errors='ignore') for c in (output, stderr))
    return (output, stderr, pipe.returncode)


def safe_run(cmd, input=None, expected=0):
    if not isinstance(expected, tuple):
        expected = (expected, )

    out, err, ret = run_command(cmd, input=input)

    if not ret in expected:
        raise SubprocessError(out, err, ret, cmd)

    return out, err, ret
