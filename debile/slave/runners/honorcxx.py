# Copyright (c) 2014 Clement Schreiner <clement@mux.me>
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

from debile.utils.commands import run_command

from firehose.model import Issue, Message, Location, File

from schroot import schroot

import os

fake_gcc = """#!/bin/sh
touch /tmp/no-honor-cxx
exit 42
"""

fake_compiler = """#!/bin/sh
exit 0
"""

fake_compiler_path = '/usr/bin/fake-compiler'

gcc_versions = ['4.6', '4.7', '4.8', '4.9',]


def honorcxx(package, suite, arch, analysis):
    chroot_name = '{0}-{1}-honorcxx'.format(suite, arch)
    with schroot(chroot_name) as chroot:
        # Let's install the real compilers
        out, err, code = chroot.run(['apt-get', 'update'], user='root')
        out_, err, code = chroot.run(['apt-get', '-y', '--no-install-recommends',
                                     'install', 'gcc', 'cpp', 'g++'
                                  ], user='root')
        out += out_
        out += err

        # Let's create fake-compiler
        with chroot.create_file('fake_compiler_path', user='root') as fake_gcc_file:
            fake_gcc_file.write(fake_gcc)

        out_, err, code = chroot.run(['chmod', '755', 'fake_compiler_path'], user='root')
        out += err


        # Let's create the fake gcc
        out_, err, code = chroot.run(['rm', '-f', '/usr/bin/gcc'], user='root')
        out += err

        out_, err, code = chroot.run(['rm', '-f', '/usr/bin/g++'], user='root')
        out += err

        out_, err, code = chroot.run(['rm', '-f', '/usr/bin/cpp'], user='root')
        out += err

        with chroot.create_file('/usr/bin/gcc', user='root') as fake_gcc_file:
            fake_gcc_file.write(fake_gcc)

        out_, err, code = chroot.run(['chmod', '755', '/usr/bin/gcc'], user='root')
        out += err

        for bin in ['gcc', 'g++', 'cpp']:
            out_, err, code = chroot.run(['ln', '-s', '/usr/bin/gcc',
                                          '/usr/bin/{0}'.format(bin)
                                      ], user='root')
            out += err

            for version in gcc_versions:
                out_, err, code = chroot.run(['rm', '-f',
                                              '/usr/bin/{0}-{1}'.format(bin, version)
                                          ], user='root')
                out += err

                out_, err, code = chroot.run(['ln', '-s', '/usr/bin/gcc',
                                              '/usr/bin/{0}-{1}'.format(bin, version)
                                          ], user='root')
                out += err

                out_, err, code = chroot.run(['sh', '-c',
                    'echo {0}-{1} hold | dpkg --set-selections'.format(bin, version)], user='root')
                out += err

                out_, err, code = chroot.run(['sh', '-c',
                    'echo {0}-{1}-base hold | dpkg --set-selections'.format(bin, version)], user='root')
                out += err

        # cleanup previous result file
        if os.path.exists('/tmp/no-honor-cxx'):
            os.remove('/tmp/no-honor-cxx')

        # let's go
        out_, err, ret = run_command([
            'sbuild',
            '-A',
            '--use-schroot-session', chroot.session,
            "-v",
            "-d", suite,
            "-j", "1",
            package,
        ])
        out += out_

        failed = False
        if os.path.exists('/tmp/no-honor-cxx'):
            failed = True
            # FIXME: firewoes complains, some data might be missing
            # File "/home/clemux/dev/debian/firewoes/firewoes/lib/debianutils.py",
            #       line 70, in get_source_url
            # >>> url_quote(message)))
            # TypeError: %d format: a number is required, not Undefined
            analysis.results.append(Issue(cwe=None,
                                testid='0',
                                location=Location(file=File('n/a', None),
                                                  function=None),
                                message=Message(text='Package does not honor CC/CXX'),
                                severity='error',
                                notes=None,
                                trace=None,
                            ))

        os.remove('/tmp/no-honor-cxx')

        return (analysis, out, failed, None, None)



def version():
    return ('honorcxx', 'n/a')
