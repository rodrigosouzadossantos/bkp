import pandas as pd
import glob
import os

paths = glob.glob("/data/images/**/*.jpg", recursive=True)
df = pd.DataFrame({
    "image_id": [os.path.basename(p) for p in paths],
    "path": paths
})
df.to_parquet("manifest.parquet", index=False)
