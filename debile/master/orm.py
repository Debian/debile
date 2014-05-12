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
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship, backref
from sqlalchemy import (Table, Column, ForeignKey, UniqueConstraint,
                        Integer, String, DateTime, Boolean)

from debile.master.utils import config
from debile.master.arches import (get_preferred_affinity, get_source_arches)


Base = declarative_base(metadata=metadata)


def _debilize(self):
    def getthing(obj, name):
        if obj is None:
            return None
        if "." in name:
            local, remote = name.split(".", 1)
            foo = getattr(obj, local)
            return getthing(foo, remote)
        if name == "__str__":
            return str(obj)
        if name == "__debilize__":
            return _debilize(obj)
        if name == "__list__":
            return [_debilize(x) for x in obj]
        return getattr(obj, name)

    if self is None:
        return None

    ret = {}
    for attribute, path in self._debile_objs.items():
        ret[attribute] = getthing(self, path)
    return ret


class Person(Base):
    __tablename__ = 'people'
    __table_args__ = (UniqueConstraint('email'),)
    _debile_objs = {
        "id": "id",
        "name": "name",
        "email": "email",
        "pgp": "pgp",
        "ssl": "ssl",
    }
    debilize = _debilize

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)

    pgp = Column(String(40), nullable=True, default=None)
    ssl = Column(String(40), nullable=True, default=None)

    def __str__(self):
        return "%s <%s>" % (self.name, self.email)

    def __repr__(self):
        return "<Person: %s (%s)>" % (self.email, self.id)


class Builder(Base):
    __table_args__ = (UniqueConstraint('name'),)
    __tablename__ = 'builders'
    _debile_objs = {
        "id": "id",
        "name": "name",
        "last_ping": "last_ping",
        "maintainer_name": "maintainer.name",
        "maintainer_email": "maintainer.email",
        "pgp": "pgp",
        "ssl": "ssl",
    }
    debilize = _debilize

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    last_ping = Column(DateTime, nullable=False)

    maintainer_id = Column(Integer, ForeignKey('people.id', ondelete="RESTRICT"), nullable=False)
    maintainer = relationship("Person", foreign_keys=[maintainer_id])

    pgp = Column(String(40), nullable=True, default=None)
    ssl = Column(String(40), nullable=True, default=None)

    def __str__(self):
        return self.name

    def __repr__(self):
        return "<Builder: %s (%s)>" % (self.name, self.id)


class Suite(Base):
    __tablename__ = 'suites'
    __table_args__ = (UniqueConstraint('name'),)
    _debile_objs = {
        "id": "id",
        "name": "name",
    }
    debilize = _debilize

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)

    def __str__(self):
        return self.name

    def __repr__(self):
        return "<Suite: %s (%s)>" % (self.name, self.id)


class Component(Base):
    __tablename__ = 'components'
    __table_args__ = (UniqueConstraint('name'),)
    _debile_objs = {
        "id": "id",
        "name": "name",
    }
    debilize = _debilize

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)

    def __str__(self):
        return self.name

    def __repr__(self):
        return "<Component: %s (%s)>" % (self.name, self.id)


class Arch(Base):
    __tablename__ = 'arches'
    __table_args__ = (UniqueConstraint('name'),)
    _debile_objs = {
        "id": "id",
        "name": "name",
    }
    debilize = _debilize

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)

    def __str__(self):
        return self.name

    def __repr__(self):
        return "<Arch: %s (%s)>" % (self.name, self.id)


class Check(Base):
    __tablename__ = 'checks'
    __table_args__ = (UniqueConstraint('name'),)
    _debile_objs = {
        "id": "id",
        "name": "name",
        "source": "source",
        "binary": "binary",
        "build": "build",
    }
    debilize = _debilize

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)

    source = Column(Boolean, nullable=False)
    binary = Column(Boolean, nullable=False)
    build = Column(Boolean, nullable=False)

    def __str__(self):
        return self.name

    def __repr__(self):
        return "<Check: %s (%s)>" % (self.name, self.id)


class Group(Base):
    __tablename__ = 'groups'
    __table_args__ = (UniqueConstraint('name'),)
    _debile_objs = {
        "id": "id",
        "name": "name",
        "maintainer_name": "maintainer.name",
        "maintainer_email": "maintainer.email",
        "repo_path": "repo_path",
        "repo_url": "repo_url",
        "files_path": "files_path",
        "files_url": "files_url",
    }
    debilize = _debilize

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)

    maintainer_id = Column(Integer, ForeignKey('people.id', ondelete="RESTRICT"), nullable=False)
    maintainer = relationship("Person", foreign_keys=[maintainer_id])

    def get_repo_info(self):
        conf = config.get("repo", None)
        custom_resolver = conf.get("custom_resolver", None)
        if custom_resolver:
            module, func = custom_resolver.rsplit(".", 1)
            m = importlib.import_module(module)
            return getattr(m, func)(self, conf)

        entires = ["repo_path", "repo_url", "files_path", "files_url"]

        for entry in entires:
            if conf.get(entry) is None:
                raise ValueError("No configured repo info. Set in master.yaml")

        return {x: conf[x].format(
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

    def __str__(self):
        return self.name

    def __repr__(self):
        return "<Group: %s (%s)>" % (self.name, self.id)


# Many-to-Many relationship
group_suite_component_association = (
    Table('group_suite_component_association', Base.metadata,
          Column('group_suite_id', Integer, ForeignKey('group_suites.id', ondelete="CASCADE"), nullable=False),
          Column('component_id', Integer, ForeignKey('components.id', ondelete="RESTRICT"), nullable=False)))


group_suite_arch_association = (
    Table('group_suite_arch_association', Base.metadata,
          Column('group_suite_id', Integer, ForeignKey('group_suites.id', ondelete="CASCADE"), nullable=False),
          Column('arch_id', Integer, ForeignKey('arches.id', ondelete="RESTRICT"), nullable=False)))


group_suite_check_association = (
    Table('group_suite_check_association', Base.metadata,
          Column('group_suite_id', Integer, ForeignKey('group_suites.id', ondelete="CASCADE"), nullable=False),
          Column('check_id', Integer, ForeignKey('checks.id', ondelete="RESTRICT"), nullable=False)))


class GroupSuite(Base):
    __tablename__ = 'group_suites'
    _debile_objs = {
        "id": "id",
        "group": "group.name",
        "suite": "suite.name",
    }
    debilize = _debilize

    id = Column(Integer, primary_key=True)

    group_id = Column(Integer, ForeignKey('groups.id', ondelete="RESTRICT"), nullable=False)
    group = relationship("Group", foreign_keys=[group_id],
                         backref=backref("group_suites", passive_deletes=True))

    suite_id = Column(Integer, ForeignKey('suites.id', ondelete="RESTRICT"), nullable=False)
    suite = relationship("Suite", foreign_keys=[suite_id])

    components = relationship("Component", secondary=group_suite_component_association)
    arches = relationship("Arch", secondary=group_suite_arch_association)
    checks = relationship("Check", secondary=group_suite_check_association)

    def get_source_checks(self):
        return [x for x in self.checks
                if x.source == True and x.build == False]

    def get_binary_checks(self):
        return [x for x in self.checks
                if x.binary == True and x.build == False]

    def get_build_checks(self):
        return [x for x in self.checks if x.build == True]

    def __str__(self):
        return "%s/%s" % (self.group, self.suite)

    def __repr__(self):
        return "<GroupSuite: %s/%s (%s)>" % (self.group, self.suite, self.id)


# Many-to-Many relationship
source_arch_association = (
    Table('source_arch_association', Base.metadata,
          Column('source_id', Integer, ForeignKey('sources.id', ondelete="CASCADE"), nullable=False),
          Column('arch_id', Integer, ForeignKey('arches.id', ondelete="RESTRICT"), nullable=False)))


class Source(Base):
    __tablename__ = 'sources'
    _debile_objs = {
        "id": "id",
        "name": "name",
        "version": "version",
        "group": "group.name",
        "suite": "suite.name",
        "component": "component.name",
        "affinity": "affinity.name",
        "uploader": "uploader.__debilize__",
        "uploaded_at": "uploaded_at",
        "directory": "directory",
        "dsc_filename": "dsc_filename",
        "dsc_path": "dsc_path",
        "dsc_url": "dsc_url",
        "group_id": "group.id",
        "maintainers": "maintainers.__list__",
    }

    def debilize(self):
        obj = _debilize(self)
        obj['group_obj'] = _debilize(self.group)
        return obj

    id = Column(Integer, primary_key=True)

    name = Column(String(255), nullable=False)
    version = Column(String(255), nullable=False)

    group_suite_id = Column(Integer, ForeignKey('group_suites.id', ondelete="RESTRICT"), nullable=False)
    group_suite = relationship("GroupSuite", foreign_keys=[group_suite_id])

    @hybrid_property
    def group(self):
        return self.group_suite.group

    @hybrid_property
    def suite(self):
        return self.group_suite.suite

    component_id = Column(Integer, ForeignKey('components.id', ondelete="RESTRICT"), nullable=False)
    component = relationship("Component", foreign_keys=[component_id])

    arches = relationship("Arch", secondary=source_arch_association)

    affinity_id = Column(Integer, ForeignKey('arches.id', ondelete="RESTRICT"), nullable=False)
    affinity = relationship("Arch", foreign_keys=[affinity_id])

    uploader_id = Column(Integer, ForeignKey('people.id', ondelete="RESTRICT"), nullable=False)
    uploader = relationship("Person", foreign_keys=[uploader_id])

    uploaded_at = Column(DateTime, nullable=False)

    directory = Column(String(255), nullable=False)
    dsc_filename = Column(String(255), nullable=False)

    @property
    def dsc_path(self):
        return "{root}/{directory}/{filename}".format(
            root=self.group.repo_path,
            directory=self.directory,
            filename=self.dsc_filename,
        )

    @property
    def dsc_url(self):
        return "{root}/{directory}/{filename}".format(
            root=self.group.repo_url,
            directory=self.directory,
            filename=self.dsc_filename,
        )

    def __str__(self):
        return "%s (%s)" % (self.name, self.version)

    def __repr__(self):
        return "<Source: %s/%s (%s)>" % (self.name, self.version, self.id)


class Maintainer(Base):
    __tablename__ = 'maintainers'
    _debile_objs = {
        "id": "id",
        "name": "name",
        "email": "email",
        "comaintainer": "comaintainer",
        "original_maintainer": "original_maintainer",
    }
    debilize = _debilize

    id = Column(Integer, primary_key=True)

    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    comaintainer = Column(Boolean, nullable=False, default=False)
    original_maintainer = Column(Boolean, nullable=False, default=False)

    source_id = Column(Integer, ForeignKey('sources.id', ondelete="CASCADE"), nullable=False)
    source = relationship("Source", foreign_keys=[source_id],
                          backref=backref('maintainers', passive_deletes=True,
                                          cascade="save-update, merge, delete"))

    def __str__(self):
        return "%s <%s>" % (self.name, self.email)

    def __repr__(self):
        return "<Maintainer: %s (%s)>" % (self.email, self.id)


class Binary(Base):
    __tablename__ = 'binaries'
    _debile_objs = {
        "id": "id",
        "name": "name",
        "version": "version",
        "group": "group.name",
        "suite": "suite.name",
        "component": "component.name",
        "arch": "arch.name",
        "builder": "build_job.builder.__debilize__",
        "uploaded_at": "uploaded_at",
        "group_id": "group.id",
        "source_id": "source.id",
        "debs": "debs.__list__",
    }

    def debilize(self):
        obj = _debilize(self)
        obj['group_obj'] = _debilize(self.group)
        obj['source_obj'] = _debilize(self.source)
        return obj

    id = Column(Integer, primary_key=True)

    @hybrid_property
    def name(self):
        return self.source.name

    @hybrid_property
    def version(self):
        return self.source.version

    arch_id = Column(Integer, ForeignKey('arches.id', ondelete="RESTRICT"), nullable=False)
    arch = relationship("Arch", foreign_keys=[arch_id])

    source_id = Column(Integer, ForeignKey('sources.id', ondelete="CASCADE"), nullable=False)
    source = relationship("Source", foreign_keys=[source_id],
                          backref=backref("binaries", passive_deletes=True,
                                          cascade="save-update, merge, delete"))

    build_job_id = Column(Integer, ForeignKey('jobs.id', ondelete="SET NULL",
                                              name='fk_build_job_id', use_alter=True),
                          nullable=True, default=None)
    build_job = relationship("Job", foreign_keys=[build_job_id],
                             backref=backref("built_binaries", passive_deletes=True))

    @hybrid_property
    def group_suite(self):
        return self.source.group_suite

    @hybrid_property
    def group(self):
        return self.source.group

    @hybrid_property
    def suite(self):
        return self.source.suite

    @hybrid_property
    def component(self):
        return self.source.component

    uploaded_at = Column(DateTime, nullable=False)

    def __str__(self):
        return "%s (%s)" % (self.name, self.version)

    def __repr__(self):
        return "<Binary: %s/%s (%s)>" % (self.name, self.version, self.id)


class Deb(Base):
    __tablename__ = 'debs'
    _debile_objs = {
        "id": "id",
        "directory": "directory",
        "filename": "filename",
        "path": "path",
        "url": "url",
    }
    debilize = _debilize

    id = Column(Integer, primary_key=True)

    directory = Column(String(255), nullable=False)
    filename = Column(String(255), nullable=False)

    binary_id = Column(Integer, ForeignKey('binaries.id', ondelete="CASCADE"), nullable=False)
    binary = relationship("Binary", foreign_keys=[binary_id],
                          backref=backref("debs", passive_deletes=True,
                                          cascade="save-update, merge, delete"))

    @hybrid_property
    def group_suite(self):
        return self.binary.group_suite

    @hybrid_property
    def group(self):
        return self.binary.group

    @hybrid_property
    def suite(self):
        return self.binary.suite

    @hybrid_property
    def component(self):
        return self.binary.component

    @hybrid_property
    def arch(self):
        return self.binary.arch

    @property
    def path(self):
        return "{root}/{directory}/{filename}".format(
            root=self.group.repo_path,
            directory=self.directory,
            filename=self.filename,
        )

    @property
    def url(self):
        return "{root}/{directory}/{filename}".format(
            root=self.group.repo_url,
            directory=self.directory,
            filename=self.filename,
        )


# Many-to-Many relationship
job_dependencies = (
    Table('job_dependencies', Base.metadata,
          Column('blocked_job_id', Integer, ForeignKey('jobs.id', ondelete="CASCADE"), nullable=False),
          Column('blocking_job_id', Integer, ForeignKey('jobs.id', ondelete="CASCADE"), nullable=False)))


class Job(Base):
    __tablename__ = 'jobs'
    _debile_objs = {
        "id": "id",
        "source": "source.__str__",
        "name": "name",
        "check": "check.name",
        "group": "group.name",
        "suite": "suite.name",
        "component": "component.name",
        "arch": "arch.name",
        "builder": "builder.__debilize__",
        "assigned_at": "assigned_at",
        "finished_at": "finished_at",
        "failed": "failed",
        "group_id": "group.id",
        "source_id": "source.id",
        "binary_id": "binary.id",
        "do_indep": "do_indep",
    }

    def debilize(self):
        obj = _debilize(self)
        obj['group_obj'] = _debilize(self.group)
        obj['source_obj'] = _debilize(self.source)
        obj['binary_obj'] = _debilize(self.binary)
        return obj

    id = Column(Integer, primary_key=True)

    @hybrid_property
    def name(self):
        return self.check.name + " [" + self.arch.name + "]"

    # This is a hack for Tanglu, so we can use dose for depwait calculations
    # instead using the as-of-now unimplemented debile depwait support.
    dose_report = Column(String(255), nullable=True, default=None)

    check_id = Column(Integer, ForeignKey('checks.id', ondelete="RESTRICT"), nullable=False)
    check = relationship("Check", foreign_keys=[check_id])

    @hybrid_property
    def group_suite(self):
        return self.source.group_suite

    @hybrid_property
    def group(self):
        return self.source.group

    @hybrid_property
    def suite(self):
        return self.source.suite

    @hybrid_property
    def component(self):
        return self.source.component

    arch_id = Column(Integer, ForeignKey('arches.id', ondelete="RESTRICT"), nullable=False)
    arch = relationship("Arch", foreign_keys=[arch_id])

    source_id = Column(Integer, ForeignKey('sources.id', ondelete="CASCADE"), nullable=False)
    source = relationship("Source", foreign_keys=[source_id],
                          backref=backref("jobs", passive_deletes=True,
                                          cascade="save-update, merge, delete"))

    binary_id = Column(Integer, ForeignKey('binaries.id', ondelete="CASCADE"),
                       nullable=True, default=None)
    binary = relationship("Binary", foreign_keys=[binary_id],
                          backref=backref("jobs", passive_deletes=True,
                                          cascade="save-update, merge, delete"))

    builder_id = Column(Integer, ForeignKey('builders.id', ondelete="RESTRICT"),
                        nullable=True, default=None)
    builder = relationship("Builder", foreign_keys=[builder_id])

    assigned_count = Column(Integer, nullable=False, default=0)
    assigned_at = Column(DateTime, nullable=True, default=None)
    finished_at = Column(DateTime, nullable=True, default=None)
    failed = Column(Boolean, nullable=True, default=None)

    depedencies = relationship(
        "Job", secondary=job_dependencies, passive_deletes=True,
        cascade="save-update, merge, delete",
        backref=backref('blocking', passive_deletes=True,
                        cascade="save-update, merge, delete"),
        primaryjoin=(id == job_dependencies.c.blocking_job_id),
        secondaryjoin=(id == job_dependencies.c.blocked_job_id),
    )

    @property
    def do_indep(self):
        return (self.check.build and
                self.arch == self.source.affinity and
                not any(x.arch.name == "all" for x in self.source.binaries))

    # Called when the .changes for a build job is processed
    def new_binary(self, arch=None):
        if not self.check.build:
            raise ValueError("add_binary() is for build jobs only!")

        arch = arch or self.arch
        if not arch.name in [self.arch.name, "all"]:
            raise ValueError("add_binary() called with invalid arch!")

        binary = Binary(build_job=self, source=self.source, arch=arch,
                        uploaded_at=datetime.utcnow())

        for job in self.source.jobs:
            if (job.check.binary and job.source == self.source and job.arch == arch):
                job.binary = binary

        self.dose_report = None
        for job in list(self.blocking):
            job.depedencies.remove(self)

        return binary

    # Called when a .dud for any job is processed
    def new_result(self, fire, failed):
        result = Result(job=self, uploaded_at=datetime.utcnow())
        result.firehose = fire
        result.failed = failed
        self.failed = failed
        # Only delete the dependency if the job was sucessfull, and
        # not if it is a build job (that is handled by add_binary().
        if not result.failed and not self.check.build:
            for job in list(self.blocking):
                job.depedencies.remove(self)
        return result

    def __str__(self):
        return "%s %s" % (self.source, self.name)

    def __repr__(self):
        return "<Job: %s %s (%s)>" % (self.source, self.name, self.id)


class Result(Base):
    __tablename__ = 'results'
    _debile_objs = {
        "id": "id",
        "job": "job.__str__",
        "group": "group.name",
        "suite": "suite.name",
        "component": "component.name",
        "arch": "arch.name",
        "uploaded_at": "uploaded_at",
        "failed": "failed",
        "directory": "directory",
        "path": "path",
        "url": "url",
        "group_id": "group.id",
        "source_id": "source.id",
        "binary_id": "binary.id",
        "job_id": "job.id",
    }

    def debilize(self):
        obj = _debilize(self)
        obj['group_obj'] = _debilize(self.group)
        obj['source_obj'] = _debilize(self.source)
        obj['binary_obj'] = _debilize(self.binary)
        obj['job_obj'] = _debilize(self.job)
        return obj

    id = Column(Integer, primary_key=True)

    job_id = Column(Integer, ForeignKey('jobs.id', ondelete="CASCADE"), nullable=False)
    job = relationship("Job", foreign_keys=[job_id],
                       backref=backref("results", passive_deletes=True,
                                       cascade="save-update, merge, delete"))

    @hybrid_property
    def source(self):
        return self.job.source

    @hybrid_property
    def binary(self):
        return self.job.binary

    @hybrid_property
    def group_suite(self):
        return self.job.group_suite

    @hybrid_property
    def group(self):
        return self.job.group

    @hybrid_property
    def suite(self):
        return self.job.suite

    @hybrid_property
    def component(self):
        return self.job.component

    @hybrid_property
    def arch(self):
        return self.job.arch

    firehose_id = Column(String, ForeignKey('analysis.id', ondelete="RESTRICT"), nullable=False)
    firehose = relationship(Analysis, single_parent=True, cascade="save-update, merge, delete, delete-orphan")

    uploaded_at = Column(DateTime, nullable=False)
    failed = Column(Boolean, nullable=False)

    @property
    def directory(self):
        return "{source}_{version}/{check}_{arch}/{id}".format(
            source=self.source.name,
            version=self.source.version,
            check=self.job.check.name,
            arch=self.job.arch.name,
            id=self.id
        )

    @property
    def path(self):
        return "{root}/{directory}".format(
            root=self.group.files_path,
            directory=self.directory,
        )

    @property
    def url(self):
        return "{root}/{directory}".format(
            root=self.group.files_url,
            directory=self.directory,
        )


def create_source(dsc, group_suite, component, uploader,
                  affinity_preference, valid_affinities):
    source = Source(
        name=dsc['Source'],
        version=dsc['Version'],
        group_suite=group_suite,
        component=component,
        uploader=uploader,
        uploaded_at=datetime.utcnow()
    )

    source.arches = get_source_arches(dsc['Architecture'].split(),
                                      group_suite.arches)

    # Sources building arch-dependent packages should build any
    # arch-independent packages on an architecture it is building
    # arch-dependent packages on.
    source.affinity = get_preferred_affinity(
        affinity_preference,
        valid_affinities.split(),
        [x for x in source.arches if x.name not in ["source", "all"]] or
        [x for x in source.group_suite.arches if x.name not in ["source", "all"]]
    )

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


def create_jobs(source, dose_report=None):
    """
    Create jobs for Source `source`, using the an architecture matching
    `valid_affinities` for any arch "all" jobs.
    """

    arch_source = None
    arch_all = None
    for arch in source.group_suite.arches:
        if arch.name == "source":
            arch_source = arch
        if arch.name == "all":
            arch_all = arch

    if not arch_source or not arch_all:
        raise ValueError("Missing arch:all or arch:source in the group_suite.")

    builds = {}
    binaries = {}

    for binary in source.binaries:
        binaries[binary.arch] = binary

    for check in source.group_suite.get_source_checks():
        j = Job(check=check, arch=arch_source,
                source=source, binary=None)
        source.jobs.append(j)

    arch_indep = None
    if arch_all in source.arches and arch_all not in binaries:
        # We need to build arch:all packages
        if source.affinity in source.arches and source.affinity not in binaries:
            # We can build them together with the arch:affinity packages
            arch_indep = source.affinity
        else:
            # We need to build them separately
            arch_indep = arch_all

    for check in source.group_suite.get_build_checks():
        for arch in source.arches:
            if arch == arch_all and arch_indep != arch_all:
                continue

            if arch not in binaries:
                j = Job(check=check, arch=arch,
                        source=source, binary=None,
                        dose_report=dose_report)
                builds[arch] = j
                source.jobs.append(j)

    if arch_indep and arch_indep in builds:
        for arch, job in builds.iteritems():
            if arch != arch_indep:
                job.depedencies.append(builds[arch_indep])

    for check in source.group_suite.get_binary_checks():
        for arch in source.arches:
            deps = []
            if arch in builds:
                deps.append(builds[arch])
            if arch_indep and arch_indep in builds and arch != arch_indep:
                deps.append(builds[arch_indep])

            binary = binaries.get(arch, None)

            j = Job(check=check, arch=arch,
                    source=source, binary=binary)
            source.jobs.append(j)

            for dep in deps:
                j.depedencies.append(dep)
