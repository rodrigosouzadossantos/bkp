"""
Sea Law — Immutable Contract
Inspired by Jules Verne.
"""

_ALLOWED = frozenset({
  "depth",
  "RTHelm",
})

def validate(api):
  current = frozenset(api.get("__all__", ()))
  if current != _ALLOWED:
    raise RuntimeError(
      "SEA LAW VIOLATED\n"
      f"Expected: {_ALLOWED}\n"
      f"Found:    {current}"
    )
