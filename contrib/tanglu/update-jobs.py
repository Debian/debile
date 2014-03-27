# Copyright (c) 2014 Matthias Klumpp <mak@debian.org>
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

import os
import apt_pkg
import yaml
from optparse import OptionParser
import fnmatch

from debile.master.utils import session
from debile.master.messaging import emit
from debile.master.filerepo import FilesAlreadyRegistered
from debile.master.orm import (Person, Builder, Suite, Component, Arch, Check,
                               Group, GroupSuite, Source, Maintainer, Binary,
                               Job, JobDependencies, Result,
                               create_source, create_jobs)

from debian.deb822 import Dsc
import debile.master.core

from rapidumolib.pkginfo import *
from rapidumolib.utils import *
from rapidumolib.config import *
from package_buildcheck import *

NEEDSBUILD_EXPORT_DIR = "/srv/dak/export/needsbuild"
REPO_DIR = "/srv/archive.tanglu.org/tanglu"


class ArchiveDebileBridge:
    def __init__(self, suite):
        conf = RapidumoConfig()
        self.scheduleBuilds = False
        self.debugMode = False

        self._distro = conf.distro_name
        self._incoming_path = conf.archive_config['incoming']
        archive_path = conf.archive_config['path']
        devel_suite = conf.archive_config['devel_suite']
        staging_suite = conf.archive_config['staging_suite']
        self._archive_components = conf.get_supported_components(devel_suite).split(" ")
        self._supported_archs = conf.get_supported_archs(devel_suite).split (" ")
        self._supported_archs.append("all")

        self._pkginfo = PackageBuildInfoRetriever()
        self._suite = suite

    @staticmethod
    def create_debile_source(session, group, suite, component_name, dsc_fname):
        user = session.query(Person).filter_by(email="dak@ftp-master.tanglu.org").one()

        group_suite = session.query(GroupSuite).filter(
            Group.name==group,
            Suite.name==suite,
        ).one()
        component = session.query(Component).filter(
            Component.name==component_name
        ).one()

        dsc = Dsc(open(dsc_fname))
        if 'Build-Architecture-Indep' in dsc:
            valid_affinities = dsc['Build-Architecture-Indep']
        elif 'X-Build-Architecture-Indep' in dsc:
            valid_affinities = dsc['X-Build-Architecture-Indep']
        elif 'X-Arch-Indep-Build-Arch' in dsc:
            valid_affinities = dsc['X-Arch-Indep-Build-Arch']
        else:
            valid_affinities = "any"

        source = create_source(dsc, group_suite, component, user)
        create_jobs(source, valid_affinities, externally_blocked=True)
        session.add(source)

        print("Created source for %s %s" % (source.name, source.version))
        emit('accept', 'source', source.debilize())

    @staticmethod
    def unblock_debile_jobs(session, source, version, group, suite, arches):
        arch_ids = [x.id for x in session.query(Arch).filter(Arch.name.in_(arches)).all()]
        jobs = session.query(Job).filter(
            Source.name==source,
            Source.version==version,
            Group.name==group,
            Suite.name==suite,
            Job.externally_blocked==True,
            Job.arch_id.in_(arch_ids),
        ).all()

        if not jobs:
            return

        for job in jobs:
            if job.arch.name in arches:
                job.externally_blocked=False
                session.add(job)

        print("Unblocked jobs for %s %s (arches: %s)" %
              (source, version, str(arches)))

    def _filter_unsupported_archs(self, pkg_archs):
        sup_archs = list()
        for arch in self._supported_archs:
            if ('any' in pkg_archs) or ('linux-any' in pkg_archs) or (arch in pkg_archs) or (("any-"+arch) in pkg_archs):
                # source arch:any doesn't mean we can build on arch:all
                if arch != "all":
                    sup_archs.append(arch)
        if ("all" in pkg_archs):
            sup_archs.append("all")

        # return and remove duplicates
        return list(set(sup_archs))

    def _get_package_depwait_report(self, pkg, arch):
        for nbpkg in self.bcheck_data[arch]:
            if (nbpkg['package'] == ('src%3a'+pkg.pkgname)) and (nbpkg['version'] == pkg.version):
                if nbpkg['status'] == 'broken':
                    return yaml.dump(nbpkg['reasons'])
        return None


    def sync_packages(self, component):
        pkg_list = self._pkginfo.get_packages_for(self._suite, component)
        pkg_dict = self._pkginfo.package_list_to_dict(pkg_list)

        self.bcheck_data = {}
        bcheck = BuildCheck(self._suite)
        for arch in self._supported_archs:
            yaml_data = bcheck.get_package_states_yaml(component, arch)
            report_data = yaml.safe_load(yaml_data)['report']
            if not report_data:
                report_data = list()
            self.bcheck_data[arch] = report_data
            yaml_file = open("%s/depwait-%s-%s_%s.yml" % (NEEDSBUILD_EXPORT_DIR, self._suite, component, arch), "w")
            yaml_file.write(yaml_data)
            yaml_file.close()

        for pkg in pkg_dict.values():
            try:
                with session() as s:
                    source = s.query(Source).filter(
                        Source.name==pkg.pkgname,
                        Source.version==pkg.version,
                        Group.name=="default",
                        Suite.name==pkg.suite,
                    ).first()
                    if not source:
                        dsc = os.path.join(REPO_DIR, pkg.directory, pkg.dsc)
                        ArchiveDebileBridge.create_debile_source(
                            s, "default", pkg.suite, component, dsc
                        )
            except Exception as ex:
                print("Skipping %s %s due to error: %s" % (pkg.pkgname, pkg.version, str(ex)))
                continue

            archs = self._filter_unsupported_archs(pkg.archs)
            pkg_build_arches = list()

            if len(archs) <= 0:
                print("Skipping job %s %s on %s, no architectures found!" % (pkg.pkgname, pkg.version, pkg.suite))
                continue

            for arch in archs:
                if not arch in pkg.installed_archs:
                    if self.debugMode:
                        print("Package %s not built for %s!" % (pkg.pkgname, arch))
                    if not self._get_package_depwait_report(pkg, arch):
                        pkg_build_arches.append(arch)

            if pkg_build_arches:
                try:
                    with session() as s:
                        ArchiveDebileBridge.unblock_debile_jobs(
                            s, pkg.pkgname, pkg.version,
                            "default", pkg.suite, pkg_build_arches
                        )
                except Exception as ex:
                    print("Skipping %s %s due to error: %s" % (pkg.pkgname, pkg.version, str(ex)))

    def sync_packages_all(self):
        for comp in self._archive_components:
            self.sync_packages(comp)

def main():
    # init Apt, we need it later
    apt_pkg.init()

    parser = OptionParser()
    parser.add_option("-u", "--update-jobs",
                  action="store_true", dest="update", default=False,
                  help="syncronize Debile with archive contents")

    (options, args) = parser.parse_args()

    if options.update:
        sync = ArchiveDebileBridge("staging")
        #sync.scheduleBuilds = options.build
        sync.sync_packages_all()
    else:
        print("Run with -h for a list of available command-line options!")

if __name__ == '__main__':
    os.environ['LANG'] = 'C'
    os.environ['LC_ALL'] = 'C'
    main()
