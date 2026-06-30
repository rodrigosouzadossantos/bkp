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
