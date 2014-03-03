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

from debile.utils.commands import run_command
from schroot import schroot

import os
import glob


def clanganalyzer(package, suite, arch, analysis):
    raise NotImplemented("Not ported")

    chroot_name = "%s-%s" % (suite, arch)
    with schroot(chroot_name) as chroot:
        # We should have the dsc file to bulid
        dsc = os.path.basename(package)
        if not dsc.endswith('.dsc'):
            raise ValueError("clanganalyzer runner must receive a dsc file")

        # Setup the chroot for scan-build run
        # 1/ install clang
        # TODO: check the return codes
        out, err, ret = chroot.run([
            'apt-get', 'install', '-y', 'clang', 'wget'
        ], user='root')

        # 2/ fake dpkg-buildpackage in the schroot
        # Replace the real dpkg-buildpackage by our script
        out_, err, ret = chroot.run([
            'mv',
            '/usr/bin/dpkg-buildpackage',
            '/usr/bin/dpkg-buildpackage.faked'
        ], user='root')
        out += out_

        internal_report_dir = "/tmp/scan-build/"
        # We will output the scan-build plist reports there
        out_, err, ret = chroot.run([
            'mkdir', '-p', internal_report_dir
        ], user='root')
        out += out_
        out_, err, ret = chroot.run([
            'chmod', '777', internal_report_dir
        ], user='root')
        out += out_

        # Create the script
        fake_dpkg_url = "http://leo.cavaille.net/public/dpkg-buildpackage-html"
        out_, err, ret = chroot.run([
            'wget', '-O', '/usr/bin/dpkg-buildpackage', fake_dpkg_url
        ], user='root')
        out += out_

        # Make it executable
        out_, err, ret = chroot.run([
            'chmod', '755', '/usr/bin/dpkg-buildpackage'
        ], user='root')
        out += out_

        # Now run sbuild in this session chroot for the package
        out_, err, ret = run_command([
            "sbuild",
            "-A",
            "--use-schroot-session", chroot.session,
            "-v",
            "-d", suite,
            "-j", "8",
            package,
        ])
        out += out_

        # Parse the plist reports into Firehose and return
        # WARN : if the previous run did not delete the folder, this will fail
        # worst, if we run several instances of virtual builders, this will
        # fail because by default /tmp is a bind mount from the physical server
        reports_dir = glob.glob(internal_report_dir+'*')

        ### SCANDALOUS HACK !!
        return analysis, out, reports_dir, None


def version():
    # TODO
    return ('clanganalyzer', 'n/a')
