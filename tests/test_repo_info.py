from debile.master.orm import Group
import debile.master.core


g = Group(name="foo")


def test_repo_info():
    c = debile.master.core.config['repo']
    debile.master.core.config['repo'] = {
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
    debile.master.core.config['repo'] = c


def fnord(group):
    return {"foo": "bar"}


def test_repo_info():
    c = debile.master.core.config['repo']
    debile.master.core.config['repo'] = {
        "custom_resolver": "%s.fnord" % (__name__)
    }
    assert g.get_repo_info() == {"foo": "bar"}
    debile.master.core.config['repo'] = c


def test_repo_props():
    c = debile.master.core.config['repo']
    debile.master.core.config['repo'] = {
        "repo_path": "/srv/debile/pool/{name}",
        "repo_url": "http://localhost/debile/pool/{name}",
        "files_path": "/srv/debile/files/{name}",
        "files_url": "http://localhost/debile/files/{name}",
    }

    assert g.repo_path == "/srv/debile/pool/foo"
    assert g.repo_url == "http://localhost/debile/pool/foo"
    assert g.files_path == "/srv/debile/files/foo"
    assert g.files_url == "http://localhost/debile/files/foo"

    debile.master.core.config['repo'] = c
