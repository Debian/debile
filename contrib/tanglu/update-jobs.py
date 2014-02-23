# Copyright (c) 2014 Matthias Klzmpp <mak@debian.org>
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
from optparse import OptionParser
import fnmatch
import datetime as dt

from firewoes.lib.hash import idify, uniquify
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

from debile.utils.dud import Dud, DudFileException
from debile.master.messaging import emit
from debile.master.orm import (Person, Builder, Source, Group, Suite,
                               Maintainer, Job, Binary, Arch, Result,
                               create_jobs)
from sqlalchemy.orm import Session, sessionmaker
import debile.master.core
from debile.utils.changes import parse_changes_file, ChangesFileException

from rapidumolib.pkginfo import *
from rapidumolib.utils import *
from package_buildcheck import *
from process_dud import *

NEEDSBUILD_EXPORT_DIR = "/srv/dak/export/needsbuild"

class BuildJobUpdater:
    def __init__(self, suite):
        parser = get_archive_config_parser()
        self.scheduleBuilds = False
        self.debugMode = False

        distro = parser.get('General', 'distro_name')
        archive_path = parser.get('Archive', 'path')
        devel_suite = parser.get('Archive', 'devel_suite')
        staging_suite = parser.get('Archive', 'staging_suite')
        self._archive_components = parser.get('Archive', 'components').split(" ")
        self._supported_archs = parser.get('Archive', 'archs').split (" ")

        self._pkginfo = PackageBuildInfoRetriever()
        if suite == devel_suite:
            self._pkginfo.extra_suite = staging_suite
        self._suite = suite
        self._session = sessionmaker(bind=debile.master.core.engine)()

    def create_debile_job(self, pkg, arches):
        gid = "default"
        sid = pkg.suite
        print("Create debile job for: " + pkg + " # arch: " + arches)

        MAINTAINER = re.compile("(?P<name>.*) \<(?P<email>.*)\>")

        group = self._session.query(Group).filter_by(name=gid).one()
        suite = self._session.query(Suite).filter_by(name=sid).one()

        source = Source(
            uploader="unknown", # FIXME we can't extract the uploader efficiently (yet)
            name=pkg.pkgname,
            version=pkg.version,
            group=group,
            suite=suite,
            uploaded_at=dt.datetime.utcnow(),
            updated_at=dt.datetime.utcnow()
        )

        #source.maintainers.append(Maintainer(
        #    comaintainer=False,
        #    **MAINTAINER.match(changes['Maintainer']).groupdict()
        #))

        create_jobs(source, self._session, arches)

        self._session.add(source)  # OK. Populated entry. Let's insert.
        self._session.commit()  # Neato.

        emit('accept', 'source', source.debilize())

    def debile_job_exists(self, pkg, arches):
        group = self._session.query(Group).filter_by(name="default").one()
        suite = self._session.query(Suite).filter_by(name=pkg.suite).one()
        try:
            source = self._session.query(Source).filter_by(name=pkg.pkgname, version=pkg.version, group=group, suite=suite).one()
        except NoResultFound:
            return False

        for arch in arches:
           ga = GroupArch(group="default", arch=arch)
           try:
               self._session.query(Job).filter_by(source=source, group=ga)
           except NoResultFound:
               return False
        return True

    def _filter_unsupported_archs(self, pkg_archs):
        sup_archs = list()
        for arch in pkg_archs:
            if arch in self._supported_archs:
                sup_archs.append(arch)
        # return and remove duplicates
        return list(set(sup_archs))

    def sync_packages(self, component, needsbuild_list):
        pkg_list = self._pkginfo.get_packages_for(self._suite, component)
        pkg_dict = self._pkginfo.package_list_to_dict(pkg_list)

        for pkg in pkg_dict.values():
            archs = self._filter_unsupported_archs(pkg.archs)

            # check if this is an arch:all package
            if archs == ["all"]:
                 if not 'all' in pkg.installed_archs:
                     needsbuild_list.write("%s_%s [%s]\n" % (pkg.pkgname, pkg.getVersionNoEpoch(), "all"))
                     if not self.debile_job_exists(pkg, ["all"]):
                         self.create_debile_job(pkg, ["all"])
                 continue

            pkgArchs = []
            for arch in self._supported_archs:
                if ('any' in archs) or ('linux-any' in archs) or (("any-"+arch) in archs) or (arch in archs):
                    pkgArchs.append(arch)
            if ("all" in archs):
                    pkgArchs.append("all")

            if len(pkgArchs) <= 0:
                print("Skipping job %s %s on %s, no architectures found!" % (pkg.pkgname, pkg.version, pkg.suite))
                continue

            # packages for arch:all are built on amd64, we don't need an extra build slot for them if it is present
            # we need to eliminate possible duplicate arch enties first, so we don't add duplicate archs (or amd64 and all together in one package)
            buildArchs = list(set(pkgArchs))
            if ("amd64" in buildArchs) and ("all" in buildArchs):
                buildArchs.remove("all")

            for arch in buildArchs:
                if not arch in pkg.installed_archs:
                    # safety check, to not build stuff twice
                    if (arch == "amd64") and ("all" in pkg.installed_archs):
                        continue
                    if self.debugMode:
                        print("Package %s not built for %s!" % (pkg.pkgname, arch))
                    needsbuild_list.write("%s_%s [%s]\n" % (pkg.pkgname, pkg.getVersionNoEpoch(), arch))
                    if not self.debile_job_exists(pkg, buildArchs):
                        # do it!
                        self.create_debile_job(pkg, buildArchs)

        #bcheck = BuildCheck()
        #for arch in self._supported_archs:
        #    yaml_data = bcheck.get_package_states_yaml(dist, component, arch)
        #    yaml_file = open("%s/depwait-%s-%s_%s.yml" % (NEEDSBUILD_EXPORT_DIR, dist, component, arch), "w")
        #    yaml_file.write(yaml_data)
        #    yaml_file.close()

    def sync_packages_all(self):
        for comp in self._archive_components:
            # we need the extra list as temporary hack for Jenkins to know if it should investigate building a package
            # (will later be replaced by the XML generated by edos-debcheck)
            if comp == "main":
                needsbuild_list = open("%s/needsbuild.list" % (NEEDSBUILD_EXPORT_DIR), "w")
            else:
                needsbuild_list = open("%s/needsbuild-%s.list" % (NEEDSBUILD_EXPORT_DIR, comp), "w")

            self.sync_packages(comp, needsbuild_list)
            needsbuild_list.close()

def main():
    # init Apt, we need it later
    apt_pkg.init()

    parser = OptionParser()
    parser.add_option("-u", "--update",
                  action="store_true", dest="update", default=False,
                  help="syncronize Debile with archive contents")

    (options, args) = parser.parse_args()

    if options.update:
        sync = BuildJobUpdater("aequorea")
        #sync.scheduleBuilds = options.build
        sync.sync_packages_all()
    else:
        print("Run with -h for a list of available command-line options!")

if __name__ == '__main__':
    os.environ['LANG'] = 'C'
    os.environ['LC_ALL'] = 'C'
    main()
