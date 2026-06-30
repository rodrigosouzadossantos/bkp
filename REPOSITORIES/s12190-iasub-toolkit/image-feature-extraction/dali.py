from nvidia.dali.pipeline import pipeline_def
import nvidia.dali.fn as fn
import nvidia.dali.types as types

import os

os.environ['AWS_PROFILE'] = 'lakefs'

@pipeline_def
def simple_test_pipe():
    # Create a constant on the GPU
    data = types.Constant(1, device="gpu")
    return data

def run_test():
    try:
        #pipe = simple_test_pipe(batch_size=4, num_threads=1, device_id=0)
        pipe = s3_pipeline(batch_size=32, num_threads=2, device_id=0)
        pipe.build()
        outputs = pipe.run()

        #total_images = pipe.epoch_size("Reader")
        print(f"Total images found in S3: {total_images}")

        print("DALI Test Success!")
        #print(f"Output from GPU: {outputs[0].as_cpu().as_array()}")
    except Exception as e:
        print(f"DALI Test Failed: {e}")

@pipeline_def
def s3_pipeline():
    # Pass the S3 path directly to the reader
    jpegs, labels = fn.readers.file(
        #file_root="s3://noaa-auv/main/NOAA-AUV/VIOLA/6000713538/FT_20241016_021430_0_BC0030VB0153.jpg", 
        file_root='s3://analise-dados/projeto-ia-submarina/ia-frente-ambiental/NOAA-AUV/VIOLA/6000713538/FT_20241016_050342_0_BC0030VB0153.jpg',
        random_shuffle=True, 
        name="Reader",
    )
    #images = fn.decoders.image(jpegs, device="mixed")
    return jpegs #images #, labels

if __name__ == "__main__":
    run_test()

