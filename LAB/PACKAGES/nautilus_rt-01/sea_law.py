"""
The Law of the Sea (RT Contract)
Jules Verne.
"""
_ALLOWED = frozenset({'depth', 'rt_call', 'RTController'})

def validate(api):
  #if frozenset(api.get("__all__",())) != _ALLOWED:
  #  raise RuntimeError("SEA LAW VIOLATED")
  current = frozenset(api.get("__all__", ()))
  if current != _ALLOWED:
    raise RuntimeError(
      "SEA LAW VIOLATED\n"
      f"Expected: {_ALLOWED}\n"
      f"Found:    {current}"
    )

