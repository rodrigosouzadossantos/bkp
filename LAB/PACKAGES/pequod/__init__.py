"""
The Pequod — Public Deck

Inspired by *Moby-Dick* by Herman Melville.
"""
import sys

from .ahab import Ahab
from .white_whale import verify_truth

__all__ = (
  "status",
  "hail_pequod",
)

_ahab = Ahab(__name__)
if not any(isinstance(x, Ahab) for x in sys.meta_path):
  sys.meta_path.insert(0, _ahab)

from .hold import status, hail_pequod

verify_truth(globals())
