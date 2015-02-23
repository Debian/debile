# Copyright (c) 2012-2013 Paul Tagliamonte <paultag@debian.org>
# Copyright (c) 2014-2015 Clement Schreiner <clement@mux.me>
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

from debile.master.orm import (Person, Builder, Suite, Component, Arch, Check,
                               Group, GroupSuite, Source, Binary, Job,
                               job_dependencies)
from debile.master.keyrings import import_pgp, import_ssl, clean_ssl_keyring
from debile.master.utils import emit

from debian.debian_support import Version
from datetime import datetime, timedelta

import threading
import logging


NAMESPACE = threading.local()


def generic_method(fn):
    def _(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except:
            logger = logging.getLogger('debile')
            logger.debug("Caught exception when processing xmlrpc request.", exc_info=True)
            raise
    return _


def builder_method(fn):
    def _(*args, **kwargs):
        if not NAMESPACE.machine:
            raise Exception("You can't do that")
        try:
            return fn(*args, **kwargs)
        except:
            logger = logging.getLogger('debile')
            logger.debug("Caught exception when processing xmlrpc request.", exc_info=True)
            raise
    return _


def user_method(fn):
    def _(*args, **kwargs):
        if not NAMESPACE.user:
            raise Exception("You can't do that")
        try:
            return fn(*args, **kwargs)
        except:
            logger = logging.getLogger('debile')
            logger.debug("Caught exception when processing xmlrpc request.", exc_info=True)
            raise
    return _


class DebileMasterInterface(object):
    """
    This is the exposed interface for the builders. Code enhancing the server
    should likely go here, unless you know what you're doing.
    """

    shutdown_request = False

    def __init__(self, ssl_keyring=None, pgp_keyring=None):
        self.ssl_keyring = ssl_keyring
        self.pgp_keyring = pgp_keyring

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

        if self.__class__.shutdown_request:
            return None

        arches = [x for x in arches if x not in ["source", "all"]]
        job = NAMESPACE.session.query(Job).join(Job.source).join(Source.group_suite).filter(
            ~Job.depedencies.any(),
            Job.dose_report == None,
            Job.assigned_at == None,
            Job.finished_at == None,
            Job.failed.is_(None),
            GroupSuite.suite.has(Suite.name.in_(suites)),
            Source.component.has(Component.name.in_(components)),
            (Job.arch.has(Arch.name.in_(arches)) |
             (Job.arch.has(Arch.name.in_(["source", "all"])) &
              Source.affinity.has(Arch.name.in_(arches)))),
            Job.check.has(Check.name.in_(checks)),
        ).order_by(
            Job.assigned_count.asc(),
            Source.uploaded_at.asc(),
        ).first()

        if job is None:
            return None

        job.assigned_count += 1
        job.assigned_at = datetime.utcnow()
        job.builder = NAMESPACE.machine

        emit('start', 'job', job.debilize())

        return job.debilize()

    @builder_method
    def close_job(self, job_id, failed):
        job = NAMESPACE.session.query(Job).get(job_id)
        job.finished_at = datetime.utcnow()

        emit('complete', 'job', job.debilize())

        return True

    @builder_method
    def forfeit_job(self, job_id):
        job = NAMESPACE.session.query(Job).get(job_id)
        job.assigned_at = None
        job.builder = None

        emit('abort', 'job', job.debilize())

        return True

    # Useful methods below.

    @generic_method
    def get_group(self, group_id):
        return NAMESPACE.session.query(Group).get(group_id).debilize()

    @generic_method
    def get_source(self, source_id):
        return NAMESPACE.session.query(Source).get(source_id).debilize()

    @generic_method
    def get_binary(self, binary_id):
        return NAMESPACE.session.query(Binary).get(binary_id).debilize()

    @generic_method
    def get_job(self, job_id):
        return NAMESPACE.session.query(Job).get(job_id).debilize()

    # Creating builders/users

    @user_method
    def create_builder(self, name, pgp, ssl):
        if self.ssl_keyring is None:
            # TODO: handle this correctly
            raise Exception

        if NAMESPACE.session.query(Builder).filter_by(name=name).first():
            raise ValueError("Slave already exists.")

        pgp = import_pgp(self.pgp_keyring, pgp)
        ssl = import_ssl(self.ssl_keyring, ssl, name)

        b = Builder(name=name, maintainer=NAMESPACE.user, pgp=pgp, ssl=ssl,
                    last_ping=datetime.utcnow())
        NAMESPACE.session.add(b)

        emit('create', 'slave', b.debilize())
        return b.debilize()

    @user_method
    def update_builder_keys(self, name, pgp, ssl):
        if self.ssl_keyring is None:
            # TODO
            raise Exception
        builder = NAMESPACE.session.query(Builder).filter_by(name=name).first()

        if not builder:
            raise ValueError("No builder with name %s." % name)

        builder.pgp = import_pgp(self.pgp_keyring, pgp)
        builder.ssl = import_ssl(self.ssl_keyring, ssl, builder.name)

        clean_ssl_keyring(self.ssl_keyring, NAMESPACE.session)

        return builder.debilize()

    @user_method
    def disable_builder(self, name):
        if self.ssl_keyring is None:
            # TODO
            raise Exception
        builder = NAMESPACE.session.query(Builder).filter_by(name=name).first()

        if not builder:
            raise ValueError("No builder with name %s." % name)

        builder.pgp = "0000000000000000DEADBEEF0000000000000000"
        builder.ssl = "0000000000000000DEADBEEF0000000000000000"

        clean_ssl_keyring(self.ssl_keyring, NAMESPACE.session)

        return builder.debilize()

    @user_method
    def create_user(self, name, email, pgp, ssl):
        if self.ssl_keyring is None:
            # TODO
            raise Exception
        if NAMESPACE.session.query(Person).filter_by(email=email).first():
            raise ValueError("User already exists.")

        pgp = import_pgp(self.pgp_keyring, pgp)
        ssl = import_ssl(self.ssl_keyring, ssl, name, email)

        p = Person(name=name, email=email, pgp=pgp, ssl=ssl)
        NAMESPACE.session.add(p)

        emit('create', 'user', p.debilize())
        return p.debilize()

    @user_method
    def update_user_keys(self, email, pgp, ssl):
        if self.ssl_keyring is None:
            # TODO
            raise Exception
        user = NAMESPACE.session.query(Person).filter_by(email=email).first()

        if not user:
            raise ValueError("No user with email %s." % email)

        user.pgp = import_pgp(self.pgp_keyring, pgp)
        user.ssl = import_ssl(self.ssl_keyring, ssl, user.name, user.email)

        clean_ssl_keyring(self.ssl_keyring, NAMESPACE.session)

        return user.debilize()

    @user_method
    def disable_user(self, email):
        if self.ssl_keyring is None:
            # TODO
            raise Exception
        user = NAMESPACE.session.query(Builder).filter_by(email=email).first()

        if not user:
            raise ValueError("No user with email %s." % email)

        user.pgp = "0000000000000000DEADBEEF0000000000000000"
        user.ssl = "0000000000000000DEADBEEF0000000000000000"

        clean_ssl_keyring(self.ssl_keyring, NAMESPACE.session)

        return user.debilize()

    # Re-run jobs

    @user_method
    def rerun_job(self, job_id):
        job = NAMESPACE.session.query(Job).get(job_id)

        if not job:
            raise ValueError("No job with id %s." % job_id)

        if any(job.built_binaries):
            raise ValueError("Can not re-run a successfull build job.")

        versions = NAMESPACE.session.query(Source.version).filter(
            Source.group_suite == job.source.group_suite,
            Source.name == job.source.name,
        )
        max_version = max([x[0] for x in versions], key=Version)
        if job.source.version != max_version:
            raise ValueError("Can not re-run a job for a superseeded source.")

        job.failed = None
        job.builder = None
        job.assigned_at = None
        job.finished_at = None

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

            job.failed = None
            job.builder = None
            job.assigned_at = None
            job.finished_at = None

    @user_method
    def retry_failed(self):
        cutoff = datetime.utcnow() - timedelta(hours=1)
        jobs = NAMESPACE.session.query(Job).filter(
            ~Job.built_binaries.any(),
            Job.check.has(Check.build == True),
            Job.finished_at != None,
            Job.finished_at < cutoff,
        )

        for job in jobs:
            versions = NAMESPACE.session.query(Source.version).filter(
                Source.group_suite == job.source.group_suite,
                Source.name == job.source.name
            )
            max_version = max([x[0] for x in versions], key=Version)
            if job.source.version != max_version:
                continue

            job.failed = None
            job.builder = None
            job.assigned_at = None
            job.finished_at = None

    @user_method
    def set_check(self, check, *args):
        is_source = True if 'source' in args else False
        is_binary = True if 'binary' in args else False
        is_build = True if 'build' in args else False

        check_query = NAMESPACE.session.query(Check).filter_by(name=check)
        if check_query.count() > 0:
            check = check_query.one()
        else:
            check = Check(name=check)

        check.source = is_source
        check.binary = is_binary
        check.build = is_build
        NAMESPACE.session.add(check)
        return check.debilize()

    @user_method
    def enable_check(self, check, group, suite):
        suite_query = NAMESPACE.session.query(Suite).filter_by(name=suite)
        group_query = NAMESPACE.session.query(Group).filter_by(name=group)

        if group_query.count() == 0:
            raise ValueError('No group named %s' % group)

        if suite_query.count() == 0:
            raise ValueError('No suite name %s' % suite)

        gs_query = NAMESPACE.session.query(GroupSuite).filter_by(
            group=group_query.one(),
            suite=suite_query.one(),
        )

        if (gs_query
                .join(GroupSuite.checks)
                .filter(Check.name == check)
                .count() > 0):
            raise ValueError('Check %s already setup for %s/%s' %
                             (check, group, suite))

        check_query = NAMESPACE.session.query(Check).filter_by(name=check)
        if check_query.count() == 0:
            raise ValueError('Check %s does not exist' % check)

        gs = gs_query.one()
        gs.checks.append(check_query.one())
        return 'Check %s added to %s.' % (check, gs)

    @user_method
    def list_checks(self, *args):
        # FIXME: return an user-friendly table
        # FIXME: list groups/suites the checks are enabled for
        checks_query = NAMESPACE.session.query(Check)
        return [c.debilize() for c in checks_query.all()]
