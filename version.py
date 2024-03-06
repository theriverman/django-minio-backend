# -*- coding: utf-8 -*-
# Author: Douglas Creager <dcreager@dcreager.net>
# Modifier: Kristof Daja <kristof@daja.hu>
# This file is placed into the public domain.

# Calculates the current version number.  If possible, this is the
# output of “git describe”, modified to conform to the versioning
# scheme that setuptools uses.  If “git describe” returns an error
# (most likely because we're in an unpacked copy of a release tarball,
# rather than in a git working copy), then we fall back on reading the
# contents of the RELEASE-VERSION file.
#
# To use this script, simply import it your setup.py file, and use the
# results of get_git_version() as your package version:
#
# from version import *
#
# setup(
#     version=get_git_version(),
#     .
#     .
#     .
# )
#
#
# This will automatically update the RELEASE-VERSION file, if
# necessary.  Note that the RELEASE-VERSION file should *not* be
# checked into git; please add it to your top-level .gitignore file.
#
# You'll probably want to distribute the RELEASE-VERSION file in your
# sdist tarballs; to do this, just create a MANIFEST.in file that
# contains the following line:
#
#   include RELEASE-VERSION
#
# Change History:
#    2020-12-12 - Updated for Python 3. Changed git describe --abbrev=7 to git describe --tags
#

__all__ = ["get_git_version"]

from subprocess import Popen, PIPE


def call_git_describe():
    # noinspection PyBroadException
    try:
        p = Popen(["git", "describe", "--tags"], stdout=PIPE, stderr=PIPE)
        p.stderr.close()
        line = p.stdout.readlines()[0]
        return line.strip().decode("utf-8")

    except Exception:
        return None


def is_dirty():
    # noinspection PyBroadException
    try:
        p = Popen(
            ["git", "diff-index", "--name-only", "HEAD"], stdout=PIPE, stderr=PIPE
        )
        p.stderr.close()
        lines = p.stdout.readlines()
        return len(lines) > 0
    except Exception:
        return False


def read_release_version():
    # noinspection PyBroadException
    try:
        f = open("RELEASE-VERSION", "r")

        try:
            version = f.readlines()[0]
            return version.strip()

        finally:
            f.close()

    except Exception:
        return None


def write_release_version(version):
    f = open("RELEASE-VERSION", "w")
    f.write("%s\n" % version)
    f.close()


def get_git_version():
    # Read in the version that's currently in RELEASE-VERSION.
    release_version = read_release_version()

    # First try to get the current version using “git describe”.
    version = call_git_describe()
    if is_dirty():
        version += "-dirty"

    # If that doesn't work, fall back on the value that's in
    # RELEASE-VERSION.
    if version is None:
        version = release_version

    # If we still don't have anything, that's an error.
    if version is None:
        raise ValueError("Cannot find the version number!")

    # If the current version is different from what's in the
    # RELEASE-VERSION file, update the file to be current.
    if version != release_version:
        write_release_version(version)

    # Finally, return the current version.
    return version


if __name__ == "__main__":
    print(get_git_version())
