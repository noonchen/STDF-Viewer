//
// error.rs
//
// StdfHelperError and conversions
//
// Author: noonchen - chennoon233@foxmail.com
// Created Date: Tue Sep 01 2026
// -----
// Last Modified: Tue Sep 01 2026
// Modified By: noonchen
// -----
// Copyright (c) 2022 noonchen
//

use pyo3::exceptions::PyException;
use pyo3::prelude::*;
use rusqlite::Error;
use rust_xlsxwriter::XlsxError;

#[derive(Debug)]
pub struct StdfHelperError {
    pub msg: String,
}

impl From<Error> for StdfHelperError {
    fn from(err: Error) -> Self {
        StdfHelperError {
            msg: err.to_string(),
        }
    }
}

impl From<std::io::Error> for StdfHelperError {
    fn from(err: std::io::Error) -> Self {
        StdfHelperError {
            msg: err.to_string(),
        }
    }
}

impl From<XlsxError> for StdfHelperError {
    fn from(err: XlsxError) -> Self {
        StdfHelperError {
            msg: err.to_string(),
        }
    }
}

impl From<serde_json::Error> for StdfHelperError {
    fn from(err: serde_json::Error) -> Self {
        StdfHelperError {
            msg: err.to_string(),
        }
    }
}

impl From<StdfHelperError> for PyErr {
    fn from(err: StdfHelperError) -> Self {
        PyException::new_err(err.msg)
    }
}
