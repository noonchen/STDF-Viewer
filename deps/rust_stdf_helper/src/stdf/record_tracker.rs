//
// stdf/record_tracker.rs
//
// State tracking during STDF file parsing and processing
//
// Author: noonchen - chennoon233@foxmail.com
// Created Date: Tue Sep 01 2026
// -----
// Last Modified: Tue Sep 01 2026
// Modified By: noonchen
// -----
// Copyright (c) 2022 noonchen
//

use crate::database::operations::{make_test_id, ColdOp, DbOp, TestId};
use crate::StdfHelperError;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::PyInt;
use rust_stdf::*;
use std::collections::HashMap;
use std::convert::Infallible;

#[repr(u32)]
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum TestIDType {
    TestNumberAndName = 0,
    TestNumberOnly = 1,
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

pub struct RecordTracker {
    // determines how the unique test id is constructed
    id_type: TestIDType,

    // (file id, test num) -> (test name -> unique test id)
    //
    // Nested so `TestNumberAndName` lookups can borrow the zero-copy view
    // string and only allocate on the vacant-entry path.
    id_map: HashMap<(usize, u32), HashMap<String, TestId>>,

    // number of unique tests seen by this tracker; local component of TestId
    test_id_counter: usize,

    // unique test id -> result scale
    scale_map: HashMap<TestId, i32>,

    // unique test id -> low limit in 1st PTR
    default_llimit: HashMap<TestId, f32>,
    // unique test id -> high limit in 1st PTR
    default_hlimit: HashMap<TestId, f32>,

    // unique test id -> fail count
    test_fail_count: HashMap<TestId, u32>,

    // file id, head, site -> dut index
    dut_index_tracker: HashMap<(usize, u8, u8), u64>,

    // file id, head -> wafer index
    wafer_index_tracker: HashMap<(usize, u8), u64>,

    // (file id, HBIN) -> (bin name, bin type)
    hbin_tracker: HashMap<(usize, u16), (String, char)>,
    // (file id, SBIN) -> (bin name, bin type)
    sbin_tracker: HashMap<(usize, u16), (String, char)>,

    // DTR/GDR location tracker, file id -> is_before_PRR?
    datalog_pos_tracker: HashMap<usize, bool>,

    // program section tracker
    program_sections: HashMap<usize, Vec<String>>,

    // for counting
    // file id -> dut count
    dut_total: HashMap<usize, u64>,
    // file id -> wafer count
    wafer_total: HashMap<usize, u64>,
}

impl RecordTracker {
    pub fn new(id_type: TestIDType) -> Self {
        RecordTracker {
            id_type,
            id_map: HashMap::with_capacity(1024),
            test_id_counter: 0,
            scale_map: HashMap::with_capacity(1024),
            default_llimit: HashMap::with_capacity(1024),
            default_hlimit: HashMap::with_capacity(1024),
            test_fail_count: HashMap::with_capacity(1024),
            dut_index_tracker: HashMap::with_capacity(128),
            wafer_index_tracker: HashMap::with_capacity(128),
            hbin_tracker: HashMap::with_capacity(128),
            sbin_tracker: HashMap::with_capacity(1024),
            datalog_pos_tracker: HashMap::with_capacity(32),
            program_sections: HashMap::with_capacity(32),
            dut_total: HashMap::with_capacity(32),
            wafer_total: HashMap::with_capacity(32),
        }
    }

    #[inline(always)]
    pub fn pir_detected(&mut self, file_id: usize, pir: &PIRView) -> u64 {
        let head_num = pir.head_num();
        let site_num = pir.site_num();
        // indicating any DTR or GDR is before PRR
        self.datalog_pos_tracker.insert(file_id, true);
        let dut_index;

        if let Some(dut_total) = self.dut_total.get_mut(&file_id) {
            // increment dut_index by 1
            *dut_total += 1;
            // update dut index tracker
            self.dut_index_tracker
                .insert((file_id, head_num, site_num), *dut_total);
            dut_index = *dut_total;
        } else {
            // no dut_index was saved for file id, set dut_index to default 1
            dut_index = 1;
            // insert dut_index=1 to hashmap
            self.dut_total.insert(file_id, dut_index);
            self.dut_index_tracker
                .insert((file_id, head_num, site_num), dut_index);
        };
        dut_index
    }

    #[inline(always)]
    pub fn prr_detected(
        &mut self,
        file_id: usize,
        prr: &PRRView,
    ) -> Result<(u64, Option<u64>), StdfHelperError> {
        let head_num = prr.head_num();
        let site_num = prr.site_num();
        let hard_bin = prr.hard_bin();
        let soft_bin = prr.soft_bin();
        let part_flg = prr.part_flg()[0];
        // in PRR, all BPS should be closed by EPS
        if let Some(pg_sec_list) = self.program_sections.get_mut(&file_id) {
            pg_sec_list.clear();
        };
        // set is_before_PRR to false
        self.datalog_pos_tracker.insert(file_id, false);
        // infer HBIN/SBIN types, it is helpful
        // when file missing HBR/SBR
        // HBIN
        self.hbin_tracker
            .entry((file_id, hard_bin))
            .or_insert_with(|| {
                let hbin_type = if part_flg & 0b00011000 == 0 {
                    'P'
                } else if part_flg & 0b00010000 == 0 {
                    'F'
                } else {
                    'U'
                };
                (String::new(), hbin_type)
            });
        // SBIN
        self.sbin_tracker
            .entry((file_id, soft_bin))
            .or_insert_with(|| {
                let sbin_type = if part_flg & 0b00011000 == 0 {
                    'P'
                } else if part_flg & 0b00010000 == 0 {
                    'F'
                } else {
                    'U'
                };
                (String::new(), sbin_type)
            });
        // get dut_index
        let dut_index = match self.dut_index_tracker.get(&(file_id, head_num, site_num)) {
            Some(stored_ind) => Ok(*stored_ind),
            // if dut_index is None, returns Err
            None => Err(StdfHelperError { msg: format!("STDF file structure error in File[{}]: PRR Head[{}] Site[{}] showed up before PIR", file_id, head_num, site_num) }),
        }?;
        // get wafer_index if WIR is detected
        let wafer_index = self.wafer_index_tracker.get(&(file_id, head_num)).copied();
        Ok((dut_index, wafer_index))
    }

    #[inline(always)]
    pub fn hbr_detected(&mut self, file_id: usize, hbr: &HBRView) {
        let bin_num = hbr.hbin_num();
        let bin_pf = hbr.hbin_pf();
        let bin_name = hbr.hbin_nam().as_str();
        let bin_pf = if bin_pf == 'P' || bin_pf == 'F' {
            bin_pf
        } else {
            'U'
        };
        // since HBR is valid, we can drop the inferred info from PRR
        if let Some((name, pf)) = self.hbin_tracker.get_mut(&(file_id, bin_num)) {
            // update name & Pass/Fail if exist
            if !bin_name.is_empty() {
                *name = bin_name.to_string();
            };
            *pf = bin_pf;
        } else {
            // insert if not exist
            self.hbin_tracker
                .insert((file_id, bin_num), (bin_name.to_string(), bin_pf));
        }
    }

    #[inline(always)]
    pub fn sbr_detected(&mut self, file_id: usize, sbr: &SBRView) {
        let bin_num = sbr.sbin_num();
        let bin_pf = sbr.sbin_pf();
        let bin_name = sbr.sbin_nam().as_str();
        let bin_pf = if bin_pf == 'P' || bin_pf == 'F' {
            bin_pf
        } else {
            'U'
        };
        // since HBR is valid, we can drop the inferred info from PRR
        if let Some((name, pf)) = self.sbin_tracker.get_mut(&(file_id, bin_num)) {
            // update name & Pass/Fail if exist
            if !bin_name.is_empty() {
                *name = bin_name.to_string();
            };
            *pf = bin_pf;
        } else {
            // insert if not exist
            self.sbin_tracker
                .insert((file_id, bin_num), (bin_name.to_string(), bin_pf));
        }
    }

    #[inline(always)]
    pub fn wir_detected(&mut self, file_id: usize, wir: &WIRView) -> u64 {
        let head_num = wir.head_num();
        let wafer_index;

        if let Some(wafer_total) = self.wafer_total.get_mut(&file_id) {
            // increment by 1
            *wafer_total += 1;
            // update wafer index tracker
            self.wafer_index_tracker
                .insert((file_id, head_num), *wafer_total);
            wafer_index = *wafer_total;
        } else {
            // set default 1 if not exists
            wafer_index = 1;
            self.wafer_total.insert(file_id, wafer_index);
            self.wafer_index_tracker
                .insert((file_id, head_num), wafer_index);
        };
        wafer_index
    }

    /// return (exist, scale) for [PTR], [MPR]
    #[inline(always)]
    pub fn update_scale(&mut self, test_id: TestId, scale: &Option<i8>) -> (bool, i32) {
        match self.scale_map.get(&test_id) {
            Some(s) => (true, *s),
            None => {
                // new test_id, insert into map
                // if scale is None, use 0 instead, for
                // it have no effect on the result
                let s = scale.unwrap_or(0) as i32;
                self.scale_map.insert(test_id, s);
                (false, s)
            }
        }
    }

    /// return (dut_index, test_id) for [PTR], [FTR], [MPR] or maybe [STR] in the future
    ///
    /// `test_txt` is only used in the `TestNumberAndName` mode,
    /// pass `None` in `TestNumberOnly` mode
    #[inline(always)]
    pub fn xtr_detected_optional(
        &mut self,
        file_id: usize,
        head_num: u8,
        site_num: u8,
        test_num: u32,
        test_txt: Option<&str>,
    ) -> Result<(u64, TestId), StdfHelperError> {
        // get dut_index
        let dut_index = match self.dut_index_tracker.get( &(file_id, head_num, site_num) ) {
            Some(stored_ind) => Ok(*stored_ind),
            // if dut_index is None, returns Err
            None => Err(StdfHelperError { msg: format!("STDF file structure error in File[{}]: TestNumber[{}] Head[{}] Site[{}] showed up before PIR", file_id, test_num, head_num, site_num) }),
        }?;

        let names = self.id_map.entry((file_id, test_num)).or_default();
        let test_id = match self.id_type {
            TestIDType::TestNumberAndName => {
                let test_txt = test_txt.ok_or_else(|| StdfHelperError {
                    msg: format!(
                        "Missing test name for test number [{}] in File[{}]",
                        test_num, file_id
                    ),
                })?;
                match names.get(test_txt) {
                    Some(id) => *id,
                    None => {
                        let local_id = self.test_id_counter;
                        self.test_id_counter += 1;
                        let unique_id = make_test_id(file_id, local_id)?;
                        names.insert(test_txt.to_owned(), unique_id);
                        unique_id
                    }
                }
            }
            // Test Name is not used, use empty string for placeholder
            TestIDType::TestNumberOnly => match names.get("") {
                Some(id) => *id,
                None => {
                    let local_id = self.test_id_counter;
                    self.test_id_counter += 1;
                    let unique_id = make_test_id(file_id, local_id)?;
                    names.insert(String::new(), unique_id);
                    unique_id
                }
            },
        };
        Ok((dut_index, test_id))
    }

    #[inline(always)]
    pub fn uses_test_name(&self) -> bool {
        self.id_type == TestIDType::TestNumberAndName
    }

    /// return `true` if test_id is already in both limit hashmaps
    #[inline(always)]
    pub fn default_limits_contains_id(&mut self, test_id: TestId) -> bool {
        let llimit_exist = self.default_llimit.contains_key(&test_id);
        let hlimit_exist = self.default_hlimit.contains_key(&test_id);

        llimit_exist && hlimit_exist
    }

    /// return `true` if test_id is already in hashmap, no update
    #[inline(always)]
    pub fn update_default_limits(&mut self, test_id: TestId, llimit: f32, hlimit: f32) -> bool {
        let llimit_exist = self.default_llimit.contains_key(&test_id);
        let hlimit_exist = self.default_hlimit.contains_key(&test_id);

        if !llimit_exist {
            // update llimit
            self.default_llimit.insert(test_id, llimit);
        }
        if !hlimit_exist {
            // update hlimit
            self.default_hlimit.insert(test_id, hlimit);
        }
        llimit_exist && hlimit_exist
    }

    /// return (llimit_changed, hlimit_changed) if [PTR] limits is differ from that of 1st PTR
    ///
    /// ## Error
    /// if no default limit can be found for test_id
    #[inline(always)]
    pub fn is_ptr_limits_changed(
        &self,
        test_id: TestId,
        llimit: f32,
        hlimit: f32,
    ) -> Result<(bool, bool), StdfHelperError> {
        // llimit
        let llimit_changed = match self.default_llimit.get(&test_id) {
            Some(dft_ll) => {
                // NAN - NAN > EPSILON is `false`
                // meaning if limit is NAN, it will return false
                Ok((llimit - *dft_ll).abs() > f32::EPSILON)
            }
            None => Err(StdfHelperError {
                msg: format!(
                    "Default low limit of Test ID [{}] cannot be read...this should never happen",
                    test_id
                ),
            }),
        }?;
        // hlimit
        let hlimit_changed = match self.default_hlimit.get(&test_id) {
            Some(dft_hl) => Ok((hlimit - *dft_hl).abs() > f32::EPSILON),
            None => Err(StdfHelperError {
                msg: format!(
                    "Default high limit of Test ID [{}] cannot be read...this should never happen",
                    test_id
                ),
            }),
        }?;
        Ok((llimit_changed, hlimit_changed))
    }

    #[inline(always)]
    pub fn get_program_section(&self, file_id: usize) -> Option<String> {
        // use `;` to join all sections
        self.program_sections
            .get(&file_id)
            .map(|pg_sec_list| pg_sec_list.join(";"))
    }

    #[inline(always)]
    pub fn get_wafer_index(&self, file_id: usize, head_num: u8) -> Result<u64, StdfHelperError> {
        match self.wafer_index_tracker.get(&(file_id, head_num)) {
            Some(ind) => Ok(*ind),
            None => Err(StdfHelperError {
                msg: format!(
                    "STDF file structure error in File[{}]: WRR Head[{}] showed up before WIR",
                    file_id, head_num
                ),
            }),
        }
    }

    #[inline(always)]
    pub fn tsr_detected(&mut self, file_id: usize, tsr: &TSRView) -> Result<(), StdfHelperError> {
        let test_num = tsr.test_num();
        let test_name_storage = tsr.test_nam().as_str();
        let test_name = test_name_storage.as_ref();
        let fail_cnt = tsr.fail_cnt();
        let names = self.id_map.get(&(file_id, test_num));
        let test_id = match self.id_type {
            TestIDType::TestNumberAndName => match names.and_then(|m| m.get(test_name)) {
                Some(id) => Ok(*id),
                None => match names.and_then(|m| m.iter().next()) {
                    Some((name, id)) => {
                        println!(
                                "TSR: [{}\t{}] matches no records in File[{}], use test name [{}] instead",
                                test_num, test_name, file_id, name
                            );
                        Ok(*id)
                    }
                    None => Err(StdfHelperError {
                        msg: format!(
                            "Test number [{}] in TSR matches no records in File[{}]",
                            test_num, file_id
                        ),
                    }),
                },
            },
            TestIDType::TestNumberOnly => match names.and_then(|m| m.get("")) {
                Some(id) => Ok(*id),
                None => match names.and_then(|m| m.iter().next()) {
                    Some((name, id)) => {
                        println!(
                            "TSR: [{}\t{}] matches no records in File[{}], use test name [{}] instead",
                            test_num, test_name, file_id, name
                        );
                        Ok(*id)
                    }
                    None => Err(StdfHelperError {
                        msg: format!(
                            "Test number [{}] in TSR matches no records in File[{}]",
                            test_num, file_id
                        ),
                    }),
                },
            },
        }?;
        // update fail cnt hashmap, only when fail cnt is valid
        if fail_cnt != u32::MAX {
            if let Some(cnt) = self.test_fail_count.get_mut(&test_id) {
                *cnt += fail_cnt;
            } else {
                // if test id is not exist, insert
                self.test_fail_count.insert(test_id, fail_cnt);
            }
        }
        Ok(())
    }

    #[inline(always)]
    pub fn get_datalog_relative_pos(&self, file_id: usize) -> (u64, bool) {
        let dut_index = match self.dut_total.get(&file_id) {
            Some(ind) => *ind,
            // DTR/GDR can appear any where in the file,
            // if it's before the 1st PIR, `None` is matched.
            None => 0,
        };
        let is_before_prr = match self.datalog_pos_tracker.get(&file_id) {
            Some(b) => *b,
            // same as above
            None => true,
        };
        (dut_index, is_before_prr)
    }

    #[inline(always)]
    pub fn bps_detected(&mut self, file_id: usize, bps: &BPSView) -> Result<(), StdfHelperError> {
        let seq_name_storage = bps.seq_name().as_str();
        let seq_name = seq_name_storage.as_ref();
        self.program_sections
            .entry(file_id)
            .and_modify(|v| v.push(seq_name.to_owned()))
            .or_insert_with(|| vec![seq_name.to_owned()]);
        Ok(())
    }

    #[inline(always)]
    pub fn eps_detected(&mut self, file_id: usize) -> Result<(), StdfHelperError> {
        self.program_sections.entry(file_id).and_modify(|v| {
            v.pop();
        });
        Ok(())
    }

    /// Append group-EOF summary ops in the same order as the legacy writer:
    /// HBR, SBR, then TSR fail counts.
    pub fn append_summary_ops(&self, ops: &mut Vec<DbOp>) {
        for (&(file_id, bin_num), (bin_nam, bin_pf)) in self.hbin_tracker.iter() {
            ops.push(DbOp::Cold(Box::new(ColdOp::Hbin {
                fid: file_id,
                bin_num,
                bin_name: bin_nam.clone(),
                bin_pf: *bin_pf,
            })));
        }
        for (&(file_id, bin_num), (bin_nam, bin_pf)) in self.sbin_tracker.iter() {
            ops.push(DbOp::Cold(Box::new(ColdOp::Sbin {
                fid: file_id,
                bin_num,
                bin_name: bin_nam.clone(),
                bin_pf: *bin_pf,
            })));
        }
        for (&test_id, &fail_cnt) in self.test_fail_count.iter() {
            ops.push(DbOp::Cold(Box::new(ColdOp::FailCount {
                test_id,
                count: fail_cnt,
            })));
        }
    }
}
