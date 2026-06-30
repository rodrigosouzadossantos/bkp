import time

start = time.time()

data = range(100_000_000)

counts = {}
for x in data:
    k = x * x
    counts[k] = counts.get(k, 0) + 1

print("Result:", sum(counts.values()))
print("Time (no Spark):", time.time() - start)
