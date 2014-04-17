from debile.master.orm import Group
from debile.master.utils import init_master

config = init_master()
g = Group(name="foo")


def test_repo_info():
    c = config['repo']
    config['repo'] = {
        "repo_path": "/srv/debile/pool/{name}",
        "repo_url": "http://localhost/debile/pool/{name}",
        "files_path": "/srv/debile/files/{name}",
        "files_url": "http://localhost/debile/files/{name}",
    }
    assert g.get_repo_info() == {
        "repo_path": "/srv/debile/pool/foo",
        "repo_url": "http://localhost/debile/pool/foo",
        "files_path": "/srv/debile/files/foo",
        "files_url": "http://localhost/debile/files/foo",
    }
    config['repo'] = c


def fnord(group, conf):
    return {"foo": "bar"}


def test_repo_info():
    c = config['repo']
    config['repo'] = {
        "custom_resolver": "%s.fnord" % (__name__)
    }
    assert g.get_repo_info() == {"foo": "bar"}
    config['repo'] = c


def test_repo_props():
    config['repo']
    config['repo'] = {
        "repo_path": "/srv/debile/pool/{name}",
        "repo_url": "http://localhost/debile/pool/{name}",
        "files_path": "/srv/debile/files/{name}",
        "files_url": "http://localhost/debile/files/{name}",
    }

    assert g.repo_path == "/srv/debile/pool/foo"
    assert g.repo_url == "http://localhost/debile/pool/foo"
    assert g.files_path == "/srv/debile/files/foo"
    assert g.files_url == "http://localhost/debile/files/foo"

    config['repo'] = c
