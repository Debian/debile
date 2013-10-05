from debile.master.server import user_method, builder_method, NAMESPACE
from debile.master.orm import Job, Arch, Check
import datetime as dt


class DebileMasterInterface(object):
    """
    This is the exposed interface for the builders. Code enhacing the server
    should likely go here, unless you know what you're doing.
    """

    # Simple stuff.

    @builder_method
    def builder_whoami(self):
        """
        ID check
        """
        return NAMESPACE.machine.name

    @user_method
    def user_whoami(self):
        """
        ID check
        """
        return NAMESPACE.user.name

    # The following trio of methods handle the job control.

    @builder_method
    def get_next_job(self, suites, arches, capabilities):
        job = NAMESPACE.session.query(Job).filter(
            Arch.name.in_(arches)
        ).filter(
            Check.name.in_(capabilities)
        ).first()
        #
        if job is None:
            return None
        #job.assigned_at = dt.datetime.utcnow()
        return job.debilize()

    @builder_method
    def close_job(self, job_id, failed):
        job = NAMESPACE.session.query(Job).get(job_id)
        job.finished_at = dt.datetime.utcnow()
        NAMESPACE.session.add(job)
        NAMESPACE.session.commit()
        return True

    @builder_method
    def forfeit_job(self, job_id):
        job = NAMESPACE.session.query(Job).get(job_id)
        job.assigned_at = None
        NAMESPACE.session.add(job)
        NAMESPACE.session.commit()
        return True

    # Useful methods below.

    def job_count(self):
        """
        Work out the job count.
        """
        return NAMESPACE.session.query(Job).count()
