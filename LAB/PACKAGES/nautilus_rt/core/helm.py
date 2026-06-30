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
