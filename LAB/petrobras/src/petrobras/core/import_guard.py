#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:

from importlib.abc import MetaPathFinder
from importlib.util import find_spec
from typing import AbstractSet


class ImportGuard( MetaPathFinder ) :
    """
    Import hook that restricts submodule imports for a given package.

    It does NOT read global state.
    All policy is injected explicitly.
    """

    def __init__(self, package : str, allowed : AbstractSet[ str ] ) -> None:
        self._package = package
        self._allowed = allowed

    def find_spec( self, fullname, path, target = None ):
        # Allow the root package itself
        if fullname == self._package:
            return find_spec( fullname )

        # Intercept only our package namespace
        if fullname.startswith( self._package + '.' ) :
            subname = fullname.rpartition( '.' )[2]

            if subname not in self._allowed:
                raise ModuleNotFoundError(
                    f"No module named '{fullname}' "
                    f"(restricted by {self._package})"
                )

            return find_spec(fullname)

        return None
