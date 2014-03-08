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

import re
import importlib
from datetime import datetime

from firewoes.lib.orm import metadata
from firehose.model import Analysis

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref
from sqlalchemy import (Table, Column, ForeignKey, UniqueConstraint,
                        Integer, String, DateTime, Boolean)

from debile.master.arches import (arch_matches, get_affine_arch)
import debile.master.core


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
        "email": "email",
        "key": "key",
    }
    debilize = _debilize

    id = Column(Integer, primary_key=True)
    username = Column(String(255))  # Unique

    name = Column(String(255))
    email = Column(String(255))
    key = Column(String(255))
    password = Column(String(255))  # Weak password. Not actually critical.

    def validate(self, password):
        return self.password == password


class Builder(Base):
    __tablename__ = 'builders'
    _debile_objs = {
        "id": "id",
        "maintainer_id": "maintainer.username",
        "maintainer": "maintainer.name",
        "name": "name",
        "key": "key",
        "last_ping": "last_ping",
    }
    debilize = _debilize

    id = Column(Integer, primary_key=True)

    maintainer_id = Column(Integer, ForeignKey('people.id'))
    maintainer = relationship("Person", foreign_keys=[maintainer_id])

    name = Column(String(255))
    key = Column(String(255))
    password = Column(String(255))  # Weak password. Not actually critical.
    last_ping = Column(DateTime, nullable=False)

    def validate(self, password):
        return self.password == password


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


class Component(Base):
    __tablename__ = 'components'
    __table_args__ = (UniqueConstraint('name'),)
    _debile_objs = {
        "id": "id",
        "name": "name",
    }
    debilize = _debilize

    id = Column(Integer, primary_key=True)
    name = Column(String(255))


class Arch(Base):
    __tablename__ = 'arches'
    __table_args__ = (UniqueConstraint('name'),)
    _debile_objs = {
        "id": "id",
        "name": "name",
    }
    debilize = _debilize

    id = Column(Integer, primary_key=True)
    name = Column(String(255))


class Check(Base):
    __tablename__ = 'checks'
    _debile_objs = {
        "id": "id",
        "name": "name",
        "source": "source",
        "binary": "binary",
        "build": "build",
    }
    debilize = _debilize

    id = Column(Integer, primary_key=True)
    name = Column(String(255))

    source = Column(Boolean)
    binary = Column(Boolean)
    build = Column(Boolean)


class Group(Base):
    __tablename__ = 'groups'
    __table_args__ = (UniqueConstraint('name'),)
    _debile_objs = {
        "id": "id",
        "name": "name",
        "maintainer_id": "maintainer.username",
        "maintainer": "maintainer.name",
        "repo_path": "repo_path",
        "repo_url": "repo_url",
        "files_path": "files_path",
        "files_url": "files_url",
    }
    debilize = _debilize

    id = Column(Integer, primary_key=True)
    name = Column(String(255))

    maintainer_id = Column(Integer, ForeignKey('people.id'))
    maintainer = relationship("Person", foreign_keys=[maintainer_id])

    def get_repo_info(self):
        conf = debile.master.core.config.get("repo", None)
        custom_resolver = conf.get("custom_resolver", None)
        if custom_resolver:
            module, func = custom_resolver.rsplit(".", 1)
            m = importlib.import_module(module)
            return getattr(m, func)(self)

        entires = ["repo_path", "repo_url", "files_path", "files_url",]
        return {x: conf.get(x).format(
            name=self.name,
            id=self.id,
        ) for x in entires}

    @property
    def repo_path(self):
        return self.get_repo_info()['repo_path']

    @property
    def repo_url(self):
        return self.get_repo_info()['repo_url']

    @property
    def files_path(self):
        return self.get_repo_info()['files_path']

    @property
    def files_url(self):
        return self.get_repo_info()['files_url']


# Many-to-Many relationship
group_suite_component_association = \
    Table('group_suite_component_association', Base.metadata,
        Column('group_suite_id', Integer, ForeignKey('group_suites.id')),
        Column('component_id', Integer, ForeignKey('components.id'))
    )

# Many-to-Many relationship
group_suite_arch_association = \
    Table('group_suite_arch_association', Base.metadata,
        Column('group_suite_id', Integer, ForeignKey('group_suites.id')),
        Column('arch_id', Integer, ForeignKey('arches.id'))
    )

# Many-to-Many relationship
group_suite_check_association = \
    Table('group_suite_check_association', Base.metadata,
        Column('group_suite_id', Integer, ForeignKey('group_suites.id')),
        Column('check_id', Integer, ForeignKey('checks.id'))
    )

class GroupSuite(Base):
    __tablename__ = 'group_suites'
    _debile_objs = {
        "id": "id",
        "group_id": "group_id",
        "suite": "suite.name",
    }
    debilize = _debilize

    id = Column(Integer, primary_key=True)

    group_id = Column(Integer, ForeignKey('groups.id'))
    group = relationship("Group", backref="suites",
                         foreign_keys=[group_id])

    suite_id = Column(Integer, ForeignKey('suites.id'))
    suite = relationship("Suite", foreign_keys=[suite_id])

    components = relationship("Component", secondary=group_suite_component_association)
    arches = relationship("Arch", secondary=group_suite_arch_association)
    checks = relationship("Check", secondary=group_suite_check_association)

    def get_source_checks(self):
        return [x for x in self.checks if x.source==True and x.build==False]

    def get_binary_checks(self):
        return [x for x in self.checks if x.binary==True and x.build==False]

    def get_build_checks(self):
        return [x for x in self.checks if x.build==True]


# Many-to-Many relationship
source_arch_association = \
    Table('source_arch_association', Base.metadata,
        Column('source_id', Integer, ForeignKey('sources.id')),
        Column('arch_id', Integer, ForeignKey('arches.id'))
    )


class Source(Base):
    __tablename__ = 'sources'
    _debile_objs = {
        "id": "id",
        "name": "name",
        "version": "version",
        "suite": "group_suite.suite.name",
        "component": "component.name",
        "group_id": "group_suite.group_id",
        "uploader": "uploader.username",
        "uploaded_at": "uploaded_at",
    }
    debilize = _debilize

    id = Column(Integer, primary_key=True)
    name = Column(String(255))
    version = Column(String(255))

    group_suite_id = Column(Integer, ForeignKey('group_suites.id'))
    group_suite = relationship("GroupSuite", foreign_keys=[group_suite_id])

    component_id = Column(Integer, ForeignKey('components.id'))
    component = relationship("Component", foreign_keys=[component_id])

    arches = relationship("Arch", secondary=source_arch_association)

    uploader_id = Column(Integer, ForeignKey('people.id'))
    uploader = relationship("Person", foreign_keys=[uploader_id])

    uploaded_at = Column(DateTime, nullable=False)


class Maintainer(Base):
    __tablename__ = 'maintainers'
    _debile_objs = {
        "id": "id",
        "name": "name",
        "email": "email",
        "comaintainer": "comaintainer",
        "original_maintainer": "original_maintainer",
        "source_id": "source_id",
    }
    debilize = _debilize

    id = Column(Integer, primary_key=True)

    name = Column(String(255))
    email = Column(String(255))
    comaintainer = Column(Boolean)
    original_maintainer = Column(Boolean)

    source_id = Column(Integer, ForeignKey('sources.id'))
    source = relationship("Source", backref='maintainers',
                          foreign_keys=[source_id])


class Binary(Base):
    __tablename__ = 'binaries'
    _debile_objs = {
        "id": "id",
        "name": "source.name",
        "version": "source.version",
        "suite": "source.group_suite.suite.name",
        "component": "source.component.name",
        "arch": "build_job.arch.name",
        "group_id": "source.group_suite.group_id",
        "source_id": "source_id",
        "builder": "build_job.builder.name",
        "uploaded_at": "uploaded_at",
    }
    debilize = _debilize

    id = Column(Integer, primary_key=True)

    source_id = Column(Integer, ForeignKey('sources.id'))
    source = relationship("Source", backref="binaries",
                          foreign_keys=[source_id])

    build_job_id = Column(Integer, ForeignKey('jobs.id',
                                              name='fk_build_job_id',
                                              use_alter=True))
    build_job = relationship("Job", backref="built_binary",
                             foreign_keys=[build_job_id])

    uploaded_at = Column(DateTime)

    @staticmethod
    def from_job(job):
        return Binary(build_job=job, source=job.source,
                      uploaded_at=datetime.utcnow())


class Job(Base):
    __tablename__ = 'jobs'
    _debile_objs = {
        "id": "id",
        "name": "name",
        "check": "check.name",
        "suite": "source.group_suite.suite.name",
        "component": "source.component.name",
        "arch": "arch.name",
        "affinity": "affinity.name",
        "group_id": "source.group_suite.group_id",
        "source_id": "source_id",
        "binary_id": "binary_id",
        "builder": "builder.name",
        "assigned_at": "assigned_at",
        "finished_at": "finished_at",
        "failed": "failed",
    }
    debilize = _debilize

    id = Column(Integer, primary_key=True)
    name = Column(String(255))

    externally_blocked = Column(Boolean, default=False)
    # This is a temporary hack for tanglu until we get better support for
    # pending job support, however that will exist. It's not exposed over the
    # API since no one should be using this.

    check_id = Column(Integer, ForeignKey('checks.id'))
    check = relationship("Check", foreign_keys=[check_id])

    arch_id = Column(Integer, ForeignKey('arches.id'))
    arch = relationship("Arch", foreign_keys=[arch_id])

    affinity_id = Column(Integer, ForeignKey('arches.id'), nullable=True)
    affinity = relationship("Arch", foreign_keys=[affinity_id])

    source_id = Column(Integer, ForeignKey('sources.id'))
    source = relationship("Source", backref="jobs",
                          foreign_keys=[source_id])

    binary_id = Column(Integer, ForeignKey('binaries.id'), nullable=True)
    binary = relationship("Binary", backref="jobs",
                          foreign_keys=[binary_id])

    builder_id = Column(Integer, ForeignKey('builders.id'), nullable=True)
    builder = relationship("Builder", foreign_keys=[builder_id])

    assigned_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    failed = Column(Boolean, nullable=True)

    # Called when the .changes for a build job is processed
    def changes_uploaded(self, session, binary):
        for jd in self.blocking:
            if (jd.blocked_job.check.binary and
                    jd.blocked_job.source == self.source and
                    jd.blocked_job.arch == self.arch):
                jd.blocked_job.binary = binary
            # Only delete the dependency if the .dud from the successfull build
            # has already been processed.
            # Using "== False" to exclude both None and True
            if self.failed == False:
                session.delete(jd)

    # Called when a .dud for any job is processed
    def dud_uploaded(self, session, result):
        self.failed = result.failed
        # Only delete the dependency if the job was sucessfull and (if this is
        # a build job) the .changes has already been processed.
        if not result.failed and \
                (not self.check.build or
                 self.built_binary is not None):
            for jd in self.blocking:
                session.delete(jd)


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
    blocked_job = relationship("Job", foreign_keys=[blocked_job_id],
                               backref='depedencies')

    # this job is done
    blocking_job_id = Column(Integer, ForeignKey('jobs.id'))
    blocking_job = relationship("Job", foreign_keys=[blocking_job_id],
                                backref='blocking')


class Result(Base):
    __tablename__ = 'results'
    _debile_objs = {
        "id": "id",
        "job_id": "job_id",
        "firehose_id": "firehose_id",
        "failed": "failed",
        "uploaded_at": "uploaded_at",
    }
    debilize = _debilize

    id = Column(Integer, primary_key=True)

    job_id = Column(Integer, ForeignKey('jobs.id'))
    job = relationship("Job", foreign_keys=[job_id])

    firehose_id = Column(String, ForeignKey('analysis.id'))
    firehose = relationship(Analysis)

    failed = Column(Boolean)
    uploaded_at = Column(DateTime, nullable=True)

    @staticmethod
    def from_job(job):
        return Result(job=job, uploaded_at=datetime.utcnow())


def create_source(dsc, group_suite, component, uploader):
    source = Source(
        name=dsc['Source'],
        version=dsc['Version'],
        group_suite=group_suite,
        component=component,
        uploader=uploader,
        uploaded_at=datetime.utcnow()
    )

    for arch in group_suite.arches:
        for x in dsc['Architecture'].split():
            if arch_matches(arch.name, x):
                source.arches.append(arch)
                break

    MAINTAINER = re.compile("(?P<name>.*) \<(?P<email>.*)\>")

    source.maintainers.append(Maintainer(
        comaintainer=False,
        original_maintainer=False,
        **MAINTAINER.match(dsc.get('Maintainer')).groupdict()
    ))

    if dsc.get('XSBC-Original-Maintainer', None):
        source.maintainers.append(Maintainer(
            comaintainer=False,
            original_maintainer=True,
            **MAINTAINER.match(dsc.get('XSBC-Original-Maintainer')).groupdict()
        ))

    whos = re.findall(r'(?:[^,"]|"(?:\\.|[^"])*")+', dsc.get("Uploaders", ""))
    for who in [x.strip() for x in whos if x.strip() != ""]:
        source.maintainers.append(Maintainer(
            comaintainer=True,
            original_maintainer=False,
            **MAINTAINER.match(who).groupdict()
        ))

    return source


def create_jobs(source):
    """
    Create jobs for Source `source', for each arch in `arches'.
    `arches' sould be a subset of `source.arches' or `None', in which case
    `source.arches' will be used instead.
    """

    arches = source.arches
    aall = None
    for arch in source.group_suite.arches:
        if arch.name == "all":
            aall = arch
    else:
        raise ValueError("Can't find arch:all in the suite arches.")

    affinity = get_affine_arch(source.arches)
    print affinity

    raise Exception

    for check in source.group_suite.get_source_checks():
        j = Job(name="%s [%s]" % (check.name, "source"),
                check=check, arch=aall, affinity=affinity,
                source=source, binary=None,
                builder=None, assigned_at=None,
                finished_at=None, failed=None)
        source.jobs.append(j)

    builds = {}

    for check in source.group_suite.get_build_checks():
        for arch in arches:
            jobaffinity = affinity if arch == aall else None

            j = Job(name="%s [%s]" % (check.name, arch.name),
                    check=check, arch=arch, affinity=jobaffinity,
                    source=source, binary=None,
                    builder=None, assigned_at=None,
                    finished_at=None, failed=None)
            builds[arch] = j
            source.jobs.append(j)

    for check in source.group_suite.get_binary_checks():
        for arch in arches:
            jobaffinity = affinity if arch == aall else None

            deps = []
            deps.append(builds[arch])
            if aall in builds and aall != arch:
                deps.append(builds[aall])

            j = Job(name="%s [%s]" % (check.name, arch.name),
                    check=check, arch=arch, affinity=jobaffinity,
                    source=source, binary=None,
                    builder=None, assigned_at=None,
                    finished_at=None, failed=None)
            source.jobs.append(j)

            jds = [JobDependencies(blocked_job=j, blocking_job=x)
                   for x in deps]
            for dep in jds:
                j.depedencies.append(dep)


def init():
    from debile.master.core import engine
    Base.metadata.create_all(engine)
