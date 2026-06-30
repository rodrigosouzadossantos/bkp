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
