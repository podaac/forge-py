"""Utility functions for working with files"""

from os import getcwd
from os.path import expanduser, expandvars, normpath, join, isabs, dirname
import yaml


def make_absolute(path, relative_to=None):
    """Convert path to absolute path.

    Does nothing if path is already absolute path.
    Expands environment variables and ~.
    If path is relative, will be resolved relative to the relative_to
    param (if provided) or the cwd."""
    expanded_path = expandvars(expanduser(path))
    if isabs(expanded_path):
        return expanded_path
    cwd = dirname(relative_to) if relative_to else getcwd()
    return normpath(join(cwd, path))


def load_yaml_file(path, relative_to=None):
    """Create dict from yaml file at location path"""
    abs_path = make_absolute(path, relative_to)
    with open(abs_path, encoding='utf-8') as stream:
        return yaml.safe_load(stream)
