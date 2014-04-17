from debile.master.arches import get_preferred_affinity, get_source_arches

class FnordArch(object):
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return "<Fnord: %s>" % (self.name)


valid_arches = [
    FnordArch("amd64"),
    FnordArch("sparc"),
    FnordArch("ppc64"),
    FnordArch("kfreebsd-amd64"),
    FnordArch("kfreebsd-i386"),
    FnordArch("hurd-amd64"),
    FnordArch("hurd-i386"),
    FnordArch("armhf"),
    FnordArch("armel"),
    FnordArch("mips"),
]


def test_affinity_basic():
    arch = get_preferred_affinity(
        ['amd64', 'sparc', 'armhf'],
        ["amd64", "sparc", "ppc64"],
        valid_arches
    )
    assert arch.name == 'amd64'


def test_affinity_out_of_order():
    arch = get_preferred_affinity(
        ['amd64', 'sparc', 'armhf'],
        ["ppc64", "sparc", "amd64"],
        valid_arches
    )
    assert arch.name == 'amd64'


def test_affinity_secondary():
    arch = get_preferred_affinity(
        ['amd64', 'sparc', 'armhf'],
        ["ppc64", "sparc"],
        valid_arches
    )
    assert arch.name == 'sparc'

def test_affinity_any():
    arch = get_preferred_affinity(
        ['amd64', 'sparc', 'armhf'],
        ["any"],
        valid_arches
    )
    assert arch.name == 'amd64'

def test_affinity_linux_any():
    arch = get_preferred_affinity(
        ['amd64', 'sparc', 'armhf'],
        ["linux-any"],
        valid_arches
    )
    assert arch.name == 'amd64'

def test_affinity_any_arm():
    arch = get_preferred_affinity(
        ['amd64', 'sparc', 'armhf'],
        ["any-arm"],
        valid_arches
    )
    assert arch.name == 'armhf'

def test_affinity_fail():
    try:
        arch = get_preferred_affinity(
            ['amd64', 'sparc', 'armhf'],
            ["ppc64", "armel"],
            valid_arches
        )
        assert False == True, "Didn't bomb out as expected."
    except ValueError:
        pass


def test_any_arches():
    assert valid_arches == get_source_arches(['any'], valid_arches)


def test_simple_arches():
    assert set(['amd64', 'armhf']) == set([
        x.name for x in get_source_arches(['amd64', 'armhf'], valid_arches)
    ])


def test_kfreebsd_arches():
    assert set([
        'kfreebsd-i386', 'kfreebsd-amd64', 'armhf'
    ]) == set([
        x.name for x in get_source_arches([
            'kfreebsd-i386', 'kfreebsd-amd64', 'armhf'
        ], valid_arches)
    ])

def test_hurd_arches():
    assert set([
        'hurd-i386', 'hurd-amd64', 'armel'
    ]) == set([
        x.name for x in get_source_arches([
            'hurd-i386', 'hurd-amd64', 'armel'
        ], valid_arches)
    ])
