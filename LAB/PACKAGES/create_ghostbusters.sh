#!/usr/bin/env bash
set -e

PKG="ghostbusters"

echo "👻 Creating Ghostbusters secure package..."

mkdir -p "$PKG"

# ----------------------------
# zuul.py — Gatekeeper
# ----------------------------
cat > "$PKG/zuul.py" << 'EOF'
import importlib.abc

class Zuul(importlib.abc.MetaPathFinder):
  def __init__(self, hq: str):
    self.hq = hq

  def find_spec(self, fullname, path, target=None):
    if fullname == self.hq:
      return None

    if fullname.startswith(self.hq + "."):
      raise ImportError(
        f"ZUUL SAYS NO!\n"
        f"Direct access to '{fullname}' is forbidden.\n"
        f"Enter only through '{self.hq}'."
      )

    return None
EOF

# ----------------------------
# vinz_clortho.py — Keymaster
# ----------------------------
cat > "$PKG/vinz_clortho.py" << 'EOF'
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
EOF

# ----------------------------
# containment.py — Internal
# ----------------------------
cat > "$PKG/containment.py" << 'EOF'
def containment_status():
  return "All ghosts contained."

def call_ghostbusters():
  return "Who ya gonna call?"
EOF

# ----------------------------
# __init__.py — HQ Entrance
# ----------------------------
cat > "$PKG/__init__.py" << 'EOF'
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
EOF

# ----------------------------
# ghost_dimension.py — Subprocess
# ----------------------------
cat > "$PKG/ghost_dimension.py" << 'EOF'
import sys
import json

def handle(msg):
  if msg["op"] == "status":
    return "Ghost Dimension stable."
  if msg["op"] == "trap":
    return f"Ghost '{msg['name']}' trapped."
  raise ValueError("Unknown operation")

for line in sys.stdin:
  cmd = json.loads(line)
  try:
    result = handle(cmd)
    print(json.dumps({"ok": True, "result": result}), flush=True)
  except Exception as e:
    print(json.dumps({"ok": False, "error": str(e)}), flush=True)
EOF

# ----------------------------
# proton_stream.py — IPC Client
# ----------------------------
cat > "$PKG/proton_stream.py" << 'EOF'
import subprocess
import json
import os
import sys

class ProtonStream:
  def __init__(self):
    worker = os.path.join(os.path.dirname(__file__), "ghost_dimension.py")
    self.proc = subprocess.Popen(
      [sys.executable, "-u", worker],
      stdin=subprocess.PIPE,
      stdout=subprocess.PIPE,
      text=True
    )

  def cross_streams(self, op, **kwargs):
    msg = json.dumps({"op": op, **kwargs})
    self.proc.stdin.write(msg + "\n")
    self.proc.stdin.flush()
    response = json.loads(self.proc.stdout.readline())
    if not response["ok"]:
      raise RuntimeError(response["error"])
    return response["result"]

  def shutdown(self):
    self.proc.terminate()
EOF

echo "✅ Package '$PKG' created successfully!"
echo
echo "📦 Structure:"
find "$PKG" -type f | sed "s|^|  - |"
