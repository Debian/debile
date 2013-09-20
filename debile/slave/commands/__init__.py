# Copyright (c) 2012-2013 Paul Tagliamonte <paultag@debian.org>
# Copyright (c) 2013 Leo Cavaille <leo@cavaille.net>
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

import importlib


PLUGINS = {
    "build": "debileslave.commands.build",
    "clanganalyzer": "debileslave.commands.clanganalyzer",

    "pep8": "debileslave.commands.pep8",
    "perlcritic": "debileslave.commands.perlcritic",
    "cppcheck": "debileslave.commands.cppcheck",
    "coccinelle": "debileslave.commands.coccinelle",

    "lintian": "debileslave.commands.lintian",
    "lintian4py": "debileslave.commands.lintian4py",

    "adequate": "debileslave.commands.adequate",
    "piuparts": "debileslave.commands.piuparts",
    "desktop-file-validate": "debileslave.commands.desktop_file_validate",
}


def load_module(what):
    path = PLUGINS[what]
    mod = importlib.import_module(path)
    return (mod.run, mod.get_version)
