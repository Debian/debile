# Copyright (c) 2012-2013 Paul Tagliamonte <paultag@debian.org>
# Copyright (c) 2014      Jon Severinsson <jon@severinsson.net>
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

from debile.utils.xmlrpc import get_proxy
from debile.utils.core import config
import sys


def _create_slave(name, pgp, ssl):
    """
        Create a slave:
            debile-remote create-slave <name> <pgp-key> <ssl-cert>
    """

    try:
        pgp = open(pgp, 'r').read()
    except IOError as e:
        print("Error whilst opening OpenPGP public key.")
        print("   %s when trying to open %s" % (str(e), pgp))
        raise

    try:
        ssl = open(ssl, 'r').read()
    except IOError as e:
        print("Error whilst opening SSL client certificate.")
        print("   %s when trying to open %s" % (str(e), ssl))
        raise

    proxy = get_proxy(config)
    print(proxy.create_builder(name, pgp, ssl))


def _update_slave_keys(name, pgp, ssl):
    """
        Replace the pgp public key and ssl certificate of a slave:
            debile-remote update-slave-keys <name> <pgp-key> <ssl-cert>
    """

    try:
        pgp = open(pgp, 'r').read()
    except IOError as e:
        print("Error whilst opening OpenPGP public key.")
        print("   %s when trying to open %s" % (str(e), pgp))
        raise

    try:
        ssl = open(ssl, 'r').read()
    except IOError as e:
        print("Error whilst opening SSL client certificate.")
        print("   %s when trying to open %s" % (str(e), ssl))
        raise

    proxy = get_proxy(config)
    print(proxy.update_builder_keys(name, pgp, ssl))


def _disable_slave(name):
    """
        Prevent a slave from being able to authenticate with the master:
            debile-remote disable-slave <name>
    """

    proxy = get_proxy(config)
    print(proxy.disable_builder(name))


def _create_user(name, email, pgp, ssl):
    """
    Create a user:
        debile-remote create-user <name> <email> <pgp-key> <ssl-cert>
    """

    try:
        pgp = open(pgp, 'r').read()
    except IOError as e:
        print("Error whilst opening OpenPGP public key.")
        print("   %s when trying to open %s" % (str(e), pgp))
        raise

    try:
        ssl = open(ssl, 'r').read()
    except IOError as e:
        print("Error whilst opening SSL client certificate.")
        print("   %s when trying to open %s" % (str(e), ssl))
        raise

    proxy = get_proxy(config)
    print(proxy.create_user(name, email, pgp, ssl))


def _update_user_keys(email, pgp, ssl):
    """
        Replace the pgp public key and ssl certificate of a user:
            debile-remote update-user-keys <email> <pgp-key> <ssl-cert>
    """

    try:
        pgp = open(pgp, 'r').read()
    except IOError as e:
        print("Error whilst opening OpenPGP public key.")
        print("   %s when trying to open %s" % (str(e), pgp))
        raise

    try:
        ssl = open(ssl, 'r').read()
    except IOError as e:
        print("Error whilst opening SSL client certificate.")
        print("   %s when trying to open %s" % (str(e), ssl))
        raise

    proxy = get_proxy(config)
    print(proxy.update_user_keys(email, pgp, ssl))


def _disable_user(email):
    """
        Prevent a user from being able to authenticate with the master:
            debile-remote disable-user <email>
    """

    proxy = get_proxy(config)
    print(proxy.disable_user(email))


def _rerun_job(job_id):
    """
    Re-runs a specified job:
        debile-remote rerun-job <job-id>
    """

    proxy = get_proxy(config)
    print(proxy.rerun_job(job_id))


def _rerun_check(check_id):
    """
    Re-runs all jobs for a specified check:
        debile-remote rerun-check <check-id>
    """

    proxy = get_proxy(config)
    print(proxy.rerun_check(check_id))


def _retry_failed():
    """
    Re-tries all failed build jobs:
        debile-remote retry-failed
    """

    proxy = get_proxy(config)
    print(proxy.retry_failed())


def _help():
    print("Commands:")
    for command in COMMANDS:
        print("  %s - %s" % (command, COMMANDS[command].__doc__))


COMMANDS = {
    "create-slave": _create_slave,
    "update-slave-keys": _update_slave_keys,
    "disable-slave": _disable_slave,
    "create-user": _create_user,
    "update-user-keys": _update_user_keys,
    "disable-user": _disable_user,
    "rerun-job": _rerun_job,
    "rerun-check": _rerun_check,
    "retry-failed": _retry_failed,
}


def main():
    args = list(sys.argv[1:])
    command = args.pop(0)
    try:
        run = COMMANDS[command]
    except KeyError:
        return _help()

    return run(*args)
