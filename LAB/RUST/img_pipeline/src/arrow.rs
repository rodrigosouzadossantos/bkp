use arrow::array::BinaryArray;
use arrow::record_batch::RecordBatch;
use std::sync::Arc;

pub fn to_arrow(data: Vec<Vec<u8>>) -> RecordBatch {
    let arr = BinaryArray::from_iter(data.iter().map(|b| Some(b.as_slice())));

    RecordBatch::try_from_iter(vec![
        ("data", Arc::new(arr) as _)
    ]).unwrap()
}
