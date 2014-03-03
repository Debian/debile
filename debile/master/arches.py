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

from debile.utils.commands import run_command


def arch_matches(arch, alias):
    """
    Check if given arch `arch` matches the other arch `alias`. This is most
    useful for the complex any-* rules.
    """

    if arch == alias:
        return True

    if arch == 'all' or arch == 'source':
        # These pseudo-arches does not match any wildcards or aliases
        return False

    if alias == 'any':
        # The 'any' wildcard matches all *real* architectures
        return True

    if alias == 'linux-any':
        # GNU/Linux arches are named <cpuabi>
        # Other Linux arches are named <libc>-linux-<cpuabi>
        return not '-' in arch or 'linux' in arch.split('-')

    if alias.endswith('-any'):
        # Non-Linux GNU/<os> arches are named <os>-<cpuabi>
        # Other non-Linux arches are named <libc>-<os>-<cpuabi>
        osname, _ = alias.split('-', 1)
        return osname in arch.split('-')

    if not "-" in arch and not "-" in alias:
        return False

    # This is a fucking disaster for perf. Do what we can to not get here.
    out, err, ret = run_command([
        "/usr/bin/dpkg-architecture",
        "-a%s" % (arch),
        "-i%s" % (alias)
    ])
    return ret == 0


def get_preferred_affinity(
    affinity_preference, valid_affinities, valid_arches
):
    """
    Given a list of strings representing the preffered affinities in the
    config, a list of string with valid affinities of the source, and a list
    of valid architectures in the suite, return the arch object to use as
    affinity for arch "all" jobs.
    """

    for affinity in affinity_preference:
        arch = None
        for x in valid_arches:
            if x.name == affinity:
                arch = x
                break
        if arch is None:
            continue
        for alias in valid_affinities:
            if arch_matches(affinity, alias):
                return arch

    raise ValueError(
        "No valid affinity - preferences: '%s'; valid: '%s'; arches %s" % (
            ", ".join(affinity_preference),
            ", ".join(valid_affinities),
            ", ".join([x.name for x in valid_arches]),))


def get_source_arches(dsc_arches, valid_arches):
    """
    Given a list of strings with the Architectures data from the dsc,
    and a list of valid Arch objects from the suite, return the Arch
    objects to add to the Source object.
    """

    ret = []

    for arch in valid_arches:
        for alias in dsc_arches:
            if arch_matches(arch.name, alias):
                ret.append(arch)
                break  # Break inner loop, continue outer loop

    return ret
