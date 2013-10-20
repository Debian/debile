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

import yaml
import datetime as dt


from debile.master.utils import session
from debile.master.orm import (Person, Builder, Group, Suite,
                               GroupArch, GroupSuite, Check, Arch)
from sqlalchemy.orm.exc import NoResultFound


def import_from_yaml(whence):
    return import_dict(yaml.safe_load(open(whence, 'r')))


def import_dict(obj):
    maintainer = obj.pop("Maintainer")
    users = obj.pop("Users")
    builders = obj.pop("Builders")
    suites = obj.pop("Suites")
    groups = obj.pop("Groups")
    checks = obj.pop("Checks")
    arches = obj.pop("Arches")

    if obj != {}:
        for key in obj:
            print "Igorning key %s" % (key)

    with session() as s:
        for user in users:
            existing = None
            try:
                existing = s.query(Person).filter_by(
                    username=user['username']
                ).one()
            except NoResultFound:
                pass

            p = Person(**user)

            if existing:
                p.id = existing.id
                s.merge(p)
            else:
                s.add(p)

        for builder in builders:
            username = builder.pop('maintainer')
            who = s.query(Person).filter_by(username=username).one()
            builder['maintainer'] = who
            builder['last_ping'] = dt.datetime.utcnow()
            s.add(Builder(**builder))

        for suite in suites:
            s.add(Suite(**suite))

        for arch in arches:
            s.add(Arch(name=arch['name']))

        for group in groups:
            arches = group.pop('arches')
            suites = group.pop('suites')

            who = s.query(Person).filter_by(username=group['maintainer']).one()
            group['maintainer'] = who
            group = Group(**group)
            s.add(group)

            for arch in arches:
                arch = s.query(Arch).filter_by(name=arch).one()
                ga = GroupArch(group=group, arch=arch)
                s.add(ga)

            for suite in suites:
                suite = s.query(Suite).filter_by(name=suite).one()
                ga = GroupSuite(group=group, suite=suite)
                s.add(ga)

        for check in checks:
            group = s.query(Group).filter_by(name=check['group']).one()
            check['group'] = group
            s.add(Check(**check))
