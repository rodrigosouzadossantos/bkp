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
