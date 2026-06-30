//////////////////////////////////////////////////////
// CORE LIB: Nautilus Orchestration Layer
//////////////////////////////////////////////////////

// Re-export crates
pub use storage::Storage;
pub use dataset::Dataset;
//pub use cv::CVPipeline;
//pub use experiment::Experiment;
//pub use visualization::Visualization;

//////////////////////////////////////////////////////
// OPTIONAL PRELUDE
//////////////////////////////////////////////////////

pub mod prelude {
    pub use crate::Storage;
    pub use crate::Dataset;
//    pub use crate::CVPipeline;
//    pub use crate::Experiment;
//    pub use crate::Visualization;
}

//////////////////////////////////////////////////////
// PYTHON BINDINGS (PyO3)
//////////////////////////////////////////////////////

use pyo3::prelude::*;

/// Main Nautilus Python module
#[pymodule]
fn nautilus(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Storage
    m.add_class::<Storage>()?;

    // Dataset
    m.add_class::<Dataset>()?;

    // CV
//    m.add_class::<CVPipeline>()?;

    // Experiment
//    m.add_class::<Experiment>()?;

    // Visualization
//    m.add_class::<Visualization>()?;

    Ok(())
}

//////////////////////////////////////////////////////
// VERSION / METADATA
//////////////////////////////////////////////////////

pub const VERSION: &str = env!("CARGO_PKG_VERSION");
