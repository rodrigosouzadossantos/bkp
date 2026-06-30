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
