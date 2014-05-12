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

from firewoes.lib.hash import idify, uniquify
from sqlalchemy.orm.exc import NoResultFound

from debile.master.utils import emit
from debile.master.dud import Dud, DudFileException
from debile.master.filerepo import FileRepo, FilesAlreadyRegistered
from debile.master.orm import Builder, Job


def process_dud(config, session, path):
    dud = Dud(path)
    jid = dud.get("X-Debile-Job", None)
    if jid is None:
        return reject_dud(session, dud, "missing-dud-job")

    try:
        dud.validate()
    except DudFileException:
        return reject_dud(session, dud, "invalid-dud-upload")

    try:
        fingerprint = dud.validate_signature(config['keyrings']['pgp'])
    except DudFileException:
        return reject_dud(session, dud, "invalid-signature")

    try:
        builder = session.query(Builder).filter_by(pgp=fingerprint).one()
    except NoResultFound:
        return reject_dud(session, dud, "invalid-dud-builder")

    job = session.query(Job).get(jid)
    if job is None:
        return reject_dud(session, dud, "invalid-dud-job")

    if dud.get("X-Debile-Failed", None) is None:
        return reject_dud(session, dud, "no-failure-notice")

    if job.builder != builder:
        return reject_dud(session, dud, "invalid-dud-uploader")

    accept_dud(config, session, dud, builder)


def reject_dud(session, dud, tag):
    session.rollback()

    print "REJECT: {source} because {tag}".format(
        tag=tag, source=dud['Source'])

    e = None
    try:
        dud.validate()
    except DudFileException as e:
        print e

    emit('reject', 'result', {
        "tag": tag,
        "source": dud['Source'],
    })

    for fp in [dud.get_filename()] + dud.get_files():
        os.unlink(fp)
    # Note this in the log.


def accept_dud(config, session, dud, builder):
    fire = dud.get_firehose()
    failed = True if dud.get('X-Debile-Failed', None) == "Yes" else False

    job = session.query(Job).get(dud['X-Debile-Job'])

    fire, _ = idify(fire)
    fire = uniquify(session, fire)

    result = job.new_result(fire, failed)
    session.add(result)

    try:
        repo = FileRepo()
        repo.add_dud(result.path, dud, config['filerepo_chmod_mode'])
    except FilesAlreadyRegistered:
        return reject_dud(session, dud, "dud-files-already-registered")

    emit('receive', 'result', result.debilize())

    # OK. It's safely in the database and repo. Let's cleanup.
    for fp in [dud.get_filename()] + dud.get_files():
        os.unlink(fp)
