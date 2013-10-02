dist_stanza = """Origin: {origin}
Label: {label}
Suite: {suite}
Codename: {codename}
Version: {version}
Architectures: {arches}
Components: {components}
Description: {descr}
SignWith: {key}
Contents: . .gz .bz2
Log: {log}
"""

incoming_stanza = """Name: default
IncomingDir: incoming
TempDir: tmp
Allow: {allow}
Cleanup: on_deny on_error
"""

uploaders_stanza = """allow * by unsigned
"""

DIST = {
    "origin": "Paul Tagliamonte",
    "label": "Debile auto-managed repo",
    "arches": "i386 amd64 armhf source",
    "components": "main",
    "log": "debile.log",
}


class Repo(object):

    @staticmethod
    def create(self):
        pass
