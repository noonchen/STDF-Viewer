use core::f64;
use numpy::ndarray::{Array1, Zip};
use numpy::{IntoPyArray, PyArray1, PyReadonlyArray1};
use pyo3::exceptions::PyValueError;
use pyo3::types::{PyBytes, PyInt};
use pyo3::{
    exceptions::{PyException, PyLookupError, PyOSError},
    intern,
    prelude::*,
    types::{PyBool, PyDict},
};
use rusqlite::{Connection, Error};
use rust_stdf::{stdf_file::*, stdf_record_type::*, StdfRecord, StdfRecordView};
use rust_xlsxwriter::{Workbook, XlsxError};
use std::collections::{HashMap, HashSet};
use std::convert::{From, Infallible};
use std::sync::atomic::{AtomicBool, AtomicU16, Ordering};
use std::sync::Arc;
use std::{thread, time, vec};

mod database_context;
mod db_ops;
mod resources;
mod rust_functions;
mod statistic_functions;
use database_context::DataBaseCtx;
use db_ops::{DbMessage, DbOp};
use rust_functions::{
    get_fields_from_code, get_file_size, process_record_view, write_json_to_sheet, RecordTracker,
    TestIDType,
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

// convert TestIDType to/from python object
impl<'src> FromPyObject<'src> for TestIDType {
    fn extract_bound(obj: &Bound<'src, PyAny>) -> PyResult<Self> {
        let val: u32 = obj.extract()?;
        match val {
            0 => Ok(TestIDType::TestNumberAndName),
            1 => Ok(TestIDType::TestNumberOnly),
            _ => Err(PyValueError::new_err(format!(
                "Invalid TestIDType value: {}",
                val
            ))),
        }
    }
}

impl<'py> IntoPyObject<'py> for TestIDType {
    type Target = PyInt;
    type Output = Bound<'py, Self::Target>;
    type Error = Infallible;

    fn into_pyobject(self, py: Python<'py>) -> Result<Self::Output, Self::Error> {
        Ok(PyInt::new(py, self as u32))
    }
}

// RAII to join threads
struct ThreadJoiner<T>(Vec<std::thread::JoinHandle<T>>);

impl<T> Drop for ThreadJoiner<T> {
    fn drop(&mut self) {
        for handle in self.0.drain(..) {
            if let Err(e) = handle.join() {
                println!("Join thread failed: {:?}", e);
            }
        }
    }
}

// RAII to fill up progress bar and generate done signal
struct ProgressBarFiller {
    progress: Arc<AtomicU16>,
    done: Arc<AtomicBool>,
}

impl Drop for ProgressBarFiller {
    fn drop(&mut self) {
        // mark progress completes
        self.progress.store(10000u16, Ordering::Relaxed);
        self.done.store(true, Ordering::Relaxed);
    }
}

/// Analyze record types in a STDF file
#[pyfunction]
#[pyo3(name = "analyzeSTDF")]
fn analyze_stdf_file(
    py: Python,
    filepath: &str,
    data_signal: Bound<'_, PyAny>,
    progress_signal: Bound<'_, PyAny>,
    stop_flag: Bound<'_, PyAny>,
) -> PyResult<()> {
    // get file size
    let file_size = get_file_size(filepath)?;
    if file_size == 0 {
        return Err(PyOSError::new_err("empty file detected"));
    }

    let is_valid_data_signal = match data_signal.getattr(intern!(py, "emit")) {
        Ok(p) => p.is_callable(),
        Err(_) => {
            println!("data_signal does not have a method `emit`");
            false
        }
    };
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

    let mut stop_flag_rust = false;
    // offset / file_size * 100
    let mut parse_progess = 0;

    let mut result_log = String::with_capacity(512);
    let mut analyze_rst = {
        let mut s = String::with_capacity(2048);
        s.insert(0, '\n');
        s
    };
    let mut total_record: u64 = 0;
    let mut previous_rec_type: u64 = 0;
    let mut dup_cnt = 0;
    let mut dut_cnt = 0;
    let mut wafer_cnt = 0;
    // rec_code -> (test num -> set of test names)
    let mut test_id_tracker = HashMap::<u64, HashMap<u32, HashSet<String>>>::with_capacity(3);
    // rec_code -> (test num -> set of test names) of TSR
    let mut tsr_id_tracker = HashMap::<u64, HashMap<u32, HashSet<String>>>::with_capacity(3);
    // rec_code -> (bin num -> has H/S bin rec?)
    let mut test_bin_tracker = HashMap::<u64, HashMap<u16, bool>>::with_capacity(2);

    // signals without gil
    let data_signal: Py<PyAny> = data_signal.into();
    let progress_signal: Py<PyAny> = progress_signal.into();
    let stop_flag: Py<PyAny> = stop_flag.into();

    py.detach(|| {
        let mut reader = match StdfReader::new(filepath) {
            Ok(r) => r,
            Err(e) => return Err(PyOSError::new_err(e.to_string())),
        };

        let mut view_iter = reader.get_rawdata_view_iter();
        while let Some(raw_view) = view_iter.next() {
            if stop_flag_rust {
                break;
            }

            let raw_view = match raw_view {
                Ok(r) => r,
                Err(e) => return Err(PyException::new_err(e.to_string())),
            };
            total_record += 1;
            let rec_code = raw_view.header.get_type();
            let rec_name = get_rec_name_from_code(rec_code);

            if rec_code == REC_UNKNOWN {
                result_log += &format!(
                    "Unknown STDF V4 Record Detected, len:{}, typ: {}, sub: {}\n",
                    raw_view.header.len, raw_view.header.typ, raw_view.header.sub
                );
                break;
            }

            if raw_view.is_type(REC_PIR | REC_WIR | REC_PRR | REC_WRR) {
                if dup_cnt != 0 && previous_rec_type != 0 {
                    // flush previous record info to result_log
                    result_log += &format!(
                        "{} × {}\n",
                        get_rec_name_from_code(previous_rec_type),
                        dup_cnt
                    );
                }

                parse_progess = raw_view.offset * 100 / file_size;
                let rec_view: StdfRecordView = (&raw_view).into();
                match rec_view {
                    StdfRecordView::PIR(pir_view) => {
                        dut_cnt += 1;
                        result_log += &format!(
                            "[{}] {} (HEAD: {}, SITE: {})\n",
                            dut_cnt, rec_name, pir_view.head_num(), pir_view.site_num()
                        );
                    }
                    StdfRecordView::WIR(wir_view) => {
                        wafer_cnt += 1;
                        result_log += &format!("{} (HEAD: {})\n", rec_name, wir_view.head_num());
                    }
                    StdfRecordView::PRR(prr_view) => {
                        result_log += &format!(
                            "{} (HEAD: {}, SITE: {})\n",
                            rec_name, prr_view.head_num(), prr_view.site_num()
                        );
                        // track all bin numbers appear in PRR
                        test_bin_tracker
                            .entry(REC_HBR)
                            .or_default()
                            .entry(prr_view.hard_bin())
                            .or_insert(false);
                        test_bin_tracker
                            .entry(REC_SBR)
                            .or_default()
                            .entry(prr_view.soft_bin())
                            .or_insert(false);
                        // send or print result_log at PRR
                        // avoid result_log takes up too much memory...
                        // println!("{}", result_log);
                        // send via qt signal..
                        if is_valid_data_signal || is_valid_stop {
                            Python::attach(|py| -> PyResult<()> {
                                if is_valid_data_signal {
                                    data_signal
                                        .bind(py)
                                        .call_method1(intern!(py, "emit"), (&result_log,))?;
                                }
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
                            })?;
                        }
                        // reset to default
                        result_log.clear();
                    }
                    StdfRecordView::WRR(wrr_view) => {
                        result_log += &format!("{} (HEAD: {})\n", rec_name, wrr_view.head_num());
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

                // track the test number, name and bin of PTR, FTR and MPR
                if raw_view.is_type(REC_PTR | REC_FTR | REC_MPR | REC_TSR | REC_HBR | REC_SBR) {
                    let rec_view: StdfRecordView = (&raw_view).into();
                    match rec_view {
                        StdfRecordView::PTR(ptr_view) => {
                            let names = test_id_tracker
                                .entry(rec_code)
                                .or_default()
                                .entry(ptr_view.test_num())
                                .or_default();
                            let name = ptr_view.test_txt().as_str();
                            if !names.contains(name.as_ref()) {
                                names.insert(name.into_owned());
                            }
                        }
                        StdfRecordView::FTR(ftr_view) => {
                            let names = test_id_tracker
                                .entry(rec_code)
                                .or_default()
                                .entry(ftr_view.test_num())
                                .or_default();
                            let name = ftr_view.test_txt().as_str();
                            if !names.contains(name.as_ref()) {
                                names.insert(name.into_owned());
                            }
                        }
                        StdfRecordView::MPR(mpr_view) => {
                            let names = test_id_tracker
                                .entry(rec_code)
                                .or_default()
                                .entry(mpr_view.test_num())
                                .or_default();
                            let name = mpr_view.test_txt().as_str();
                            if !names.contains(name.as_ref()) {
                                names.insert(name.into_owned());
                            }
                        }
                        StdfRecordView::TSR(tsr_view) => {
                            let rec_code = match tsr_view.test_typ() {
                                'P' => REC_PTR,
                                'F' => REC_FTR,
                                'M' => REC_MPR,
                                _ => continue,
                            };
                            let names = tsr_id_tracker
                                .entry(rec_code)
                                .or_default()
                                .entry(tsr_view.test_num())
                                .or_default();
                            let name = tsr_view.test_nam().as_str();
                            if !names.contains(name.as_ref()) {
                                names.insert(name.into_owned());
                            }
                        }
                        StdfRecordView::HBR(hbr_view) => {
                            if let Some(s) = test_bin_tracker.get_mut(&REC_HBR) {
                                if let Some(b) = s.get_mut(&hbr_view.hbin_num()) {
                                    *b = true;
                                }
                            } else {
                                analyze_rst += &format!(
                                    "\nWarning: HBR (Bin {}) appears before any PRR!\n",
                                    hbr_view.hbin_num()
                                );
                            }
                        }
                        StdfRecordView::SBR(sbr_view) => {
                            if let Some(s) = test_bin_tracker.get_mut(&REC_SBR) {
                                if let Some(b) = s.get_mut(&sbr_view.sbin_num()) {
                                    *b = true;
                                }
                            } else {
                                analyze_rst += &format!(
                                    "\nWarning: SBR (Bin {}) appears before any PRR!\n",
                                    sbr_view.sbin_num()
                                );
                            }
                        }
                        _ => { /* impossible case */ }
                    }
                }
            }
        } // for loop

        // print last record
        if dup_cnt != 0 && previous_rec_type != 0 {
            // flush previous log
            result_log += &format!(
                "{} × {}\n",
                get_rec_name_from_code(previous_rec_type),
                dup_cnt
            );
        }

        // analyze the hashmaps
        // 1. all bin numbers should have a corresponding HBR/SBR (warning)
        test_bin_tracker.iter().for_each(|(bin_type, bin_map)| {
            let bin_type = get_rec_name_from_code(*bin_type);
            bin_map.iter().for_each(|(bin_num, &has_rec)| {
                if !has_rec {
                    analyze_rst += &format!(
                        "\nWarning: missing {} for bin number [{}]\n",
                        bin_type, bin_num
                    );
                }
            });
        });

        // 2. each test should have corresponding TSR (warning)
        // flatten `num -> {names}` into a set of borrowed (num, name) pairs for comparison
        fn flatten_id_map(m: &HashMap<u32, HashSet<String>>) -> HashSet<(u32, &str)> {
            m.iter()
                .flat_map(|(num, names)| names.iter().map(move |n| (*num, n.as_str())))
                .collect()
        }
        tsr_id_tracker.iter().for_each(|(rec_code, tsr_map)| {
            // get id set from test tracker, check for mismatch
            let test_set = flatten_id_map(test_id_tracker.entry(*rec_code).or_default());
            let tsr_set = flatten_id_map(tsr_map);
            let mut mismatch_test: Vec<&(u32, &str)> = test_set.difference(&tsr_set).collect();
            let mut mismatch_tsr: Vec<&(u32, &str)> = tsr_set.difference(&test_set).collect();
            let has_mis_test = mismatch_test.len() > 1;
            let has_mis_tsr = mismatch_tsr.len() > 1;

            if has_mis_test || has_mis_tsr {
                let rec_code = get_rec_name_from_code(*rec_code);
                // print mismatched test records
                if has_mis_test {
                    analyze_rst += &format!("\nWarning: no TSR detected for following {}(s)\n", rec_code);
                    mismatch_test.sort_by_key(|&a| a.0);
                    mismatch_test.iter().for_each(|&&(num, name)| {
                        analyze_rst += &format!("\t({}, \"{}\")\n", num, name);
                    });
                } else {
                    analyze_rst += &format!("\nWarning: all {}s have matching TSR, but\n", rec_code);
                }
                // print mismatch TSR
                if has_mis_tsr {
                    analyze_rst += &format!("there are TSRs have no matching {}\n", rec_code);
                    mismatch_tsr.sort_by_key(|&a| a.0);
                    mismatch_tsr.iter().for_each(|&&(num, name)| {
                        analyze_rst += &format!("\t({}, \"{}\")\n", num, name);
                    });
                }
            }
        });

        // 3. test number should only appear once (warning)
        {
            let mut reused = false;
            test_id_tracker.iter().for_each(|(rec_code, num_map)| {
                let rec_code = get_rec_name_from_code(*rec_code);
                // if a test number maps to more than one name, it is reused
                num_map.iter().for_each(|(num, names)| {
                    if names.len() > 1 {
                        reused = true;
                        // add the test num and name as duplicates to result
                        analyze_rst += &format!(
                            "\nWarning: test number [{}] is reused in multiple {}s\n",
                            num, rec_code
                        );
                        names.iter().for_each(|s| {
                            analyze_rst += &format!("\t({}, \"{}\")\n", num, s);
                        });
                    }
                });
            });
            if reused {
                analyze_rst += "\nNote: if test records share a test number and refer to the same test, \
                                consider selecting 'Number Only' as the 'Test Identifier' in settings.\n";
            }
        }

        // 4. test number cannot be reused in multiple record types (error)
        {
            let mut reused = false;
            // create a 
            // a. (num, name) -> set of <rec_code> hashmap 
            // b. num -> set of <rec_code> hashmap
            // for detection
            let mut reverse_id_map = HashMap::<(u32, &str), HashSet<u64>>::new();
            let mut reverse_num_map = HashMap::<u32, HashSet<u64>>::new();
            test_id_tracker.iter().for_each(|(rec_code, num_map)| {
                num_map.iter().for_each(|(num, names)| {
                    names.iter().for_each(|name| {
                        reverse_id_map
                            .entry((*num, name.as_str()))
                            .or_default()
                            .insert(*rec_code);
                        reverse_num_map
                            .entry(*num)
                            .or_default()
                            .insert(*rec_code);
                    });
                });
            });
            // check test number reuse
            reverse_num_map.iter().for_each(|(num, rec_set)| {
                if rec_set.len() > 1 {
                    reused = true;
                    analyze_rst += &format!("\nError: test number [{}] is reused in {:?}!\n",
                        num,
                        rec_set
                            .iter()
                            .map(|&code| get_rec_name_from_code(code))
                            .collect::<Vec<&str>>()
                    );
                }
            });
            if reused {
                analyze_rst += "\nNote: When a test number is reused in multiple record types, \
                        plots and statistics will be unreliable when selecting 'Number Only' as 'Test Identifier' in settings!\
                        \nConsider using 'Number + Name' instead.\n";
            }

            reused = false;
            // check test number & name reuse
            reverse_id_map.iter().for_each(|(&(num, name), rec_set)| {
                if rec_set.len() > 1 {
                    reused = true;
                    analyze_rst += &format!("\nFatal: test number and name [{}, \"{}\"] are reused in {:?}!\n",
                        num, name,
                        rec_set
                            .iter()
                            .map(|&code| get_rec_name_from_code(code))
                            .collect::<Vec<&str>>()
                    );
                }
            });
            if reused {
                analyze_rst += "\nFatal Note: Test number and name are reused in multiple record types, \
                        STDF-Viewer doesn't support this file and results of listed tests will be unreliable!\n";
            }
        }

        result_log += &analyze_rst;
        result_log += &format!(
            "\nTotal wafers: {}\nTotal duts/dies: {}\nTotal Records: {}\nAnalysis Finished",
            wafer_cnt, dut_cnt, total_record
        );
        if stop_flag_rust {
            result_log += "\n***Operation terminated by User***";
        }
        // println!("{}", result_log);
        // send via qt signal..
        Python::attach(|py| -> PyResult<()> {
            if is_valid_data_signal {
                data_signal
                    .bind(py)
                    .call_method1(intern!(py, "emit"), (result_log,))?;
            }
            if is_valid_progress_signal {
                progress_signal
                    .bind(py)
                    .call_method1(intern!(py, "emit"), (100u64,))?;
            }
            Ok(())
        })?;
        Ok(())
    })
}

/// create sqlite3 database for given stdf files
#[pyfunction]
#[pyo3(name = "generate_database")]
fn generate_database(
    py: Python,
    dbpath: String,
    stdf_paths: Vec<Vec<String>>,
    test_id_type: TestIDType,
    build_db_index: bool,
    progress_signal: Bound<'_, PyAny>,
    stop_flag: Bound<'_, PyAny>,
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
    if num_groups == 0 {
        return Err(PyValueError::new_err("No STDF files provided"));
    }
    if stdf_paths.iter().any(|v| v.is_empty()) {
        return Err(PyValueError::new_err("Empty STDF file group detected"));
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

    // signals without gil
    let progress_signal: Py<PyAny> = progress_signal.into();
    let stop_flag: Py<PyAny> = stop_flag.into();

    // Channel payload is now a batch of `DbOp`s.
    const OPS_PER_BATCH: usize = 128;
    const CHANNEL_CAP: usize = 64;
    let (tx, rx) = crossbeam_channel::bounded::<DbMessage>(CHANNEL_CAP);

    // Shared control/state between workers, writer, and the GIL progress thread.
    let global_stop = Arc::new(AtomicBool::new(false));
    let fgroup_done = Arc::new(AtomicBool::new(false));
    let total_progress = Arc::new(AtomicU16::new(0));
    let progress_values: Vec<Arc<AtomicU16>> = (0..num_groups)
        .map(|_| Arc::new(AtomicU16::new(0)))
        .collect();

    let mut thread_handles = vec![];
    let mut thread_txes = Vec::with_capacity(num_groups);
    // clone {num_groups-1} sender, and push the `tx` to last
    (0..num_groups - 1)
        .map(|_| thread_txes.push(tx.clone()))
        .count();
    thread_txes.push(tx);

    // Each thread handles one parsing/tracking task of one file group.
    for (fid, (fgroups, thread_tx)) in stdf_paths.clone().into_iter().zip(thread_txes).enumerate() {
        let worker_stop = global_stop.clone();
        let worker_progress = progress_values[fid].clone();
        let handle = thread::spawn(move || -> Result<(), StdfHelperError> {
            let num_files = fgroups.len();
            let mut record_tracker = RecordTracker::new(test_id_type);
            let mut ops: Vec<DbOp> = Vec::with_capacity(OPS_PER_BATCH);

            // loop fpath in a group in vector order,
            // this step CANNOT be parallel, since
            // superseded flag must overwrite all the
            // DUTs in the previous files
            for (sub_fid, fpath) in fgroups.iter().enumerate() {
                if worker_stop.load(Ordering::Relaxed) {
                    break;
                }
                let file_size = match get_file_size(fpath) {
                    Ok(size) => size as f32,
                    Err(e) => {
                        let msg = format!("Cannot get file size:\n{}\n\nMessage:\n{}", fpath, e);
                        let _ = thread_tx.send(DbMessage::WorkerError { msg });
                        return Ok(());
                    }
                };
                if file_size == 0.0 {
                    let msg = format!("Empty file detected!\n\n{}", fpath);
                    let _ = thread_tx.send(DbMessage::WorkerError { msg });
                    return Ok(());
                }
                let mut stdf_reader = match StdfReader::new(fpath) {
                    Ok(r) => r,
                    Err(e) => {
                        let msg = format!("Cannot parse this file:\n{}\n\nMessage:\n{}", fpath, e);
                        let _ = thread_tx.send(DbMessage::WorkerError { msg });
                        return Ok(());
                    }
                };
                // Parse with the zero-copy view iterator and keep all
                // RecordTracker bookkeeping in this worker thread.
                // Only DbOp batches cross the channel.
                let mut view_iter = stdf_reader.get_rawdata_view_iter();
                while let Some(raw_view) = view_iter.next() {
                    if worker_stop.load(Ordering::Relaxed) {
                        break;
                    }

                    let raw_view = match raw_view {
                        Ok(r) => r,
                        Err(_) => {
                            // there is only one error, that is
                            // unexpected EOF, we just silently
                            // stop here
                            break;
                        }
                    };

                    // calculate the reading progress in each thread
                    let progress_x100 = 10000.0
                        * (raw_view.offset as f32 / file_size + sub_fid as f32)
                        / num_files as f32;
                    worker_progress.store(progress_x100 as u16, Ordering::Relaxed);

                    let rec_view: StdfRecordView = (&raw_view).into();
                    if let Err(e) = process_record_view(
                        &mut record_tracker,
                        fid,
                        sub_fid,
                        raw_view.byte_order,
                        rec_view,
                        &mut ops,
                    ) {
                        let msg = format!("File[{}]: {}", fid, e.msg);
                        let _ = thread_tx.send(DbMessage::WorkerError { msg });
                        return Ok(());
                    }

                    if ops.len() >= OPS_PER_BATCH {
                        let batch = std::mem::replace(&mut ops, Vec::with_capacity(OPS_PER_BATCH));
                        if thread_tx.send(DbMessage::Batch(batch)).is_err() {
                            // Writer is gone (stop or error). Stop reading.
                            return Ok(());
                        }
                    }
                }
            }

            // Group EOF: emit HBR/SBR/TSR summaries, then flush any partial
            // batch. Channel FIFO preserves operation order for this fid.
            record_tracker.append_summary_ops(&mut ops);
            if !ops.is_empty() && thread_tx.send(DbMessage::Batch(ops)).is_err() {
                return Ok(());
            }
            Ok(())
        });
        thread_handles.push(handle);
    }

    let global_stop_copy = global_stop.clone();
    let total_progress_copy = total_progress.clone();
    let progress_values_copy = progress_values.clone();
    let fgroup_done_copy = fgroup_done.clone();

    if is_valid_progress_signal || is_valid_stop {
        // start another thread for updating stop signal
        // and sending progress back to python
        let gil_th = thread::spawn(move || -> Result<(), StdfHelperError> {
            let mut stop_cur_thread = false;
            loop {
                let done = fgroup_done_copy.load(Ordering::Relaxed);
                let current_progress: u16 = if done || num_groups == 0 {
                    10000
                } else {
                    (progress_values_copy
                        .iter()
                        .map(|p| p.load(Ordering::Relaxed) as u32)
                        .sum::<u32>()
                        / num_groups as u32) as u16
                };
                total_progress_copy.store(current_progress, Ordering::Relaxed);
                // access python object inside a gil block
                if let Err(py_e) = Python::attach(|py| -> PyResult<()> {
                    if is_valid_progress_signal {
                        progress_signal
                            .bind(py)
                            .call_method1(intern!(py, "emit"), (current_progress,))?;
                    }
                    if is_valid_stop {
                        let stop_from_py = stop_flag
                            .bind(py)
                            .getattr(intern!(py, "stop"))?
                            .extract::<bool>()?;
                        global_stop_copy.store(stop_from_py, Ordering::Relaxed);
                        stop_cur_thread |= stop_from_py;
                    };
                    Ok(())
                }) {
                    // print python exceptions occured
                    // in this thread and exit...
                    println!("{}", py_e);
                    break;
                }
                // exit when file group parsing is finished or the user stopped.
                if done || stop_cur_thread {
                    break;
                }
                // sleep for 100ms
                thread::sleep(time::Duration::from_millis(100));
            }
            Ok(())
        });
        thread_handles.push(gil_th);
    }

    py.detach(|| -> Result<(), StdfHelperError> {
        // use RAII to join threads
        let _joiner = ThreadJoiner(thread_handles);
        // use RAII to fill bar and stop gil thread
        let _filler = ProgressBarFiller {
            progress: total_progress.clone(),
            done: fgroup_done.clone(),
        };

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

        let mut transaction_count_up = 0usize;
        // writer only binds + steps prepared statements
        for msg in rx {
            match msg {
                DbMessage::Batch(batch) => {
                    let op_count = batch.len();
                    for op in batch {
                        op.apply(&mut db_ctx)?;
                    }
                    // commit and begin a new transaction after a fixed number
                    // of operations
                    transaction_count_up += op_count;
                    if transaction_count_up > 1_000_000 {
                        transaction_count_up = 0;
                        db_ctx.start_new_transaction()?;
                    }
                }
                DbMessage::WorkerError { msg } => {
                    return Err(StdfHelperError { msg });
                }
            }
        }

        // finalize database (flushes the writer-side multi-row batches)
        db_ctx.finalize(build_db_index)?;
        if let Err((_, err)) = conn.close() {
            return Err(StdfHelperError::from(err));
        };
        Ok(())
    })?;

    Ok(())
}

/// read MIR records from a STDF file
/// exit if found
#[pyfunction]
#[pyo3(name = "read_MIR")]
fn read_mir<'py>(py: Python<'py>, fpath: String) -> PyResult<Bound<'py, PyDict>> {
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
fn get_icon_src<'py>(py: Python<'py>, icon_name: String) -> PyResult<Bound<'py, PyBytes>> {
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
                    panic!("Unknown record found! {h:?}");
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

/// Cumulative Distribution Function, used in PP plot.
#[pyfunction]
#[pyo3(name = "norm_cdf")]
fn norm_cdf<'py>(
    py: Python<'py>,
    data: PyReadonlyArray1<f64>,
    mean: f64,
    stddev: f64,
) -> PyResult<Bound<'py, PyArray1<f64>>> {
    let data = data.as_array();
    let mut p = Array1::from_elem(data.len(), f64::NAN);

    if stddev != 0.0 && !stddev.is_nan() {
        Zip::from(&data).and(&mut p).par_for_each(|d, prob| {
            let d_norm = (*d - mean) / stddev;
            *prob = statistic_functions::ndtr(d_norm)
        });
    }
    Ok(p.into_pyarray(py))
}

/// Empirical CDF, used in PP plot.
#[pyfunction]
#[pyo3(name = "empirical_cdf")]
fn empirical_cdf<'py>(
    py: Python<'py>,
    data: PyReadonlyArray1<f64>,
) -> PyResult<Bound<'py, PyArray1<f64>>> {
    // equivalent to scipy.stats.rankdata() in 'max' mode
    let data = data.as_array();
    let dsz = data.len();
    let mut p = Array1::from_elem(dsz, 0.0f64);
    if dsz == 0 {
        return Ok(p.into_pyarray(py));
    }

    let mut idx_sort: Vec<usize> = (0usize..dsz).collect();
    idx_sort.sort_by(|&i, &j| data[i].total_cmp(&data[j]));

    // for same values in data, returns same rank_max
    // need to count repeated number
    let mut i = 0;
    while i < dsz {
        let mut j = i + 1;
        while j < dsz && data[idx_sort[i]] == data[idx_sort[j]] {
            // found duplicates
            j += 1;
        }
        // position of duplicates: [i, j-1]
        // rank begins at 1, and we are in max mode, so:
        let rank = (j - 1) as f64 + 1.0f64;
        for &orig_index in &idx_sort[i..j] {
            p[orig_index] = rank / (dsz as f64);
        }
        i = j;
    }

    Ok(p.into_pyarray(py))
}

/// Inverse of Cumulative Distribution Function, used in QQ plot
#[pyfunction]
#[pyo3(name = "norm_ppf")]
fn norm_ppf<'py>(
    py: Python<'py>,
    p: PyReadonlyArray1<f64>,
    mean: f64,
    stddev: f64,
) -> PyResult<Bound<'py, PyArray1<f64>>> {
    let p = p.as_array();
    let init = if stddev == 0.0 { mean } else { f64::NAN };
    let mut q = Array1::from_elem(p.len(), init);

    if stddev != 0.0 && !stddev.is_nan() {
        Zip::from(&p).and(&mut q).par_for_each(|prob, quantile| {
            let q_norm = statistic_functions::ndtri(*prob);
            *quantile = q_norm * stddev + mean
        });
    }
    Ok(q.into_pyarray(py))
}

/// A Python module implemented in Rust.
#[pymodule]
fn rust_stdf_helper(py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    let test_id_type = PyModule::new(py, "TestIDType")?;
    test_id_type.add("TestNumberAndName", TestIDType::TestNumberAndName)?;
    test_id_type.add("TestNumberOnly", TestIDType::TestNumberOnly)?;

    m.add_submodule(&test_id_type)?;
    m.add_function(wrap_pyfunction!(analyze_stdf_file, m)?)?;
    m.add_function(wrap_pyfunction!(generate_database, m)?)?;
    m.add_function(wrap_pyfunction!(read_mir, m)?)?;
    m.add_function(wrap_pyfunction!(get_icon_src, m)?)?;
    m.add_function(wrap_pyfunction!(stdf_to_xlsx, m)?)?;
    m.add_function(wrap_pyfunction!(norm_cdf, m)?)?;
    m.add_function(wrap_pyfunction!(empirical_cdf, m)?)?;
    m.add_function(wrap_pyfunction!(norm_ppf, m)?)?;
    Ok(())
}
