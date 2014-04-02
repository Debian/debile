# Copyright (c) 2012-2013 Paul Tagliamonte <paultag@debian.org>
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

from debile.master.server import user_method, builder_method, NAMESPACE
from debile.master.orm import (Person, Builder, Suite, Component, Arch, Check,
                               Group, GroupSuite, Source, Binary, Job)
from debile.master.messaging import emit
from debile.master.keyrings import import_pgp, import_ssl, clean_ssl_keyring

from debian.debian_support import Version
from datetime import datetime
import shutil
import os


class DebileMasterInterface(object):
    """
    This is the exposed interface for the builders. Code enhacing the server
    should likely go here, unless you know what you're doing.
    """

    # Simple stuff.

    @builder_method
    def builder_whoami(self):
        """
        ID check
        """
        return NAMESPACE.machine.name

    @user_method
    def user_whoami(self):
        """
        ID check
        """
        return NAMESPACE.user.name

    # The following trio of methods handle the job control.

    @builder_method
    def get_next_job(self, suites, components, arches, checks):
        NAMESPACE.machine.last_ping = datetime.utcnow()
        NAMESPACE.session.add(NAMESPACE.machine)
        NAMESPACE.session.commit()

        job = NAMESPACE.session.query(Job).join(Job.source).join(Job.check).filter(
            ~Job.depedencies.any(),
            Job.externally_blocked == False,
            Job.assigned_at == None,
            Job.finished_at == None,
            GroupSuite.suite.has(Suite.name.in_(suites)),
            Source.component.has(Component.name.in_(components)),
            Job.arch.has(Arch.name.in_(arches)),
            Job.affinity.has(Arch.name.in_(arches)),
            Job.check.has(Check.name.in_(checks)),
        ).order_by(
            Check.build.desc(),
            Source.uploaded_at.asc(),
        ).first()

        if job is None:
            return None

        job.assigned_at = datetime.utcnow()
        job.builder = NAMESPACE.machine
        NAMESPACE.session.add(job)
        NAMESPACE.session.commit()

        emit('start', 'job', job.debilize())

        return job.debilize()

    @builder_method
    def close_job(self, job_id, failed):
        job = NAMESPACE.session.query(Job).get(job_id)
        job.finished_at = datetime.utcnow()

        NAMESPACE.session.add(job)
        NAMESPACE.session.commit()

        emit('complete', 'job', job.debilize())

        return True

    @builder_method
    def forfeit_job(self, job_id):
        job = NAMESPACE.session.query(Job).get(job_id)
        job.assigned_at = None
        job.builder = None
        NAMESPACE.session.add(job)
        NAMESPACE.session.commit()

        emit('abort', 'job', job.debilize())

        return True

    # Useful methods below.

    def get_group(self, group_id):
        return NAMESPACE.session.query(Group).get(group_id).debilize()

    def get_source(self, source_id):
        return NAMESPACE.session.query(Source).get(source_id).debilize()

    def get_binary(self, binary_id):
        return NAMESPACE.session.query(Binary).get(binary_id).debilize()

    def get_job(self, job_id):
        return NAMESPACE.session.query(Job).get(job_id).debilize()

    # Creating builders/users

    @user_method
    def create_builder(self, name, pgp, ssl):
        if NAMESPACE.session.query(Builder).filter_by(name=name).first():
            raise ValueError("Slave already exists.")

        pgp = import_pgp(pgp)
        ssl = import_ssl(ssl, name)

        b = Builder(name=name, maintainer=NAMESPACE.user, pgp=pgp, ssl=ssl,
                    last_ping=datetime.utcnow())
        NAMESPACE.session.add(b)
        NAMESPACE.session.commit()

        emit('create', 'slave', b.debilize())
        return b.debilize()

    @user_method
    def update_builder_keys(self, name, pgp, ssl):
        builder = NAMESPACE.session.query(Builder).filter_by(name=name).first()

        if not builder:
            raise ValueError("No builder with name %s." % name)

        builder.pgp = import_pgp(pgp)
        builder.ssl = import_ssl(ssl, name)

        NAMESPACE.session.add(builder)
        NAMESPACE.session.commit()
        clean_ssl_keyring(NAMESPACE.session)

        return builder.debilize()

    @user_method
    def disable_builder(self, name):
        builder = NAMESPACE.session.query(Builder).filter_by(name=name).first()

        if not builder:
            raise ValueError("No builder with name %s." % name)

        builder.pgp = "0000000000000000DEADBEEF0000000000000000"
        builder.ssl = "0000000000000000DEADBEEF0000000000000000"

        NAMESPACE.session.add(builder)
        NAMESPACE.session.commit()
        clean_ssl_keyring(NAMESPACE.session)

        return builder.debilize()

    @user_method
    def create_user(self, name, email, pgp, ssl):
        if NAMESPACE.session.query(Person).filter_by(email=email).first():
            raise ValueError("User already exists.")

        pgp = import_pgp(pgp)
        ssl = import_ssl(ssl, name, email)

        p = Person(name=name, email=email, pgp=pgp, ssl=ssl)
        NAMESPACE.session.add(p)
        NAMESPACE.session.commit()

        emit('create', 'user', p.debilize())
        return p.debilize()

    @user_method
    def update_user_keys(self, email, pgp, ssl):
        user = NAMESPACE.session.query(Person).filter_by(email=email).first()

        if not user:
            raise ValueError("No user with email %s." % email)

        user.pgp = import_pgp(pgp)
        user.ssl = import_ssl(ssl, user.name, user.email)

        NAMESPACE.session.add(user)
        NAMESPACE.session.commit()
        clean_ssl_keyring(NAMESPACE.session)

        return user.debilize()

    @user_method
    def disable_user(self, email):
        user = NAMESPACE.session.query(Builder).filter_by(email=email).first()

        if not user:
            raise ValueError("No user with email %s." % email)

        user.pgp = "0000000000000000DEADBEEF0000000000000000"
        user.ssl = "0000000000000000DEADBEEF0000000000000000"

        NAMESPACE.session.add(user)
        NAMESPACE.session.commit()
        clean_ssl_keyring(NAMESPACE.session)

        return user.debilize()

    # Re-run jobs

    @user_method
    def rerun_job(self, job_id):
        job = NAMESPACE.session.query(Job).get(job_id)

        if not job:
            raise ValueError("No job with id %s." % job_id)

        # Using "== False" to exclude both None and True
        if job.check.build and job.failed == False:
            raise ValueError("Can not re-run a successfull build job.")

        if os.access(job.files_path, os.F_OK):
            shutil.rmtree(job.files_path)

        job.failed = None
        job.builder = None
        job.assigned_at = None
        job.finished_at = None
        NAMESPACE.session.add(job)
        NAMESPACE.session.commit()

        return job.debilize()

    @user_method
    def rerun_check(self, name):
        check = NAMESPACE.session.query(Check).filter_by(name=name).one()

        if check.build:
            raise ValueError("Can not re-run a build check.")

        jobs = NAMESPACE.session.query(Job).filter(
            Job.check == check
        )

        for job in jobs:
            versions = NAMESPACE.session.query(Source.version).filter(
                Source.group_suite == job.source.group_suite,
                Source.name == job.source.name,
            )
            max_version = max([x[0] for x in versions], key=Version)
            if job.source.version != max_version:
                continue

            if os.access(job.files_path, os.F_OK):
                shutil.rmtree(job.files_path)

            job.failed = None
            job.builder = None
            job.assigned_at = None
            job.finished_at = None
            NAMESPACE.session.add(job)
            NAMESPACE.session.commit()

        return jobs.count()

    @user_method
    def retry_failed(self):
        jobs = NAMESPACE.session.query(Job).filter(
            Job.failed == True,
            Job.check.has(Check.build == True),
        )

        for job in jobs:
            versions = NAMESPACE.session.query(Source.version).filter(
                Source.group_suite == job.source.group_suite,
                Source.name == job.source.name
            )
            max_version = max([x[0] for x in versions], key=Version)
            if job.source.version != max_version:
                continue

            if os.access(job.files_path, os.F_OK):
                shutil.rmtree(job.files_path)

            job.failed = None
            job.builder = None
            job.assigned_at = None
            job.finished_at = None
            NAMESPACE.session.add(job)
            NAMESPACE.session.commit()

        return jobs.count()
