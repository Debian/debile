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

try:
    import fedmsg
except ImportError:
    fedmsg = None

if fedmsg:
    fedmsg.init(
        topic_prefix='org.anized',
        environment='dev',
        sign_messages=False,
        endpoints={
            "debile.leliel":  [
                  "tcp://localhost:3000",
                  "tcp://localhost:3001",
                  "tcp://localhost:3002",
                  "tcp://localhost:3003",
            ],
        },
    )

def emit(topic, modname, message):
    # <topic_prefix>.<env>.<modname>.<topic>
    modname = "debile.%s" % (modname)
    if fedmsg:
        return fedmsg.publish(topic=topic, modname=modname, msg=message)
