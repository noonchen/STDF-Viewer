use numpy::ndarray::{Array1, Array2, Zip};
use numpy::{IntoPyArray, PyReadonlyArray1, PyReadonlyArray2};
use pyo3::{
    exceptions::{PyException, PyOSError},
    intern,
    prelude::*,
    types::{PyBool, PyDict},
};
use rusqlite::{Connection, Error};
use rust_stdf::{stdf_file::*, stdf_record_type::*, ByteOrder, StdfRecord};
use std::convert::From;
use std::sync::atomic::{AtomicBool, AtomicU16, Ordering};
use std::sync::{mpsc, Arc};
use std::{thread, time};

mod database_context;
mod rust_functions;
use database_context::DataBaseCtx;
use rust_functions::{get_file_size, process_incoming_record, process_summary_data, RecordTracker};

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

    let mut reader = match StdfReader::new(filepath) {
        Ok(r) => r,
        Err(e) => return Err(PyOSError::new_err(e.to_string())),
    };

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

    py.allow_threads(|| {
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

    py.allow_threads(|| {
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
fn generate_database(
    py: Python,
    dbpath: String,
    stdf_paths: Vec<String>,
    progress_signal: &PyAny,
    stop_flag: &PyAny,
) -> PyResult<()> {
    // do nothing if no file
    let num_files = stdf_paths.len();
    if num_files == 0 {
        return Ok(());
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
    let mut thread_txes = Vec::with_capacity(num_files);
    // clone {num_files-1} sender, and push the `tx` to last
    (0..num_files - 1)
        .map(|_| thread_txes.push(tx.clone()))
        .count();
    thread_txes.push(tx);

    // sending parsing work to
    // other threads.
    // one file per thread
    for (fid, (fpath, thread_tx)) in stdf_paths
        .into_iter()
        .zip(thread_txes.into_iter())
        .enumerate()
    {
        let handle = thread::spawn(move || {
            let file_size = get_file_size(&fpath).unwrap() as f32;
            let mut stdf_reader = StdfReader::new(fpath).unwrap();
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
                let progress_x100 = raw_rec.offset as f32 * 10000.0 / file_size;
                if thread_tx.send((fid, progress_x100, raw_rec)).is_err() {
                    break;
                }
            }
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
        let gil_th = thread::spawn(move || {
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

        let mut record_tracker = RecordTracker::new();
        let mut progress_tracker = vec![0.0f32; num_files];
        let mut transaction_count_up = 0;
        // process and write database in main thread
        for (fid, progress_x100, raw_rec) in rx {
            let rec_info = (
                fid,
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
                    (progress_tracker.iter().sum::<f32>() / num_files as f32) as u16,
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
            handle.join().unwrap();
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

/// A Python module implemented in Rust.
#[pymodule]
fn rust_stdf_helper(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(analyze_stdf_file, m)?)?;
    m.add_function(wrap_pyfunction!(parse_ptr_ftr_from_raw, m)?)?;
    m.add_function(wrap_pyfunction!(parse_mpr_from_raw, m)?)?;
    m.add_function(wrap_pyfunction!(generate_database, m)?)?;
    Ok(())
}
