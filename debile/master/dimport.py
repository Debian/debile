import yaml
import datetime as dt


from debile.master.utils import session
from debile.master.orm import People, Builders
from sqlalchemy.orm.exc import NoResultFound


def import_from_yaml(whence):
    return import_dict(yaml.safe_load(open(whence, 'r')))


def import_dict(obj):
    maintainer = obj.pop("Maintainer")
    users = obj.pop("Users")
    builders = obj.pop("Builders")
    if obj != {}:
        for key in obj:
            print "Igorning key %s" % (key)

    with session() as s:
        for user in users:
            existing = None
            try:
                existing = s.query(People).filter_by(
                    username=user['username']
                ).one()
            except NoResultFound:
                pass

            p = People(**user)

            if existing:
                p.id = existing.id
                s.merge(p)
            else:
                s.add(p)

    with session() as s:
        for builder in builders:
            username = builder.pop('maintainer')
            who = s.query(People).filter_by(username=username).one()
            builder['maintainer'] = who.id
            builder['last_ping'] = dt.datetime.utcnow()
            s.add(Builders(**builder))
