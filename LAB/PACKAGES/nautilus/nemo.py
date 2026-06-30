"""
Captain Nemo — Master of the Nautilus

Inspired by *Twenty Thousand Leagues Under the Sea*
by Jules Verne.
"""
import importlib.abc

class Nemo(importlib.abc.MetaPathFinder):
  def __init__(self, vessel: str):
    self.vessel = vessel

  def find_spec(self, fullname, path, target=None):
    if fullname == self.vessel:
      return None

    if fullname.startswith(self.vessel + "."):
      raise ImportError(
        f"CAPTAIN NEMO DENIES ACCESS!\n"
        f"Direct access to '{fullname}' is forbidden.\n"
        f"Enter only through '{self.vessel}'."
      )

    return None
