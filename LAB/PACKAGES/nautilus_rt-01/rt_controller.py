import socket, struct

class RTController:
  def __init__(self,sock="/tmp/nautilus_rt.sock"):
    self.s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
    self.s.connect(sock)

  def call(self,x:int)->int:
    self.s.sendall(struct.pack("i",x))
    return struct.unpack("i",self.s.recv(4))[0]
