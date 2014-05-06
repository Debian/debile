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

from debile.utils.config import get_config

from contextlib import contextmanager
from importlib import import_module
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


config = {}
Session = sessionmaker()
fedmsg = None


def _init_config(path):
    config.update(get_config(name="master.yaml", path=path))
    return config


def _init_sqlalchemy(config):
    engine = create_engine(config['database'])
    Session.configure(bind=engine)


def _init_fedmsg(config):
    global fedmsg

    if not 'fedmsg' in config:
        return

    try:
        fedmsg = import_module("fedmsg")
    except:
        return

    fedmsg.init(
        topic_prefix=config['fedmsg'].get("prefix", "org.anized"),
        environment=config['fedmsg'].get("environment", "dev"),
        sign_messages=config['fedmsg'].get("sign", False),
        endpoints=config['fedmsg'].get("endpoints", {}),
    )


def init_master(confpath=None, fedmsg=True):
    c = _init_config(confpath)
    _init_sqlalchemy(c)
    if fedmsg:
        _init_fedmsg(c)
    return c


@contextmanager
def session():
    session_ = Session()
    if session_.get_bind().driver == "sqlite":
        print("Explicitly enabling foreign keys in sqlite")
        session_.execute("PRAGMA foreign_keys=ON")

    try:
        yield session_
        session_.commit()
    except:
        session_.rollback()
        raise
    finally:
        session_.close()


def emit(topic, modname, message):
    # <topic_prefix>.<env>.<modname>.<topic>
    modname = "debile.%s" % (modname)
    if fedmsg:
        return fedmsg.publish(topic=topic, modname=modname, msg=message)
