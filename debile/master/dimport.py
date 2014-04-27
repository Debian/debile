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
from sqlalchemy.sql import exists

from debile.master.utils import session
from debile.master.orm import (Person, Builder, Suite, Component, Arch, Check,
                               Group, GroupSuite, Base)

DEADBEEF = "0000000000000000DEADBEEF0000000000000000"


def main(args, config):
    obj = yaml.safe_load(open(args.file, 'r'))

    users = obj.pop("Users", [])
    builders = obj.pop("Builders", [])
    suites = obj.pop("Suites", [])
    components = obj.pop("Components", [])
    arches = obj.pop("Arches", [])
    checks = obj.pop("Checks", [])
    groups = obj.pop("Groups", [])

    with session() as s:
        Base.metadata.create_all(s.bind)

        for user in users:
            s.add(Person(**user))

        for builder in builders:
            who = s.query(Person).filter_by(email=builder['maintainer']).one()
            builder['maintainer'] = who
            builder['last_ping'] = datetime.utcnow()
            s.add(Builder(**builder))

        for suite in suites:
            s.add(Suite(**suite))

        for component in components:
            s.add(Component(**component))

        for arch in ["source", "all"]:
            s.add(Arch(name=arch))

        for arch in arches:
            s.add(Arch(name=arch['name']))

        for check in checks:
            s.add(Check(**check))

        for group in groups:
            suites = group.pop('suites')

            who = s.query(Person).filter_by(email=group['maintainer']).one()
            group['maintainer'] = who
            group = Group(**group)
            s.add(group)

            for suite in suites:
                gs = GroupSuite(group=group, suite=s.query(Suite).filter_by(
                    name=suite['suite']).one())

                for component in suite.pop('components'):
                    component = s.query(Component).filter_by(
                        name=component
                    ).one()
                    gs.components.append(component)

                for arch in ["source", "all"] + suite.pop('arches'):
                    arch = s.query(Arch).filter_by(name=arch).one()
                    gs.arches.append(arch)

                for check in suite.pop('checks'):
                    check = s.query(Check).filter_by(name=check).one()
                    gs.checks.append(check)

                s.add(gs)

        sane = True
        for key in obj:
            print "Unknown key '%s' in yaml file '%s'" % (key, args.file)
            sane = False

        if not s.query(exists().where(Person.id == Person.id)).scalar():
            print "No users in yaml file '%s'" % args.file
            sane = False
        elif not s.query(exists().where((Person.ssl != None) & (Person.ssl != DEADBEEF))).scalar():
            print "No enabled users in yaml file '%s' (user 'ssl' key missing or dummy 'DEADBEEF' string)" % args.file
            sane = False

        if not s.query(exists().where(GroupSuite.id == GroupSuite.id)).scalar():
            print "No group in yaml file '%s'" % args.file
            sane = False

        for group in s.query(Group).filter(~Group.group_suites.any()):
            print "No suites in group '%s' " % group.name
            sane = False

        for gs in s.query(GroupSuite).filter(~GroupSuite.arches.any((Arch.name != 'source') & (Arch.name != 'all'))):
            print "No arches in group '%s' suite '%s'" % (gs.group.name, gs.suite.name)
            sane = False

        for gs in s.query(GroupSuite).filter(~GroupSuite.components.any()):
            print "No components in group '%s' suite '%s'" % (gs.group.name, gs.suite.name)
            sane = False

        for gs in s.query(GroupSuite).filter(~GroupSuite.checks.any()):
            print "No checks in group '%s' suite '%s'" % (gs.group.name, gs.suite.name)
            sane = False

        if not sane and not args.force:
            raise Exception("Sanity checks failed, use --force to override")
