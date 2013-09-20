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


LINE_INFO = re.compile(
    r"(?P<minutes>\d+)m(?P<sec>(\d(\.?))+)s (?P<severity>\w+): (?P<info>.*)")


def parse_piuparts(lines, path):
    obj = None
    info = None

    cur_msg = ""

    cat = {
        "dependency-is-messed-up": ["you have held broken packages", ],
        "conffile-stuff-sucks": ["owned by: .+"],
        "command-not-found": ["command not found|: not found"],
        "conffile-modified": [
            "debsums reports modifications inside the chroot"
        ]
    }

    def handle_obj(obj):
        for k, v in cat.items():
            for expr in v:
                if re.findall(expr, cur_msg) != []:
                    obj.testid = k
                    break
        #if obj.testid is None:
        #    print(cur_msg)
        #    raise Exception
        return obj

    for line in lines:
        if line.startswith(" "):
            cur_msg += "\n" + line.strip()
            continue

        match = LINE_INFO.match(line)
        if match is None:
            continue

        info = match.groupdict()
        if info['severity'] in ['DEBUG', 'DUMP', 'INFO']:
            continue

        if obj:
            yield handle_obj(obj)
            cur_msg = ""

        obj = Issue(cwe=None,
                    testid=None,
                    location=Location(file=File(path, None),
                                      function=None,
                                      point=None),
                    severity=info['severity'],
                    message=Message(text=""),
                    notes=None,
                    trace=None)
    if obj:
        yield handle_obj(obj)
