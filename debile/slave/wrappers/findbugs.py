# Copyright (c) 2012-2013 Paul Tagliamonte <paultag@debian.org>
# Copyright (c) 2013 Leo Cavaille <leo@cavaille.net>
# Copyright (c) 2013 Sylvestre Ledru <sylvestre@debian.org>
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
import lxml.etree

# We require:
# findbugs TODO
# --enable=all . --xml 1>/dev/null  ( stderr )


def parse_findbugs(payload):
    tree = lxml.etree.fromstring(payload)
    for result in tree.xpath("//BugCollection/BugInstance/Class/SourceLine"):
        keys = result.keys()

        p = None
        # Start is not always defined
        if 'start' in keys:
            line = result.attrib['start']
            p = Point(int(line), 0)

        if 'end' in keys:
            lineEnd = result.attrib['end']
            p = Point(int(line), int(lineEnd))

        if 'sourcepath' in keys:
            path = result.attrib['sourcepath']
        else:
            path = "unknown"

        message, = result.xpath("../../LongMessage")
        message = message.text
        testid = result.getparent().getparent().attrib['instanceHash']
        rank = result.getparent().getparent().attrib['rank']
        if rank <= 4:
            severity = "scariest"
        elif rank <= 9:
            severity = "scary"
        elif rank <= 14:
            severity = "troubling"
        else:
            severity = "concern"

        yield Issue(cwe=None,
                    testid=testid,
                    location=Location(
                        file=File(path, None),
                        function=None,
                        point=p),
                    severity=severity,
                    message=Message(text=message),
                    notes=None,
                    trace=None)
