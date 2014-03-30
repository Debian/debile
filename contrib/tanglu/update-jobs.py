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
from apt_pkg import version_compare

from debile.utils.deb822 import Dsc
from debile.master.utils import session
from debile.master.messaging import emit
from debile.master.orm import (Person, Builder, Suite, Component, Arch, Check,
                               Group, GroupSuite, Source, Maintainer, Binary,
                               Job, JobDependencies, Result,
                               create_source, create_jobs)

from rapidumolib.pkginfo import PackageBuildInfoRetriever
from rapidumolib.config import RapidumoConfig
from package_buildcheck import BuildCheck

NEEDSBUILD_EXPORT_DIR = "/srv/dak/export/needsbuild"
REPO_DIR = "/srv/archive.tanglu.org/tanglu"


class ArchiveDebileBridge:
    def __init__(self, suite):
        conf = RapidumoConfig()
        self.scheduleBuilds = False
        self.debugMode = False

        self._distro = conf.distro_name
        self._incoming_path = conf.archive_config['incoming']
        devel_suite = conf.archive_config['devel_suite']
        staging_suite = conf.archive_config['staging_suite']
        a_suite = suite
        if suite == staging_suite:
            a_suite = devel_suite
        self._archive_components = conf.get_supported_components(a_suite).split(" ")
        self._supported_archs = conf.get_supported_archs(a_suite).split(" ")
        self._supported_archs.append("all")

        self._pkginfo = PackageBuildInfoRetriever()
        self._suite = suite

    @staticmethod
    def create_debile_source(session, group, suite, component_name, installed_arches, dsc_fname):
        user = session.query(Person).filter_by(email="dak@ftp-master.tanglu.org").one()

        group_suite = session.query(GroupSuite).filter(
            Group.name == group,
            Suite.name == suite,
        ).one()
        component = session.query(Component).filter(
            Component.name == component_name
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
        create_jobs(source, valid_affinities,
                    installed_arches=installed_arches,
                    externally_blocked=True)
        session.add(source)

        # Drop any old jobs that are still pending.
        jobs = session.query(Job).join(Job.source).filter(
            Source.group_suite == source.group_suite,
            Source.name == source.name,
        )
        for job in jobs:
            if not job.assigned_at and version_compare(source.version, job.source.version) > 0:
                session.delete(job)

        print("Created source for %s %s" % (source.name, source.version))
        emit('accept', 'source', source.debilize())

        return source

    @staticmethod
    def unblock_debile_jobs(session, source, arches):
        jobs = session.query(Job).filter(
            Job.source == source,
            Job.externally_blocked == True,
            Job.arch.has(Arch.name.in_(arches)),
        ).all()

        if not jobs:
            return

        for job in jobs:
            if job.arch.name in arches:
                job.externally_blocked = False
                session.add(job)

        print("Unblocked jobs for %s %s (arches: %s)" %
              (source.name, source.version, str(arches)))

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
                        Source.name == pkg.pkgname,
                        Source.version == pkg.version,
                        Group.name == "default",
                        Suite.name == pkg.suite,
                    ).first()

                    if not source:
                        dsc = os.path.join(REPO_DIR, pkg.directory, pkg.dsc)
                        source = ArchiveDebileBridge.create_debile_source(s, "default", pkg.suite, component, pkg.installed_archs, dsc)

                    unblock_arches = [arch for arch in self._supported_archs
                                      if not self._get_package_depwait_report(pkg, arch)]

                    if unblock_arches:
                        ArchiveDebileBridge.unblock_debile_jobs(s, source, unblock_arches)

            except Exception as ex:
                print("Skipping %s %s due to error: %s" % (pkg.pkgname, pkg.version, str(ex)))
                continue

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
