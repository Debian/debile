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

from firehose.model import Issue, Message, File, Location
import re

OUTPUT_REGEX = re.compile(r"(?P<package>.*): (?P<tag>[^\s]*) (?P<info>.*)")


def parse_adequate(lines):
    for line in lines:
        info = OUTPUT_REGEX.match(line).groupdict()

        testid = info['tag']
        severity = "error"
        pth = info['info'].split(" ", 1)
        pth = pth[0] if pth else None

        if pth is None:
            continue

        yield Issue(cwe=None,
                    testid=testid,
                    location=Location(file=File(pth, None),
                                      function=None,
                                      point=None),
                    severity=severity,
                    message=Message(text=line),
                    notes=None,
                    trace=None)
