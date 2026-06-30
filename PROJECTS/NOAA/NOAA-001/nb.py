import marimo

__generated_with = "0.21.1"
app = marimo.App(width="medium")


@app.cell
def _():
    import polars as pl
    import polars.selectors as cs

    df = pl.read_parquet("outputs/features.parquet")

    print("All columns in dataset:")
    for c in df.columns:
        print("-", c)

    return cs, df, pl


@app.cell
def _():
    from obstore.store import S3Store

    store = S3Store("analise-dados",
        region="sa-east-1",
        access_key_id="AKIA5GCWF4XZJUSLZ5OT",
        secret_access_key="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",
    )
    return


@app.cell
def _(df):
    df.count()
    return


@app.cell
def _(cs, df):
    # Select all numeric types
    numeric_df = df.select(cs.numeric())
    #print(numeric_df.head())

    summary = numeric_df.describe()
    print(summary)
    return (numeric_df,)


@app.cell
def _(df, pl):
    missing_stats = df.select([
        pl.col(c).null_count().alias(c) for c in df.columns
    ])
    print("Missing values per feature:")
    print(missing_stats)
    return


@app.cell
def _(numeric_df):
    corr = numeric_df.to_numpy()
    import numpy as np

    corr_matrix = np.corrcoef(corr.T)
    print("Correlation matrix shape:", corr_matrix.shape)
    return


@app.cell
def _(cs, df, pl):
    from sklearn.cluster import KMeans


    # Load numeric features
    numeric_df_ = df.select(cs.numeric())

    # Convert to NumPy for scikit-learn
    X = numeric_df_.to_numpy()

    # Run KMeans
    k = 2  # e.g., benthic vs non-benthic
    kmeans = KMeans(n_clusters=k, random_state=42)
    labels = kmeans.fit_predict(X)

    # Add cluster labels back to Polars DataFrame
    numeric_df_ = numeric_df_.with_columns(pl.Series("cluster", labels))
    print(numeric_df_.head())
    return


if __name__ == "__main__":
    app.run()
