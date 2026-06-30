"""
Captain Ahab — The Gatekeeper

Inspired by *Moby-Dick* by Herman Melville.
"""
import importlib.abc

class Ahab(importlib.abc.MetaPathFinder):
  def __init__(self, ship: str):
    self.ship = ship

  def find_spec(self, fullname, path, target=None):
    if fullname == self.ship:
      return None

    if fullname.startswith(self.ship + "."):
      raise ImportError(
        f"CAPTAIN AHAB DENIES PASSAGE!\n"
        f"Direct access to '{fullname}' is forbidden.\n"
        f"Board only through '{self.ship}'."
      )

    return None
