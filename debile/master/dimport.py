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
from datetime import datetime

from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

from debile.master.utils import session
from debile.master.orm import (Person, Builder, Suite, Component, Arch, Check,
                               Group, GroupSuite, Source, Maintainer, Binary)


def import_from_yaml(whence):
    return import_dict(yaml.safe_load(open(whence, 'r')))


def import_dict(obj):
    users = obj.pop("Users", [])
    builders = obj.pop("Builders", [])
    suites = obj.pop("Suites", [])
    components = obj.pop("Components", [])
    arches = obj.pop("Arches", [])
    checks = obj.pop("Checks", [])
    groups = obj.pop("Groups", [])

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
            builder['last_ping'] = datetime.utcnow()
            s.add(Builder(**builder))

        for suite in suites:
            s.add(Suite(**suite))

        for component in components:
            s.add(Component(**component))

        for arch in arches:
            s.add(Arch(name=arch['name']))

        for check in checks:
            s.add(Check(**check))

        for group in groups:
            suites = group.pop('suites')

            who = s.query(Person).filter_by(username=group['maintainer']).one()
            group['maintainer'] = who
            group = Group(**group)
            s.add(group)

            for suite in suites:
                gs = GroupSuite(
                    group=group,
                    suite=s.query(Suite).filter_by(name=suite['suite']).one(),
                    affinity_preference=suite.pop('affinity_preference')
                )

                for component in suite.pop('components'):
                    component = s.query(Component).filter_by(name=component).one()
                    gs.components.append(component)
                for arch in suite.pop('arches'):
                    arch = s.query(Arch).filter_by(name=arch).one()
                    gs.arches.append(arch)
                for check in suite.pop('checks'):
                    check = s.query(Check).filter_by(name=check).one()
                    gs.checks.append(check)

                s.add(gs)
