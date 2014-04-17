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
from datetime import datetime, timedelta

from debile.utils.deb822 import Dsc
from debile.master.utils import init_master, session, emit
from debile.master.orm import (Person, Builder, Suite, Component, Arch, Check,
                               Group, GroupSuite, Source, Binary, Job, Deb,
                               create_source, create_jobs)

from rapidumolib.pkginfo import PackageBuildInfoRetriever
from rapidumolib.config import RapidumoConfig
from rapidumolib.buildcheck import BuildCheck

NEEDSBUILD_EXPORT_DIR = "/srv/dak/export/needsbuild"


class ArchiveDebileBridge:
    def __init__(self, config):
        self._conf = RapidumoConfig()
        self._affinity_preference = config["affinity_preference"]
        self._archive_path = "%s/%s" % (self._conf.archive_config['path'], self._conf.distro_name)
        self._pkginfo = PackageBuildInfoRetriever(self._conf)
        self._bcheck = BuildCheck(self._conf)

    def create_debile_source(self, session, pkg):
        user = session.query(Person).filter_by(email="dak@ftp-master.tanglu.org").one()

        group_suite = session.query(GroupSuite).join(GroupSuite.group).join(GroupSuite.suite).filter(
            Group.name == "default",
            Suite.name == pkg.suite,
        ).one()
        component = session.query(Component).filter(
            Component.name == pkg.component
        ).one()

        dsc_fname = "{root}/{directory}/{filename}".format(
            root=self._archive_path,
            directory=pkg.directory,
            filename=pkg.dsc,
        )

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
        source.directory = pkg.directory
        source.dsc_filename = pkg.dsc
        session.add(source)

        for aname in pkg.installed_archs:
            arch = session.query(Arch).filter_by(name=aname).one()
            binary = Binary(source=source, arch=arch, uploaded_at=source.uploaded_at)
            session.add(binary)

            for name, arch, filename in pkg.binaries:
                if arch == binary.arch.name:
                    directory, _, filename = filename.rpartition('/')
                    deb = Deb(binary=binary, directory=directory, filename=filename)
                    session.add(deb)

        create_jobs(source, self._affinity_preference, valid_affinities, externally_blocked=True)

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

    def create_debile_binaries(self, session, source, pkg):
        for job in source.jobs:
            if job.check.build and not job.built_binary and job.arch.name in pkg.installed_archs:
                binary = job.new_binary()
                session.add(binary)

                for name, arch, filename in pkg.binaries:
                    if arch == binary.arch.name:
                        directory, _, filename = filename.rpartition('/')
                        deb = Deb(binary=binary, directory=directory, filename=filename)
                        session.add(deb)

                emit('accept', 'binary', binary.debilize())

    def unblock_debile_jobs(self, session, source, arches):
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

    def _get_package_depwait_report(self, bcheck_data, pkg, arch):
        for nbpkg in bcheck_data[pkg.component][arch]:
            if (nbpkg['package'] == ('src%3a'+pkg.pkgname)) and (nbpkg['version'] == pkg.version):
                if nbpkg['status'] == 'broken':
                    return yaml.dump(nbpkg['reasons'])
        return None

    def sync_packages(self, suite):
        pkg_dict = self._pkginfo.get_packages_dict(suite)

        base_suite = self._conf.get_base_suite(suite)
        components = self._conf.get_supported_components(base_suite).split(" ")
        supported_archs = self._conf.get_supported_archs(base_suite).split(" ")
        supported_archs.append("all")

        bcheck_data = {}
        for component in components:
            bcheck_data[component] = {}
            for arch in supported_archs:
                yaml_data = self._bcheck.get_package_states_yaml(suite, component, arch)
                report_data = yaml.safe_load(yaml_data)['report']
                if not report_data:
                    report_data = list()
                bcheck_data[component][arch] = report_data
                yaml_file = open("%s/depwait-%s-%s_%s.yml" % (NEEDSBUILD_EXPORT_DIR, suite, component, arch), "w")
                yaml_file.write(yaml_data)
                yaml_file.close()

        for pkg in pkg_dict.values():
            try:
                with session() as s:
                    source = s.query(Source).join(Source.group_suite).join(GroupSuite.group).join(GroupSuite.suite).filter(
                        Source.name == pkg.pkgname,
                        Source.version == pkg.version,
                        Group.name == "default",
                        Suite.name == pkg.suite,
                    ).first()

                    if not source:
                        source = self.create_debile_source(s, pkg)
                    else:
                        self.create_debile_binaries(s, source, pkg)

                    unblock_arches = [arch for arch in supported_archs
                                      if not self._get_package_depwait_report(bcheck_data, pkg, arch)]

                    if unblock_arches:
                        self.unblock_debile_jobs(s, source, unblock_arches)

            except Exception as ex:
                print("Skipping %s (%s) in %s due to error: %s" % (pkg.pkgname, pkg.version, pkg.suite, str(ex)))
                continue

    def reschedule_missing_uploads(self):
        with session() as s:
            cutoff = datetime.utcnow() - timedelta(days=1)

            jobs = s.query(Job).filter(
                Job.failed == None,
                Job.finished_at != None,
                Job.finished_at < cutoff,
            )

            for job in jobs:
                # Still missing the .dud one day after the builder told debile-master it had finished the job
                print("Rescheduling %s in %s due to missing *.dud upload" % (str(job), str(job.group_suite)))
                job.failed = None
                job.builder = None
                job.assigned_at = None
                job.finished_at = None

            jobs = s.query(Job).join(Job.check).filter(
                Check.build == True,
                Job.failed == False,
                Job.built_binary == None,
                Job.finished_at != None,
                Job.finished_at < cutoff,
            )

            for job in jobs:
                # Still missing the .changes one day after the builder told debile-master it had finished the build job
                print("Rescheduling %s in %s due to missing *.changes upload" % (str(job), str(job.group_suite)))
                job.failed = None
                job.builder = None
                job.assigned_at = None
                job.finished_at = None


def main():
    # init Apt, we need it later
    apt_pkg.init()

    parser = OptionParser()
    parser.add_option("-u", "--update-jobs",
                      action="store_true", dest="update", default=False,
                      help="syncronize Debile with archive contents")

    (options, args) = parser.parse_args()
    config = init_master()

    if options.update:
        sync = ArchiveDebileBridge(config)
        sync.sync_packages("staging")
        sync.sync_packages("aequorea-updates")
        sync.reschedule_missing_uploads()
    else:
        print("Run with -h for a list of available command-line options!")

if __name__ == '__main__':
    os.environ['LANG'] = 'C'
    os.environ['LC_ALL'] = 'C'
    main()
