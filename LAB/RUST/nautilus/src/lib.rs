//use pyo3::prelude::*;
//
///// A Python module implemented in Rust.
//#[pymodule]
//mod nautilus {
//    use pyo3::prelude::*;
//
//    /// Formats the sum of two numbers as string.
//    #[pyfunction]
//    fn sum_as_string(a: usize, b: usize) -> PyResult<String> {
//        Ok((a + b).to_string())
//    }
//}



use pyo3::prelude::*;
use pyo3::exceptions::PyRuntimeError;

use tokio::runtime::Runtime;
use std::collections::HashMap;

use aws_sdk_s3::Client;
use aws_sdk_s3::error::SdkError;
use aws_sdk_s3::operation::list_objects_v2::ListObjectsV2Error;


fn aws_error_to_py(err: SdkError<ListObjectsV2Error>) -> PyErr {
    match &err {
        SdkError::ConstructionFailure(e) => PyRuntimeError::new_err(
            format!(
                "AWS request construction failed.\n\
                 This usually means AWS_REGION is missing or invalid.\n\
                 Details: {:#?}",
                e
            )
        ),

        SdkError::DispatchFailure(e) => PyRuntimeError::new_err(
            format!(
                "AWS request dispatch failed.\n\
                 Possible causes:\n\
                 - AWS_REGION not set\n\
                 - Network / TLS issue\n\
                 - Invalid endpoint\n\
                 Details: {:#?}",
                e
            )
        ),

        SdkError::TimeoutError(e) => PyRuntimeError::new_err(
            format!(
                "AWS request timed out while contacting S3.\n\
                 Details: {:#?}",
                e
            )
        ),

        SdkError::ResponseError(e) => PyRuntimeError::new_err(
            format!(
                "AWS S3 returned an error response.\n\
                 HTTP status: {:?}\n\
                 Raw response: {:#?}\n\
                 Check bucket name, region, and permissions.",
                e.raw().status(),
                e
            )
        ),

        _ => PyRuntimeError::new_err(format!(
            "Unhandled AWS SDK error:\n{:#?}",
            err
        )),
    }
}


async fn list_prefix(
    client: Client,
    bucket: String,
    prefix: String,
) -> (String, Vec<String>) {
    let mut keys = Vec::new();

    if let Ok(output) = client
        .list_objects_v2()
        .bucket(bucket)
        .prefix(&prefix)
        .send()
        .await
    {
        for obj in output.contents() {
            if let Some(key) = obj.key() {
                keys.push(key.to_string());
            }
        }
    }

    (prefix, keys)
}


#[pyfunction]
fn list_bucket_parallel(
    bucket: String,
    prefix: Option<String>,
) -> PyResult<HashMap<String, Vec<String>>> {
    let rt = Runtime::new().unwrap();

    rt.block_on(async {
        let config = aws_config::load_defaults(
            aws_config::BehaviorVersion::latest(),
        )
        .await;

        let client = Client::new(&config);

        // === LIST PREFIXES ===
        let mut request = client
            .list_objects_v2()
            .bucket(&bucket)
            .delimiter("/");

        if let Some(ref p) = prefix {
            request = request.prefix(p);
        }

        let resp = request
            .send()
            .await
            .map_err(aws_error_to_py)?;

        let prefixes: Vec<String> = resp
            .common_prefixes()
            .iter()
            .filter_map(|cp| cp.prefix().map(|s| s.to_string()))
            .collect();

        // === PARALLEL LIST PER PREFIX ===
        let mut handles = Vec::new();

        for p in prefixes {
            let client_clone = client.clone();
            let bucket_clone = bucket.clone();

            handles.push(tokio::spawn(async move {
                list_prefix(client_clone, bucket_clone, p).await
            }));
        }

        let mut result = HashMap::new();

        for handle in handles {
            let (p, keys) = handle
                .await
                .map_err(|e| {
                    PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(
                        e.to_string(),
                    )
                })?;
            result.insert(p, keys);
        }

        Ok(result)
    })
}


#[pymodule]
fn nautilus(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(list_bucket_parallel, m)?)?;
    Ok(())
}
