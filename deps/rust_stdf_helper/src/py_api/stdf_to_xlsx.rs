//
// stdf_to_xlsx.rs
//
// STDF to XLSX conversion.
//
// Author: noonchen - chennoon233@foxmail.com
// Created Date: Tue Sep 01 2026
// -----
// Last Modified: Tue Sep 01 2026
// Modified By: noonchen
// -----
// Copyright (c) 2022 noonchen
//

use crate::generic::error::StdfHelperError;
use crate::generic::helper::get_file_size;
use pyo3::exceptions::PyOSError;
use pyo3::intern;
use pyo3::prelude::*;
use pyo3::types::PyBool;
use rust_stdf::{stdf_file::*, stdf_record_type::*, StdfRecord};
use rust_xlsxwriter::{Workbook, Worksheet, XlsxError};
use std::collections::HashMap;

/// convert stdf to xlsx file
#[pyfunction]
#[pyo3(name = "stdf_to_xlsx")]
pub fn stdf_to_xlsx(
    py: Python,
    stdf_path: String,
    xlsx_path: String,
    progress_signal: Bound<'_, PyAny>,
    stop_flag: Bound<'_, PyAny>,
) -> PyResult<()> {
    // get file size
    let file_size = get_file_size(&stdf_path)?;
    if file_size == 0 {
        return Err(PyOSError::new_err("empty file detected"));
    }

    let is_valid_progress_signal = match progress_signal.getattr(intern!(py, "emit")) {
        Ok(p) => p.is_callable(),
        Err(_) => {
            println!("progress_signal does not have a method `emit`");
            false
        }
    };
    let is_valid_stop = match stop_flag.getattr(intern!(py, "stop")) {
        Ok(p) => p.is_instance_of::<PyBool>(),
        Err(_) => {
            println!("stop_flag does not have an bool attr `stop`");
            false
        }
    };

    let progress_signal: Py<PyAny> = progress_signal.into();
    let stop_flag: Py<PyAny> = stop_flag.into();

    let mut stop_flag_rust = false;
    let mut parse_progess = 0;

    py.detach(|| -> Result<(), StdfHelperError> {
        // create a xlsx
        let mut xlsx = Workbook::new();
        let bold_format = rust_xlsxwriter::Format::new().set_bold();
        let mut next_line_map = HashMap::with_capacity(40);
        let mut reader = match StdfReader::new(&stdf_path) {
            Ok(r) => r,
            Err(e) => {
                return Err(StdfHelperError {
                    msg: format!("Cannot parse this file:\n{}\n\nMessage:\n{}", &stdf_path, e),
                })
            }
        };
        for raw_rec in reader.get_rawdata_iter() {
            if stop_flag_rust {
                break;
            }
            let raw_rec = match raw_rec {
                Ok(raw) => raw,
                Err(e) => return Err(StdfHelperError { msg: e.to_string() }),
            };
            // file offset for calculating progress
            parse_progess = raw_rec.offset * 100 / file_size;
            let stdf_rec = StdfRecord::from(raw_rec);
            // use record name as hashmap key
            let rec_name = get_rec_name_from_code(stdf_rec.get_type());
            let field_names = get_fields_from_code(stdf_rec.get_type());
            // get sheet from workbook
            let sheet = match xlsx.worksheet_from_name(rec_name) {
                Ok(s) => s,
                Err(_) => {
                    // create new if not exist
                    let s = xlsx.add_worksheet();
                    s.set_name(rec_name)?;
                    // based on the record type, write the column header
                    for (col, field) in field_names.iter().enumerate() {
                        s.write_string_with_format(0, col as u16, *field, &bold_format)?;
                    }
                    s
                }
            };
            // get row + 1 for writing the new line
            let &mut row = next_line_map
                .entry(rec_name)
                .and_modify(|r| *r += 1)
                .or_insert(1);
            // serialize inner record, then write to sheet in field order
            let mut check_signal = false;
            let json = match stdf_rec {
                // rec type 15
                StdfRecord::PTR(r) => serde_json::to_value(&r)?,
                StdfRecord::MPR(r) => serde_json::to_value(&r)?,
                StdfRecord::FTR(r) => serde_json::to_value(&r)?,
                StdfRecord::STR(r) => serde_json::to_value(&r)?,
                // rec type 5
                StdfRecord::PIR(r) => serde_json::to_value(&r)?,
                StdfRecord::PRR(r) => {
                    // check stop signal and send progress if we encountered PRR
                    check_signal = true;
                    serde_json::to_value(&r)?
                }
                // rec type 2
                StdfRecord::WIR(r) => serde_json::to_value(&r)?,
                StdfRecord::WRR(r) => serde_json::to_value(&r)?,
                StdfRecord::WCR(r) => serde_json::to_value(&r)?,
                // rec type 50
                StdfRecord::GDR(r) => serde_json::to_value(&r)?,
                StdfRecord::DTR(r) => serde_json::to_value(&r)?,
                // rec type 10
                StdfRecord::TSR(r) => serde_json::to_value(&r)?,
                // rec type 1
                StdfRecord::MIR(r) => serde_json::to_value(&r)?,
                StdfRecord::MRR(r) => serde_json::to_value(&r)?,
                StdfRecord::PCR(r) => serde_json::to_value(&r)?,
                StdfRecord::HBR(r) => serde_json::to_value(&r)?,
                StdfRecord::SBR(r) => serde_json::to_value(&r)?,
                StdfRecord::PMR(r) => serde_json::to_value(&r)?,
                StdfRecord::PGR(r) => serde_json::to_value(&r)?,
                StdfRecord::PLR(r) => serde_json::to_value(&r)?,
                StdfRecord::RDR(r) => serde_json::to_value(&r)?,
                StdfRecord::SDR(r) => serde_json::to_value(&r)?,
                StdfRecord::PSR(r) => serde_json::to_value(&r)?,
                StdfRecord::NMR(r) => serde_json::to_value(&r)?,
                StdfRecord::CNR(r) => serde_json::to_value(&r)?,
                StdfRecord::SSR(r) => serde_json::to_value(&r)?,
                StdfRecord::CDR(r) => serde_json::to_value(&r)?,
                // rec type 0
                StdfRecord::FAR(r) => serde_json::to_value(&r)?,
                StdfRecord::ATR(r) => serde_json::to_value(&r)?,
                StdfRecord::VUR(r) => serde_json::to_value(&r)?,
                // rec type 20
                StdfRecord::BPS(r) => serde_json::to_value(&r)?,
                StdfRecord::EPS(r) => serde_json::to_value(&r)?,
                // rec type 180: Reserved
                // rec type 181: Reserved
                StdfRecord::ReservedRec(r) => serde_json::to_value(&r)?,
                StdfRecord::UnknownRec(h) => {
                    return Err(StdfHelperError {
                        msg: format!(
                            "Unknown record found:\ntyp: {}, sub: {}, len: {}",
                            h.typ,
                            h.sub,
                            h.raw_data.len()
                        ),
                    });
                }
            };
            write_json_to_sheet(json, field_names, sheet, row)?;

            if check_signal && (is_valid_progress_signal || is_valid_stop) {
                if let Err(e) = Python::attach(|py| -> PyResult<()> {
                    if is_valid_progress_signal {
                        progress_signal
                            .bind(py)
                            .call_method1(intern!(py, "emit"), (parse_progess,))?;
                    }
                    if is_valid_stop {
                        stop_flag_rust = stop_flag
                            .bind(py)
                            .getattr(intern!(py, "stop"))?
                            .extract::<bool>()?;
                    }
                    Ok(())
                }) {
                    return Err(StdfHelperError { msg: e.to_string() });
                }
            }
        }
        // save xlsx to path
        xlsx.save(std::path::Path::new(&xlsx_path))?;
        Ok(())
    })?;

    Ok(())
}
#[inline(always)]
pub fn get_fields_from_code(type_code: u64) -> &'static [&'static str] {
    use rust_stdf::stdf_record_type::*;
    match type_code {
        // rec type 15
        REC_PTR => rust_stdf::PTR::FIELD_NAMES_AS_ARRAY,
        REC_MPR => rust_stdf::MPR::FIELD_NAMES_AS_ARRAY,
        REC_FTR => rust_stdf::FTR::FIELD_NAMES_AS_ARRAY,
        REC_STR => rust_stdf::STR::FIELD_NAMES_AS_ARRAY,
        // rec type 5
        REC_PIR => rust_stdf::PIR::FIELD_NAMES_AS_ARRAY,
        REC_PRR => rust_stdf::PRR::FIELD_NAMES_AS_ARRAY,
        // rec type 2
        REC_WIR => rust_stdf::WIR::FIELD_NAMES_AS_ARRAY,
        REC_WRR => rust_stdf::WRR::FIELD_NAMES_AS_ARRAY,
        REC_WCR => rust_stdf::WCR::FIELD_NAMES_AS_ARRAY,
        // rec type 50
        REC_GDR => rust_stdf::GDR::FIELD_NAMES_AS_ARRAY,
        REC_DTR => rust_stdf::DTR::FIELD_NAMES_AS_ARRAY,
        // rec type 0
        REC_FAR => rust_stdf::FAR::FIELD_NAMES_AS_ARRAY,
        REC_ATR => rust_stdf::ATR::FIELD_NAMES_AS_ARRAY,
        REC_VUR => rust_stdf::VUR::FIELD_NAMES_AS_ARRAY,
        // rec type 1
        REC_MIR => rust_stdf::MIR::FIELD_NAMES_AS_ARRAY,
        REC_MRR => rust_stdf::MRR::FIELD_NAMES_AS_ARRAY,
        REC_PCR => rust_stdf::PCR::FIELD_NAMES_AS_ARRAY,
        REC_HBR => rust_stdf::HBR::FIELD_NAMES_AS_ARRAY,
        REC_SBR => rust_stdf::SBR::FIELD_NAMES_AS_ARRAY,
        REC_PMR => rust_stdf::PMR::FIELD_NAMES_AS_ARRAY,
        REC_PGR => rust_stdf::PGR::FIELD_NAMES_AS_ARRAY,
        REC_PLR => rust_stdf::PLR::FIELD_NAMES_AS_ARRAY,
        REC_RDR => rust_stdf::RDR::FIELD_NAMES_AS_ARRAY,
        REC_SDR => rust_stdf::SDR::FIELD_NAMES_AS_ARRAY,
        REC_PSR => rust_stdf::PSR::FIELD_NAMES_AS_ARRAY,
        REC_NMR => rust_stdf::NMR::FIELD_NAMES_AS_ARRAY,
        REC_CNR => rust_stdf::CNR::FIELD_NAMES_AS_ARRAY,
        REC_SSR => rust_stdf::SSR::FIELD_NAMES_AS_ARRAY,
        REC_CDR => rust_stdf::CDR::FIELD_NAMES_AS_ARRAY,
        // rec type 10
        REC_TSR => rust_stdf::TSR::FIELD_NAMES_AS_ARRAY,
        // rec type 20
        REC_BPS => rust_stdf::BPS::FIELD_NAMES_AS_ARRAY,
        REC_EPS => rust_stdf::EPS::FIELD_NAMES_AS_ARRAY,
        // rec type 180: Reserved
        // rec type 181: Reserved
        REC_RESERVE => rust_stdf::ReservedRec::FIELD_NAMES_AS_ARRAY,
        // not matched
        _ => &[""; 0],
    }
}

#[inline(always)]
pub fn write_json_to_sheet(
    json: serde_json::Value,
    field_names: &[&str],
    sheet: &mut Worksheet,
    row: u32,
) -> Result<(), XlsxError> {
    for (col, &field) in field_names.iter().enumerate() {
        let col = col as u16;
        let v = &json[field];
        match v {
            serde_json::Value::Number(n) => {
                sheet.write_number(row, col, n.as_f64().unwrap_or(f64::NAN))?
            }
            serde_json::Value::Null => sheet.write_string(row, col, "N/A")?,
            serde_json::Value::String(s) => sheet.write_string(row, col, s)?,
            _ => sheet.write_string(row, col, v.to_string())?,
        };
    }
    Ok(())
}
