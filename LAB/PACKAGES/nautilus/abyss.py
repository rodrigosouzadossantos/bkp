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
