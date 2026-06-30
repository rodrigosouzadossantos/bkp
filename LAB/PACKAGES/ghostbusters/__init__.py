import sys

from .zuul import Zuul
from .vinz_clortho import validate_keys

__all__ = (
  "containment_status",
  "call_ghostbusters",
)

_zuul = Zuul(__name__)
if not any(isinstance(x, Zuul) for x in sys.meta_path):
  sys.meta_path.insert(0, _zuul)

from .containment import containment_status, call_ghostbusters

validate_keys(globals())
