import nvidia.dali.pipeline as pipeline
import nvidia.dali.fn as fn

pipe = pipeline.Pipeline(batch_size=1, num_threads=1, device_id=0)

with pipe:
  images, labels = fn.readers.file(file_root="s3://noaa-auv/main/NOAA-AUV/VIOLA/6000713538")
  images = fn.decoders.image(images, device="mixed")
  pipe.set_outputs(images, labels)

pipe.build()
outputs = pipe.run()

print(f"Shape: {outputs[0].shape()}")

