"""
The White Whale — The Immutable Truth

Inspired by *Moby-Dick* by Herman Melville.
"""

_THE_TRUTH = frozenset({
  "status",
  "hail_pequod",
})

def verify_truth(deck_globals: dict) -> None:
  current = frozenset(deck_globals.get("__all__", ()))
  if current != _THE_TRUTH:
    raise RuntimeError(
      "THE WHITE WHALE HAS BEEN DEFIED!\n"
      f"Expected truth: {_THE_TRUTH}\n"
      f"Found lies:     {current}"
    )
