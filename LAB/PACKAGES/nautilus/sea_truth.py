"""
The Law of the Sea — Immutable Truth

Inspired by *Twenty Thousand Leagues Under the Sea*
by Jules Verne.
"""

_OCEAN_LAW = frozenset({
  "depth",
  "hail_nautilus",
})

def verify_ocean_law(deck_globals: dict) -> None:
  current = frozenset(deck_globals.get("__all__", ()))
  if current != _OCEAN_LAW:
    raise RuntimeError(
      "THE LAW OF THE SEA HAS BEEN BROKEN!\n"
      f"Expected: {_OCEAN_LAW}\n"
      f"Found:    {current}"
    )
