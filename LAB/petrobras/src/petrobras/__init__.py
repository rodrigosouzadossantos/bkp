#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# vim: set tabstop=2 shiftwidth=2 softtabstop=2 expandtab:

import os
import sys

from importlib.metadata import metadata, version, PackageNotFoundError
from packaging.specifiers import SpecifierSet
from packaging.version import Version

from .core.import_guard import ImportGuard

import logging

from .core.observer import Observer
from .core.observer_logger import ObserverLogger
from .core.observer_ui import ObserverUI
from .core.output_router import OutputRouter

from .lib.config.logging import configure_observer_logging

_observer = Observer("petrobras")
_observer.install()

_router = OutputRouter()

def _emit_output(text: str) -> None:
  _router.emit(text)

_observer.subscribe(_router.observe)




#ui = ObserverUI()
#_observer.subscribe(ui.handle_event)

#_output_sink = None

#def _emit_output(text: str) -> None:
#  """
#  Internal output dispatcher.
#  """
#  if _output_sink is not None:
#    _output_sink(text)
#
#_output_sink = ui.emit_output



class StdoutProxy:
  """
  Safe stdout proxy.

  - Captures print() output
  - Never raises
  - Does NOT touch stderr
  """

  def __init__(self, sink) -> None:
    self._sink = sink

  def write(self, text: str) -> None:
    try:
      if text:
        self._sink(text)
        sys.__stdout__.flush()
    except Exception:
      # Never propagate errors
      pass

  def flush(self) -> None:
    pass

#sys.stdout = StdoutProxy(ui._write_output)

_logger = ObserverLogger(
    logger=configure_observer_logging( level_console=logging.WARN )
)

_observer.subscribe(_logger.handle_event)

# =============================================================================
# Double-check the Python version against the requirements specified in the
# package metadata. This is a safeguard to ensure that the package is being
# used with a compatible Python version, even if the package manager (like
# pip) did not enforce it during installation.
#
# This is particularly important for packages that may be installed in
# environments where multiple Python versions are present, or where the
# package manager's version checking might not be reliable.
#
# By performing this check at runtime, the package can provide a clear error
# message to the user if they are using an incompatible Python version, which
# can help prevent runtime errors and improve the overall user experience.
# =============================================================================

__appname__ : str = metadata( 'petrobras' ) \
      .get( 'name', 'Petrobras' )
try :
  requires_python : str = metadata( 'Petrobras' ) \
      .get( 'requires-python', '0.0' )

except PackageNotFoundError as e :
  raise ImportError( f'Package {__appname__} not found' ) from e

spec = SpecifierSet(requires_python)

pyver = Version(
    '.'.join( str(part)
    for part in sys.version_info[:3]
  )
)

if pyver not in spec:
  raise ImportError(
    f'{__appname__} requires Python {requires_python},'
    f' but {pyver} is running'
  )

__version__ : str = version( 'Petrobras' )


# =============================================================================
# Configuration of the module's public API and behavior when imported.
#
# This section defines the public interface of the module, including any
# special attributes or behaviors that should be exposed to users when they
# import the module.
#
# This may include defining special methods like __getattr__ to control
# attribute access, or modifying the module's class to make it callable.
#
# The goal is to provide a clear and intuitive API for users of the module,
# while also ensuring that the module behaves in a consistent and expected
# manner when imported.
#
# This section is crucial for defining how users will interact with the
# module and for ensuring that the module's functionality is accessible
# in a way that makes sense given the design of the package.
#
# It also helps to establish the identity of the module and to provide
# a clear interface for users, which can improve the usability and
# maintainability of the package as a whole.
#
# By carefully configuring the module's public API and behavior, we can
# create a package that is both powerful and easy to use, while also
# providing a clear and consistent experience for users when they import
# and interact with the module.
#
# This is an important aspect of package design and can have a significant
# impact on the overall success and adoption of the package within the
# Petrobras specialist workforce.
# =============================================================================

# __getattr__'s module (PEP 562)
def __getattr__( attr : str ) -> str :

  if attr == 'name' :
    return __appname__

  if attr in _PUBLIC_NAMES :
    return globals()[attr]

  raise ImportError(
    f"cannot import name '{attr}' from {__name__} "
    f"(allowed: {', '.join(__all__) or 'none'})"
  )

def __dir__( ) :
  return sorted( _PUBLIC_NAMES )


## Turns the module into a callable
#from .core.petrobras import Petrobras
#class _CallableModule( types.ModuleType ) :
#  def __call__( self, *args, **kwargs ) -> Petrobras :
#    return Petrobras( *args, **kwargs )
#
## Change module class on runtime to make it callable
#sys.modules[__name__].__class__ = _CallableModule


# =============================================================================
# Only explicitly listed names in __all__ will be importable from the module.
# =============================================================================

def _seal_namespace():
  allowed = set(_PUBLIC_NAMES)
  allowed.update({
      "__all__",
      "__name__",
      "__file__",
      "__package__",
      "__spec__",
      "__loader__",
      "__builtins__",
  })

  for name in list(globals()):

    if name.startswith("__"):
      continue

    if name not in allowed:
      del globals()[name]


def run( name ):
  _emit_output(f"Hello, {name}!")

__all__ : list[ str ] = [
  'run',
]

_PUBLIC_NAMES = set(__all__)

if os.environ.get("DISABLE_IMPORT_GUARD") != "1":
  guard = ImportGuard(
    package=__name__,
    allowed=frozenset(__all__),
  )

  if not any(
    isinstance(f, ImportGuard)
      for f in sys.meta_path
  ):
    sys.meta_path.insert(0, guard)



#_seal_namespace( )
