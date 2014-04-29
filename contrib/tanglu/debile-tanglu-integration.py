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

from argparse import ArgumentParser
from datetime import datetime, timedelta
from apt_pkg import version_compare

from debile.utils.deb822 import Dsc
from debile.master.utils import init_master, session, emit
from debile.master.orm import (Person, Suite, Component, Arch, Check, Group,
                               GroupSuite, Source, Binary, Deb, Job,
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

    def _create_debile_source(self, session, pkg):
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
        oldsources = session.query(Source).filter(
            Source.group_suite == source.group_suite,
            Source.name == source.name,
        )
        for oldsource in oldsources:
            if version_compare(oldsource.version, source.version) >= 0:
                continue
            for job in oldsource.jobs:
                if (not job.results and not job.built_binary):
                    session.delete(job)
                elif job.failed is None:
                    job.failed = True
            if not any(job.check.build for job in oldsource.jobs):
                session.delete(oldsource)

        print("Created source for %s %s" % (source.name, source.version))
        emit('accept', 'source', source.debilize())

    def _create_debile_binaries(self, session, source, pkg):
        for job in source.jobs:
            if job.check.build and not job.built_binary and job.arch.name in pkg.installed_archs:
                binary = job.new_binary()
                session.add(binary)

                for name, arch, filename in pkg.binaries:
                    if arch == binary.arch.name:
                        directory, _, filename = filename.rpartition('/')
                        deb = Deb(binary=binary, directory=directory, filename=filename)
                        session.add(deb)

                if not job.assigned_at or job.failed is True:
                    # Dak accepted a binary that wasn't built by debile, eg a manual binary upload.
                    # Remove the now useless build job, to be consistent with create_debile_source behaviour
                    # (does not create a build job if dak accepted the binary before debile knew about the source)
                    binary.build_job = None
                    session.delete(job)

                print("Created binary for %s %s on %s" % (binary.name, binary.version, binary.arch))
                emit('accept', 'binary', binary.debilize())

    def _create_depwait_report(self, suite):
        base_suite = self._conf.get_base_suite(suite)
        components = self._conf.get_supported_components(base_suite).split(" ")
        supported_archs = self._conf.get_supported_archs(base_suite).split(" ")

        bcheck_data = {}
        for component in components:
            bcheck_data[component] = {}
            for arch in supported_archs:
                yaml_data = self._bcheck.get_package_states_yaml(suite, component, arch)
                yaml_data = yaml_data.replace("%3a", ":")  # Support for wheezy version of dose-builddebcheck
                report_data = yaml.safe_load(yaml_data)['report']
                if not report_data:
                    report_data = list()
                bcheck_data[component][arch] = report_data
                yaml_file = open("%s/depwait-%s-%s_%s.yml" % (NEEDSBUILD_EXPORT_DIR, suite, component, arch), "w")
                yaml_file.write(yaml_data)
                yaml_file.close()
        return bcheck_data

    def _get_package_depwait_report(self, bcheck_data, job):
        for nbpkg in bcheck_data[job.component.name][job.affinity.name]:
            if (nbpkg['package'] == ("src:" + job.source.name) and (nbpkg['version'] == job.source.version)):
                if nbpkg['status'] == 'broken':
                    return yaml.dump(nbpkg['reasons'])
        return None

    def import_pkgs(self, suite):
        pkg_dict = self._pkginfo.get_packages_dict(suite)

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
                        self._create_debile_source(s, pkg)
                    elif pkg.installed_archs:
                        self._create_debile_binaries(s, source, pkg)

            except Exception as ex:
                print("Skipping %s (%s) in %s due to error: %s" % (pkg.pkgname, pkg.version, pkg.suite, str(ex)))

    def unblock_jobs(self, suite):
        bcheck_data = self._create_depwait_report(suite)

        with session() as s:
            jobs = s.query(Job).join(Job.check).join(Job.source).join(Source.group_suite).join(GroupSuite.group).join(GroupSuite.suite).filter(
                Group.name == "default",
                Suite.name == suite,
                Check.build == True,
                Job.externally_blocked == True,
            )

            for job in jobs:
                try:
                    if not self._get_package_depwait_report(bcheck_data, job):
                        job.externally_blocked = False
                        print("Unblocked job %s (%s) %s" % (job.source.name, job.source.version, job.name))
                except Exception as ex:
                    print("Skipping %s (%s) %s due to error: %s" % (job.source.name, job.source.version, job.name, str(ex)))

    def prune_pkgs(self, suite):
        base_suite = self._conf.get_base_suite(suite)
        suites = [suite, base_suite] if suite != base_suite else [suite]
        components = self._conf.get_supported_components(base_suite).split(" ")

        pkg_list = []
        for s in suites:
            for c in components:
                pkg_list += self._pkginfo._get_package_list(s, c)

        pkgs = set()
        pkgs.update(pkg.pkgname + " " + pkg.version for pkg in pkg_list)

        with session() as s:
            sources = s.query(Source).join(Source.group_suite).join(GroupSuite.group).join(GroupSuite.suite).filter(
                Group.name == "default",
                Suite.name == suite,
            )

            for source in sources:
                if not (source.name + " " + source.version) in pkgs and not os.path.exists(source.dsc_path):
                    print("Removed obsolete source %s %s" % (source.name, source.version))
                    # Package no longer in the archive (neither in the index nor the pool)
                    s.delete(source)

    def reschedule_jobs(self):
        with session() as s:

            cutoff = datetime.utcnow() - timedelta(days=1)
            jobs = s.query(Job).filter(
                Job.failed.is_(None),
                Job.finished_at != None,
                Job.finished_at < cutoff,
            )

            for job in jobs:
                # Still missing the .dud a day after the builder told debile-master it had finished the job
                print("Rescheduling %s in %s due to missing *.dud upload" % (str(job), str(job.group_suite)))
                job.failed = None
                job.builder = None
                job.assigned_at = None
                job.finished_at = None

            cutoff = datetime.utcnow() - timedelta(days=7)
            jobs = s.query(Job).join(Job.check).filter(
                Check.build == True,
                Job.failed.is_(False),
                Job.built_binary == None,
                Job.finished_at != None,
                Job.finished_at < cutoff,
            )

            for job in jobs:
                # Still missing the .changes a week after the builder told debile-master it had finished the build job
                print("Rescheduling %s in %s due to missing *.changes upload" % (str(job), str(job.group_suite)))
                job.failed = None
                job.builder = None
                job.assigned_at = None
                job.finished_at = None


def main():
    # init Apt, we need it later
    apt_pkg.init()

    parser = ArgumentParser(description="Debile Tanglu integration script")

    actions = parser.add_argument_group("Actions")
    actions.add_argument("--import", action="store_true", dest="import_pkgs",
                         help="Import new packages from Dak to Debile")
    actions.add_argument("--unblock", action="store_true", dest="unblock_jobs",
                         help="Run dose and unblock jobs that are now buildable")
    actions.add_argument("--prune", action="store_true", dest="prune_pkgs",
                         help="Prune packages no longer in Dak from Debile")
    actions.add_argument("--reschedule", action="store_true", dest="reschedule_jobs",
                         help="Reschedule jobs where debile is still waiting for an upload")

    parser.add_argument("--config", action="store", dest="config", default=None,
                        help="Path to the master.yaml config file.")
    parser.add_argument("suites", action="store", nargs='*',
                        help="Suites to process.")

    args = parser.parse_args()
    config = init_master(args.config)
    bridge = ArchiveDebileBridge(config)

    if args.import_pkgs:
        for suite in args.suites:
            bridge.import_pkgs(suite)
    if args.unblock_jobs:
        for suite in args.suites:
            bridge.unblock_jobs(suite)
    if args.prune_pkgs:
        for suite in args.suites:
            bridge.prune_pkgs(suite)
    if args.reschedule_jobs:
        bridge.reschedule_jobs()

if __name__ == '__main__':
    os.environ['LANG'] = 'C'
    os.environ['LC_ALL'] = 'C'
    main()
