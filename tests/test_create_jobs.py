# Copyright (c) 2014 Clement Schreiner <clement@mux.me>
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

from debile.master.orm import (Arch, Check, Component, Group,
                               GroupSuite,
                               Person, Source, Suite,
                               create_jobs,
                               metadata)
#from debile.master.utils import session

from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

import datetime
import unittest




class TestCreateJobs(unittest.TestCase):
    """ Test case for debile.master.orm.create_jobs """

    def setUp(self):
        engine = create_engine(
            'postgresql://' # fill URI here
        )

        Session = sessionmaker(bind=engine)
        self.session = Session()

        metadata.drop_all(bind=engine)
        metadata.create_all(bind=engine)


        user = Person(name='Foo Bar', email='foo@example.org')
        self.session.add(user)

        arch_all = Arch(name='all')
        valid_arches = [Arch(name='amd64'), Arch(name='source'), arch_all]

        component = Component(name='main')

        group = Group(name='default', maintainer=user)
        suite = Suite(name='unstable')

        self.groupsuite = GroupSuite(group=group, suite=suite,
                                     arches=valid_arches)
        self.groupsuite.checks.append(Check(name='lintian', source=True,
                                            binary=False, build=False))
        self.session.add(self.groupsuite)

        self.source = Source(name='foo', version='0.1',
                             group_suite=self.groupsuite, component=component,
                             arches=[arch_all], affinity=arch_all,
                             uploader=user,
                             uploaded_at=datetime.datetime.utcnow(),
                             directory='/tmp',
                             dsc_filename='/tmp/foo.dsc')
        self.session.add(self.source)
        self.session.commit()

    def test_create_job(self):
        for check in self.source.group_suite.checks:
            print check, check.source

        create_jobs(self.source)
        print self.source.jobs
        self.session.commit()

if __name__ == "__main__":
    unittest.main()
