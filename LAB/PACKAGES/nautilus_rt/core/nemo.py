"""
Captain Nemo — Import Gatekeeper (Hardened)
Inspired by Jules Verne.
"""
import importlib.abc
import sys

class Nemo(importlib.abc.MetaPathFinder):
  def __init__(self, vessel: str):
    self.vessel = vessel

  def find_spec(self, fullname, path, target=None):
    # Allow root package
    if fullname == self.vessel:
      return None

    # Only guard our own namespace
    if not fullname.startswith(self.vessel + "."):
      return None

    # Identify importer
    try:
      frame = sys._getframe(1)
      importer = frame.f_globals.get("__name__", "")
    except Exception:
      importer = ""

    # ✅ Allow ONLY internal imports (same package)
    if importer == self.vessel or importer.startswith(self.vessel + "."):
      return None

    # ❌ Block EVERYTHING else (including subpackages)
    raise ImportError(
      "CAPTAIN NEMO DENIES ACCESS\n"
      f"External import of internal module '{fullname}' is forbidden"
    )
