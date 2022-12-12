// use numpy::ndarray::{Array1, Array2, Zip};
// use numpy::{IntoPyArray, PyArray2, PyReadonlyArray1, PyReadonlyArray2};
use pyo3::exceptions::PyValueError;
use pyo3::types::PyBytes;
use pyo3::{
    exceptions::{PyException, PyLookupError, PyOSError},
    intern,
    prelude::*,
    types::{PyBool, PyDict},
};
use rusqlite::{Connection, Error};
use rust_stdf::{stdf_file::*, stdf_record_type::*, StdfRecord};
use rust_xlsxwriter::{Workbook, XlsxError};
use std::collections::HashMap;
use std::convert::From;
use std::sync::atomic::{AtomicBool, AtomicU16, Ordering};
use std::sync::{mpsc, Arc};
use std::{thread, time};

mod database_context;
mod resources;
mod rust_functions;
use database_context::DataBaseCtx;
use rust_functions::{
    get_fields_from_code, get_file_size, process_incoming_record, process_summary_data,
    write_json_to_sheet, RecordTracker,
};

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

/// Analyze record types in a STDF file
#[pyfunction]
#[pyo3(name = "analyzeSTDF")]
fn analyze_stdf_file(
    py: Python,
    filepath: &str,
    data_signal: &PyAny,
    progress_signal: &PyAny,
    stop_flag: &PyAny,
) -> PyResult<()> {
    // get file size
    let file_size = get_file_size(filepath)?;
    if file_size == 0 {
        return Err(PyOSError::new_err("empty file detected"));
    }

    let data_signal: Py<PyAny> = data_signal.into();
    let progress_signal: Py<PyAny> = progress_signal.into();
    let stop_flag: Py<PyAny> = stop_flag.into();
    //
    let is_valid_data_signal = match data_signal.getattr(py, intern!(py, "emit")) {
        Ok(p) => p.as_ref(py).is_callable(),
        Err(_) => {
            println!("data_signal does not have a method `emit`");
            false
        }
    };
    let is_valid_progress_signal = match progress_signal.getattr(py, intern!(py, "emit")) {
        Ok(p) => p.as_ref(py).is_callable(),
        Err(_) => {
            println!("progress_signal does not have a method `emit`");
            false
        }
    };
    let is_valid_stop = match stop_flag.getattr(py, intern!(py, "stop")) {
        Ok(p) => p.as_ref(py).is_instance_of::<PyBool>()?,
        Err(_) => {
            println!("stop_flag does not have an bool attr `stop`");
            false
        }
    };

    let mut stop_flag_rust = false;
    // offset / file_size * 100
    let mut parse_progess = 0;

    let mut result_log = String::with_capacity(512);
    let mut total_record: u64 = 0;
    let mut previous_rec_type: u64 = 0;
    let mut dup_cnt = 0;
    let mut dut_cnt = 0;
    let mut wafer_cnt = 0;

    py.allow_threads(|| {
        let mut reader = match StdfReader::new(filepath) {
            Ok(r) => r,
            Err(e) => return Err(PyOSError::new_err(e.to_string())),
        };

        for rec in reader.get_rawdata_iter() {
            if stop_flag_rust {
                break;
            }

            let rec = match rec {
                Ok(r) => r,
                Err(e) => return Err(PyException::new_err(e.to_string())),
            };
            total_record += 1;
            let rec_code = rec.header.get_type();
            let rec_name = get_rec_name_from_code(rec_code);

            if rec_code == REC_INVALID {
                result_log += &format!(
                    "Invalid STDF V4 Record Detected, len:{}, typ: {}, sub: {}\n",
                    rec.header.len, rec.header.typ, rec.header.sub
                );
                break;
            }

            if rec.is_type(REC_PIR | REC_WIR | REC_PRR | REC_WRR) {
                if dup_cnt != 0 && previous_rec_type != 0 {
                    // flush previous record info to result_log
                    result_log += &format!(
                        "{} × {}\n",
                        get_rec_name_from_code(previous_rec_type),
                        dup_cnt
                    );
                }

                parse_progess = rec.offset * 100 / file_size;
                let parsed_rec: StdfRecord = rec.into();
                match parsed_rec {
                    StdfRecord::PIR(pir_rec) => {
                        dut_cnt += 1;
                        result_log += &format!(
                            "[{}] {} (HEAD: {}, SITE: {})\n",
                            dut_cnt, rec_name, pir_rec.head_num, pir_rec.site_num
                        );
                    }
                    StdfRecord::WIR(wir_rec) => {
                        wafer_cnt += 1;
                        result_log += &format!("{} (HEAD: {})\n", rec_name, wir_rec.head_num);
                    }
                    StdfRecord::PRR(prr_rec) => {
                        result_log += &format!(
                            "{} (HEAD: {}, SITE: {})\n",
                            rec_name, prr_rec.head_num, prr_rec.site_num
                        );
                        // send or print result_log at PRR
                        // avoid result_log takes up too much memory...
                        // println!("{}", result_log);
                        // send via qt signal..
                        if is_valid_data_signal || is_valid_stop {
                            Python::with_gil(|py| -> PyResult<()> {
                                if is_valid_data_signal {
                                    data_signal.call_method1(
                                        py,
                                        intern!(py, "emit"),
                                        (result_log,),
                                    )?;
                                }
                                if is_valid_progress_signal {
                                    progress_signal.call_method1(
                                        py,
                                        intern!(py, "emit"),
                                        (parse_progess,),
                                    )?;
                                }
                                if is_valid_stop {
                                    stop_flag_rust = stop_flag
                                        .getattr(py, intern!(py, "stop"))?
                                        .extract::<bool>(py)?;
                                }
                                Ok(())
                            })?;
                        }
                        // reset to default
                        result_log = String::with_capacity(512);
                    }
                    StdfRecord::WRR(wrr_rec) => {
                        result_log += &format!("{} (HEAD: {})\n", rec_name, wrr_rec.head_num);
                    }
                    _ => { /* impossible case */ }
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
                        // flush previous record
                        result_log += &format!(
                            "{} × {}\n",
                            get_rec_name_from_code(previous_rec_type),
                            dup_cnt
                        );
                    }
                    previous_rec_type = rec_code;
                    dup_cnt = 1;
                }
            }
        }

        // print last record
        if dup_cnt != 0 && previous_rec_type != 0 {
            // flush previous log
            result_log += &format!(
                "{} × {}\n",
                get_rec_name_from_code(previous_rec_type),
                dup_cnt
            );
        }

        result_log += &format!(
            "\nTotal wafers: {}\nTotal duts/dies: {}\nTotal Records: {}\nAnalysis Finished",
            wafer_cnt, dut_cnt, total_record
        );
        if stop_flag_rust {
            result_log += "\n***Operation terminated by User***";
        }
        // println!("{}", result_log);
        // send via qt signal..
        Python::with_gil(|py| -> PyResult<()> {
            if is_valid_data_signal {
                let _ = data_signal.call_method1(py, intern!(py, "emit"), (result_log,))?;
            }
            if is_valid_progress_signal {
                progress_signal.call_method1(py, intern!(py, "emit"), (100u64,))?;
            }
            Ok(())
        })?;
        Ok(())
    })
}

// /// read data from python file object
// #[pyfunction]
// #[pyo3(name = "read_rawList")]
// fn read_raw_from_fileobj<'py>(
//     py: Python<'py>,
//     fileobj: PyObject,
//     offset: PyReadonlyArray1<i64>,
//     lens: PyReadonlyArray1<i32>,
// ) -> PyResult<&'py PyArray2<u8>> {
//     // validate `fileobj`
//     let no_read = match fileobj.getattr(py, intern!(py, "read")) {
//         Ok(p) => !p.as_ref(py).is_callable(),
//         Err(_) => true,
//     };
//     let no_seek = match fileobj.getattr(py, intern!(py, "seek")) {
//         Ok(p) => !p.as_ref(py).is_callable(),
//         Err(_) => true,
//     };
//     if no_read || no_seek {
//         return Err(PyErr::new::<PyValueError, _>(
//             "Object doesn't have `read` or `seek` method",
//         ));
//     };

//     let offset = offset.as_array();
//     let lens = lens.as_array();
//     let max_len = lens.iter().fold(0, |m, &x| std::cmp::max(m, x)) as usize;
//     // initiate a 2D array for storing file data
//     // row count = len(offset)
//     // column count = max(len)
//     let mut data_list = Array2::from_elem((offset.dim(), max_len), 0u8);
//     if max_len > 0 {
//         for ((&oft, &len), mut data_row) in offset.iter().zip(lens.iter()).zip(data_list.rows_mut())
//         {
//             if oft >= 0 && len > 0 {
//                 // seek to `offset`
//                 fileobj.call_method1(py, intern!(py, "seek"), (oft,))?;
//                 // read `len`
//                 let rslt = fileobj.call_method1(py, intern!(py, "read"), (len,))?;
//                 let pybytes: &PyBytes = rslt.cast_as(py)?;
//                 let read_data = pybytes.as_bytes();
//                 let dst = &mut data_row
//                     .as_slice_mut()
//                     .expect("cannot get slice from ndarray row")[..len as usize];
//                 dst.copy_from_slice(read_data);
//             }
//         }
//     }
//     Ok(data_list.into_pyarray(py))
// }

// /// get PTR/FTR results and flags from raw bytes
// #[pyfunction]
// #[pyo3(name = "parse_PTR_FTR_rawList")]
// fn parse_ptr_ftr_from_raw<'py>(
//     py: Python<'py>,
//     is_ptr: bool,
//     is_le: bool,
//     raw: PyReadonlyArray2<u8>,
//     lens: PyReadonlyArray1<i32>,
// ) -> PyResult<&'py PyDict> {
//     let endian = if is_le {
//         ByteOrder::LittleEndian
//     } else {
//         ByteOrder::BigEndian
//     };
//     let raw = raw.as_array();
//     let lens = lens.as_array();
//     let rec_cnt = lens.dim();
//     let max_len = lens.iter().fold(0, |m, &x| std::cmp::max(m, x));
//     // create Array for storing results
//     let mut data_list = Array1::from_elem(rec_cnt, f32::NAN);
//     let mut flag_list = Array1::from_elem(rec_cnt, -1i32);

//     fn inner_parse(
//         is_ptr: bool,
//         order: &ByteOrder,
//         raw_data: &[u8],
//         &length: &i32,
//         result: &mut f32,
//         flag: &mut i32,
//     ) {
//         if length < 0 {
//             // represent an invalid raw data
//             // do nothing, since the default data is invalid
//             return;
//         }

//         let length = length as usize;
//         let raw_data = &raw_data[..length];
//         if is_ptr {
//             // parse PTR
//             let mut ptr_rec = rust_stdf::PTR::new();
//             ptr_rec.read_from_bytes(raw_data, order);

//             *result = if f32::is_finite(ptr_rec.result) {
//                 ptr_rec.result
//             } else if f32::is_sign_positive(ptr_rec.result) {
//                 // +inf, replace with max f32
//                 f32::MAX
//             } else {
//                 // -inf, replace with min f32
//                 f32::MIN
//             };
//             *flag = ptr_rec.test_flg[0].into();
//         } else {
//             // parse FTR
//             let mut ftr_rec = rust_stdf::FTR::new();
//             ftr_rec.read_from_bytes(raw_data, order);
//             *result = ftr_rec.test_flg[0].into();
//             *flag = ftr_rec.test_flg[0].into();
//         };
//     }

//     if max_len > 0 {
//         py.allow_threads(|| {
//             // parallel parse data
//             Zip::from(raw.rows())
//                 .and(&lens)
//                 .and(&mut data_list)
//                 .and(&mut flag_list)
//                 .par_for_each(|r, l, d, f| {
//                     inner_parse(
//                         is_ptr,
//                         &endian,
//                         r.to_slice().expect("cannot get slice from numpy ndarray"),
//                         l,
//                         d,
//                         f,
//                     )
//                 });
//         });
//     }
//     let data_list = data_list.into_pyarray(py);
//     let flag_list = flag_list.into_pyarray(py);
//     let dict = PyDict::new(py);
//     dict.set_item("dataList", data_list)?;
//     dict.set_item("flagList", flag_list)?;
//     Ok(dict)
// }

// /// get MPR results, states and flags from raw bytes
// #[pyfunction]
// #[pyo3(name = "parse_MPR_rawList")]
// fn parse_mpr_from_raw<'py>(
//     py: Python<'py>,
//     is_le: bool,
//     pin_cnt: u16,
//     rslt_cnt: u16,
//     raw: PyReadonlyArray2<u8>,
//     lens: PyReadonlyArray1<i32>,
// ) -> PyResult<&'py PyDict> {
//     let endian = if is_le {
//         ByteOrder::LittleEndian
//     } else {
//         ByteOrder::BigEndian
//     };
//     let rslt_cnt = rslt_cnt as usize;
//     let pin_cnt = pin_cnt as usize;
//     let raw = raw.as_array();
//     let lens = lens.as_array();
//     let rec_cnt = lens.dim();
//     let max_len = lens.iter().fold(0, |m, &x| std::cmp::max(m, x));
//     // create Array for storing results
//     // contiguous is required in order to get slice from ndarray,
//     // must iter by row...
//     // row: dutIndex, col: pin
//     let mut data_list = Array2::from_elem((rec_cnt, rslt_cnt), f32::NAN);
//     let mut state_list = Array2::from_elem((rec_cnt, pin_cnt), 16i32);
//     let mut flag_list = Array1::from_elem(rec_cnt, -1i32);

//     #[allow(clippy::too_many_arguments)]
//     fn inner_parse(
//         order: &ByteOrder,
//         pin_cnt: usize,
//         rslt_cnt: usize,
//         raw_data: &[u8],
//         &length: &i32,
//         result_slice: &mut [f32],
//         state_slice: &mut [i32],
//         flag: &mut i32,
//     ) {
//         if length < 0 {
//             // represent an invalid raw data
//             // do nothing, since the default data is invalid
//             return;
//         }

//         let length = length as usize;
//         let raw_data = &raw_data[..length];
//         // parse MPR
//         let mut mpr_rec = rust_stdf::MPR::new();
//         mpr_rec.read_from_bytes(raw_data, order);
//         // update result
//         for (&rslt, ind) in mpr_rec.rtn_rslt.iter().zip(0..rslt_cnt) {
//             result_slice[ind] = if f32::is_finite(rslt) {
//                 rslt
//             } else if f32::is_sign_positive(rslt) {
//                 // +inf, replace with max f32
//                 f32::MAX
//             } else {
//                 // -inf, replace with min f32
//                 f32::MIN
//             };
//         }
//         // update state
//         for (&state, ind) in mpr_rec.rtn_stat.iter().zip(0..pin_cnt) {
//             state_slice[ind] = state as i32;
//         }
//         *flag = mpr_rec.test_flg[0].into();
//     }

//     if max_len > 0 {
//         py.allow_threads(|| {
//             // parallel parse data
//             Zip::from(raw.rows())
//                 .and(&lens)
//                 .and(data_list.rows_mut())
//                 .and(state_list.rows_mut())
//                 .and(&mut flag_list)
//                 .par_for_each(|r, l, d, s, f| {
//                     inner_parse(
//                         &endian,
//                         pin_cnt,
//                         rslt_cnt,
//                         r.to_slice().expect("cannot get slice from numpy ndarray"),
//                         l,
//                         d.into_slice().expect("ndarray is not contiguous"),
//                         s.into_slice().expect("ndarray is not contiguous"),
//                         f,
//                     )
//                 });
//         });
//     }
//     // previous order: row: dutIndex, col: pin
//     // python expected: row: pin, col: dutIndex
//     let data_list = data_list.reversed_axes().into_pyarray(py);
//     let state_list = state_list.reversed_axes().into_pyarray(py);
//     let flag_list = flag_list.into_pyarray(py);
//     let dict = PyDict::new(py);
//     dict.set_item("dataList", data_list)?;
//     dict.set_item("statesList", state_list)?;
//     dict.set_item("flagList", flag_list)?;
//     Ok(dict)
// }

/// create sqlite3 database for given stdf files
#[pyfunction]
#[pyo3(name = "generate_database")]
fn generate_database(
    py: Python,
    dbpath: String,
    stdf_paths: Vec<Vec<String>>,
    progress_signal: &PyAny,
    stop_flag: &PyAny,
) -> PyResult<()> {
    // stdf_paths is a Vec of Vec<String>, each sub vec
    // indicates a group of stdf files that needs to be merged.
    //
    // For example:
    // [["v1_1", "v1_2", "v1_3"],
    //  ["v2_1", "v2_2"]]
    //
    // "v1_x" is the 1st group of file, they will be treated as
    // a single file (Fid=0) in the database.
    //
    // "v2_x" is another group with Fid=1.
    //
    // do nothing if empty file group detected
    let num_groups = stdf_paths.len();
    if stdf_paths.iter().map(|v| v.is_empty()).any(|b| b) {
        return Err(PyValueError::new_err("Empty STDF file group detected"));
    }

    // convert and check python arguments
    let progress_signal: Py<PyAny> = progress_signal.into();
    let stop_flag: Py<PyAny> = stop_flag.into();

    let is_valid_progress_signal = match progress_signal.getattr(py, intern!(py, "emit")) {
        Ok(p) => p.as_ref(py).is_callable(),
        Err(_) => {
            println!("progress_signal does not have a method `emit`");
            false
        }
    };
    let is_valid_stop = match stop_flag.getattr(py, intern!(py, "stop")) {
        Ok(p) => p.as_ref(py).is_instance_of::<PyBool>()?,
        Err(_) => {
            println!("stop_flag does not have an bool attr `stop`");
            false
        }
    };

    // prepare channel for multithreading communication
    let (tx, rx) = mpsc::channel();
    let mut thread_handles = vec![];
    let mut thread_txes = Vec::with_capacity(num_groups);
    // clone {num_groups-1} sender, and push the `tx` to last
    (0..num_groups - 1)
        .map(|_| thread_txes.push(tx.clone()))
        .count();
    thread_txes.push(tx);

    // sending parsing work to
    // other threads.
    // one file group per thread
    for (fid, (fgroups, thread_tx)) in stdf_paths
        .clone()
        .into_iter()
        .zip(thread_txes.into_iter())
        .enumerate()
    {
        let handle = thread::spawn(move || -> Result<(), StdfHelperError> {
            let num_files = fgroups.len();
            // loop fpath in a group in vector order,
            // this step CANNOT be parallel, since
            // superseded flag must overwrite all the
            // DUTs in the previous files
            for (sub_fid, fpath) in fgroups.iter().enumerate() {
                let file_size = get_file_size(fpath)? as f32;
                if file_size == 0.0 {
                    return Err(StdfHelperError {
                        msg: format!("Empty file detected!\n\n{}", fpath),
                    });
                }
                let mut stdf_reader = match StdfReader::new(fpath) {
                    Ok(r) => r,
                    Err(e) => {
                        return Err(StdfHelperError {
                            msg: format!("Cannot parse this file:\n{}\n\nMessage:\n{}", fpath, e),
                        })
                    }
                };
                for raw_rec in stdf_reader.get_rawdata_iter() {
                    let raw_rec = match raw_rec {
                        Ok(r) => r,
                        Err(_) => {
                            // there is only one error, that is
                            // unexpected EOF, we just sliently
                            // stop here
                            break;
                        }
                    };
                    // calculate the reading progress in each thread
                    let progress_x100 = 10000.0
                        * (raw_rec.offset as f32 / file_size + sub_fid as f32)
                        / num_files as f32;
                    // send
                    if thread_tx
                        .send((fid, sub_fid, progress_x100, raw_rec))
                        .is_err()
                    {
                        break;
                    }
                }
            }
            Ok(())
        });
        thread_handles.push(handle);
    }

    // create some atomic var for data communication between threads
    let global_stop = Arc::new(AtomicBool::new(false));
    // only need to hold a number <= 10000, u16 should be enough
    let total_progress = Arc::new(AtomicU16::new(0));

    let global_stop_copy = global_stop.clone();
    let total_progress_copy = total_progress.clone();

    if is_valid_progress_signal || is_valid_stop {
        // start another thread for updating stop signal
        // and sending progress back to python
        let gil_th = thread::spawn(move || -> Result<(), StdfHelperError> {
            loop {
                let current_progress = total_progress_copy.load(Ordering::Relaxed);
                // sleep for 100ms
                thread::sleep(time::Duration::from_millis(100));
                // access python object inside a gil block
                if let Err(py_e) = Python::with_gil(|py| -> PyResult<()> {
                    if is_valid_progress_signal {
                        progress_signal.call_method1(
                            py,
                            intern!(py, "emit"),
                            (current_progress,),
                        )?;
                    }
                    if is_valid_stop {
                        global_stop_copy.store(
                            stop_flag
                                .getattr(py, intern!(py, "stop"))?
                                .extract::<bool>(py)?,
                            Ordering::Relaxed,
                        );
                    };
                    Ok(())
                }) {
                    // print python exceptions occured
                    // in this thread and exit...
                    println!("{}", py_e);
                    break;
                }
                if current_progress == 10000 {
                    break;
                }
            }
            Ok(())
        });
        thread_handles.push(gil_th);
    }

    py.allow_threads(|| -> Result<(), StdfHelperError> {
        // initiate sqlite3 database
        let conn = match Connection::open(&dbpath) {
            Ok(conn) => conn,
            Err(e) => return Err(StdfHelperError { msg: e.to_string() }),
        };
        let mut db_ctx = DataBaseCtx::new(&conn)?;

        // store file paths to database
        for (fid, fgroup) in stdf_paths.iter().enumerate() {
            for (sub_fid, fpath) in fgroup.iter().enumerate() {
                db_ctx.insert_file_name(rusqlite::params![fid, sub_fid, fpath])?;
            }
        }

        let mut record_tracker = RecordTracker::new();
        let mut progress_tracker = vec![0.0f32; num_groups];
        let mut transaction_count_up = 0;
        // process and write database in main thread
        for (fid, sub_fid, progress_x100, raw_rec) in rx {
            let rec_info = (
                fid,
                sub_fid,
                raw_rec.byte_order,
                raw_rec.offset,
                raw_rec.raw_data.len(),
                StdfRecord::from(raw_rec),
            );
            process_incoming_record(&mut db_ctx, &mut record_tracker, rec_info)?;

            if is_valid_progress_signal {
                // main thread will calculate the `total progress`
                if let Some(v) = progress_tracker.get_mut(fid) {
                    *v = progress_x100;
                };
                total_progress.store(
                    (progress_tracker.iter().sum::<f32>() / num_groups as f32) as u16,
                    Ordering::Relaxed,
                );
            }

            if is_valid_stop && global_stop.load(Ordering::Relaxed) {
                break;
            }

            // commit and begin a new transaction after fixed number of records
            transaction_count_up += 1;
            if transaction_count_up > 1_000_000 {
                transaction_count_up = 0;
                db_ctx.start_new_transaction()?;
            }
        }
        // write HBR/SBR/TSR into database
        process_summary_data(&mut db_ctx, &mut record_tracker)?;
        // write 10000 as the sign of complete...
        total_progress.store(10000u16, Ordering::Relaxed);

        // join threads
        for handle in thread_handles {
            handle.join().unwrap()?;
        }
        // finalize database
        db_ctx.finalize()?;
        if let Err((_, err)) = conn.close() {
            return Err(StdfHelperError::from(err))?;
        };
        Ok(())
    })?;

    Ok(())
}

/// read MIR records from a STDF file
/// exit if found
#[pyfunction]
#[pyo3(name = "read_MIR")]
fn read_mir(py: Python<'_>, fpath: String) -> PyResult<&'_ PyDict> {
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
    for rec in reader.get_record_iter() {
        let rec = match rec {
            Ok(r) => r,
            Err(e) => {
                return Err(PyOSError::new_err(format!(
                    "Error when reading MIR record of this file:\n{}\n\n{}",
                    &fpath, e
                )))
            }
        };
        if let StdfRecord::MIR(mir_rec) = rec {
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
                                let timestamp =
                                    rust_functions::u32_to_localtime(n.as_u64().unwrap() as u32);
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

/// read data from python file object
#[pyfunction]
#[pyo3(name = "get_icon_src")]
fn get_icon_src(py: Python, icon_name: String) -> PyResult<&PyBytes> {
    use flate2::read::ZlibDecoder;
    use resources::*;
    use std::io::Read;

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

/// convert stdf to xlsx file
#[pyfunction]
#[pyo3(name = "stdf_to_xlsx")]
fn stdf_to_xlsx(
    py: Python,
    stdf_path: String,
    xlsx_path: String,
    progress_signal: &PyAny,
    stop_flag: &PyAny,
) -> PyResult<()> {
    // get file size
    let file_size = get_file_size(&stdf_path)?;
    if file_size == 0 {
        return Err(PyOSError::new_err("empty file detected"));
    }

    let progress_signal: Py<PyAny> = progress_signal.into();
    let stop_flag: Py<PyAny> = stop_flag.into();

    let is_valid_progress_signal = match progress_signal.getattr(py, intern!(py, "emit")) {
        Ok(p) => p.as_ref(py).is_callable(),
        Err(_) => {
            println!("progress_signal does not have a method `emit`");
            false
        }
    };
    let is_valid_stop = match stop_flag.getattr(py, intern!(py, "stop")) {
        Ok(p) => p.as_ref(py).is_instance_of::<PyBool>()?,
        Err(_) => {
            println!("stop_flag does not have an bool attr `stop`");
            false
        }
    };

    let mut stop_flag_rust = false;
    let mut parse_progess = 0;

    py.allow_threads(|| -> Result<(), StdfHelperError> {
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
                        s.write_string(0, col as u16, field, &bold_format)?;
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
            match stdf_rec {
                // rec type 15
                StdfRecord::PTR(r) => {
                    let json = serde_json::to_value(&r)?;
                    write_json_to_sheet(json, field_names, sheet, row)?;
                }
                StdfRecord::MPR(r) => {
                    let json = serde_json::to_value(&r)?;
                    write_json_to_sheet(json, field_names, sheet, row)?;
                }
                StdfRecord::FTR(r) => {
                    let json = serde_json::to_value(&r)?;
                    write_json_to_sheet(json, field_names, sheet, row)?;
                }
                StdfRecord::STR(r) => {
                    let json = serde_json::to_value(&r)?;
                    write_json_to_sheet(json, field_names, sheet, row)?;
                }
                // rec type 5
                StdfRecord::PIR(r) => {
                    let json = serde_json::to_value(&r)?;
                    write_json_to_sheet(json, field_names, sheet, row)?;
                }
                StdfRecord::PRR(r) => {
                    let json = serde_json::to_value(&r)?;
                    write_json_to_sheet(json, field_names, sheet, row)?;
                    // check stop signal and send progress if we encountered PRR
                    if is_valid_progress_signal || is_valid_stop {
                        if let Err(e) = Python::with_gil(|py| -> PyResult<()> {
                            if is_valid_progress_signal {
                                progress_signal.call_method1(
                                    py,
                                    intern!(py, "emit"),
                                    (parse_progess,),
                                )?;
                            }
                            if is_valid_stop {
                                stop_flag_rust = stop_flag
                                    .getattr(py, intern!(py, "stop"))?
                                    .extract::<bool>(py)?;
                            }
                            Ok(())
                        }) {
                            return Err(StdfHelperError { msg: e.to_string() });
                        }
                    }
                }
                // rec type 2
                StdfRecord::WIR(r) => {
                    let json = serde_json::to_value(&r)?;
                    write_json_to_sheet(json, field_names, sheet, row)?;
                }
                StdfRecord::WRR(r) => {
                    let json = serde_json::to_value(&r)?;
                    write_json_to_sheet(json, field_names, sheet, row)?;
                }
                StdfRecord::WCR(r) => {
                    let json = serde_json::to_value(&r)?;
                    write_json_to_sheet(json, field_names, sheet, row)?;
                }
                // rec type 50
                StdfRecord::GDR(r) => {
                    let json = serde_json::to_value(&r)?;
                    write_json_to_sheet(json, field_names, sheet, row)?;
                }
                StdfRecord::DTR(r) => {
                    let json = serde_json::to_value(&r)?;
                    write_json_to_sheet(json, field_names, sheet, row)?;
                }
                // rec type 10
                StdfRecord::TSR(r) => {
                    let json = serde_json::to_value(&r)?;
                    write_json_to_sheet(json, field_names, sheet, row)?;
                }
                // rec type 1
                StdfRecord::MIR(r) => {
                    let json = serde_json::to_value(&r)?;
                    write_json_to_sheet(json, field_names, sheet, row)?;
                }
                StdfRecord::MRR(r) => {
                    let json = serde_json::to_value(&r)?;
                    write_json_to_sheet(json, field_names, sheet, row)?;
                }
                StdfRecord::PCR(r) => {
                    let json = serde_json::to_value(&r)?;
                    write_json_to_sheet(json, field_names, sheet, row)?;
                }
                StdfRecord::HBR(r) => {
                    let json = serde_json::to_value(&r)?;
                    write_json_to_sheet(json, field_names, sheet, row)?;
                }
                StdfRecord::SBR(r) => {
                    let json = serde_json::to_value(&r)?;
                    write_json_to_sheet(json, field_names, sheet, row)?;
                }
                StdfRecord::PMR(r) => {
                    let json = serde_json::to_value(&r)?;
                    write_json_to_sheet(json, field_names, sheet, row)?;
                }
                StdfRecord::PGR(r) => {
                    let json = serde_json::to_value(&r)?;
                    write_json_to_sheet(json, field_names, sheet, row)?;
                }
                StdfRecord::PLR(r) => {
                    let json = serde_json::to_value(&r)?;
                    write_json_to_sheet(json, field_names, sheet, row)?;
                }
                StdfRecord::RDR(r) => {
                    let json = serde_json::to_value(&r)?;
                    write_json_to_sheet(json, field_names, sheet, row)?;
                }
                StdfRecord::SDR(r) => {
                    let json = serde_json::to_value(&r)?;
                    write_json_to_sheet(json, field_names, sheet, row)?;
                }
                StdfRecord::PSR(r) => {
                    let json = serde_json::to_value(&r)?;
                    write_json_to_sheet(json, field_names, sheet, row)?;
                }
                StdfRecord::NMR(r) => {
                    let json = serde_json::to_value(&r)?;
                    write_json_to_sheet(json, field_names, sheet, row)?;
                }
                StdfRecord::CNR(r) => {
                    let json = serde_json::to_value(&r)?;
                    write_json_to_sheet(json, field_names, sheet, row)?;
                }
                StdfRecord::SSR(r) => {
                    let json = serde_json::to_value(&r)?;
                    write_json_to_sheet(json, field_names, sheet, row)?;
                }
                StdfRecord::CDR(r) => {
                    let json = serde_json::to_value(&r)?;
                    write_json_to_sheet(json, field_names, sheet, row)?;
                }
                // rec type 0
                StdfRecord::FAR(r) => {
                    let json = serde_json::to_value(&r)?;
                    write_json_to_sheet(json, field_names, sheet, row)?;
                }
                StdfRecord::ATR(r) => {
                    let json = serde_json::to_value(&r)?;
                    write_json_to_sheet(json, field_names, sheet, row)?;
                }
                StdfRecord::VUR(r) => {
                    let json = serde_json::to_value(&r)?;
                    write_json_to_sheet(json, field_names, sheet, row)?;
                }
                // rec type 20
                StdfRecord::BPS(r) => {
                    let json = serde_json::to_value(&r)?;
                    write_json_to_sheet(json, field_names, sheet, row)?;
                }
                StdfRecord::EPS(r) => {
                    let json = serde_json::to_value(&r)?;
                    write_json_to_sheet(json, field_names, sheet, row)?;
                }
                // rec type 180: Reserved
                // rec type 181: Reserved
                StdfRecord::ReservedRec(r) => {
                    let json = serde_json::to_value(&r)?;
                    write_json_to_sheet(json, field_names, sheet, row)?;
                }
                StdfRecord::InvalidRec(h) => {
                    panic!("Invalid record found! {h:?}")
                }
            }
        }
        // save xlsx to path
        xlsx.save_to_path(std::path::Path::new(&xlsx_path))?;
        Ok(())
    })?;

    Ok(())
}

/// A Python module implemented in Rust.
#[pymodule]
fn rust_stdf_helper(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(analyze_stdf_file, m)?)?;
    // m.add_function(wrap_pyfunction!(read_raw_from_fileobj, m)?)?;
    // m.add_function(wrap_pyfunction!(parse_ptr_ftr_from_raw, m)?)?;
    // m.add_function(wrap_pyfunction!(parse_mpr_from_raw, m)?)?;
    m.add_function(wrap_pyfunction!(generate_database, m)?)?;
    m.add_function(wrap_pyfunction!(read_mir, m)?)?;
    m.add_function(wrap_pyfunction!(get_icon_src, m)?)?;
    m.add_function(wrap_pyfunction!(stdf_to_xlsx, m)?)?;
    Ok(())
}
