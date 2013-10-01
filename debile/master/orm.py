from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import (Column, Integer, String, DateTime, ForeignKey, Boolean,
                        UniqueConstraint)

Base = declarative_base()


class People(Base):
    __tablename__ = 'people'
    __table_args__ = (UniqueConstraint('username'),)

    id = Column(Integer, primary_key=True)
    username = Column(String(255))  # Unique

    name = Column(String(255))
    key = Column(String(255))
    email = Column(String(255))
    password = Column(String(255))  # Weak password. Not actually critical.



class Builders(Base):
    __tablename__ = 'builders'

    id = Column(Integer, primary_key=True)
    maintainer = Column(Integer, ForeignKey('people.id'))

    name = Column(String(255))
    key = Column(String(255))
    password = Column(String(255))  # Weak password. Not actually critical.
    last_ping = Column(DateTime, nullable=False)



class Arch(Base):
    __tablename__ = 'arches'

    id = Column(Integer, primary_key=True)

    name = Column(String(255))
    maintainer = Column(Integer, ForeignKey('people.id'))


class Groups(Base):
    __tablename__ = 'groups'

    id = Column(Integer, primary_key=True)

    name = Column(String(255))
    maintainer = Column(Integer, ForeignKey('people.id'))


class Suite(Base):
    __tablename__ = 'suites'
    id = Column(Integer, primary_key=True)
    name = Column(String(255))


class Sources(Base):
    __tablename__ = 'sources'

    id = Column(Integer, primary_key=True)

    uploader = Column(Integer, ForeignKey('people.id'))
    name = Column(String(255))
    version = Column(String(255))
    group = Column(Integer, ForeignKey('groups.id'))
    suite = Column(Integer, ForeignKey('suites.id'))
    uploaded_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)


class Maintainers(Base):
    __tablename__ = 'maintainers'

    id = Column(Integer, primary_key=True)

    name = Column(String(255))
    email = Column(String(255))
    suite = Column(Integer, ForeignKey('sources.id'))
    comaintainer = Column(Boolean)


class Binaries(Base):
    __tablename__ = 'binaries'

    id = Column(Integer, primary_key=True)

    source = Column(Integer, ForeignKey('sources.id'))
    builder = Column(Integer, ForeignKey('builders.id'))
    name = Column(String(255))
    version = Column(String(255))
    suite = Column(Integer, ForeignKey('suites.id'))
    group = Column(Integer, ForeignKey('groups.id'))
    arch = Column(Integer, ForeignKey('arches.id'))
    uploaded_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)


class Checks(Base):
    __tablename__ = 'checks'

    id = Column(Integer, primary_key=True)

    name = Column(String(255))
    group = Column(Integer, ForeignKey('groups.id'))
    source = Column(Boolean)
    binary = Column(Boolean, nullable=True)


class Jobs(Base):
    __tablename__ = 'jobs'

    id = Column(Integer, primary_key=True)

    name = Column(String(255))
    score = Column(Integer)
    builder = Column(Integer, ForeignKey('builders.id'))
    source = Column(Integer, ForeignKey('sources.id'))
    binary = Column(Integer, ForeignKey('binaries.id'), nullable=True)
    check = Column(Integer, ForeignKey('checks.id'))
    arch = Column(Integer, ForeignKey('arches.id'))


class Results(Base):
    __tablename__ = 'results'

    id = Column(Integer, primary_key=True)

    name = Column(String(255))
    failed = Column(Boolean)
    source = Column(Integer, ForeignKey('sources.id'))
    binary = Column(Integer, ForeignKey('binaries.id'), nullable=True)
    # firehose = Column(Integer, ForeignKey('firehose.id'))


def init():
    from debile.master.core import engine
    Base.metadata.create_all(engine)
