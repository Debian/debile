from debile.master.server import user_method, builder_method, NAMESPACE
from debile.master.orm import Job



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
        jobs = NAMESPACE.session.query(Job)
        raise NotImplemented

    @builder_method
    def close_job(self, job_id, failed):
        job = NAMESPACE.session.query(Job).get(job_id)
        raise NotImplemented

    @builder_method
    def forfeit_job(self, job_id):
        job = NAMESPACE.session.query(Job).get(job_id)
        raise NotImplemented

    # Useful methods below.

    def job_count(self):
        """
        Work out the job count.
        """
        return NAMESPACE.session.query(Job).count()
