use pyo3::prelude::*;

mod database;
mod generic;
mod py_api;
mod stdf;
pub use generic::error::StdfHelperError;

/// A Python module implemented in Rust.
#[pymodule]
fn rust_stdf_helper(py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    py_api::register(py, m)
}
