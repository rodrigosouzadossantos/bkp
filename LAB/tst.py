import petrobras
from time import sleep

for i in range(1, 19):
  petrobras.run(f"Petro #{i:02d}")
  print(f"Petro #{i:02d}")
  sleep(0.2)





