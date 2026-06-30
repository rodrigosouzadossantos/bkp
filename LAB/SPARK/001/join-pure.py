import time

start = time.time()

d1 = {i: i*2 for i in range(5_000_000)}
d2 = {i: i*3 for i in range(5_000_000)}

total = 0
for k in d1:
    total += d1[k] + d2[k]

print(total)
print("Python time:", time.time() - start)
