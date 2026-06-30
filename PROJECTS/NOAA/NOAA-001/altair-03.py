import polars as pl
import pandas as pd
import altair as alt

FEATURES_PATH = "features.parquet"

# -------------------------------
# Load dataset
# -------------------------------
df = pl.read_parquet(FEATURES_PATH)
print(f"Loaded {df.height} rows and {df.width} columns")

# Numeric columns
numeric_cols = df.select(pl.numeric_columns()).columns
numeric_df = df.select(numeric_cols)

# Convert to pandas for Altair
pdf = numeric_df.to_pandas()

# -------------------------------
# Missing / zero values heatmap
# -------------------------------
missing_df = pdf.isna() | (pdf == 0)
missing_df = missing_df.reset_index().melt(id_vars="index", var_name="feature", value_name="missing")
missing_df["missing"] = missing_df["missing"].astype(int)

missing_heatmap = alt.Chart(missing_df).mark_rect().encode(
    x=alt.X("index:O", title="Row"),
    y=alt.Y("feature:N", title="Feature"),
    color=alt.Color("missing:Q", scale=alt.Scale(scheme="viridis"), title="Missing/Zero"),
    tooltip=["feature", "index", "missing"]
).properties(width=800, height=400, title="Missing / Zero Values Heatmap")

# -------------------------------
# Correlation heatmap
# -------------------------------
corr_df = pdf.corr().reset_index().melt(id_vars="index", var_name="feature2", value_name="corr")
corr_df = corr_df.rename(columns={"index": "feature1"})

corr_heatmap = alt.Chart(corr_df).mark_rect().encode(
    x=alt.X("feature1:N", title="Feature 1"),
    y=alt.Y("feature2:N", title="Feature 2"),
    color=alt.Color("corr:Q", scale=alt.Scale(scheme="redblue", domain=(-1, 1)), title="Correlation"),
    tooltip=["feature1", "feature2", "corr"]
).properties(width=600, height=600, title="Correlation Heatmap")

# -------------------------------
# Scatter matrix (sampled)
# -------------------------------
SAMPLE_SIZE = 5000
pdf_sample = pdf.sample(SAMPLE_SIZE, random_state=42) if pdf.shape[0] > SAMPLE_SIZE else pdf

scatter_charts = []
for i, col_x in enumerate(numeric_cols):
    for j, col_y in enumerate(numeric_cols):
        if i >= j:
            continue
        c = alt.Chart(pdf_sample).mark_circle(size=10, opacity=0.5).encode(
            x=alt.X(f"{col_x}:Q"),
            y=alt.Y(f"{col_y}:Q"),
            tooltip=[col_x, col_y]
        ).properties(width=150, height=150)
        scatter_charts.append(c)

from altair import hconcat, vconcat

def make_grid(charts, ncols):
    rows = [hconcat(*charts[i:i+ncols]) for i in range(0, len(charts), ncols)]
    return vconcat(*rows)

scatter_matrix = make_grid(scatter_charts, ncols=5)

# -------------------------------
# Tabs selector
# -------------------------------
tabs = alt.binding_radio(options=["Missing", "Correlation", "Scatter"], name="Select view: ")
tab_select = alt.selection_single(fields=["tab"], bind=tabs, init={"tab": "Missing"})

# Wrap each chart in a "tab" column to show/hide
missing_heatmap = missing_heatmap.add_selection(tab_select).transform_calculate(tab="'Missing'").transform_filter(alt.datum.tab == "Missing")
corr_heatmap = corr_heatmap.add_selection(tab_select).transform_calculate(tab="'Correlation'").transform_filter(alt.datum.tab == "Correlation")
scatter_matrix = scatter_matrix.add_selection(tab_select).transform_calculate(tab="'Scatter'").transform_filter(alt.datum.tab == "Scatter")

# -------------------------------
# Combine charts vertically
# -------------------------------
dashboard = alt.vconcat(missing_heatmap, corr_heatmap, scatter_matrix)

# -------------------------------
# Save as HTML
# -------------------------------
dashboard.save("eda_dashboard.html")
print("Dashboard saved as eda_dashboard.html. Open it in your browser to explore.")
