#!/usr/bin/env bash
set -e

PKG="nautilus"

echo "🌊 Creating the Nautilus secure package (in honor of Jules Verne)..."

mkdir -p "$PKG"

# ----------------------------
# nemo.py — Captain Nemo (Gatekeeper)
# ----------------------------
cat > "$PKG/nemo.py" << 'EOF'
"""
Captain Nemo — Master of the Nautilus

Inspired by *Twenty Thousand Leagues Under the Sea*
by Jules Verne.
"""
import importlib.abc

class Nemo(importlib.abc.MetaPathFinder):
  def __init__(self, vessel: str):
    self.vessel = vessel

  def find_spec(self, fullname, path, target=None):
    if fullname == self.vessel:
      return None

    if fullname.startswith(self.vessel + "."):
      raise ImportError(
        f"CAPTAIN NEMO DENIES ACCESS!\n"
        f"Direct access to '{fullname}' is forbidden.\n"
        f"Enter only through '{self.vessel}'."
      )

    return None
EOF

# ----------------------------
# sea_truth.py — The Immutable Ocean Law
# ----------------------------
cat > "$PKG/sea_truth.py" << 'EOF'
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
EOF

# ----------------------------
# hull.py — Internal Compartments
# ----------------------------
cat > "$PKG/hull.py" << 'EOF'
"""
The Hull — Internal Compartments

Inspired by *Twenty Thousand Leagues Under the Sea*
by Jules Verne.
"""

def depth():
  return "20,000 leagues beneath the surface."

def hail_nautilus():
  return "The sea is everything. It covers seven-tenths of the terrestrial globe."
EOF

# ----------------------------
# __init__.py — The Deck of the Nautilus
# ----------------------------
cat > "$PKG/__init__.py" << 'EOF'
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
EOF

# ----------------------------
# abyss.py — Isolated Subprocess (The Deep)
# ----------------------------
cat > "$PKG/abyss.py" << 'EOF'
"""
The Abyss — Isolated Execution

Inspired by *Twenty Thousand Leagues Under the Sea*
by Jules Verne.
"""
import sys
import json

def command(msg):
  if msg["op"] == "pressure":
    return "Pressure stable at extreme depth."
  if msg["op"] == "scan":
    return f"Scanning abyssal zone: {msg.get('zone', 'unknown')}."
  raise ValueError("Unknown command")

for line in sys.stdin:
  req = json.loads(line)
  try:
    res = command(req)
    print(json.dumps({"ok": True, "result": res}), flush=True)
  except Exception as e:
    print(json.dumps({"ok": False, "error": str(e)}), flush=True)
EOF

# ----------------------------
# airlock.py — IPC Channel
# ----------------------------
cat > "$PKG/airlock.py" << 'EOF'
"""
The Airlock — IPC Channel

Inspired by *Twenty Thousand Leagues Under the Sea*
by Jules Verne.
"""
import subprocess
import json
import os
import sys

class Airlock:
  def __init__(self):
    worker = os.path.join(os.path.dirname(__file__), "abyss.py")
    self.proc = subprocess.Popen(
      [sys.executable, "-u", worker],
      stdin=subprocess.PIPE,
      stdout=subprocess.PIPE,
      text=True
    )

  def transmit(self, op, **kwargs):
    msg = json.dumps({"op": op, **kwargs})
    self.proc.stdin.write(msg + "\n")
    self.proc.stdin.flush()
    response = json.loads(self.proc.stdout.readline())
    if not response["ok"]:
      raise RuntimeError(response["error"])
    return response["result"]

  def seal(self):
    self.proc.terminate()
EOF

echo "✅ Package '$PKG' created successfully!"
echo
echo "📦 Structure:"
find "$PKG" -type f | sed "s|^|  - |"
echo
echo "📜 Inspired by *Twenty Thousand Leagues Under the Sea* — Jules Verne (1870)"
