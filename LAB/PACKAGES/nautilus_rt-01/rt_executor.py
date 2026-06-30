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
