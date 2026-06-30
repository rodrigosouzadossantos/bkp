import polars as pl
import altair as alt
import pandas as pd

FEATURES_PATH = "features.parquet"

# -------------------------------
# Load dataset
# -------------------------------
df = pl.read_parquet(FEATURES_PATH)
print(f"Loaded {df.height} rows and {df.width} columns")

# Numeric columns
numeric_cols = df.select(pl.numeric_columns()).columns
numeric_df = df.select(numeric_cols)

# Convert to pandas (Altair requires pandas)
pdf = numeric_df.to_pandas()

# -------------------------------
# 1️⃣ Missing / zero values heatmap
# -------------------------------
missing_df = pdf.isna() | (pdf == 0)
missing_df = missing_df.reset_index().melt(id_vars="index", var_name="feature", value_name="missing")
missing_df["missing"] = missing_df["missing"].astype(int)

missing_heatmap = alt.Chart(missing_df).mark_rect().encode(
    x=alt.X("index:O", title="Row"),
    y=alt.Y("feature:N", title="Feature"),
    color=alt.Color("missing:Q", scale=alt.Scale(scheme="viridis"), title="Missing/Zero"),
    tooltip=["feature", "index", "missing"]
).properties(
    width=800, height=400, title="Missing / Zero Values Heatmap"
)

# -------------------------------
# 2️⃣ Correlation heatmap
# -------------------------------
corr_df = pdf.corr().reset_index().melt(id_vars="index", var_name="feature2", value_name="corr")
corr_df = corr_df.rename(columns={"index": "feature1"})

corr_heatmap = alt.Chart(corr_df).mark_rect().encode(
    x=alt.X("feature1:N", title="Feature 1"),
    y=alt.Y("feature2:N", title="Feature 2"),
    color=alt.Color("corr:Q", scale=alt.Scale(scheme="redblue"), title="Correlation"),
    tooltip=["feature1", "feature2", "corr"]
).properties(
    width=600, height=600, title="Correlation Heatmap"
)

# -------------------------------
# 3️⃣ Scatter matrix / pairplot (sampled)
# -------------------------------
SAMPLE_SIZE = 5000
pdf_sample = pdf.sample(SAMPLE_SIZE, random_state=42) if pdf.shape[0] > SAMPLE_SIZE else pdf

scatter_charts = []
for i, col_x in enumerate(numeric_cols):
    for j, col_y in enumerate(numeric_cols):
        if i >= j:
            continue  # upper triangle only
        c = alt.Chart(pdf_sample).mark_circle(size=10, opacity=0.5).encode(
            x=alt.X(f"{col_x}:Q"),
            y=alt.Y(f"{col_y}:Q"),
            tooltip=[col_x, col_y]
        ).properties(width=150, height=150)
        scatter_charts.append(c)

from altair import vconcat, hconcat

def make_grid(charts, ncols):
    rows = [hconcat(*charts[i:i+ncols]) for i in range(0, len(charts), ncols)]
    return vconcat(*rows)

scatter_matrix = make_grid(scatter_charts, ncols=5)

# -------------------------------
# 4️⃣ Tab selector
# -------------------------------
tab_selector = alt.binding_radio(options=["Missing", "Correlation", "Scatter"], name="Select view: ")
tab_selection = alt.selection_single(fields=["tab"], bind=tab_selector, init={"tab": "Missing"})

# Wrap each chart with a "tab" column
missing_chart_tab = missing_heatmap.add_selection(tab_selection).transform_filter(alt.datum.tab == "Missing")
corr_chart_tab = corr_heatmap.add_selection(tab_selection).transform_filter(alt.datum.tab == "Correlation")
scatter_chart_tab = scatter_matrix.add_selection(tab_selection).transform_filter(alt.datum.tab == "Scatter")

# Altair doesn’t fully support multi-chart selection natively,
# so we emulate by showing/hiding charts via selection
# In practice, you can render each separately or create a small dashboard HTML
missing_heatmap.show()
corr_heatmap.show()
scatter_matrix.show()
