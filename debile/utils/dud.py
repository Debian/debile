# -*- coding: utf-8 -*-

from debile.utils import run_command
from debile import __version__
from debian import deb822

from email.Utils import formatdate
import hashlib
import os


class DudFileException(Exception):
    pass


class Dud(object):

    defaults = {
        "Format": "1.0",
        "Generator": "debile.utils.dud/%s" % (__version__)
    }
    required = ["Format", "Created-By", "Date", "Files",
                "Source", "Version", "Architecture"]

    def __init__(self):
        self._files = []
        self._data = deb822.Deb822()
        self._data['Date'] = formatdate()
        for k, v in self.defaults.items():
            self._data[k] = v

    def __setitem__(self, entry, value):
        self._data[entry] = value

    def __getitem__(self, entry):
        return self._data[entry]

    def add_file(self, fp):
        self._files.append(fp)

    def get_file_digest(self, type_):
        digest = ""
        for fp in self.files():
            statinfo = os.stat(fp)
            size = statinfo.st_size

            m = hashlib.new(type_)
            with open(fp, 'r') as fd:
                for buf in fd.read(128):
                    m.update(buf)
            if type_ != 'md5':
                digest += "\n {hash} {size} {path}".format(
                    hash=m.hexdigest(),
                    size=size,
                    path=fp
                )
            else:
                digest += "\n {hash} {size} debile debile {path}".format(
                    hash=m.hexdigest(),
                    size=size,
                    path=fp
                )
        return digest

    def write_dud(self, fp, key=None):
        self._data['Files'] = self.get_file_digest('md5')
        self._data['Checksum-Sha1'] = self.get_file_digest('sha1')
        self._data['Checksum-Sha256'] = self.get_file_digest('sha256')

        for entry in self.required:
            if entry not in self._data:
                raise ValueError("Missing key: %s" % (entry))

        with open(fp, 'w') as fd:
            self._data.dump(fd=fd)

        if key is not None:
            run_command(['gpg', '-u', key, '--clearsign', fp])
            os.unlink(fp)
            os.rename("%s.asc" % (fp), fp)

    def files(self):
        for fp in self._files:
            yield fp


def from_file(fp):
    data = deb822.Deb822(open(fp, 'r'))
