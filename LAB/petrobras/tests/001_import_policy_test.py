#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:

import importlib
import pytest


def test_root_import_works():
  import petrobras

  assert callable(petrobras)
  obj = petrobras()
  assert obj.name == "Petrobras"


def test_from_import_allowed():
  from petrobras import Petrobras

  obj = Petrobras()
  assert obj.name == "Petrobras"


def test_import_submodule_denied():
  import petrobras

  with pytest.raises(ModuleNotFoundError):
    __import__("petrobras.lib")


def test_from_import_submodule_denied():
  import petrobras

  with pytest.raises(ImportError):
    from petrobras import lib  # noqa: F401


def test_reload_safe():
  import petrobras

  importlib.reload(petrobras)
  assert callable(petrobras)


def test_single_import_guard_installed():
  import petrobras
  import sys

  guards = [
    f for f in sys.meta_path
    if type(f).__name__ == 'ImportGuard'
  ]
  assert len(guards) == 1
