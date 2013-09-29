from debile.master.orm import Sources
import debile.master.core

from contextlib import contextmanager
from sqlalchemy.orm import Session, sessionmaker


@contextmanager
def session():
    Session = sessionmaker(bind=debile.master.core.engine)
    session_ = Session()

    try:
        yield session_
    except:
        # Don't let it through
        raise
    else:
        session_.commit()
