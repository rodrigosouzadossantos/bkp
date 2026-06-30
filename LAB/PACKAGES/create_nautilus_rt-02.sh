#!/usr/bin/env bash
set -e

PKG="nautilus_rt"

echo "🌊 Creating Nautilus‑RT (PECI‑RT) — Jules Verne"

CORE="${PKG}/core"

mkdir -p "$CORE"

# ===============================
# nemo.py — Gatekeeper
# ===============================
cat > "${CORE}/nemo.py" << 'EOF'
"""
Captain Nemo — Gatekeeper
Inspired by *Twenty Thousand Leagues Under the Sea*
by Jules Verne.
"""
import importlib.abc
import sys

class Nemo(importlib.abc.MetaPathFinder):
  def __init__(self, vessel):
    self.vessel = vessel

  def find_spec(self, fullname, path, target=None):
    if fullname == self.vessel:
      return None

    if not fullname.startswith(self.vessel + "."):
      return None

    try:
      importer = sys._getframe(1).f_globals.get("__name__", "")
    except Exception:
      importer = ""

    if importer.startswith(self.vessel):
      return None

    raise ImportError(
      f"CAPTAIN NEMO DENIES ACCESS\n"
      f"External import of '{fullname}' is forbidden"
    )
EOF

# ===============================
# sea_law.py — Contract
# ===============================
cat > "${CORE}/sea_law.py" << 'EOF'
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
EOF

# ===============================
# deck.py — Public API
# ===============================
cat > "${CORE}/deck.py" << 'EOF'
def depth():
  return "20,000 leagues under the sea"
EOF

# ===============================
# engine.py — RT Executor
# ===============================
cat > "${CORE}/engine.py" << 'EOF'
import socket
import os
import struct
import time

SOCKET_PATH = "/tmp/nautilus_rt.sock"
IDLE_TIMEOUT_SEC = 30

def systemd_notify(msg: str):
  sock_path = os.environ.get("NOTIFY_SOCKET")
  if not sock_path:
    return
  addr = sock_path
  if addr[0] == "@":
    addr = "\0" + addr[1:]
  s = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
  s.connect(addr)
  s.sendall(msg.encode())
  s.close()

# Cleanup old socket
if os.path.exists(SOCKET_PATH):
  os.remove(SOCKET_PATH)

sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
sock.bind(SOCKET_PATH)
sock.listen(1)
sock.settimeout(IDLE_TIMEOUT_SEC)

systemd_notify("READY=1")
last_watchdog = time.monotonic()

print("Engine ready, waiting for Helm...")

try:
  conn, _ = sock.accept()
except socket.timeout:
  print("No connection, shutting down")
  raise SystemExit(0)

conn.settimeout(1)
last_activity = time.monotonic()

while True:
  # Send watchdog ping
  now = time.monotonic()
  if now - last_watchdog >= 5:
    systemd_notify("WATCHDOG=1")
    last_watchdog = now

  try:
    data = conn.recv(4)
    if not data:
      break

    last_activity = now
    x = struct.unpack("i", data)[0]
    conn.sendall(struct.pack("i", x * 2))

  except socket.timeout:
    if now - last_activity > IDLE_TIMEOUT_SEC:
      print("Idle timeout, exiting")
      break

conn.close()
sock.close()
print("Engine stopped")
EOF

# ===============================
# helm.py — RT Helm
# ===============================
cat > "${CORE}/helm.py" << 'EOF'
"""
Helm — Real-Time Flow Control
Auto-reconnect enabled
Inspired by Jules Verne.
"""
import socket
import struct
import time

class RTHelm:
  def __init__(self, socket_path="/tmp/nautilus_rt.sock", retry_sec=1):
    self.socket_path = socket_path
    self.retry_sec = retry_sec
    self.sock = None
    self._connect()

  def _connect(self):
    while True:
      try:
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(self.socket_path)
        return
      except OSError:
        time.sleep(self.retry_sec)

  def call(self, x: int) -> int:
    try:
      self.sock.sendall(struct.pack("i", x))
      return struct.unpack("i", self.sock.recv(4))[0]
    except OSError:
      # Engine restarted — reconnect
      self._connect()
      self.sock.sendall(struct.pack("i", x))
      return struct.unpack("i", self.sock.recv(4))[0]
EOF

# ===============================
# __init__.py — Nautilus‑RT Deck
# ===============================
cat > "$PKG/__init__.py" << 'EOF'
"""
Nautilus‑RT — PECI‑RT Reference Implementation
Inspired by *Twenty Thousand Leagues Under the Sea*
by Jules Verne.
"""
import sys
from .core.nemo import Nemo
from .core.sea_law import validate
from .core.deck import depth
from .core.helm import RTHelm

__all__ = (
  "depth",
  "RTHelm",
)

nemo = Nemo(__name__)
if not any(isinstance(x, Nemo) for x in sys.meta_path):
  sys.meta_path.insert(0, nemo)

validate(globals())
EOF

echo "✅ Nautilus‑RT created with canonical naming"
echo "📦 Files:"
find "$PKG" -type f | sed "s/^/ - /"
