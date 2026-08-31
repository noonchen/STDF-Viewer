//
// read_mir.rs
//
// Read MIR info from a STDF file
//
// Author: noonchen - chennoon233@foxmail.com
// Created Date: Tue Sep 01 2026
// -----
// Last Modified: Tue Sep 01 2026
// Modified By: noonchen
// -----
// Copyright (c) 2022 noonchen
//

use crate::generic::helper::u32_to_localtime;
use pyo3::exceptions::{PyLookupError, PyOSError};
use pyo3::prelude::*;
use pyo3::types::PyDict;
use rust_stdf::{stdf_file::*, StdfRecordView};
/// read MIR records from a STDF file
/// exit if found
#[pyfunction]
#[pyo3(name = "read_MIR")]
pub fn read_mir<'py>(py: Python<'py>, fpath: String) -> PyResult<Bound<'py, PyDict>> {
    use rust_stdf::MIR;
    use serde_json::{self, Value};

    let dict = PyDict::new(py);
    let mut reader = match StdfReader::new(&fpath) {
        Ok(r) => r,
        Err(e) => {
            return Err(PyOSError::new_err(format!(
                "Cannot parse this file:\n{}\n\nMessage:\n{}",
                &fpath, e
            )))
        }
    };

    let mut view_it = reader.get_rawdata_view_iter();
    while let Some(v) = view_it.next() {
        let raw_view = match v {
            Ok(r) => r,
            Err(e) => {
                return Err(PyOSError::new_err(format!(
                    "Error when reading MIR record of this file:\n{}\n\n{}",
                    &fpath, e
                )))
            }
        };
        if let StdfRecordView::MIR(mir_view) = (&raw_view).into() {
            let mir_rec = mir_view.to_owned();
            if let Ok(mir_json) = serde_json::to_value(&mir_rec) {
                // iter thru MIR fields
                for &field in MIR::FIELD_NAMES_AS_ARRAY {
                    let v = &mir_json[field];
                    match v {
                        Value::String(s) => {
                            if !s.is_empty() && s != " " {
                                dict.set_item(field, s)?
                            }
                        }
                        Value::Number(n) => {
                            if field == "SETUP_T" || field == "START_T" {
                                let timestamp = u32_to_localtime(n.as_u64().unwrap() as u32);
                                dict.set_item(field, timestamp)?
                            } else {
                                dict.set_item(field, n.as_i64())?
                            }
                        }
                        _ => {}
                    };
                }

                return Ok(dict);
            }
        }
    }

    Err(PyLookupError::new_err(format!(
        "MIR Record is not found in this file:\n{}\n",
        &fpath
    )))
}
