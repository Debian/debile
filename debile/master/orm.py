from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import (Column, Integer, String, DateTime, ForeignKey, Boolean,
                        UniqueConstraint)

Base = declarative_base()


class Person(Base):
    __tablename__ = 'people'
    __table_args__ = (UniqueConstraint('username'),)

    id = Column(Integer, primary_key=True)
    username = Column(String(255))  # Unique

    name = Column(String(255))
    key = Column(String(255))
    email = Column(String(255))
    password = Column(String(255))  # Weak password. Not actually critical.



class Builder(Base):
    __tablename__ = 'builders'

    id = Column(Integer, primary_key=True)
    maintainer = Column(Integer, ForeignKey('people.id'))

    name = Column(String(255))
    key = Column(String(255))
    password = Column(String(255))  # Weak password. Not actually critical.
    last_ping = Column(DateTime, nullable=False)



class Group(Base):
    __tablename__ = 'groups'
    __table_args__ = (UniqueConstraint('name'),)

    id = Column(Integer, primary_key=True)

    name = Column(String(255))
    maintainer = Column(Integer, ForeignKey('people.id'))


class Suite(Base):
    __tablename__ = 'suites'
    __table_args__ = (UniqueConstraint('name'),)

    id = Column(Integer, primary_key=True)
    name = Column(String(255))


class Source(Base):
    __tablename__ = 'sources'

    id = Column(Integer, primary_key=True)

    uploader = Column(Integer, ForeignKey('people.id'))
    name = Column(String(255))
    version = Column(String(255))
    group = Column(Integer, ForeignKey('groups.id'))
    suite = Column(Integer, ForeignKey('suites.id'))
    uploaded_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)


class Maintainer(Base):
    __tablename__ = 'maintainers'

    id = Column(Integer, primary_key=True)

    name = Column(String(255))
    email = Column(String(255))
    source = Column(Integer, ForeignKey('sources.id'))
    comaintainer = Column(Boolean)


class Binary(Base):
    __tablename__ = 'binaries'

    id = Column(Integer, primary_key=True)

    source = Column(Integer, ForeignKey('sources.id'))
    builder = Column(Integer, ForeignKey('builders.id'))
    name = Column(String(255))
    version = Column(String(255))
    suite = Column(Integer, ForeignKey('suites.id'))
    group = Column(Integer, ForeignKey('groups.id'))
    arch = Column(String(255))
    uploaded_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)


class Check(Base):
    __tablename__ = 'checks'

    id = Column(Integer, primary_key=True)

    built_at = Column(DateTime, nullable=True)

    name = Column(String(255))
    source = Column(Boolean)
    binary = Column(Boolean)


class Job(Base):
    __tablename__ = 'jobs'

    id = Column(Integer, primary_key=True)

    assigned_at = Column(DateTime, nullable=False)
    finished_at = Column(DateTime, nullable=True)

    name = Column(String(255))
    score = Column(Integer)
    builder = Column(Integer, ForeignKey('builders.id'))
    source = Column(Integer, ForeignKey('sources.id'))
    binary = Column(Integer, ForeignKey('binaries.id'), nullable=True)
    check = Column(Integer, ForeignKey('checks.id'))
    arch = Column(String(255))


class Result(Base):
    __tablename__ = 'results'

    id = Column(Integer, primary_key=True)

    failed = Column(Boolean)
    source = Column(Integer, ForeignKey('sources.id'))
    binary = Column(Integer, ForeignKey('binaries.id'), nullable=True)
    check = Column(Integer, ForeignKey('checks.id'))

    # firehose = Column(Integer, ForeignKey('firehose.id'))


def init():
    from debile.master.core import engine
    Base.metadata.create_all(engine)
