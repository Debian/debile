from debian.deb822 import _gpg_multivalued

# Copy of debian.deb822.Dsc with Package-List: support added.
class Dsc2(_gpg_multivalued):
    _multivalued_fields = {
        "package-list": [ "name", "type", "section", "priority"],
        "files": [ "md5sum", "size", "name" ],
        "checksums-sha1": ["sha1", "size", "name"],
        "checksums-sha256": ["sha256", "size", "name"],
    }
