from debile.utils import run_command


class Repo(object):

    def __init__(self, root):
        self.root = root

    def add_changes(self, changes):
        dist = changes['distribution']
        self.include(dist, changes.get_changes_file())

    def _exec(self, *args):
        cmd = ["reprepro", "-Vb", self.root,] + list(args)
        return run_command(cmd)

    def include(self, distribution, changes):
        return self._exec("include", distribution, changes)

    def includedeb(self, distribution, deb):
        raise NotImplemented()

    def includeudeb(self, distribution, udeb):
        raise NotImplemented()

    def includedsc(self, distributions, dsc):
        raise NotImplemented()

    def list(self, distribution, name):
        raise NotImplemented()

    def clearvanished(self):
        raise NotImplemented()
