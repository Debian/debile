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

from debile.utils import run_command
from debile.master.core import config
import fcntl
import os

def import_pgp(keydata):
    """
    keydata should be public key data to be imported to the keyring.
    The return value will be the sha1 fingerprint of the public key added.
    """

    out, err, ret = run_command([
        "gpg", "--batch", "--status-fd", "1"
        "--no-default-keyring", "--keyring", config['keyrings']['pgp'],
        "--import"
    ], input=keydata)

    fingerprint = None
    for line in out.split("\n"):
        data = line.split()
        if data[0] != "[GNUPG:]":
            continue

        if data[1] == "IMPORT_OK":
            fingerprint = data[3]
            break
    else:
        raise ValueError(
            "And nothing of value was lost (gpg failed to import)")

    return fingerprint


def import_ssl(certdata, cn=None, email=None):
    """
    certdata should be pem-formated certificate data to be added to the keyring.
    The return value will be the sha1 fingerprint of the certificate added.
    """

    # Check that this realy is a pem-formated certificate,
    # and get the fingerprint and subject of the certificate
    out, err, ret = run_command([
        "openssl", "x509", "-noout", "-inform", "pem", "-sha1",
        "-fingerprint", "-subject"
    ], input=certdata)

    fingerprint = None
    subject = None
    for line in out.split("\n"):
        data = line.split("=", 2)
        if data[0] == "SHA1 Fingerprint":
            fingerprint = data[1].replace(':','')
        if data[0] == "subject":
            subject = data[1].split('/')

    if fingerprint is None or subject is None:
        raise ValueError("And nothing of value was lost (openssl failed to import)")

    # SSLSocket breaks badly on multiple certifiates with the same subject
    # in the keyring, so ensure that it unique to this slave/user.
    if (cn and not "CN={cn}".format(cn=cn) in subject) or \
       (email and not "emailAddress={email}".format(email=email)):
        raise ValueError("And nothing of value was lost (openssl failed to import)")

    # Add the valid pem-formated certificate to the keyring.
    keyring = open(config['keyrings']['ssl'], 'a')
    fcntl.lockf(keyring, fcntl.LOCK_EX)
    keyring.write(certdata)
    keyring.close()

    return fingerprint
