from debile.utils import run_command
import deb822
import StringIO
import requests
import gzip

SOURCE = "dists/{suite}/{section}/source/Sources.gz"


def dget(path):
    out, err, ret = run_command(["dget", "-ux", path])
    if ret != 0:
        print ret, err
        raise Exception("DAMNIT; dget fucked us")


def aget(archive, suite, section, source, version):
    url = "{archive}/{path}".format(
        archive=archive,
        path=SOURCE.format(suite=suite, section=section
    ))

    for entry in deb822.Deb822.iter_paragraphs(gzip.GzipFile(
            fileobj=StringIO.StringIO(requests.get(url).content))):

        path = entry['Directory']

        dsc = None
        for fp in entry['Files'].splitlines():
            if fp.strip() == "":
                continue

            hash_, size, fid = fp.split()
            if fid.endswith(".dsc"):
                dsc = fid

        if entry['Package'] == source and entry['Version'] == version:
            dget("{archive}/{pool}/{dsc}".format(
                archive=archive,
                pool=path,
                dsc=dsc,
            ))
            break
    else:
        print "BALLS."
        raise Exception


def main():
    import sys
    return aget(*sys.argv[1:])
