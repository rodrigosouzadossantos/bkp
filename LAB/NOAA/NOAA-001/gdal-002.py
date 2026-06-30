from osgeo import gdal, osr

def get_full_dataset_info(file_path):
    # Open dataset and enable exceptions for better debugging
    gdal.UseExceptions()
    ds = gdal.Open(file_path)
    
    # 1. Projection and SRS Info
    wkt_raw = ds.GetProjection()
    srs = osr.SpatialReference()
    srs.ImportFromWkt(wkt_raw)
    
    # 2. Geotransform (Position & Resolution)
    gt = ds.GetGeoTransform()
    
    # 3. Comprehensive Data Collection
    full_info = {
        "file": file_path,
        "driver": ds.GetDriver().LongName,
        "wkt_raw": wkt_raw,
        "epsg": srs.GetAuthorityCode(None),
        "dimensions": {"width": ds.RasterXSize, "height": ds.RasterYSize},
        "geotransform": gt,
        "metadata_general": ds.GetMetadata(),
        "bands": []
    }

    # 4. Extract Per-Band Information
    for i in range(1, ds.RasterCount + 1):
        band = ds.GetRasterBand(i)
        
        # Calculate statistics (min, max, mean, stddev)
        try:
            stats = band.GetStatistics(True, True) # (min, max, mean, stddev)
        except:
            stats = None

        band_info = {
            "index": i,
            "description": band.GetDescription(),
            "data_type": gdal.GetDataTypeName(band.DataType),
            "no_data_value": band.GetNoDataValue(),
            "color_interpretation": gdal.GetColorInterpretationName(band.GetColorInterpretation()),
            "statistics": stats,
            "metadata": band.GetMetadata()
        }
        full_info["bands"].append(band_info)

    return full_info

# Execution
data = get_full_dataset_info('FT_20240415_001838_3_BC0030VB0082.tif')

import pprint
pp = pprint.PrettyPrinter(indent=1)
pp.pprint(data)
