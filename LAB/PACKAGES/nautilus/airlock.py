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
