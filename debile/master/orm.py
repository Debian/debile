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

import os.path
import datetime as dt
import debile.master.core
from debile.master.reprepro import Repo

from firewoes.lib.orm import metadata
from firehose.model import Analysis

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref
from sqlalchemy import (Column, Integer, String, DateTime, ForeignKey,
                        Boolean, UniqueConstraint)

Base = declarative_base(metadata=metadata)


def _debilize(self):
    def getthing(obj, name):
        if "." in name:
            local, remote = name.split(".", 1)
            foo = getattr(obj, local)
            if foo is None:
                return foo
            return getthing(foo, remote)
        local = name
        return getattr(obj, local)

    ret = {}
    for attribute, path in self._debile_objs.items():
        ret[attribute] = getthing(self, path)

    return ret


class Person(Base):
    __tablename__ = 'people'
    __table_args__ = (UniqueConstraint('username'),)
    _debile_objs = {
        "id": "id",
        "username": "username",
        "name": "name",
        "key": "key",
    }
    debilize = _debilize

    id = Column(Integer, primary_key=True)
    username = Column(String(255))  # Unique

    name = Column(String(255))
    key = Column(String(255))
    email = Column(String(255))
    password = Column(String(255))  # Weak password. Not actually critical.

    def validate(self, password):
        return self.password == password


class Builder(Base):
    __tablename__ = 'builders'
    _debile_objs = {
        "id": "id",
        "maintainer_id": "maintainer.username",
        "name": "name",
        "key": "key",
        "last_ping": "last_ping",
    }
    debilize = _debilize

    id = Column(Integer, primary_key=True)
    maintainer_id = Column(Integer, ForeignKey('people.id'))
    maintainer = relationship("Person")

    name = Column(String(255))
    key = Column(String(255))
    password = Column(String(255))  # Weak password. Not actually critical.
    last_ping = Column(DateTime, nullable=False)

    def validate(self, password):
        return self.password == password


class Group(Base):
    __tablename__ = 'groups'
    __table_args__ = (UniqueConstraint('name'),)
    _debile_objs = {
        "id": "id",
        "name": "name",
        "maintainer_id": "maintainer.name",
    }
    debilize = _debilize

    id = Column(Integer, primary_key=True)

    name = Column(String(255))

    maintainer_id = Column(Integer, ForeignKey('people.id'))
    maintainer = relationship("Person")

    arches = relationship("GroupArch", backref="group")
    suites = relationship("GroupSuite", backref="group")

    checks = relationship("Check", backref="check")

    def get_repo(self):
        root = debile.master.core.config['repo']['base']
        name = self.name or "default"
        base = os.path.join(root, name)
        return Repo(base)


class Arch(Base):
    __tablename__ = 'arches'
    _debile_objs = {
        "id": "id",
        "name": "name",
    }
    debilize = _debilize

    id = Column(Integer, primary_key=True)
    name = Column(String(255))


class GroupArch(Base):
    __tablename__ = 'group_arches'
    _debile_objs = {
        "id": "id",
        "group_id": "group.name",
        "arch_id": "arch.name",
    }
    debilize = _debilize

    id = Column(Integer, primary_key=True)

    group_id = Column(Integer, ForeignKey('groups.id'))
    #group = relationship("Group")

    arch_id = Column(Integer, ForeignKey('arches.id'))
    arch = relationship("Arch")


class GroupSuite(Base):
    __tablename__ = 'group_suites'
    _debile_objs = {
        "id": "id",
        "group_id": "group.name",
        "suite_id": "suite.name",
    }
    debilize = _debilize

    id = Column(Integer, primary_key=True)

    group_id = Column(Integer, ForeignKey('groups.id'))
    #group = relationship("Group")

    suite_id = Column(Integer, ForeignKey('suites.id'))
    suite = relationship("Suite")


class Suite(Base):
    __tablename__ = 'suites'
    __table_args__ = (UniqueConstraint('name'),)
    _debile_objs = {
        "id": "id",
        "name": "name",
    }
    debilize = _debilize

    id = Column(Integer, primary_key=True)
    name = Column(String(255))


class Source(Base):
    __tablename__ = 'sources'
    _debile_objs = {
        "id": "id",
        "name": "name",
        "version": "version",
        "group": "group.name",
        "suite": "suite.name",
        "uploader": "uploader.username",
        "uploaded_at": "uploaded_at",
        "updated_at": "updated_at",
    }
    debilize = _debilize

    id = Column(Integer, primary_key=True)

    name = Column(String(255))
    version = Column(String(255))

    group_id = Column(Integer, ForeignKey('groups.id'))
    group = relationship("Group")

    suite_id = Column(Integer, ForeignKey('suites.id'))
    suite = relationship("Suite")

    uploader_id = Column(Integer, ForeignKey('people.id'))
    uploader = relationship("Person")

    uploaded_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    jobs = relationship("Job")
    maintainers = relationship("Maintainer")

    def create_jobs(self, session, arches):
        group = self.group
        aall = session.query(Arch).filter_by(name='all').one()  # All

        arch_list = []
        for arch in arches:
            if arch in ['any', 'linux-any']:
                arch_list += [x.arch for x in group.arches if
                              x.arch.name != 'all']
                # The reason we filter all out is because all packages
                # with any packages are marked `any all' not just `any'
            else:
                arch_list.append(session.query(Arch).filter_by(
                    name=arch
                ).one())

        for check in group.checks:
            if not check.source:
                continue

            if check.arched:
                for arch in arch_list:
                    #print self.name, check.name, arch.name
                    j = Job(assigned_at=None, finished_at=None,
                            name=check.name, score=100, builder=None,
                            source=self, binary=None, check=check,
                            suite=self.suite, arch=arch)
                    self.jobs.append(j)

            if check.arched is False:
                #print self.name, check.name, 'all'
                j = Job(assigned_at=None, finished_at=None,
                        name=check.name, score=100, builder=None,
                        source=self, binary=None, check=check,
                        suite=self.suite, arch=aall)
                self.jobs.append(j)


class Maintainer(Base):
    __tablename__ = 'maintainers'
    _debile_objs = {
        "id": "id",
        "name": "name",
        "email": "email",
        "comaintainer": "comaintainer",
        "source_id": "source_id",
    }
    debilize = _debilize

    id = Column(Integer, primary_key=True)

    name = Column(String(255))
    email = Column(String(255))
    comaintainer = Column(Boolean)

    source_id = Column(Integer, ForeignKey('sources.id'))
    source = relationship("Source")


class Binary(Base):
    __tablename__ = 'binaries'
    _debile_objs = {
        "id": "id",
        "source": "source_id",
        "builder": "builder_id",
        "suite": "suite.name",
        "group": "group.name",
        "name": "name",
        "version": "version",
        "arch": "arch.name",
        "uploaded_at": "uploaded_at",
        "updated_at": "updated_at",
    }
    debilize = _debilize

    id = Column(Integer, primary_key=True)

    source_id = Column(Integer, ForeignKey('sources.id'))
    source = relationship("Source")

    builder_id = Column(Integer, ForeignKey('builders.id'))
    builder = relationship("Builder")

    suite_id = Column(Integer, ForeignKey('suites.id'))
    suite = relationship("Suite")

    group_id = Column(Integer, ForeignKey('groups.id'))
    group = relationship("Group")

    arch_id = Column(Integer, ForeignKey('arches.id'))
    arch = relationship("Arch")

    jobs = relationship("Job")

    name = Column(String(255))
    version = Column(String(255))
    uploaded_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    @classmethod
    def from_source(cls, source, arch, builder):
        return Binary(arch=arch, source=source, builder=builder,
                      suite=source.suite, group=source.group, name=source.name,
                      version=source.version, uploaded_at=dt.datetime.utcnow(),
                      updated_at=dt.datetime.utcnow())

    def create_jobs(self, session):
        group = self.group
        for check in (x for x in group.checks if x.binary):
            print "New job ({arch}) for {name} - {check}".format(
                arch=self.arch.name,
                name=self.name,
                check=check.name
            )
            j = Job(assigned_at=None, finished_at=None,
                    name=check.name, score=100, builder=None,
                    source=self.source, binary=self, check=check,
                    suite=self.suite, arch=self.arch)
            self.jobs.append(j)


class Check(Base):
    __tablename__ = 'checks'
    _debile_objs = {
        "id": "id",
        "group_id": "group.name",
        "name": "name",
        "source": "source",
        "binary": "binary",
        "arched": "arched",
    }
    debilize = _debilize

    id = Column(Integer, primary_key=True)

    group_id = Column(Integer, ForeignKey('groups.id'))
    group = relationship("Group")

    name = Column(String(255))
    source = Column(Boolean)
    binary = Column(Boolean)
    arched = Column(Boolean, nullable=False)


class Job(Base):
    __tablename__ = 'jobs'
    _debile_objs = {
        "id": "id",
        "name": "name",
        "score": "score",
        "assigned_at": "assigned_at",
        "finished_at": "finished_at",
        "builder": "builder.name",
        "source_id": "source_id",
        "binary_id": "binary_id",
        "check": "check.name",
        "arch": "arch.name",
        "suite": "suite.name",
    }
    debilize = _debilize

    id = Column(Integer, primary_key=True)

    assigned_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)

    name = Column(String(255))
    score = Column(Integer)

    builder_id = Column(Integer, ForeignKey('builders.id'), nullable=True)
    builder = relationship("Builder")

    source_id = Column(Integer, ForeignKey('sources.id'))
    source = relationship("Source")

    binary_id = Column(Integer, ForeignKey('binaries.id'), nullable=True)
    binary = relationship("Binary")

    check_id = Column(Integer, ForeignKey('checks.id'))
    check = relationship("Check")

    arch_id = Column(Integer, ForeignKey('arches.id'))
    arch = relationship("Arch")

    suite_id = Column(Integer, ForeignKey('suites.id'))
    suite = relationship("Suite")

    results = relationship("Result")


class JobDependencies(Base):
    __tablename__ = 'job_dependencies'
    _debile_objs = {
        "id": "id",
        "blocked_job_id": "blocked_job_id",
        "blocking_job_id": "blocking_job_id",
    }
    debilize = _debilize

    id = Column(Integer, primary_key=True)

    # The job that can not run until
    blocked_job_id = Column(Integer, ForeignKey('jobs.id'))
    blocked_job = relationship("Job", foreign_keys=[blocked_job_id])

    # this job is done
    blocking_job_id = Column(Integer, ForeignKey('jobs.id'))
    blocking_job = relationship("Job", foreign_keys=[blocking_job_id])


class Result(Base):
    __tablename__ = 'results'
    _debile_objs = {
        "id": "id",
        "failed": "failed",
        "source_id": "source_id",
        "binary_id": "binary_id",
        "check_id": "check.name",
        "job_id": "job_id",
    }
    debilize = _debilize

    id = Column(Integer, primary_key=True)

    failed = Column(Boolean)
    source_id = Column(Integer, ForeignKey('sources.id'))
    source = relationship("Source")

    binary_id = Column(Integer, ForeignKey('binaries.id'), nullable=True)
    binary = relationship("Binary")

    check_id = Column(Integer, ForeignKey('checks.id'))
    check = relationship("Check")

    job_id = Column(Integer, ForeignKey('jobs.id'))
    job = relationship("Job")

    firehose_id = Column(Integer, ForeignKey('analysis.id'))
    firehose = relationship(Analysis)


def init():
    from debile.master.core import engine
    Base.metadata.create_all(engine)
