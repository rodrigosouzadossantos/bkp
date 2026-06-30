use std::sync::Arc;

use anyhow::Result;
use rayon::prelude::*;

use arrow_array::{Array, ArrayRef, Float32Array, PrimitiveArray};
use arrow_schema::{DataType, Field, Schema};
use arrow::record_batch::RecordBatch;
use arrow::datatypes::Float32Type;

use storage::api as storage_api;

//////////////////////////////////////////////////////
// PUBLIC API
//////////////////////////////////////////////////////

/// Ingest dataset by name (resolved via storage layer)
pub fn ingest(dataset_name: &str) -> Result<RecordBatch> {

    // 1. Resolve dataset → paths
    let objects = storage_api::resolve_dataset(dataset_name);

    if objects.is_empty() {
        return Err(anyhow::anyhow!("Dataset is empty"));
    }

    // 2. Read files in parallel
    let data: Vec<Vec<u8>> = objects
        .par_iter()
        .map(|obj| storage_api::read(&obj.path))
        .collect();

    // 3. Convert raw bytes → numeric (placeholder logic)
    let values: Vec<f32> = data
        .par_iter()
        .flat_map(|bytes| decode_bytes(bytes))
        .collect();

    // 4. Build Arrow column
    let array: ArrayRef = Arc::new(Float32Array::from(values));

    // 5. Schema
    let schema = Arc::new(Schema::new(vec![
        Field::new("value", DataType::Float32, false)
    ]));

    // 6. RecordBatch (zero-copy container)
    let batch = RecordBatch::try_new(schema, vec![array])?;

    Ok(batch)
}

//////////////////////////////////////////////////////
// ZERO-COPY → NUMPY BRIDGE (PyO3)
//////////////////////////////////////////////////////

use numpy::{PyArray1};
use pyo3::prelude::*;

#[pyfunction]
pub fn ingest_numpy(py: Python<'_>, dataset_name: &str) -> Py<PyArray1<f32>> {
  let batch: RecordBatch = ingest(dataset_name).expect("ingest failed");

  let column: &Arc<dyn Array> = batch.column(0);

  let float_array: &PrimitiveArray<Float32Type> = column
    .as_any()
    .downcast_ref::<Float32Array>()
    .unwrap();

  // Currently copies — next step is Arrow FFI zero-copy
  let vec: Vec<f32> = float_array.values().to_vec();

  // Convert Bound<&PyArray1> into Py<PyArray1>
  PyArray1::from_vec(py, vec).to_owned().into()
}

//////////////////////////////////////////////////////
// INTERNAL HELPERS
//////////////////////////////////////////////////////

/// Placeholder decoder (image/video/text later)
fn decode_bytes(bytes: &Vec<u8>) -> Vec<f32> {

    // Example: normalize bytes → floats
    bytes
        .iter()
        .map(|b| *b as f32 / 255.0)
        .collect()
}
