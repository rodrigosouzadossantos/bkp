"""
Nautilus‑RT — PECI‑RT Reference Implementation
Inspired by *Twenty Thousand Leagues Under the Sea*
by Jules Verne.
"""
import sys
from .core.nemo import Nemo
from .core.sea_law import validate
from .core.deck import depth
from .core.helm import RTHelm

__all__ = (
  "depth",
  "RTHelm",
)

nemo = Nemo(__name__)
if not any(isinstance(x, Nemo) for x in sys.meta_path):
  sys.meta_path.insert(0, nemo)

validate(globals())
