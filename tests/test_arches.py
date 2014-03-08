from debile.master.arches import get_concrete_arches, get_affine_arch
import debile.master.core


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
    a = debile.master.core.config['affinity']
    debile.master.core.config['affinity'] = ['amd64', 'sparc', 'armhf']
    arch = get_affine_arch([
        FnordArch("amd64"),
        FnordArch("sparc"),
        FnordArch("ppc64"),
    ])
    assert arch.name == 'amd64'
    debile.master.core.config['affinity'] = a


def test_affinity_out_of_order():
    a = debile.master.core.config['affinity']
    debile.master.core.config['affinity'] = ['amd64', 'sparc', 'armhf']
    arch = get_affine_arch([
        FnordArch("ppc64"),
        FnordArch("sparc"),
        FnordArch("amd64"),
    ])
    assert arch.name == 'amd64'
    debile.master.core.config['affinity'] = a


def test_affinity_secondary():
    a = debile.master.core.config['affinity']
    debile.master.core.config['affinity'] = ['amd64', 'sparc', 'armhf']
    arch = get_affine_arch([
        FnordArch("ppc64"),
        FnordArch("sparc"),
    ])
    assert arch.name == 'sparc'
    debile.master.core.config['affinity'] = a


def test_affinity_fail():
    a = debile.master.core.config['affinity']
    debile.master.core.config['affinity'] = ['amd64', 'sparc', 'armhf']
    try:
        get_affine_arch([
            FnordArch("ppc64"),
            FnordArch("armel"),
        ])
        assert False == True, "Didn't bomb out as expected."
    except ValueError:
        pass

    debile.master.core.config['affinity'] = a


def test_any_arches():
    assert set(valid_arches) == get_concrete_arches(['any'], valid_arches)


def test_simple_arches():
    assert set(['amd64', 'armhf']) == set([
        x.name for x in get_concrete_arches(['amd64', 'armhf'], valid_arches)
    ])


def test_kfreebsd_arches():
    assert set([
        'kfreebsd-i386', 'kfreebsd-amd64', 'armhf'
    ]) == set([
        x.name for x in get_concrete_arches([
            'kfreebsd-i386', 'kfreebsd-amd64', 'armhf'
        ], valid_arches)
    ])

def test_hurd_arches():
    assert set([
        'hurd-i386', 'hurd-amd64', 'armel'
    ]) == set([
        x.name for x in get_concrete_arches([
            'hurd-i386', 'hurd-amd64', 'armel'
        ], valid_arches)
    ])
