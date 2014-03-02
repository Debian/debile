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

from debile.utils.aget import find_dsc
from debile.master.messaging import emit
from debile.master.filerepo import FilesAlreadyRegistered
from debile.master.orm import (Person, Builder, Suite, Component, Arch, Check,
                               Group, GroupSuite, Source, Maintainer, Binary,
                               Job, JobDependencies, Result,
                               create_source, create_jobs)

from debian.deb822 import Dsc
from sqlalchemy.orm import Session, sessionmaker
import debile.master.core

from rapidumolib.pkginfo import *
from rapidumolib.utils import *
from rapidumolib.config import *
from package_buildcheck import *

NEEDSBUILD_EXPORT_DIR = "/srv/dak/export/needsbuild"

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
        Session = sessionmaker(bind=debile.master.core.engine)
        self._session = Session()

    def create_debile_job(self, pkg, pkg_component, pkg_arches):
        uploader = "dak"
        group = "default"
        suite = pkg.suite

        group_suite = self._session.query(GroupSuite).filter(
            Group.name==group,
            Suite.name==suite,
        ).one()

        source = self._session.query(Source).filter(
            Source.name==pkg.pkgname,
            Source.version==pkg.version,
            GroupSuite.group==group_suite.group,
        ).first()

        if not source:
            dsc_fname = find_dsc(group_suite.group.repo_path, suite,
                                 pkg_component, pkg.pkgname, pkg.version)
            component = self._session.query(Component).filter_by(name=pkg_component).one()
            user = self._session.query(Person).filter_by(username=uploader).one()
            dsc = Dsc(open(dsc_fname))
            source = create_source(dsc, group_suite, component, user)
            create_jobs(source, self._session, pkg_arches)
            print("Created job for %s (archs: %s)" % (pkg.pkgname, str(pkg_arches)))
        else:
            arches = list()
            for arch in pkg_arches:
                job = self._session.query(Job).filter(
                    Job.source==source,
                    Arch.name==arch
                ).first()
                if job is None:
                    arches.append(arch)
            if len(arches) == 0:
                return
            create_jobs(source, self._session, arches)
            print("Created job for %s (archs: %s)" % (pkg.pgname, str(arches)))

        self._session.add(source)  # OK. Populated entry. Let's insert.
        self._session.commit()  # Neato.

        emit('accept', 'source', source.debilize())

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
            self.bcheck_data[arch] = yaml.safe_load(yaml_data)['report']
            yaml_file = open("%s/depwait-%s-%s_%s.yml" % (NEEDSBUILD_EXPORT_DIR, self._suite, component, arch), "w")
            yaml_file.write(yaml_data)
            yaml_file.close()

        for pkg in pkg_dict.values():
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

            self.create_debile_job(pkg, component, pkg_build_arches)

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
