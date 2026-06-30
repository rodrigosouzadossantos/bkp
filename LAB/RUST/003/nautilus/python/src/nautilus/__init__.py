from . import _core
from ._core import *

# Automatically set __all__ to include everything exported by Rust
__all__ = [
  name for name in dir(_core)
    if not name.startswith("_")
] # pyright: ignore [reportUnsupportedDunderAll]

# Clean up the reference to the binary module itself
del _core

def hello() -> str:
    return hello_from_bin()
