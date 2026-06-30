# Quickstart

```python
from Subsea.pipelines.image_pipeline import ImagePipeline

pipeline = ImagePipeline()

df = pipeline.run( [ 'image1.jpg', 'image2.jpg' ] )

print( df )
```


