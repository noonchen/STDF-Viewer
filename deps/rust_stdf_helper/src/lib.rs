use numpy::ndarray::{Array1, Array2, Zip};
use numpy::{IntoPyArray, PyReadonlyArray1, PyReadonlyArray2};
use pyo3::{
    exceptions::{PyException, PyOSError},
    prelude::*,
    types::PyDict,
};
use rusqlite::{Connection, Error};
use rust_stdf::{stdf_file::*, stdf_record_type::*, ByteOrder, StdfRecord};
use std::convert::From;
use std::sync::mpsc;
use std::thread;

mod database_context;
mod rust_functions;
use database_context::DataBaseCtx;
use rust_functions::{process_incoming_record, RecordTracker};

// impl std::convert::From<rusqlite::Error> for PyErr {
//     fn from(err: Error) -> Self {
//         pyo3::exceptions::PyException::new_err(err.to_string())
//     }
// }

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

impl From<StdfHelperError> for PyErr {
    fn from(err: StdfHelperError) -> Self {
        PyException::new_err(err.msg)
    }
}

/// Analyze record types in a STDF file
#[pyfunction]
#[pyo3(name = "analyzeSTDF")]
fn analyze_stdf_file(filepath: &str) -> PyResult<String> {
    let mut reader = match StdfReader::new(filepath) {
        Ok(r) => r,
        Err(e) => return Err(PyOSError::new_err(e.to_string())),
    };

    let mut tmp_log;
    let mut result_log = String::new();
    let mut total_record: u64 = 0;
    let mut previous_rec_type: u64 = 0;
    let mut dup_cnt = 0;
    let mut dut_cnt = 0;
    let mut wafer_cnt = 0;

    for rec in reader.get_record_iter() {
        total_record += 1;
        let rec_code = rec.get_type();
        let rec_name = get_rec_name_from_code(rec_code);

        if rec_code == REC_INVALID {
            result_log += "Invalid STDF V4 Record Detected\n";
            break;
        }

        if rec.is_type(REC_PIR | REC_WIR | REC_PRR | REC_WRR) {
            if dup_cnt != 0 && previous_rec_type != 0 {
                // flush previous log
                tmp_log = format!(
                    "{} × {}\n",
                    get_rec_name_from_code(previous_rec_type),
                    dup_cnt
                );
                result_log += &tmp_log;
            }

            match rec {
                StdfRecord::PIR(pir_rec) => {
                    dut_cnt += 1;
                    tmp_log = format!(
                        "[{}] {} (HEAD: {}, SITE: {})\n",
                        dut_cnt, rec_name, pir_rec.head_num, pir_rec.site_num
                    );
                    result_log += &tmp_log;
                }
                StdfRecord::WIR(wir_rec) => {
                    wafer_cnt += 1;
                    tmp_log = format!("{} (HEAD: {})\n", rec_name, wir_rec.head_num);
                    result_log += &tmp_log;
                }
                StdfRecord::PRR(prr_rec) => {
                    tmp_log = format!(
                        "{} (HEAD: {}, SITE: {})\n",
                        rec_name, prr_rec.head_num, prr_rec.site_num
                    );
                    result_log += &tmp_log;
                }
                StdfRecord::WRR(wrr_rec) => {
                    tmp_log = format!("{} (HEAD: {})\n", rec_name, wrr_rec.head_num);
                    result_log += &tmp_log;
                }
                _ => {}
            }
            // reset preheader to 0, in order to print every PXR WXR
            previous_rec_type = 0;
            dup_cnt = 0;
        } else {
            // other record types
            if previous_rec_type == rec_code {
                dup_cnt += 1;
            } else {
                if previous_rec_type != 0 {
                    // print previous record
                    tmp_log = format!(
                        "{} × {}\n",
                        get_rec_name_from_code(previous_rec_type),
                        dup_cnt
                    );
                    result_log += &tmp_log;
                }
                previous_rec_type = rec_code;
                dup_cnt = 1;
            }
        }
    }

    // print last record
    if dup_cnt != 0 && previous_rec_type != 0 {
        // flush previous log
        tmp_log = format!(
            "{} × {}\n",
            get_rec_name_from_code(previous_rec_type),
            dup_cnt
        );
        result_log += &tmp_log;
    }

    tmp_log = format!(
        "\nTotal wafers: {}\nTotal duts/dies: {}\nTotal Records: {}\nAnalysis Finished",
        wafer_cnt, dut_cnt, total_record
    );
    result_log += &tmp_log;
    Ok(result_log)
}

/// get PTR/FTR results and flags from raw bytes
#[pyfunction]
#[pyo3(name = "parse_PTR_FTR_rawList")]
fn parse_ptr_ftr_from_raw<'py>(
    py: Python<'py>,
    is_ptr: bool,
    is_le: bool,
    raw: PyReadonlyArray2<u8>,
    lens: PyReadonlyArray1<i32>,
) -> PyResult<&'py PyDict> {
    let endian = if is_le {
        ByteOrder::LittleEndian
    } else {
        ByteOrder::BigEndian
    };
    let raw = raw.as_array();
    let lens = lens.as_array();
    let rec_cnt = lens.dim();
    // create Array for storing results
    let mut data_list = Array1::from_elem(rec_cnt, f32::NAN);
    let mut flag_list = Array1::from_elem(rec_cnt, -1i32);

    fn inner_parse(
        is_ptr: bool,
        order: &ByteOrder,
        raw_data: &[u8],
        &length: &i32,
        result: &mut f32,
        flag: &mut i32,
    ) {
        if length < 0 {
            // represent an invalid raw data
            // do nothing, since the default data is invalid
            return;
        }

        let length = length as usize;
        let raw_data = &raw_data[..length];
        if is_ptr {
            // parse PTR
            let mut ptr_rec = rust_stdf::PTR::new();
            ptr_rec.read_from_bytes(raw_data, order);

            *result = if f32::is_finite(ptr_rec.result) {
                ptr_rec.result
            } else if f32::is_sign_positive(ptr_rec.result) {
                // +inf, replace with max f32
                f32::MAX
            } else {
                // -inf, replace with min f32
                f32::MIN
            };
            *flag = ptr_rec.test_flg[0].into();
        } else {
            // parse FTR
            let mut ftr_rec = rust_stdf::FTR::new();
            ftr_rec.read_from_bytes(raw_data, order);
            *result = ftr_rec.test_flg[0].into();
            *flag = ftr_rec.test_flg[0].into();
        };
    }
    // parallel parse data
    Zip::from(raw.rows())
        .and(&lens)
        .and(&mut data_list)
        .and(&mut flag_list)
        .par_for_each(|r, l, d, f| {
            inner_parse(
                is_ptr,
                &endian,
                r.to_slice().expect("cannot get slice from numpy ndarray"),
                l,
                d,
                f,
            )
        });
    let data_list = data_list.into_pyarray(py);
    let flag_list = flag_list.into_pyarray(py);
    let dict = PyDict::new(py);
    dict.set_item("dataList", data_list)?;
    dict.set_item("flagList", flag_list)?;
    Ok(dict)
}

/// get MPR results, states and flags from raw bytes
#[pyfunction]
#[pyo3(name = "parse_MPR_rawList")]
fn parse_mpr_from_raw<'py>(
    py: Python<'py>,
    is_le: bool,
    pin_cnt: u16,
    rslt_cnt: u16,
    raw: PyReadonlyArray2<u8>,
    lens: PyReadonlyArray1<i32>,
) -> PyResult<&'py PyDict> {
    let endian = if is_le {
        ByteOrder::LittleEndian
    } else {
        ByteOrder::BigEndian
    };
    let rslt_cnt = rslt_cnt as usize;
    let pin_cnt = pin_cnt as usize;
    let raw = raw.as_array();
    let lens = lens.as_array();
    let rec_cnt = lens.dim();
    // create Array for storing results
    // contiguous is required in order to get slice from ndarray,
    // must iter by row...
    // row: dutIndex, col: pin
    let mut data_list = Array2::from_elem((rec_cnt, rslt_cnt), f32::NAN);
    let mut state_list = Array2::from_elem((rec_cnt, pin_cnt), 16i32);
    let mut flag_list = Array1::from_elem(rec_cnt, -1i32);

    #[allow(clippy::too_many_arguments)]
    fn inner_parse(
        order: &ByteOrder,
        pin_cnt: usize,
        rslt_cnt: usize,
        raw_data: &[u8],
        &length: &i32,
        result_slice: &mut [f32],
        state_slice: &mut [i32],
        flag: &mut i32,
    ) {
        if length < 0 {
            // represent an invalid raw data
            // do nothing, since the default data is invalid
            return;
        }

        let length = length as usize;
        let raw_data = &raw_data[..length];
        // parse MPR
        let mut mpr_rec = rust_stdf::MPR::new();
        mpr_rec.read_from_bytes(raw_data, order);
        // update result
        for (&rslt, ind) in mpr_rec.rtn_rslt.iter().zip(0..rslt_cnt) {
            result_slice[ind] = if f32::is_finite(rslt) {
                rslt
            } else if f32::is_sign_positive(rslt) {
                // +inf, replace with max f32
                f32::MAX
            } else {
                // -inf, replace with min f32
                f32::MIN
            };
        }
        // update state
        for (&state, ind) in mpr_rec.rtn_stat.iter().zip(0..pin_cnt) {
            state_slice[ind] = state as i32;
        }
        *flag = mpr_rec.test_flg[0].into();
    }

    // parallel parse data
    Zip::from(raw.rows())
        .and(&lens)
        .and(data_list.rows_mut())
        .and(state_list.rows_mut())
        .and(&mut flag_list)
        .par_for_each(|r, l, d, s, f| {
            inner_parse(
                &endian,
                pin_cnt,
                rslt_cnt,
                r.to_slice().expect("cannot get slice from numpy ndarray"),
                l,
                d.into_slice().expect("ndarray is not contiguous"),
                s.into_slice().expect("ndarray is not contiguous"),
                f,
            )
        });
    // previous order: row: dutIndex, col: pin
    // python expected: row: pin, col: dutIndex
    let data_list = data_list.reversed_axes().into_pyarray(py);
    let state_list = state_list.reversed_axes().into_pyarray(py);
    let flag_list = flag_list.into_pyarray(py);
    let dict = PyDict::new(py);
    dict.set_item("dataList", data_list)?;
    dict.set_item("statesList", state_list)?;
    dict.set_item("flagList", flag_list)?;
    Ok(dict)
}

/// create sqlite3 database for given stdf files
#[pyfunction]
#[pyo3(name = "generate_database")]
fn generate_database(dbpath: String, stdf_paths: Vec<String>) -> PyResult<()> {
    // do nothing if no file
    let num_files = stdf_paths.len();
    if num_files == 0 {
        return Ok(());
    }
    // initiate sqlite3 database
    let conn = match Connection::open(&dbpath) {
        Ok(conn) => conn,
        Err(e) => return Err(PyOSError::new_err(e.to_string())),
    };
    let mut db_ctx = DataBaseCtx::new(&conn)?;

    // prepare channel for multithreading communication
    let (tx, rx) = mpsc::channel();
    let mut thread_handles = vec![];
    let mut thread_txes = Vec::with_capacity(num_files);

    // clone {num_files-1} sender
    (0..num_files - 1)
        .map(|_| thread_txes.push(tx.clone()))
        .count();
    // push the last tx into vector
    thread_txes.push(tx);

    // one thread per file, use raw data record because we need to store offset and such.
    for (fid, (fpath, thread_tx)) in stdf_paths
        .into_iter()
        .zip(thread_txes.into_iter())
        .enumerate()
    {
        let handle = thread::spawn(move || {
            let mut stdf_reader = StdfReader::new(fpath).unwrap();
            for raw_rec in stdf_reader.get_rawdata_iter() {
                thread_tx.send((fid, raw_rec)).unwrap();
            }
        });
        thread_handles.push(handle);
    }

    let mut record_tracker = RecordTracker::new();
    // process and write database in main thread
    for (fid, raw_rec) in rx {
        let rec_info = (
            fid,
            raw_rec.byte_order,
            raw_rec.offset,
            raw_rec.raw_data.len(),
            StdfRecord::from(raw_rec),
        );
        process_incoming_record(&mut db_ctx, &mut record_tracker, rec_info)?;
    }

    // join threads
    for handle in thread_handles {
        handle.join().unwrap();
    }
    // finalize database
    db_ctx.finalize()?;
    if let Err((_, err)) = conn.close() {
        return Err(StdfHelperError::from(err))?;
    }
    Ok(())
}

/// A Python module implemented in Rust.
#[pymodule]
fn rust_stdf_helper(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(analyze_stdf_file, m)?)?;
    m.add_function(wrap_pyfunction!(parse_ptr_ftr_from_raw, m)?)?;
    m.add_function(wrap_pyfunction!(parse_mpr_from_raw, m)?)?;
    m.add_function(wrap_pyfunction!(generate_database, m)?)?;
    Ok(())
}
