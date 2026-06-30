import polars as pl
import plotly.express as px
import plotly.graph_objects as go

FEATURES_PATH = "features.parquet"
df = pl.read_parquet(FEATURES_PATH)
print(f"Loaded {df.height} rows and {df.width} columns")

# -------------------------------
# Numeric columns
# -------------------------------
numeric_cols = df.select(pl.numeric_columns()).columns
numeric_df = df.select(numeric_cols)

# -------------------------------
# 1️⃣ Missing value heatmap
# -------------------------------
missing_df = numeric_df.select([
    ((pl.col(c).is_null()) | (pl.col(c) == 0)).alias(c)
    for c in numeric_cols
])
missing_matrix = missing_df.to_numpy().astype(int)

fig_missing = go.Figure(
    data=go.Heatmap(
        z=missing_matrix.T,
        x=list(range(df.height)),
        y=numeric_cols,
        colorscale="Viridis",
        colorbar=dict(title="Missing/Zero"),
    )
)
fig_missing.update_layout(title="Missing / Zero Values Heatmap")
fig_missing.show()

# -------------------------------
# 2️⃣ Correlation heatmap
# -------------------------------
corr_df = numeric_df.to_pandas().corr()  # small memory usage for correlation
fig_corr = px.imshow(
    corr_df,
    text_auto=True,
    color_continuous_scale="RdBu_r",
    title="Correlation Heatmap of Numeric Features",
    aspect="auto",
)
fig_corr.show()

# -------------------------------
# 3️⃣ Scatter matrix (pairplot) – interactive
# -------------------------------
SUBSAMPLE = 5000
if df.height > SUBSAMPLE:
    df_sample = df.sample(n=SUBSAMPLE, with_replacement=False, seed=42)
else:
    df_sample = df

fig_scatter = px.scatter_matrix(
    df_sample.to_pandas(),
    dimensions=numeric_cols,
    color=None,
    title="Interactive Scatter Matrix of Numeric Features",
    height=900,
)
fig_scatter.update_traces(diagonal_visible=True, marker=dict(size=3, opacity=0.6))
fig_scatter.show()
