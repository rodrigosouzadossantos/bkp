import polars as pl
import numpy as np
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
import matplotlib.pyplot as plt

# Load data
df = pl.read_parquet("outputs/features.parquet")

# ---------------------------
# 1. Select numeric columns
# ---------------------------
feature_cols = [
    "entropy",
    "laplacian_var",
    "brightness_mean",
    "brightness_std",
    "saturation_mean",
    "saturation_std",
    "edge_density"
]

numeric_df = df.select(feature_cols)


# ---------------------------
# 2. Replace inf with null
# ---------------------------
numeric_df = numeric_df.with_columns([
    pl.when(pl.col(c).is_infinite())
      .then(None)
      .otherwise(pl.col(c))
      .alias(c)
    for c in numeric_df.columns
])

# ---------------------------
# 3. Fill nulls with median
# ---------------------------
numeric_df = numeric_df.with_columns([
    pl.col(c).fill_null(pl.col(c).median()).alias(c)
    for c in numeric_df.columns
])

# ---------------------------
# 4. Remove low-variance columns
# ---------------------------
variances = numeric_df.select([
    pl.col(c).var().alias(c) for c in numeric_df.columns
]).to_dict(as_series=False)

# Keep only useful columns
good_cols = [
    c for c in numeric_df.columns
    if variances[c][0] is not None and variances[c][0] > 1e-6
]

numeric_df = numeric_df.select(good_cols)

print(f"Using {len(good_cols)} features")

# ---------------------------
# 5. Convert to NumPy
# ---------------------------
X = numeric_df.to_numpy()

# ---------------------------
# 6. PCA
# ---------------------------
pca = PCA(n_components=2)
X_pca = pca.fit_transform(X)

plt.figure(figsize=(8,6))
plt.scatter(X_pca[:, 0], X_pca[:, 1], alpha=0.3)
plt.title("PCA Projection")
plt.xlabel("PC1")
plt.ylabel("PC2")
plt.show()

# ---------------------------
# 7. Clustering
# ---------------------------
kmeans = KMeans(n_clusters=3, random_state=42)
labels = kmeans.fit_predict(X)

plt.figure(figsize=(8,6))
plt.scatter(X_pca[:, 0], X_pca[:, 1], c=labels, cmap="viridis", alpha=0.3)
plt.title("Clusters")
plt.xlabel("PC1")
plt.ylabel("PC2")
plt.show()
