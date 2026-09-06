//
// mod.rs
//
// Python module registration.
//
// Author: noonchen - chennoon233@foxmail.com
// Created Date: Tue Sep 01 2026
// -----
// Last Modified: Tue Sep 01 2026
// Modified By: noonchen
// -----
// Copyright (c) 2022 noonchen
//

pub mod analyze_stdf;
pub mod fetcher;
pub mod generate_database;
pub mod get_icon_src;
pub mod read_mir;
pub mod statistics;
pub mod stdf_to_xlsx;

use crate::stdf::record_tracker::TestIDType;
use pyo3::prelude::*;

pub fn register(py: Python, module: &Bound<'_, PyModule>) -> PyResult<()> {
    let test_id_type = PyModule::new(py, "TestIDType")?;
    test_id_type.add("TestNumberAndName", TestIDType::TestNumberAndName)?;
    test_id_type.add("TestNumberOnly", TestIDType::TestNumberOnly)?;

    module.add_submodule(&test_id_type)?;
    module.add_function(wrap_pyfunction!(analyze_stdf::analyze_stdf, module)?)?;
    module.add_function(wrap_pyfunction!(
        generate_database::generate_database,
        module
    )?)?;
    module.add_function(wrap_pyfunction!(read_mir::read_mir, module)?)?;
    module.add_function(wrap_pyfunction!(get_icon_src::get_icon_src, module)?)?;
    module.add_function(wrap_pyfunction!(stdf_to_xlsx::stdf_to_xlsx, module)?)?;
    module.add_function(wrap_pyfunction!(statistics::norm_cdf, module)?)?;
    module.add_function(wrap_pyfunction!(statistics::empirical_cdf, module)?)?;
    module.add_function(wrap_pyfunction!(statistics::norm_ppf, module)?)?;
    module.add_class::<fetcher::PyDataFetcher>()?;

    Ok(())
}
