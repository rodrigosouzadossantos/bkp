#!/usr/bin/env bash
set -e

PKG="nautilus_rt"
echo "🌊 Creating Nautilus‑RT (PECI‑RT) — Jules Verne"

mkdir -p "$PKG"

# ===============================
# nemo.py — Gatekeeper
# ===============================
cat > "$PKG/nemo.py" << 'EOF'
"""
Captain Nemo — RT Gatekeeper
Inspired by *Twenty Thousand Leagues Under the Sea*
by Jules Verne.
"""
import importlib.abc

class Nemo(importlib.abc.MetaPathFinder):
  def __init__(self, vessel):
    self.vessel = vessel

  def find_spec(self, fullname, path, target=None):
    if fullname == self.vessel:
      return None
    if fullname.startswith(self.vessel + "."):
      raise ImportError("CAPTAIN NEMO DENIES ACCESS")
    return None
EOF

# ===============================
# sea_law.py — Contract Validator
# ===============================
cat > "$PKG/sea_law.py" << 'EOF'
"""
The Law of the Sea (RT Contract)
Jules Verne.
"""
_ALLOWED = frozenset({"depth", "rt_call"})

def validate(api):
  if frozenset(api.get("__all__",())) != _ALLOWED:
    raise RuntimeError("SEA LAW VIOLATED")
EOF

# ===============================
# hull.py — Public API
# ===============================
cat > "$PKG/hull.py" << 'EOF'
def depth():
  return "20000 leagues under the sea"

def rt_call(x:int)->int:
  return x * 2
EOF

# ===============================
# rt_executor.py — Persistent RT Worker
# ===============================
cat > "$PKG/rt_executor.py" << 'EOF'
"""
RT Executor — Persistent Process
Jules Verne.
"""
import socket, os, struct

SOCK="/tmp/nautilus_rt.sock"
if os.path.exists(SOCK): os.remove(SOCK)

s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
s.bind(SOCK)
s.listen(1)

conn,_=s.accept()
while True:
  data=conn.recv(8)
  if not data: break
  x=struct.unpack("i",data[:4])[0]
  conn.sendall(struct.pack("i",x*2))
EOF

# ===============================
# rt_controller.py — RT IPC Client
# ===============================
cat > "$PKG/rt_controller.py" << 'EOF'
import socket, struct

class RTController:
  def __init__(self,sock="/tmp/nautilus_rt.sock"):
    self.s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
    self.s.connect(sock)

  def call(self,x:int)->int:
    self.s.sendall(struct.pack("i",x))
    return struct.unpack("i",self.s.recv(4))[0]
EOF

# ===============================
# __init__.py — Nautilus RT
# ===============================
cat > "$PKG/__init__.py" << 'EOF'
"""
Nautilus‑RT — PECI‑RT Reference Implementation
Inspired by Jules Verne.
"""
import sys
from .nemo import Nemo
from .sea_law import validate
from .hull import depth, rt_call

__all__=("depth","rt_call")

n=Nemo(__name__)
if not any(isinstance(x,Nemo) for x in sys.meta_path):
  sys.meta_path.insert(0,n)

validate(globals())
EOF

echo "✅ Nautilus‑RT created"
echo "📦 Files:"
find "$PKG" -type f | sed "s/^/ - /"
