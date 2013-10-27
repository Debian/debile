from debile.utils import run_command
import deb822
import StringIO
import requests
import gzip
import os

PACKAGES = "dists/{suite}/{section}/binary-{arch}/Packages.gz"


def dget(path):
    out, err, ret = run_command(["dget", "-u", path])
    if ret != 0:
        print ret, err
        raise Exception("DAMNIT; dget fucked us")


def bget(archive, suite, section, arch, source, version):
    # http://debian.lcs.mit.edu/debian/dists/unstable/main/binary-amd64/Packages.gz

    url = "{archive}/{path}".format(
        archive=archive,
        path=PACKAGES.format(
            suite=suite,
            section=section,
            arch=arch,
        )
    )

    packages = []
    for entry in deb822.Deb822.iter_paragraphs(gzip.GzipFile(
            fileobj=StringIO.StringIO(requests.get(url).content))):
        pkg_source = entry.get("Source", entry['Package'])
        if pkg_source == source:
            packages.append(entry)

    if packages == []:
        raise Exception("Damnit, no such packages?")

    ret = []
    for package in packages:
        path = "{archive}/{pool}".format(
            archive=archive,
            pool=package['Filename']
        )
        ret.append(os.path.basename(path))
        dget(path)

    return ret


def main():
    import sys
    return bget(*sys.argv[1:])
