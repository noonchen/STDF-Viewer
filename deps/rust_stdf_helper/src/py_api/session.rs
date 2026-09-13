//
// session.rs
//
// Python bindings for session database validation and saving.
//
// Author: noonchen - chennoon233@foxmail.com
// Created Date: Tue Sep 01 2026
// -----
// Last Modified: Tue Sep 01 2026
// Modified By: noonchen
// -----
// Copyright (c) 2026 noonchen
//

use crate::database::session::{
    save_session as run_save_session, validate_session as run_validate,
};
use pyo3::prelude::*;

/// Validate a session database. Returns `(is_valid, message)`, where `message`
/// is empty when the database is valid.
#[pyfunction]
pub fn validate_session(path: &str) -> PyResult<(bool, String)> {
    match run_validate(path) {
        Ok(check) => Ok((check.valid, check.message)),
        Err(e) => Ok((false, e.msg)),
    }
}

/// Save the session database to `dst` with SQLite's online backup API: the
/// copy is consistent even while the database is open and being indexed.
#[pyfunction]
pub fn save_session(py: Python<'_>, src: &str, dst: &str) -> PyResult<()> {
    py.detach(|| run_save_session(src, dst))?;
    Ok(())
}
