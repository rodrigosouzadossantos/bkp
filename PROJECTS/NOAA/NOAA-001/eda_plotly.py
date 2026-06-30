import polars as pl
import plotly.express as px
import plotly.figure_factory as ff
import plotly.graph_objects as go

FEATURES_PATH = "features.parquet"
df = pl.read_parquet(FEATURES_PATH)
print(f"Loaded {df.height} rows and {df.width} columns")

# -------------------------------
# Numeric Columns
# -------------------------------
numeric_cols = df.select(pl.numeric_columns()).columns

# -------------------------------
# MISSING VALUE HEATMAP
# -------------------------------
# Create binary matrix: 1 if missing, 0 if present
missing_matrix = df.select([pl.col(c).is_null().cast(pl.Int8).alias(c) for c in df.columns])

fig_missing = px.imshow(
    missing_matrix.to_numpy().T,
    labels=dict(x="Rows", y="Features", color="Missing"),
    x=list(range(df.height)),
    y=missing_matrix.columns,
    color_continuous_scale="Reds",
)
fig_missing.update_layout(title="Missing Value Heatmap (1 = missing, 0 = present)")
fig_missing.show()

# -------------------------------
# FEATURE CORRELATION HEATMAP
# -------------------------------
if numeric_cols:
    corr_matrix = df.select(numeric_cols).to_pandas().corr()  # Polars doesn't yet compute full correlation matrix natively
    fig_corr = px.imshow(
        corr_matrix.values,
        x=numeric_cols,
        y=numeric_cols,
        color_continuous_scale="RdBu_r",
        zmin=-1,
        zmax=1,
        text_auto=".2f",
    )
    fig_corr.update_layout(title="Correlation Heatmap of Numeric Features")
    fig_corr.show()

# -------------------------------
# DISTRIBUTION PLOTS (INTERACTIVE)
# -------------------------------
for col in numeric_cols:
    fig = ff.create_distplot([df[col].to_numpy()], group_labels=[col], show_hist=True, show_rug=False)
    fig.update_layout(title=f"Distribution of {col}")
    fig.show()
