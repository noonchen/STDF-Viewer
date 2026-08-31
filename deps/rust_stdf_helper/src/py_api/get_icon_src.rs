//
// get_icon_src.rs
//
// Provide icon source data for UI display
//
// Author: noonchen - chennoon233@foxmail.com
// Created Date: Tue Sep 01 2026
// -----
// Last Modified: Tue Sep 01 2026
// Modified By: noonchen
// -----
// Copyright (c) 2022 noonchen
//

use crate::generic::resources::*;
use flate2::read::ZlibDecoder;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::PyBytes;
use std::io::Read;

/// read data from python file object
#[pyfunction]
#[pyo3(name = "get_icon_src")]
pub fn get_icon_src<'py>(py: Python<'py>, icon_name: String) -> PyResult<Bound<'py, PyBytes>> {
    let icon_name = icon_name.as_str();
    let raw = match icon_name {
        "About" => ABOUT,
        "AddFont" => ADDFONT,
        "App" => APP,
        "ColorPalette" => COLORPALETTE,
        "Convert" => CONVERT,
        "Export" => EXPORT,
        "FailMarker" => FAILMARKER,
        "LoadSession" => LOADSESSION,
        "Merge" => MERGE,
        "Open" => OPEN,
        "SaveSession" => SAVESESSION,
        "Settings" => SETTINGS,
        "Tools" => TOOLS,
        "tab_bin" => TAB_BIN,
        "tab_correlation" => TAB_CORRELATION,
        "tab_hist" => TAB_HIST,
        "tab_info" => TAB_INFO,
        "tab_ppqq" => TAB_PPQQ,
        "tab_trend" => TAB_TREND,
        "tab_wafer" => TAB_WAFER,
        _ => APP,
    };
    let mut z = ZlibDecoder::new(raw);
    let mut uncompressed_data: Vec<u8> = Vec::with_capacity(2048);
    if let Err(e) = z.read_to_end(&mut uncompressed_data) {
        return Err(PyValueError::new_err(e.to_string()));
    }
    Ok(PyBytes::new(py, &uncompressed_data))
}
