import polars as pl
import plotly.express as px
import plotly.figure_factory as ff

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
# POLARS CORRELATION MATRIX (100% POLARS)
# -------------------------------
def polars_corr_matrix(df: pl.DataFrame, cols: list[str]) -> pl.DataFrame:
    """
    Compute correlation matrix in Polars (Pearson) for given numeric columns.
    """
    n = df.height
    corr_dict = {}
    for i, col1 in enumerate(cols):
        corr_row = []
        x = df[col1]
        mean_x = x.mean()
        std_x = x.std()
        for j, col2 in enumerate(cols):
            y = df[col2]
            mean_y = y.mean()
            std_y = y.std()
            cov = ((x - mean_x) * (y - mean_y)).sum() / (n - 1)
            corr = cov / (std_x * std_y) if std_x > 0 and std_y > 0 else 0.0
            corr_row.append(corr)
        corr_dict[col1] = corr_row
    return pl.DataFrame(corr_dict, columns=cols)

if numeric_cols:
    corr_df = polars_corr_matrix(df, numeric_cols)

    fig_corr = px.imshow(
        corr_df.to_numpy(),
        x=numeric_cols,
        y=numeric_cols,
        color_continuous_scale="RdBu_r",
        zmin=-1,
        zmax=1,
        text_auto=".2f",
    )
    fig_corr.update_layout(title="Correlation Heatmap of Numeric Features (Polars)")
    fig_corr.show()

# -------------------------------
# DISTRIBUTION PLOTS (INTERACTIVE)
# -------------------------------
for col in numeric_cols:
    fig = ff.create_distplot([df[col].to_numpy()], group_labels=[col], show_hist=True, show_rug=False)
    fig.update_layout(title=f"Distribution of {col}")
    fig.show()
