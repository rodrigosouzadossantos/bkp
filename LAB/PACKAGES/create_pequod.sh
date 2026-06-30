#!/usr/bin/env bash
set -e

PKG="pequod"

echo "⚓ Creating the Pequod secure package (in honor of Herman Melville)..."

mkdir -p "$PKG"

# ----------------------------
# ahab.py — Captain Ahab
# ----------------------------
cat > "$PKG/ahab.py" << 'EOF'
"""
Captain Ahab — The Gatekeeper

Inspired by *Moby-Dick* by Herman Melville.
"""
import importlib.abc

class Ahab(importlib.abc.MetaPathFinder):
  def __init__(self, ship: str):
    self.ship = ship

  def find_spec(self, fullname, path, target=None):
    if fullname == self.ship:
      return None

    if fullname.startswith(self.ship + "."):
      raise ImportError(
        f"CAPTAIN AHAB DENIES PASSAGE!\n"
        f"Direct access to '{fullname}' is forbidden.\n"
        f"Board only through '{self.ship}'."
      )

    return None
EOF

# ----------------------------
# white_whale.py — The Truth
# ----------------------------
cat > "$PKG/white_whale.py" << 'EOF'
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
EOF

# ----------------------------
# hold.py — Internal Cargo
# ----------------------------
cat > "$PKG/hold.py" << 'EOF'
"""
The Hold — Internal Cargo

Inspired by *Moby-Dick* by Herman Melville.
"""

def status():
  return "The ship holds fast."

def hail_pequod():
  return "From hell's heart I stab at thee!"
EOF

# ----------------------------
# __init__.py — The Deck
# ----------------------------
cat > "$PKG/__init__.py" << 'EOF'
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
EOF

# ----------------------------
# open_sea.py — Subprocess
# ----------------------------
cat > "$PKG/open_sea.py" << 'EOF'
"""
The Open Sea — Isolated Execution

Inspired by *Moby-Dick* by Herman Melville.
"""
import sys
import json

def command(msg):
  if msg["op"] == "weather":
    return "The sea is calm."
  if msg["op"] == "harpoon":
    return f"Harpoon cast at '{msg['target']}'."
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
# harpoon_line.py — IPC
# ----------------------------
cat > "$PKG/harpoon_line.py" << 'EOF'
"""
The Harpoon Line — IPC Channel

Inspired by *Moby-Dick* by Herman Melville.
"""
import subprocess
import json
import os
import sys

class HarpoonLine:
  def __init__(self):
    worker = os.path.join(os.path.dirname(__file__), "open_sea.py")
    self.proc = subprocess.Popen(
      [sys.executable, "-u", worker],
      stdin=subprocess.PIPE,
      stdout=subprocess.PIPE,
      text=True
    )

  def cast(self, op, **kwargs):
    msg = json.dumps({"op": op, **kwargs})
    self.proc.stdin.write(msg + "\n")
    self.proc.stdin.flush()
    response = json.loads(self.proc.stdout.readline())
    if not response["ok"]:
      raise RuntimeError(response["error"])
    return response["result"]

  def strike_colors(self):
    self.proc.terminate()
EOF

echo "✅ Package '$PKG' created successfully!"
echo
echo "📦 Structure:"
find "$PKG" -type f | sed "s|^|  - |"
echo
echo "📜 Inspired by *Moby-Dick* — Herman Melville (1851)"
