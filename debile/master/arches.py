# Copyright (c) 2012-2013 Paul Tagliamonte <paultag@debian.org>
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

from debile.utils import run_command
import debile.master.core
import functools


def arch_matches(arch, alias):
    """
    Check if given arch `arch` matches the other arch `alias`. This is most
    useful for the complex any-* rules.
    """

    if arch == alias or alias == "any":
        return True

    if alias == 'linux-any':
        # This is a generalization for Debian. Please update if this is
        # wrong for other places. A hit to shell out is *COSTLY*; like; orders
        # of magnatude more costly.
        if '-' in alias:
            return False
        return True

    if alias == 'kfreebsd-any':
        return 'kfreebsd-' in arch

    if alias == 'hurd-any':
        return 'hurd-' in arch

    if not "-" in arch and not "-" in alias:
        return False

    # This is a fucking disaster for perf. Do what we can to not get here.
    out, err, ret = run_command([
        "/usr/bin/dpkg-architecture",
        "-a%s" % (arch),
        "-i%s" % (alias)
    ])
    return ret == 0


def get_affine_arch(arches):
    affinities = debile.master.core.config.get("affinity", [])

    if affinities == []:
        raise ValueError("No set affinity. This is a problem")

    for affinity in affinities:
        for arch in arches:
            if arch_matches(arch.name, affinity):
                return arch

    raise ValueError("No valid affinity for series: '%s' from '%s'" % (
        ", ".join([x.name for x in arches]),
        ", ".join(affinities),
    ))


def afilter(arches, arch):
    return [
        x for x in arches if arch_matches(x.name, arch)
    ]


def get_concrete_arches(arches, valid_arches):
    """
    Given a list of strings representing data from the .dsc `arches`,
    and the `valid_arches` of the suite, return the concrete arches objects
    which may be used.
    """

    expansions = {"any": valid_arches,}
    valid_wildcards = ["linux-any", "kfreebsd-any", "hurd-any"]
    af = functools.partial(afilter, valid_arches)

    for wildcard in valid_wildcards:
        expansions[wildcard] = af(wildcard)

    va = {a.name: a for a in valid_arches}
    ret = set()

    for arch in arches:
        if 'any' not in arch and arch not in va:
            continue

        if 'any' in arch and arch not in expansions:
            raise NotImplementedError("I don't know about %s. Fix debile." % (
                arch
            ))

        for x in expansions.get(arch, [va.get(arch)]):
            if x is None:
                raise ValueError("God what the hell is going on")
                # This shouldn't happen, like, ever. Literally ever.

            ret.add(x)
    return ret
