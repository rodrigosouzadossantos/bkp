import importlib.abc

class Zuul(importlib.abc.MetaPathFinder):
  def __init__(self, hq: str):
    self.hq = hq

  def find_spec(self, fullname, path, target=None):
    if fullname == self.hq:
      return None

    if fullname.startswith(self.hq + "."):
      raise ImportError(
        f"ZUUL SAYS NO!\n"
        f"Direct access to '{fullname}' is forbidden.\n"
        f"Enter only through '{self.hq}'."
      )

    return None
