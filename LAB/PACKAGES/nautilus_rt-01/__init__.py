"""
Nautilus‑RT — PECI‑RT Reference Implementation
Inspired by Jules Verne.
"""
import sys
from .nemo import Nemo
from .sea_law import validate
from .hull import depth, rt_call
from .rt_controller import RTController


__all__ = (
  "depth",
  "rt_call",
  'RTController',
)


n = Nemo( __name__ )
if not any(
  isinstance( x,Nemo )
    for x in sys.meta_path
) :
  sys.meta_path.insert( 0,n )

validate( globals( ) )
