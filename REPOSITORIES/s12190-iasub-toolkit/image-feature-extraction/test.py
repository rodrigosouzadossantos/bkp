import boto3
from PIL import Image
from io import BytesIO

# 1. Setup Session and Client
s3_client = (
  boto3
    .Session(profile_name='lakefs')
    .client(
      's3',
      endpoint_url='http://localhost:8000'
    )
)

# 2. Get the object from S3
response = s3_client.get_object(
  Bucket='noaa-auv',
  Key='main/NOAA-AUV/VIOLA/6000713538/FT_20241016_053320_3_BC0030VB0153.jpg'
)

# 3. Read the 'Body' stream
image_data = response['Body'].read()

# 4. Open as an image object
image = Image.open(BytesIO(image_data))
image.show()

