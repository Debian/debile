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
                               Group, GroupSuite, Source, Binary, Job,
                               JobDependencies)
from debile.master.messaging import emit
from debile.master.keyrings import import_pgp, import_ssl

from datetime import datetime


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
        suite_ids = [
            x.id for x in NAMESPACE.session.query(Suite).filter(
                Suite.name.in_(suites)
            ).all()
        ]
        component_ids = [
            x.id for x in NAMESPACE.session.query(Component).filter(
                Component.name.in_(components)
            ).all()
        ]
        arch_ids = [
            x.id for x in NAMESPACE.session.query(Arch).filter(
                Arch.name.in_(arches)
            ).all()
        ]
        check_ids = [
            x.id for x in NAMESPACE.session.query(Check).filter(
                Check.name.in_(checks)
            ).all()
        ]

        job = NAMESPACE.session.query(Job).filter(
            Job.externally_blocked == False,
            Job.assigned_at == None,
            Job.finished_at == None,
            GroupSuite.suite_id.in_(suite_ids),
            Source.component_id.in_(component_ids),
            Job.arch_id.in_(arch_ids),
            Job.affinity_id.in_(arch_ids),
            Job.check_id.in_(check_ids),
        ).outerjoin(Job.depedencies).filter(
            JobDependencies.id == None
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
    def create_user(self, name, email, pgp, ssl):
        if NAMESPACE.session.query(Builder).filter_by(email=email).first():
            raise ValueError("User already exists.")

        pgp = import_pgp(pgp)
        ssl = import_ssl(ssl, name, email)

        p = Person(name=name, email=email, pgp=pgp, ssl=ssl)
        NAMESPACE.session.add(p)
        NAMESPACE.session.commit()

        emit('create', 'user', p.debilize())
        return p.debilize()
