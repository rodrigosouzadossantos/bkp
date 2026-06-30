from osgeo import gdal, osr
gdal.UseExceptions()

ds = gdal.Open('FT_20240415_001838_3_BC0030VB0082.tif')

exif = ds.GetMetadata('EXIF')
for key, value in exif.items():
    print(f'{key}: {value}')

domain = ds.GetMetadataDomainList()
print(domain)

for d in domain:
    print(f'Metadata domain: {d}')
    metadata = ds.GetMetadata(d)
    for key, value in metadata.items():
        print(f'  {key}: {value}')

print('Raster size:', (ds.RasterXSize, ds.RasterYSize))

print('=' * 80)
# ========================================================================

gt = ds.GetGeoTransform()
print('GeoTransform:', gt)
if gt:
    print('Origin (top left):', (gt[0], gt[3]))
    print('Pixel size:', (gt[1], gt[5]))

print('=' * 80)
# ========================================================================

proj = ds.GetProjection()
#print('Projection:', proj)
if proj:
    # 1. Initialize the Spatial Reference object
    srs = gdal.osr.SpatialReference()
    srs.ImportFromWkt(proj)
    #print('EPSG Code:', srs.GetAttrValue('AUTHORITY', 1))

    # 2. Extract Top-Level Identifiers
    info = {
        "Projected_CS": srs.GetAttrValue("PROJCS"),
        "Geographic_CS": srs.GetAttrValue("GEOGCS"),
        "Datum": srs.GetAttrValue("DATUM"),
        "Projection_Type": srs.GetAttrValue("PROJECTION"),
        "EPSG_Code": srs.GetAuthorityCode(None),
        "Prime_Meridian": srs.GetAttrValue("PRIMEM"),
        "Angular_Unit": srs.GetAttrValue("UNIT"),
        "Radian_Conversion_Factor": srs.GetAngularUnits(),
        "Angular_Unit_epsg": srs.GetAttrValue("GEOGCS|UNIT"),
    }

    # 3. Extract Mathematical Projection Parameters
    # Using SRS_PP constants ensures you get the right value regardless of string order
    info["Parameters"] = {
        "Latitude_of_Origin": srs.GetProjParm(gdal.osr.SRS_PP_LATITUDE_OF_ORIGIN),
        "Central_Meridian": srs.GetProjParm(gdal.osr.SRS_PP_CENTRAL_MERIDIAN),
        "Scale_Factor": srs.GetProjParm(gdal.osr.SRS_PP_SCALE_FACTOR),
        "False_Easting": srs.GetProjParm(gdal.osr.SRS_PP_FALSE_EASTING),
        "False_Northing": srs.GetProjParm(gdal.osr.SRS_PP_FALSE_NORTHING),
    }

    # 4. Extract Spheroid and Units
    info["Spheroid"] = {
        "Name": srs.GetAttrValue("SPHEROID"),
        "Semi_Major_Axis": srs.GetSemiMajor(),
        "Inverse_Flattening": srs.GetInvFlattening(),
    }

    info["Units_and_Axes"] = {
        "Linear_Unit": srs.GetLinearUnitsName(),
        "Meters_Per_Unit": srs.GetLinearUnits(),
        "Axis_0": srs.GetAttrValue("AXIS", 0),
        "Axis_1": srs.GetAttrValue("AXIS", 1),
    }

    print('Projection Information:')
    for key, value in info.items():
        if isinstance(value, dict):
            print(f'  {key}:')
            for subkey, subvalue in value.items():
                print(f'    {subkey}: {subvalue}')
        else:
            print(f'  {key}: {value}')

print('=' * 80)
# ========================================================================

def extract_everything(ds):
    # Enable exceptions for better error catching

    # --- 1. PROJECTION & SRS EXTRACTION ---
    wkt_raw = ds.GetProjection()
    srs = osr.SpatialReference()
    srs.ImportFromWkt(wkt_raw)

    # Prime Meridian and Angular Units (Missing in previous steps)
    pm_name = srs.GetAttrValue("PRIMEM")                 # "Greenwich"
    pm_offset = float(srs.GetAttrValue("PRIMEM", 1))      # 0.0

    ang_unit_name = srs.GetAttrValue("GEOGCS|UNIT")      # "degree"
    rad_per_unit = srs.GetAngularUnits()                 # 0.0174532925...

    # --- 2. DATASET METADATA ---
    gt = ds.GetGeoTransform()

    info = {
        "identifiers": {
            "proj_cs": srs.GetAttrValue("PROJCS"),
            "geog_cs": srs.GetAttrValue("GEOGCS"),
            "epsg": srs.GetAuthorityCode(None)
        },
        "spatial_reference": {
            "prime_meridian": {"name": pm_name, "offset": pm_offset},
            "angular_units": {"name": ang_unit_name, "radians": rad_per_unit},
            "spheroid": {
                "name": srs.GetAttrValue("SPHEROID"),
                "semi_major": srs.GetSemiMajor(),
                "inv_flattening": srs.GetInvFlattening()
            },
            "parameters": {
                "central_meridian": srs.GetProjParm(osr.SRS_PP_CENTRAL_MERIDIAN),
                "scale_factor": srs.GetProjParm(osr.SRS_PP_SCALE_FACTOR),
                "false_easting": srs.GetProjParm(osr.SRS_PP_FALSE_EASTING),
                "false_northing": srs.GetProjParm(osr.SRS_PP_FALSE_NORTHING)
            }
        },
        "raster_details": {
            "size": {"width": ds.RasterXSize, "height": ds.RasterYSize},
            "origin": {"x": gt[0], "y": gt[3]},
            "pixel_size": {"width": gt[1], "height": gt[5]},
            "bands": []
        }
    }

    # --- 3. BAND EXTRACTION ---
    for i in range(1, ds.RasterCount + 1):
        band = ds.GetRasterBand(i)
        stats = band.GetStatistics(True, True) # min, max, mean, stddev

        info["raster_details"]["bands"].append({
            "band_index": i,
            "type": gdal.GetDataTypeName(band.DataType),
            "color": gdal.GetColorInterpretationName(band.GetColorInterpretation()),
            "no_data": band.GetNoDataValue(),
            "min": stats[0],
            "max": stats[1],
            "mean": stats[2]
        })

    return info



def get_corners(ds):
    gt = ds.GetGeoTransform()
    width = ds.RasterXSize
    height = ds.RasterYSize

    # 1. Setup Coordinate Transformation (UTM to Lat/Long)
    source_srs = osr.SpatialReference()
    source_srs.ImportFromWkt(ds.GetProjection())
    
    target_srs = osr.SpatialReference()
    target_srs.ImportFromEPSG(4326)  # WGS84 (Standard Lat/Long)
    
    # Required for GDAL 3.0+ to ensure (Lat, Lon) vs (Lon, Lat) order
    target_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    
    transform = osr.CoordinateTransformation(source_srs, target_srs)

    def get_coords(px, py):
        # Calculate UTM
        x = gt[0] + px * gt[1] + py * gt[2]
        y = gt[3] + px * gt[4] + py * gt[5]
        
        # Transform to Lat/Long
        lon, lat, _ = transform.TransformPoint(x, y)
        
        # Format as DMS (Degrees Minutes Seconds) helper
        def to_dms(val, is_lat):
            abs_val = abs(val)
            d = int(abs_val)
            m = int((abs_val - d) * 60)
            s = round((abs_val - d - m/60) * 3600, 2)
            direction = ""
            if is_lat: direction = "N" if val >= 0 else "S"
            else: direction = "E" if val >= 0 else "W"
            return f"{d}d{m}' {s}\"{direction}"

        return f"({x:12.3f}, {y:12.3f}) ({to_dms(lon, False)}, {to_dms(lat, True)})"

    # 2. Extract specific points
    print(f"Upper Left  {get_coords(0, 0)}")
    print(f"Lower Left  {get_coords(0, height)}")
    print(f"Upper Right {get_coords(width, 0)}")
    print(f"Lower Right {get_coords(width, height)}")
    print(f"Center      {get_coords(width/2, height/2)}")

get_corners(ds)


print('=' * 80)
# ========================================================================

for i in range(ds.RasterCount):
    band = ds.GetRasterBand(i + 1)
    print(f'Band {i + 1}:')
    print('  Description:', band.GetDescription())
    print('  Data type:', gdal.GetDataTypeName(band.DataType))
    print('  NoData value:', band.GetNoDataValue())
    print('  Minimum:', band.GetMinimum())
    print('  Maximum:', band.GetMaximum())
    print('  Statistics:', band.GetStatistics(True, True))
    print('  Color interpretation:',
          gdal.GetColorInterpretationName(band.GetColorInterpretation()))
    print('  Color table:', band.GetColorTable())
    print('  metadata:', band.GetMetadata())
    print('  scale:', band.GetScale())
    print('  offset:', band.GetOffset())
    print('  unit type:', band.GetUnitType())
    print('  category names:', band.GetCategoryNames())
