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

from firehose.model import Issue, Message, File, Location, Point
import re


LINE_RE = re.compile(
    r"(?P<path>.*):(?P<line>\d+):(?P<col>\d+): (?P<err>[^ ]+) (?P<msg>.*)"
)


def parse_pep8(lines):
    for line in lines:
        info = LINE_RE.match(line).groupdict()
        severity = "error" if info['err'].startswith("E") else "warning"
        yield Issue(cwe=None,
                    testid=info['err'],
                    location=Location(file=File(info['path'], None),
                                      function=None,
                                      point=Point(*(int(x) for x in (
                                          info['line'], info['col'])))),
                    severity=severity,
                    message=Message(text=line),
                    notes=None,
                    trace=None)
