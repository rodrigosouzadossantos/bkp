from pyspark.sql.types import StructType, StructField, StringType, IntegerType, DoubleType, ArrayType, MapType

noaa_auv_schema = StructType([
  StructField("path", StringType()),

  StructField("width", IntegerType()),
  StructField("height", IntegerType()),
  StructField("brightness", DoubleType()),
  StructField("contrast", DoubleType()),
  StructField("blur", DoubleType()),

  StructField("mean_r", DoubleType()),
  StructField("mean_g", DoubleType()),
  StructField("mean_b", DoubleType()),

  StructField("lbp_hist", ArrayType(DoubleType())),
  StructField("hist_r", ArrayType(DoubleType())),
  StructField("hist_g", ArrayType(DoubleType())),
  StructField("hist_b", ArrayType(DoubleType())),

  StructField("gps_lat", DoubleType()),
  StructField("gps_lon", DoubleType()),
  StructField("depth", DoubleType()),
  StructField("altitude", DoubleType()),
  StructField("pitch", DoubleType()),
  StructField("roll", DoubleType()),
  StructField("yaw", DoubleType()),

  StructField("camera_model", StringType()),
  StructField("camera_serial", StringType()),
  StructField("exposure", DoubleType()),
  StructField("aperture", DoubleType()),
  StructField("analog_gain", DoubleType()),
  StructField("digital_gain", DoubleType()),
  StructField("sensor_gain", DoubleType()),

  StructField("exif", MapType(StringType(), StringType()))
])
