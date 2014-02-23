#!/usr/bin/python
# Copyright (C) 2013-2014 Matthias Klumpp <mak@debian.org>
#
# Licensed under the GNU General Public License Version 3
#
# This program is free software: you can reself._suiteribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is self._suiteributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import apt_pkg
import sys
import subprocess
import yaml
from optparse import OptionParser
from ConfigParser import SafeConfigParser

from rapidumolib.utils import *
from rapidumolib.pkginfo import *

class BuildCheck:
    def __init__(self, suite):
        parser = get_archive_config_parser()
        path = parser.get('Archive', 'path')
        self._archive_path = path
        self._suite = suite
        self._pkginfo = SourcePackageInfoRetriever(path, parser.get('General', 'distro_name'), suite)
        if self._suite == "staging":
            self._pkginfo.extra_suite = parser.get('Archive', 'devel_suite')

    def _get_binary_indices_list(self, comp, arch):
        archive_indices = []
        archive_binary_index_path = self._archive_path + "/dists/%s/%s/binary-%s/Packages.gz" % (self._suite, comp, arch)
        archive_indices.append(archive_binary_index_path)
        if arch == "all":
            # if arch is all, we feed the solver with a binary architecture as example, to solve dependencies on arch-specific stuff
            archive_binary_index_path_arch = self._archive_path + "/dists/%s/%s/binary-amd64/Packages.gz" % (self._suite, comp)
            archive_indices.append(archive_binary_index_path_arch)
        else:
            # any architecture canb also depend on arch:all stuff, so we add it to the loop
            archive_binary_index_path_all = self._archive_path + "/dists/%s/%s/binary-all/Packages.gz" % (self._suite, comp)
            archive_indices.append(archive_binary_index_path_all)

        if self._suite == "staging":
            # staging needs the aequorea data (it is no complete suite)
            archive_indices.extend(self._get_binary_indices_list("aequorea", comp, arch))

        return archive_indices

    def _run_dose_builddebcheck(self, comp, arch):
        # we always need main components
        archive_indices = self._get_binary_indices_list(self._suite, "main", arch)
        if comp != "main":
            # if the component is not main, add it to the list
            comp_indices = self._get_binary_indices_list(self._suite, comp, arch)
            archive_indices.extend(comp_indices)
            if comp == "non-free":
                # non-free might need contrib
                comp_indices = self._get_binary_indices_list(self._suite, "contrib", arch)
                archive_indices.extend(comp_indices)

        # append the corresponding sources information
        archive_source_index_path = self._archive_path + "/dists/%s/%s/source/Sources.gz" % (self._suite, comp)
        archive_indices.append(archive_source_index_path)

        dose_cmd = ["dose-builddebcheck", "--quiet", "-e", "-f", "--summary", "--deb-native-arch=%s" % (arch)]
        # add the archive index files
        dose_cmd.extend(archive_indices)

        proc = subprocess.Popen(dose_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = proc.communicate()
        output = stdout
        if (proc.returncode != 0):
            return False, output
        return True, output

    def check_build(self, component, package_name, arch, force_buildcheck=False):
        pkgList = self._pkginfo.get_packages_for(self._suite, component)
        pkg_dict = self._pkginfo.package_list_to_dict(pkgList)
        # NOTE: The dictionary always contains the most recent pkg version
        # This means there is no need for any additional version checks :)

        if package_name not in pkg_dict:
            print("Package %s was not found in %s!" % (package_name, self._suite))
            return 1
        src_pkg = pkg_dict[package_name]

        if (not arch in src_pkg.installedArchs) or (force_buildcheck):
            ret, info = self._run_dose_builddebcheck(self._suite, component, arch)
            doc = yaml.load(info)
            if doc['report'] is not None:
                for p in doc['report']:
                    if p['package'] == ('src%3a' + package_name):
                        print("Package '%s (%s)' has unsatisfiable dependencies on %s:\n%s" % (package_name, p['version'], arch, yaml.dump(p['reasons'])))
                        # return code 8, which means dependency-wait
                        return 8
                if force_buildcheck:
                    print("All build-dependencies are satisfied.")
                    # if we forced a buildcheck and did not find a problem, check again if we really need to build the package
                    if not arch in src_pkg.installedArchs:
                        return 0
                    else:
                        return 1
                # yay, we can build the package!
                return 0

        # apparently, we don't need to build the package
        return 1

    def get_package_states_yaml(self, component, arch):
        ret, info = self._run_dose_builddebcheck(self._suite, component, arch)

        return info

def main():
    # init Apt, we need it later
    apt_pkg.init()

    parser = OptionParser()
    parser.add_option("-c", "--check",
                  action="store_true", dest="check", default=False,
                  help="check if the given package name can be built (returns 1 if not, 8 if dep-wait, 0 if build should be scheduled)")
    parser.add_option("--force-buildcheck",
                  action="store_true", dest="force_buildcheck", default=False,
                  help="enforce a check for build dependencies")

    (options, args) = parser.parse_args()

    if options.check:
        if len(args) != 4:
            print("Invalid number of arguments (need suite, component, package-name, arch)")
            sys.exit(6)
        suite = args[0]
        comp = args[1]
        package_name = args[2]
        arch = args[3]
        bc = BuildCheck(suite)
        code = bc.check_build(comp, package_name, arch, force_buildcheck=options.force_buildcheck)
        if code == 1:
            print("There is no need to build this package.")
        if code == 0:
            print("We should (re)build this package.")
        sys.exit(code)
    else:
        print("Run with -h for a list of available command-line options!")

if __name__ == "__main__":
    os.environ['LANG'] = 'C'
    os.environ['LC_ALL'] = 'C'
    main()
