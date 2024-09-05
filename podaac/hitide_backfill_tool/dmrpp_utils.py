"""Static functions to read dmrpp files, parse version from file, and determine dmrpp state."""

import xml.etree.ElementTree as element_tree
from enum import Enum


class DmrppState(Enum):
    """Represents a granule's dmrpp file state/status."""

    OLDER_VERSION = 1       # Will update
    MISSING_VERSION = 2     # Will update
    MATCHED_VERSION = 3     # Don't update
    NEWER_VERSION = 4       # Don't update


def parse_version(version_string):
    """Parses input version_string string and returns it as a tuple in format (X, X, X, X)."""

    try:
        version, build = version_string.split("-")
        version = [int(v) for v in version.split(".")]
        build = int(build)
        return tuple(version + [build])
    except Exception as exc:
        raise Exception(f"Could not parse version string {version_string}") from exc


def get_dmrpp_version(s3, s3_dmrpp_url):
    """Returns the version string from the dmrpp file.  If file or version not found,
    returns "" (empty string)."""
    # pylint: disable=C0103

    version = ""

    try:
        xml = s3.read_file_from_s3(s3_dmrpp_url)
        root = element_tree.fromstring(xml)

        for attr_name, attr_value in root.items():
            if attr_name.endswith("version"):
                version = attr_value
                break
    except Exception:                                       # pylint: disable=W0703
        pass
    return version
