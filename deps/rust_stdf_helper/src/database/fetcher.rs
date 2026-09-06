// fetcher.rs
//
// Pure Rust data fetcher with the cache design agreed for the Python reference.
//
// Author: noonchen - chennoon233@foxmail.com
// Created Date: Tue Sep 01 2026
// -----
// Last Modified: Tue Sep 01 2026
// Modified By: noonchen
// -----
// Copyright (c) 2026 noonchen
//

use crate::generic::error::StdfHelperError;
use lru::LruCache;
use ndarray::{Array1, Array2};
use rusqlite::Connection;
use std::collections::HashMap;
use std::num::NonZeroUsize;

#[derive(Debug, Clone)]
pub struct TestInfo {
    pub test_id: i64,
    pub rec_header: i64,
    pub test_num: i64,
    pub test_name: String,
    pub res_scal: Option<i64>,
    pub llimit: Option<f64>,
    pub hlimit: Option<f64>,
    pub unit: Option<String>,
    pub opt_flag: Option<i64>,
    pub fail_count: Option<i64>,
    pub rtn_icnt: Option<i64>,
    pub rslt_pgm_cnt: Option<i64>,
    pub lspec: Option<f64>,
    pub hspec: Option<f64>,
    pub vect_nam: Option<String>,
    pub seq_name: Option<String>,
}

pub struct TestDataCacheEntry {
    pub rec_header: i64,
    pub data: Array2<f32>,
    pub flags: Array1<i16>,
    pub states: Option<Array2<u8>>,
    pub valid_test_idx: Vec<usize>,
}

pub struct FetchedTestData {
    pub rec_header: i64,
    pub dut_list: Array1<u32>,
    pub data: Array2<f32>,
    pub flags: Array1<i16>,
    pub states: Option<Array2<u8>>,
}

pub struct DataFetcher {
    conn: Connection,
    file_paths: Vec<Vec<String>>,
    full_dut: HashMap<usize, Array1<u32>>,
    head_site_idx: HashMap<(usize, i64, Option<i64>), Vec<usize>>,
    test_info: HashMap<(usize, i64, String), TestInfo>,
    test_data: LruCache<(i64, usize), TestDataCacheEntry>,
}

impl DataFetcher {
    pub fn open(path: &str) -> Result<Self, StdfHelperError> {
        let conn = Connection::open(path)?;
        let mut fetcher = Self {
            conn,
            file_paths: Vec::new(),
            full_dut: HashMap::new(),
            head_site_idx: HashMap::new(),
            test_info: HashMap::new(),
            test_data: LruCache::new(NonZeroUsize::new(128).unwrap()),
        };
        fetcher.read_file_paths()?;
        fetcher.build_file_caches()?;
        Ok(fetcher)
    }

    pub fn close(&self) {}

    pub fn num_files(&self) -> usize {
        self.file_paths.len()
    }

    pub fn file_paths(&self) -> Vec<Vec<String>> {
        self.file_paths.clone()
    }

    pub fn read_file_paths(&mut self) -> Result<(), StdfHelperError> {
        let mut d: HashMap<i64, Vec<String>> = HashMap::new();
        {
            let mut stmt = self.conn.prepare(
                "SELECT Fid, Filename FROM File_List ORDER BY Fid, SubFid",
            )?;
            let rows = stmt.query_map([], |row| {
                Ok((row.get::<_, i64>(0)?, row.get::<_, String>(1)?))
            })?;
            for row in rows {
                let (fid, path) = row?;
                d.entry(fid).or_default().push(path);
            }
        }
        let mut keys: Vec<i64> = d.keys().copied().collect();
        keys.sort_unstable();
        let mut paths = Vec::new();
        for fid in keys {
            paths.push(d.remove(&fid).unwrap());
        }
        self.file_paths = paths;
        Ok(())
    }

    fn build_file_caches(&mut self) -> Result<(), StdfHelperError> {
        for fid in 0..self.num_files() {
            let n: i64 = self.conn.query_row(
                "SELECT MAX(DUTIndex) FROM Dut_Info WHERE Fid=?",
                [fid as i64],
                |row| row.get(0),
            )?;
            let n = n.max(0) as usize;
            self.full_dut
                .insert(fid, Array1::from_iter(1..=n as u32));

            let mut site_lists: HashMap<(i64, i64), Vec<usize>> = HashMap::new();
            let mut head_lists: HashMap<i64, Vec<usize>> = HashMap::new();
            {
                let mut stmt = self.conn.prepare(
                    "SELECT DUTIndex, HEAD_NUM, SITE_NUM FROM Dut_Info WHERE Fid=? AND Supersede=0",
                )?;
                let rows = stmt.query_map([fid as i64], |row| {
                    Ok((
                        row.get::<_, i64>(0)?,
                        row.get::<_, i64>(1)?,
                        row.get::<_, i64>(2)?,
                    ))
                })?;
                for row in rows {
                    let (dut_index, head, site) = row?;
                    let idx = dut_index as usize - 1;
                    site_lists.entry((head, site)).or_default().push(idx);
                    head_lists.entry(head).or_default().push(idx);
                }
            }
            for ((head, site), mut vals) in site_lists {
                vals.sort_unstable();
                self.head_site_idx.insert((fid, head, Some(site)), vals);
            }
            for (head, mut vals) in head_lists {
                vals.sort_unstable();
                self.head_site_idx.insert((fid, head, None), vals);
            }
        }
        Ok(())
    }

    pub fn get_site_list(&self) -> Result<Vec<i64>, StdfHelperError> {
        let mut stmt = self
            .conn
            .prepare("SELECT DISTINCT SITE_NUM FROM Dut_Info")?;
        let sites = stmt
            .query_map([], |row| row.get::<_, i64>(0))?
            .collect::<Result<Vec<_>, _>>()?;
        Ok(sites)
    }

    pub fn get_head_list(&self) -> Result<Vec<i64>, StdfHelperError> {
        let mut stmt = self
            .conn
            .prepare("SELECT DISTINCT HEAD_NUM FROM Dut_Info")?;
        let heads = stmt
            .query_map([], |row| row.get::<_, i64>(0))?
            .collect::<Result<Vec<_>, _>>()?;
        Ok(heads)
    }

    pub fn get_test_info(
        &mut self,
        test_tup: (i64, &str),
        file_id: usize,
    ) -> Result<Option<TestInfo>, StdfHelperError> {
        let key = (file_id, test_tup.0, test_tup.1.to_string());
        if let Some(info) = self.test_info.get(&key) {
            return Ok(Some(info.clone()));
        }
        let info = self.conn.query_row(
            "SELECT TEST_ID, recHeader, TEST_NUM, TEST_NAME, RES_SCAL, LLimit, HLimit, Unit, OPT_FLAG, FailCount, RTN_ICNT, RSLT_PGM_CNT, LSpec, HSpec, VECT_NAM, SEQ_NAME \
             FROM Test_Info WHERE Fid=? AND TEST_NUM=? AND TEST_NAME=?",
            rusqlite::params![file_id as i64, test_tup.0, test_tup.1],
            |row| {
                Ok(TestInfo {
                    test_id: row.get(0)?,
                    rec_header: row.get(1)?,
                    test_num: row.get(2)?,
                    test_name: row.get(3)?,
                    res_scal: row.get(4)?,
                    llimit: row.get(5)?,
                    hlimit: row.get(6)?,
                    unit: row.get(7)?,
                    opt_flag: row.get(8)?,
                    fail_count: row.get(9)?,
                    rtn_icnt: row.get(10)?,
                    rslt_pgm_cnt: row.get(11)?,
                    lspec: row.get(12)?,
                    hspec: row.get(13)?,
                    vect_nam: row.get(14)?,
                    seq_name: row.get(15)?,
                })
            },
        );
        match info {
            Ok(info) => {
                self.test_info.insert(key, info.clone());
                Ok(Some(info))
            }
            Err(rusqlite::Error::QueryReturnedNoRows) => Ok(None),
            Err(e) => Err(e.into()),
        }
    }

    fn ensure_test_data(
        &mut self,
        test_id: i64,
        rec_header: i64,
        file_id: usize,
    ) -> Result<TestDataCacheEntry, StdfHelperError> {
        let key = (test_id, file_id);
        if let Some(entry) = self.test_data.get(&key) {
            return Ok(clone_entry(entry));
        }

        let n = self.full_dut.get(&file_id).map(|a| a.len()).unwrap_or(0);
        let mut flags = Array1::from_elem(n, -1i16);
        let mut valid = Vec::new();

        let entry = if rec_header == 10 {
            let mut data = Array2::from_elem((n, 1), f32::NAN);
            {
                let mut stmt = self.conn.prepare(
                    "SELECT DUTIndex, RESULT, TEST_FLAG FROM PTR_Data WHERE TEST_ID=? ORDER BY DUTIndex",
                )?;
                let rows = stmt.query_map([test_id], |row| {
                    Ok((
                        row.get::<_, i64>(0)?,
                        row.get::<_, f32>(1)?,
                        row.get::<_, i64>(2)?,
                    ))
                })?;
                for row in rows {
                    let (dut_index, result, flag) = row?;
                    let pos = dut_index as usize - 1;
                    if pos < n {
                        data[[pos, 0]] = result;
                        flags[pos] = flag as i16;
                        valid.push(pos);
                    }
                }
            }
            TestDataCacheEntry {
                rec_header,
                data,
                flags,
                states: None,
                valid_test_idx: valid,
            }
        } else if rec_header == 20 {
            let mut data = Array2::from_elem((n, 0), 0.0f32);
            {
                let mut stmt = self.conn.prepare(
                    "SELECT DUTIndex, TEST_FLAG FROM FTR_Data WHERE TEST_ID=? ORDER BY DUTIndex",
                )?;
                let rows = stmt.query_map([test_id], |row| {
                    Ok((row.get::<_, i64>(0)?, row.get::<_, i64>(1)?))
                })?;
                for row in rows {
                    let (dut_index, flag) = row?;
                    let pos = dut_index as usize - 1;
                    if pos < n {
                        flags[pos] = flag as i16;
                        valid.push(pos);
                    }
                }
            }
            TestDataCacheEntry {
                rec_header,
                data,
                flags,
                states: None,
                valid_test_idx: valid,
            }
        } else if rec_header == 15 {
            let rows_vec: Vec<(i64, String, String, i64)> = {
                let mut stmt = self.conn.prepare(
                    "SELECT DUTIndex, RTN_RSLT, RTN_STAT, TEST_FLAG FROM MPR_Data WHERE TEST_ID=? ORDER BY DUTIndex",
                )?;
                let rows = stmt.query_map([test_id], |row| {
                    Ok((
                        row.get::<_, i64>(0)?,
                        row.get::<_, String>(1)?,
                        row.get::<_, String>(2)?,
                        row.get::<_, i64>(3)?,
                    ))
                })?;
                rows.collect::<Result<Vec<_>, _>>()?
            };
            let rslt_cnt = if rows_vec.is_empty() {
                0
            } else {
                rows_vec[0].1.len() / 8
            };
            if rslt_cnt == 0 {
                TestDataCacheEntry {
                    rec_header,
                    data: Array2::from_shape_fn((n, 0), |_| f32::NAN),
                    flags,
                    states: Some(Array2::from_shape_fn((n, 0), |_| 0xFu8)),
                    valid_test_idx: valid,
                }
            } else {
                let mut data = Array2::from_elem((n, rslt_cnt), f32::NAN);
                let mut states = Array2::from_elem((n, rslt_cnt), 0xFu8);
                for (dut_index, rslt_hex, stat_hex, flag) in rows_vec {
                    let pos = (dut_index - 1) as usize;
                    if pos < n {
                        let result = hex_to_f32s(&rslt_hex);
                        let stat = hex_to_u8s(&stat_hex);
                        flags[pos] = flag as i16;
                        valid.push(pos);
                        for (j, value) in result.into_iter().enumerate() {
                            data[[pos, j]] = value;
                        }
                        for (j, value) in stat.into_iter().enumerate() {
                            states[[pos, j]] = value;
                        }
                    }
                }
                TestDataCacheEntry {
                    rec_header,
                    data,
                    flags,
                    states: Some(states),
                    valid_test_idx: valid,
                }
            }
        } else {
            TestDataCacheEntry {
                rec_header,
                data: Array2::from_shape_fn((n, 0), |_| f32::NAN),
                flags,
                states: None,
                valid_test_idx: valid,
            }
        };

        let _ = self.test_data.push(key, clone_entry(&entry));
        Ok(entry)
    }

    pub fn get_test_data_from_head_site(
        &mut self,
        test_tup: (i64, &str),
        heads: &[i64],
        sites: &[i64],
        file_id: usize,
    ) -> Result<Option<FetchedTestData>, StdfHelperError> {
        let info = match self.get_test_info(test_tup, file_id)? {
            Some(info) => info,
            None => return Ok(None),
        };

        let mut selected: Vec<usize> = Vec::new();
        if sites.contains(&-1) {
            for &head in heads {
                if let Some(list) = self.head_site_idx.get(&(file_id, head, None)) {
                    selected.extend_from_slice(list);
                }
            }
        } else {
            for &head in heads {
                for &site in sites {
                    if let Some(list) = self.head_site_idx.get(&(file_id, head, Some(site))) {
                        selected.extend_from_slice(list);
                    }
                }
            }
        }
        selected.sort_unstable();
        selected.dedup();

        let entry = self.ensure_test_data(info.test_id, info.rec_header, file_id)?;
        let idx = intersect_sorted(&selected, &entry.valid_test_idx);
        Ok(Some(make_fetched_data(
            self.full_dut.get(&file_id).unwrap(),
            &entry,
            &idx,
        )))
    }

    pub fn get_test_data_from_dut_index(
        &mut self,
        test_tup: (i64, &str),
        duts: &[i64],
        file_id: usize,
    ) -> Result<Option<FetchedTestData>, StdfHelperError> {
        let info = match self.get_test_info(test_tup, file_id)? {
            Some(info) => info,
            None => return Ok(None),
        };
        if duts.is_empty() {
            return Ok(None);
        }
        let entry = self.ensure_test_data(info.test_id, info.rec_header, file_id)?;
        let n = self.full_dut.get(&file_id).map(|a| a.len()).unwrap_or(0);
        let mut sorted_duts = duts.to_vec();
        sorted_duts.sort_unstable();
        let idx: Vec<usize> = sorted_duts
            .iter()
            .filter_map(|&dut| {
                let pos = dut - 1;
                if pos >= 0 && (pos as usize) < n {
                    Some(pos as usize)
                } else {
                    None
                }
            })
            .collect();
        Ok(Some(make_fetched_data(
            self.full_dut.get(&file_id).unwrap(),
            &entry,
            &idx,
        )))
    }
}

fn make_fetched_data(
    full_dut: &Array1<u32>,
    entry: &TestDataCacheEntry,
    idx: &[usize],
) -> FetchedTestData {
    let dut_list: Array1<u32> = full_dut.select(ndarray::Axis(0), idx);

    if entry.rec_header == 10 {
        let data2 = entry.data.select(ndarray::Axis(0), idx);
        let mut flat = Array1::from_elem(idx.len(), f32::NAN);
        for (i, row) in data2.outer_iter().enumerate() {
            flat[i] = row[0];
        }
        FetchedTestData {
            rec_header: entry.rec_header,
            dut_list,
            data: flat.into_shape((idx.len(), 1)).unwrap(),
            flags: entry.flags.select(ndarray::Axis(0), idx),
            states: None,
        }
    } else if entry.rec_header == 15 {
        let data = entry.data.select(ndarray::Axis(0), idx);
        let states = entry
            .states
            .as_ref()
            .map(|s| s.select(ndarray::Axis(0), idx));
        FetchedTestData {
            rec_header: entry.rec_header,
            dut_list,
            data,
            flags: entry.flags.select(ndarray::Axis(0), idx),
            states,
        }
    } else {
        FetchedTestData {
            rec_header: entry.rec_header,
            dut_list,
            data: Array2::from_shape_fn((idx.len(), 0), |_| 0.0f32),
            flags: entry.flags.select(ndarray::Axis(0), idx),
            states: None,
        }
    }
}

fn clone_entry(entry: &TestDataCacheEntry) -> TestDataCacheEntry {
    TestDataCacheEntry {
        rec_header: entry.rec_header,
        data: entry.data.clone(),
        flags: entry.flags.clone(),
        states: entry.states.clone(),
        valid_test_idx: entry.valid_test_idx.clone(),
    }
}

fn intersect_sorted(a: &[usize], b: &[usize]) -> Vec<usize> {
    let mut result = Vec::new();
    let (mut i, mut j) = (0, 0);
    while i < a.len() && j < b.len() {
        if a[i] == b[j] {
            result.push(a[i]);
            i += 1;
            j += 1;
        } else if a[i] < b[j] {
            i += 1;
        } else {
            j += 1;
        }
    }
    result
}

fn hex_to_f32s(hex: &str) -> Vec<f32> {
    hex_bytes(hex)
        .chunks_exact(4)
        .map(|c| f32::from_le_bytes([c[0], c[1], c[2], c[3]]))
        .collect()
}

fn hex_to_u8s(hex: &str) -> Vec<u8> {
    hex_bytes(hex)
}

fn hex_bytes(hex: &str) -> Vec<u8> {
    let mut bytes = Vec::with_capacity(hex.len() / 2);
    let chars: Vec<char> = hex.chars().collect();
    let mut i = 0;
    while i + 1 < chars.len() {
        if let (Some(hi), Some(lo)) = (
            chars[i].to_digit(16),
            chars[i + 1].to_digit(16),
        ) {
            bytes.push(((hi << 4) | lo) as u8);
        }
        i += 2;
    }
    bytes
}
