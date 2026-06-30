"""
Captain Nemo — RT Gatekeeper
Inspired by *Twenty Thousand Leagues Under the Sea*
by Jules Verne.
"""
import importlib.abc
import sys

class Nemo(importlib.abc.MetaPathFinder):
  def __init__(self, vessel):
    self.vessel = vessel

  def find_spec(self, fullname, path, target=None):
    # Always allow root package
    if fullname == self.vessel:
      return None

    # Only care about our own namespace
    if not fullname.startswith(self.vessel + "."):
      return None

    # Inspect importer
    try:
      frame = sys._getframe(1)
      importer = frame.f_globals.get("__name__", "")
    except Exception:
      importer = ""

    # ✅ Allow internal imports (package importing itself)
    if importer.startswith(self.vessel):
      return None

    # ❌ Block external access
    raise ImportError(
      f"CAPTAIN NEMO DENIES ACCESS\n"
      f"External import of '{fullname}' is forbidden"
    )
