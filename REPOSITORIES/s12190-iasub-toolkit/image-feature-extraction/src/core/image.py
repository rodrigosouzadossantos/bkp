from pyspark.sql.types import *
iceberg_schema = StructType([
  StructField("image_id", StringType(), False),
  StructField("format_info", StructType([
    StructField("codec", StringType(), True),
    StructField("resolution", ArrayType(IntegerType()), True),
    StructField("dtype", StringType(), True)
  ])),
  StructField("spatial", StructType([
    StructField("bbox", ArrayType(DoubleType()), True), # [MinX, MinY, MaxX, MaxY]
    StructField("center", ArrayType(DoubleType()), True),
    StructField("geokeys", MapType(StringType(), IntegerType()), True)
  ])),
  StructField("subsea_eda", StructType([
    StructField("uciqe_score", DoubleType(), True),      # Qualidade científica
    StructField("red_loss_ratio", DoubleType(), True),   # Atenuação de cor
    StructField("avg_saturation", DoubleType(), True),   # Saturação subaquática
    StructField("sharpness_tenengrad", DoubleType(), True),
    StructField("data_coverage_pct", DoubleType(), True) # Pixels úteis vs pretos
  ])),
  StructField("clustering_identity", StructType([
    StructField("phash", StringType(), True),            # Detecção de duplicatas
    StructField("feature_vector", ArrayType(LongType()), True) # Histograma RGB p/ K-Means
  ])),
  StructField("raw_header_tags", MapType(StringType(), StringType(), True))
])



import nvimgcodecimport cupy as cpimport numpy as np
class SubseaExtractor:
  def __init__(self):
    self.decoder = nvimgcodec.Decoder()

  def decode_geokeys(self, directory):
    if directory is None: return {}
    KEYS = {1024: "ModelType", 1025: "RasterType", 2048: "GeogType", 3072: "ProjType"}
    decoded = {}
    for i in range(1, int(directory[3]) + 1):
      k, v = directory[i*4], directory[i*4 + 3]
      decoded[KEYS.get(k, f"Key_{k}")] = int(v)
    return decoded

  def process_record(self, image_bytes, record_id):
    # --- 1. Decode & Header Parsing ---
    image = self.decoder.decode(image_bytes)
    tags = {
      str(t.id): (t.value.tolist() if isinstance(t.value, np.ndarray) else str(t.value))
      for t in image.metadata
    }

    # --- 2. Spatial / GeoTIFF Logic ---
    w, h = image.width, image.height
    geokeys = self.decode_geokeys(image.metadata.get(34735))

    bbox, center = None, None
    if "33922" in tags and "33550" in tags:
      t, p = image.metadata[33922], image.metadata[33550]
      bbox = [float(t[3]), float(t[4] - (h * p[1])), float(t[3] + (w * p[0])), float(t[4])]
      center = [float(t[3] + (w * p[0]/2)), float(t[4] - (h * p[1]/2))]

    # --- 3. GPU Features ---
    gpu_img = cp.asarray(image.cuda())
    r, g, b = gpu_img[:,:,0], gpu_img[:,:,1], gpu_img[:,:,2]

    # Subsea Specifics
    red_loss = float(cp.mean(r) / (cp.mean(g) + cp.mean(b) + 1e-7))

    # UCIQE (Quality Index)
    chroma_a = r.astype(cp.float32) - g.astype(cp.float32)
    chroma_b = 0.5 * (r.astype(cp.float32) + g.astype(cp.float32)) - b.astype(cp.float32)
    chroma = cp.sqrt(chroma_a**2 + chroma_b**2)
    uciqe = (0.4680 * cp.std(chroma)) + (0.2745 * (cp.max(r)-cp.min(r))) + (0.2576 * cp.mean(chroma))

    # Sharpness & Identity
    dx, dy = cp.diff(gpu_img, axis=1), cp.diff(gpu_img, axis=0)
    sharpness = float(cp.var(cp.sqrt(dx[:-1, :]**2 + dy[:, :-1]**2)))

    # pHash for Duplicates
    img_small = cp.resize(gpu_img, (8, 8))
    phash = "".join(["1" if x > cp.mean(img_small) else "0" for x in img_small.flatten().tolist()])
    phash_hex = hex(int(phash, 2))[2:]

    # Cluster Vector (RGB Histogram 3x32 bins)
    h_r = cp.histogram(r, 32, (0, 255))[0]
    h_g = cp.histogram(g, 32, (0, 255))[0]
    h_b = cp.histogram(b, 32, (0, 255))[0]
    cluster_vec = cp.concatenate([h_r, h_g, h_b]).tolist()

    return {
      "image_id": record_id,
      "format_info": {"codec": image.codec_name, "resolution": [w, h], "dtype": str(image.sample_type)},
      "spatial": {"bbox": bbox, "center": center, "geokeys": geokeys},
      "subsea_eda": {
        "uciqe_score": float(uciqe), "red_loss_ratio": red_loss,
        "avg_saturation": float(cp.mean(chroma)/255), "sharpness_tenengrad": sharpness,
        "data_coverage_pct": float(cp.count_nonzero(gpu_img) / gpu_img.size)
      },
      "clustering_identity": {"phash": phash_hex, "feature_vector": cluster_vec},
      "raw_header_tags": {k: str(v) for k, v in tags.items()}
    }

