import numpy as np
import time

start = time.time()

data = np.arange(100_000_000)
mods = data * data

unique, counts = np.unique(mods, return_counts=True)

print("Result:", counts.sum())
print("Time (NumPy):", time.time() - start)
