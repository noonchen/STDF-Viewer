//
// analyze_stdf.rs
//
// Display record layout of a STDF file, including
// basic checks.
//
// Author: noonchen - chennoon233@foxmail.com
// Created Date: Tue Sep 01 2026
// -----
// Last Modified: Tue Sep 01 2026
// Modified By: noonchen
// -----
// Copyright (c) 2022 noonchen
//

use crate::generic::helper::get_file_size;
use pyo3::exceptions::{PyException, PyOSError};
use pyo3::intern;
use pyo3::prelude::*;
use pyo3::types::PyBool;
use rust_stdf::{stdf_file::*, stdf_record_type::*, StdfRecordView};
use std::collections::{HashMap, HashSet};

/// Analyze record types in a STDF file
#[pyfunction]
#[pyo3(name = "analyzeSTDF")]
pub fn analyze_stdf(
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
