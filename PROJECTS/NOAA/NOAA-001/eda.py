import polars as pl

# -------------------------------
# LOAD DATA
# -------------------------------
FEATURES_PATH = "features.parquet"
df = pl.read_parquet(FEATURES_PATH)
print(f"Loaded {df.height} rows and {df.width} columns")

# -------------------------------
# BASIC OVERVIEW
# -------------------------------
print("\n=== COLUMN TYPES ===")
print(df.dtypes)

print("\n=== HEAD ===")
print(df.head(5))

# -------------------------------
# NUMERIC & CATEGORICAL SPLIT
# -------------------------------
numeric_cols = df.select(pl.numeric_columns()).columns
categorical_cols = [c for c in df.columns if c not in numeric_cols]

print("\nNumeric columns:", numeric_cols)
print("Categorical columns:", categorical_cols)

# -------------------------------
# MISSING VALUES
# -------------------------------
missing_per_column = df.select([
    pl.col(c).is_null().sum().alias(c) for c in df.columns
])
print("\n=== MISSING VALUES PER COLUMN ===")
print(missing_per_column)

# -------------------------------
# BASIC STATS
# -------------------------------
print("\n=== NUMERIC STATS ===")
print(df.select(numeric_cols).describe())

# -------------------------------
# CORRELATION MATRIX
# -------------------------------
if numeric_cols:
    corr_matrix = df.select(numeric_cols).to_pandas().corr()
    print("\n=== CORRELATION MATRIX ===")
    print(corr_matrix)

# -------------------------------
# QUICK VISUALIZATION (OPTIONAL)
# -------------------------------
try:
    import matplotlib.pyplot as plt
    import seaborn as sns

    for col in numeric_cols:
        plt.figure(figsize=(6, 4))
        sns.histplot(df[col].to_numpy(), bins=50, kde=True)
        plt.title(f"Distribution of {col}")
        plt.show()
except ImportError:
    print("Install matplotlib and seaborn for plotting.")
