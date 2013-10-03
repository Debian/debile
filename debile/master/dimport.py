import yaml
import datetime as dt


from debile.master.utils import session
from debile.master.orm import Person, Builder, Group, Suite
from sqlalchemy.orm.exc import NoResultFound


def import_from_yaml(whence):
    return import_dict(yaml.safe_load(open(whence, 'r')))


def import_dict(obj):
    maintainer = obj.pop("Maintainer")
    users = obj.pop("Users")
    builders = obj.pop("Builders")
    suites = obj.pop("Suites")

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
            builder['maintainer'] = who.id
            builder['last_ping'] = dt.datetime.utcnow()
            s.add(Builder(**builder))

        for suite in suites:
            s.add(Suite(**suite))

        default_group = Group(name=None, maintainer=None)
        s.add(default_group)
