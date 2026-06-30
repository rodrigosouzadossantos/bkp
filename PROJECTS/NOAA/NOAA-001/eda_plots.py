import polars as pl
import matplotlib.pyplot as plt
import seaborn as sns

FEATURES_PATH = "features.parquet"
df = pl.read_parquet(FEATURES_PATH)
print(f"Loaded {df.height} rows and {df.width} columns")

# -------------------------------
# Numeric and Categorical Columns
# -------------------------------
numeric_cols = df.select(pl.numeric_columns()).columns
categorical_cols = [c for c in df.columns if c not in numeric_cols]

# -------------------------------
# MISSING VALUE HEATMAP
# -------------------------------
missing_df = df.select([
    pl.col(c).is_null().cast(pl.Int8).alias(c) for c in df.columns
])
plt.figure(figsize=(12, 6))
sns.heatmap(missing_df.to_pandas().T, cbar=False, cmap="Reds")
plt.title("Missing Value Heatmap (1 = missing, 0 = present)")
plt.xlabel("Rows")
plt.ylabel("Features")
plt.show()

# -------------------------------
# FEATURE CORRELATION HEATMAP
# -------------------------------
if numeric_cols:
    corr_matrix = df.select(numeric_cols).to_pandas().corr()
    plt.figure(figsize=(10, 8))
    sns.heatmap(corr_matrix, annot=True, fmt=".2f", cmap="coolwarm", square=True)
    plt.title("Correlation Heatmap of Numeric Features")
    plt.show()

# -------------------------------
# DISTRIBUTION PLOTS FOR ALL NUMERIC FEATURES
# -------------------------------
for col in numeric_cols:
    plt.figure(figsize=(6, 4))
    sns.histplot(df[col].to_numpy(), bins=50, kde=True)
    plt.title(f"Distribution of {col}")
    plt.show()
