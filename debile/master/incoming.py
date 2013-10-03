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

import os
import re
import fnmatch
import datetime as dt
from debian import deb822

from sqlalchemy.orm.exc import NoResultFound

from debile.master.utils import session
from debile.master.orm import Person, Builder, Source, Group, Suite, Maintainer
from debile.utils.changes import parse_changes_file, ChangesFileException


def process_directory(path):
    abspath = os.path.abspath(path)
    for fp in os.listdir(abspath):
        path = os.path.join(abspath, fp)
        for glob, handler in DELEGATE.items():
            if fnmatch.fnmatch(path, glob):
                handler(path)
                break


def process_changes(path):
    changes = parse_changes_file(path)
    try:
        changes.validate()
    except ChangesFileException as e:
        return reject_changes(changes, "invalid-upload")

    key = changes.validate_signature()

    if changes.is_source_only_upload():
        try:
            with session() as s:
                who = s.query(Person).filter_by(key=key).one()
        except NoResultFound:
            return reject_changes(changes, "invalid-user")

        return accept_source_changes(changes, who)

    if changes.is_binary_only_upload():
        try:
            with session() as s:
                builder = s.query(Builder).filter_by(key=key).one()
        except NoResultFound:
            return reject_changes(changes, "invalid-builder")

        return accept_binary_changes(changes, builder)

    raise Exception

def process_dud(path):
    pass


def reject_dud():
    pass


def accept_dud():
    pass


def reject_changes(changes, tag):
    print "REJECT: {source} because {tag}".format(
        tag=tag, source=changes.get_package_name())

    for fp in [changes.get_filename()] + changes.get_files():
        os.unlink(fp)
    # Note this in the log.


def accept_source_changes(changes, user):

    gid = changes.get('X-Lucy-Group', None)
    sid = changes['Distribution']

    MAINTAINER = re.compile("(?P<name>.*) \<(?P<email>.*)\>")

    with session() as s:
        group = s.query(Group).filter_by(name=gid).one()
        suite = s.query(Suite).filter_by(name=sid).one()

        source = Source(
            uploader=user.id,
            name=changes['Source'],
            version=changes['Version'],
            group=group.id,
            suite=suite.id,
            uploaded_at=dt.datetime.utcnow(),
            updated_at=dt.datetime.utcnow()
        )

        s.add(source)

        s.add(Maintainer(
            comaintainer=False,
            **MAINTAINER.match(changes['Maintainer']).groupdict()
        ))

        dsc = changes.get_dsc_obj()

        whos = (x.strip() for x in
                dsc.get("Uploaders", "").split(",") if x != "")

        for who in whos:
            s.add(Maintainer(
                comaintainer=True,
                **MAINTAINER.match(who).groupdict()
            ))

        # OK. We have a changes in order. Let's roll.
        repo = group.get_repo()
        repo.add_changes(changes)


def accept_binary_changes(changes, builder):
    pass


DELEGATE = {
    "*.changes": process_changes,
    "*.dud": process_dud,
}
