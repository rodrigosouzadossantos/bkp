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
