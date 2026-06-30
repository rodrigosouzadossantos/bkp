"""
The Nautilus — Public Deck

Inspired by *Twenty Thousand Leagues Under the Sea*
by Jules Verne.
"""
import sys

from .nemo import Nemo
from .sea_truth import verify_ocean_law

__all__ = (
  "depth",
  "hail_nautilus",
)

_nemo = Nemo(__name__)
if not any(isinstance(x, Nemo) for x in sys.meta_path):
  sys.meta_path.insert(0, _nemo)

from .hull import depth, hail_nautilus

verify_ocean_law(globals())
