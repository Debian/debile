# -*- coding: utf-8 -*-

from debian import deb822
from debile.utils import run_command


class Dud(object):
    def __init__(self, filename):
        pass

    def add_file(self, fp):
        pass

    def validate_signature(self):
        pass

    def validate_hashes(self):
        pass

    def validate(self):
        pass

    def get_files(self):
        pass
