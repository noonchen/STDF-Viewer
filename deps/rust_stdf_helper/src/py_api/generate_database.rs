//
// generate_database.rs
//
// Generate SQLite3 database for given STDF files.
//
// Author: noonchen - chennoon233@foxmail.com
// Created Date: Tue Sep 01 2026
// -----
// Last Modified: Tue Sep 01 2026
// Modified By: noonchen
// -----
// Copyright (c) 2022 noonchen
//

use crate::database::context::DatabaseCtx;
use crate::database::operations::{DbMessage, DbOp};
use crate::generic::error::StdfHelperError;
use crate::generic::helper::get_file_size;
use crate::stdf::record_processor::process_record_view;
use crate::stdf::record_tracker::{RecordTracker, TestIDType};
use crossbeam_channel;
use pyo3::exceptions::PyValueError;
use pyo3::intern;
use pyo3::prelude::*;
use pyo3::types::PyBool;
use rusqlite::Connection;
use rust_stdf::{stdf_file::*, StdfRecordView};
use std::sync::atomic::{AtomicBool, AtomicU16, Ordering};
use std::sync::Arc;
use std::{thread, time};

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

/// create sqlite3 database for given stdf files
#[pyfunction]
#[pyo3(name = "generate_database")]
pub fn generate_database(
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
        let mut db_ctx = DatabaseCtx::new(&conn)?;

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
