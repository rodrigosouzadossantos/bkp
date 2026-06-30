_ALLOWED_KEYS = frozenset({
  "containment_status",
  "call_ghostbusters",
})

def validate_keys(hq_globals: dict) -> None:
  current = frozenset(hq_globals.get("__all__", ()))
  if current != _ALLOWED_KEYS:
    raise RuntimeError(
      "VINZ CLORTHO DENIES ACCESS!\n"
      f"Expected keys: {_ALLOWED_KEYS}\n"
      f"Found keys:    {current}"
    )
