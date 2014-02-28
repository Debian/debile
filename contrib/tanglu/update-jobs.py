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
import datetime as dt

from firewoes.lib.hash import idify, uniquify
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

from debile.utils.dud import Dud, DudFileException
from debile.master.messaging import emit
from debile.master.orm import (Person, Builder, Source, Group, Suite,
                               Maintainer, Job, Binary, Arch, Result,
                               GroupArch, create_jobs)
from sqlalchemy.orm import Session, sessionmaker
import debile.master.core
from debile.utils.changes import parse_changes_file, ChangesFileException

from rapidumolib.pkginfo import *
from rapidumolib.utils import *
from rapidumolib.config import *
from package_buildcheck import *
from process_dud import *

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
        self._session = sessionmaker(bind=debile.master.core.engine)()

    def create_debile_job(self, pkg, pkg_arches):
        gid = "default"
        sid = pkg.suite

        arches = list()
        for arch in pkg_arches:
            if not self.debile_job_exists(pkg, arch):
                arches.append(arch)
        if len(arches) == 0:
            return

        print("Create debile job for: " + str(pkg) + " # arch: " + str(arches))

        MAINTAINER = re.compile("(?P<name>.*) \<(?P<email>.*)\>")

        group = self._session.query(Group).filter_by(name=gid).one()
        suite = self._session.query(Suite).filter_by(name=sid).one()
        fake_uploader = self._session.query(Person).filter_by(username="dak").one()

        source = self._session.query(Source).filter(Source.name==pkg.pkgname, Source.version==pkg.version, Source.group==group, Source.suite==suite).first()
        if not source:
            source = Source(
                uploader=fake_uploader, # FIXME we can't extract the uploader efficiently (yet)
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

    def debile_job_exists(self, pkg, arch):
        group = self._session.query(Group).filter_by(name="default").one()
        suite = self._session.query(Suite).filter_by(name=pkg.suite).one()
        try:
            source = self._session.query(Source).filter_by(name=pkg.pkgname, version=pkg.version, group=group, suite=suite).one()
        except NoResultFound:
            return False

        arch_obj = self._session.query(Arch).filter_by(name=arch).one()
        ga = GroupArch(group=group, arch=arch_obj)
        if not self._session.query(Job).filter(Job.source==source, Job.arch==arch_obj).first():
            return False
        return True

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

            # check if this is an arch:all package
            if archs == ["all"]:
                 if not 'all' in pkg.installed_archs:
                     if not self._get_package_depwait_report(pkg, "all"):
                         self.create_debile_job(pkg, ["all"])
                 continue

            if len(archs) <= 0:
                print("Skipping job %s %s on %s, no architectures found!" % (pkg.pkgname, pkg.version, pkg.suite))
                continue

            for arch in archs:
                if not arch in pkg.installed_archs:
                    if self.debugMode:
                        print("Package %s not built for %s!" % (pkg.pkgname, arch))
                    if not self._get_package_depwait_report(pkg, "all"):
                        # do it!
                        self.create_debile_job(pkg, [arch])

    def sync_packages_all(self):
        for comp in self._archive_components:
            self.sync_packages(comp)

    def _reject_dud(self, dud, tag):
        print "REJECT: {source} because {tag}".format(
            tag=tag, source=dud['Source'])

        e = None
        try:
            dud.validate()
        except DudFileException as e:
            print e

        emit('reject', 'result', {
            "tag": tag,
            "source": dud['Source'],
        })

        for fp in [dud.get_filename()] + dud.get_files():
            os.unlink(fp)
        # Note this in the log.

    def _accept_dud(self, dud, builder):
        fire = dud.get_firehose()
        failed = True if dud.get('X-Debile-Failed', None) == "Yes" else False

        job = self._session.query(Job).get(dud['X-Debile-Job'])

        fire, _ = idify(fire)
        fire = uniquify(self._session, fire)

        result = Result()
        result.job = job
        result.source = job.source
        result.check = job.check
        result.firehose = fire
        result.binary = job.binary  # It's nullable. That's cool.
        self._session.merge(result)  # Needed because a *lot* of the Firehose is
        # going to need unique ${WORLD}.

        job.close(self._session, failed)
        self._session.commit()  # Neato.

        repo = result.get_repo()
        try:
            repo.add_dud(dud)
        except FilesAlreadyRegistered:
            return reject_dud(self._session, dud, "dud-files-already-registered")

        emit('receive', 'result', result.debilize())
        #  repo.add_dud removes the files

    def process_dud(self, path):
        dud = Dud(filename=path)
        jid = dud.get("X-Debile-Job", None)
        if jid is None:
            return self._reject_dud(dud, "missing-dud-job")

        try:
            dud.validate()
        except DudFileException as e:
            return self._reject_dud(dud, "invalid-dud-upload")

        key = dud.validate_signature()

        try:
            builder = self._session.query(Builder).filter_by(key=key).one()
        except NoResultFound:
            return self._reject_dud(dud, "invalid-dud-builder")

        try:
            job = self._session.query(Job).get(jid)
        except NoResultFound:
            return self._reject_dud(dud, "invalid-dud-job")

        if dud.get("X-Debile-Failed", None) is None:
            return self._reject_dud(dud, "no-failure-notice")

        if job.builder != builder:
            return self._reject_dud(dud, "invalid-dud-uploader")

        self._accept_dud(dud, builder)

    def process_incoming(self):
        os.chdir(self._incoming_path)
        for fname in os.listdir(self._incoming_path):
            if fname.endswith(".dud"):
                self.process_dud("%s/%s" % (self._incoming_path, fname))
        os.chdir("/tmp/")

def main():
    # init Apt, we need it later
    apt_pkg.init()

    parser = OptionParser()
    parser.add_option("-u", "--update-jobs",
                  action="store_true", dest="update", default=False,
                  help="syncronize Debile with archive contents")
    parser.add_option("-p", "--process-incoming",
                  action="store_true", dest="process_incoming", default=False,
                  help="import DUD files from incoming")

    (options, args) = parser.parse_args()

    if options.update:
        sync = ArchiveDebileBridge("staging")
        #sync.scheduleBuilds = options.build
        sync.sync_packages_all()
    elif options.process_incoming:
        adb = ArchiveDebileBridge("staging")
        adb.process_incoming()
    else:
        print("Run with -h for a list of available command-line options!")

if __name__ == '__main__':
    os.environ['LANG'] = 'C'
    os.environ['LC_ALL'] = 'C'
    main()
