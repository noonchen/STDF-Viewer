//
// read_header.rs
//
// Read the STDF initial-sequence metadata (FAR/ATR/SDR + first WIR).
//
use crate::generic::helper::u32_to_localtime;
use pyo3::exceptions::PyOSError;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use rust_stdf::{stdf_file::*, ByteOrder, StdfRecordView};

/// Read metadata that is available near the beginning of an STDF file.
///
/// Returns FAR/ATR/SDR fields and the first WIR (if any). This is a bounded
/// header scan: it stops at the first DUT-level record (PIR/PTR/MPR/FTR/PRR)
/// or after the first WIR.
#[pyfunction(name = "read_header_extra")]
pub fn read_header_extra<'py>(py: Python<'py>, fpath: String) -> PyResult<Bound<'py, PyDict>> {
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

    let atr_list = PyList::empty(py);
    let sdr_list = PyList::empty(py);
    let wir_list = PyList::empty(py);
    let mut records = 0usize;
    let mut view_it = reader.get_rawdata_view_iter();

    while let Some(v) = view_it.next() {
        records += 1;
        if records > 8192 {
            break;
        }
        let raw_view = match v {
            Ok(r) => r,
            Err(_) => break,
        };
        match (&raw_view).into() {
            StdfRecordView::FAR(far) => {
                dict.set_item(
                    "BYTE_ORDER",
                    if raw_view.byte_order == ByteOrder::LittleEndian {
                        "Little endian"
                    } else {
                        "Big endian"
                    },
                )?;
                dict.set_item("STDF_VER", far.stdf_ver())?;
            }
            StdfRecordView::ATR(atr) => {
                atr_list.append(format!(
                    "Time: {}\nCMD: {}",
                    u32_to_localtime(atr.mod_tim()),
                    atr.cmd_line().as_str()
                ))?;
            }
            StdfRecordView::SDR(sdr) => {
                let d = PyDict::new(py);
                d.set_item("HEAD_NUM", sdr.head_num())?;
                d.set_item("SITE_GRP", sdr.site_grp())?;
                d.set_item("SITE_CNT", sdr.site_cnt())?;
                let sites: Vec<u16> = sdr.site_num().into_iter().map(|s| s as u16).collect();
                d.set_item("SITES", sites)?;
                for (key, value) in [
                    ("HAND_TYP", sdr.hand_typ().as_str()),
                    ("HAND_ID", sdr.hand_id().as_str()),
                    ("CARD_TYP", sdr.card_typ().as_str()),
                    ("CARD_ID", sdr.card_id().as_str()),
                ] {
                    if !value.is_empty() {
                        d.set_item(key, value)?;
                    }
                }
                sdr_list.append(d)?;
            }
            StdfRecordView::WIR(wir) => {
                let d = PyDict::new(py);
                d.set_item("HEAD_NUM", wir.head_num())?;
                d.set_item("SITE_GRP", wir.site_grp())?;
                d.set_item("START_T", u32_to_localtime(wir.start_t()))?;
                d.set_item("WAFER_ID", wir.wafer_id().as_str())?;
                wir_list.append(d)?;
                // WIR appears right before the wafer's DUT records; enough.
                break;
            }
            StdfRecordView::PIR(_)
            | StdfRecordView::PTR(_)
            | StdfRecordView::MPR(_)
            | StdfRecordView::FTR(_)
            | StdfRecordView::PRR(_) => break,
            _ => {}
        }
    }

    dict.set_item("ATR", atr_list)?;
    dict.set_item("SDR", sdr_list)?;
    dict.set_item("WIR", wir_list)?;
    Ok(dict)
}
