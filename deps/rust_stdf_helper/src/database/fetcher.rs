// fetcher.rs
//
// Pure Rust data fetcher with typed STDF domain values and cached access.
//
// Author: noonchen - chennoon233@foxmail.com
// Created Date: Tue Sep 01 2026
// -----
// Last Modified: Tue Sep 01 2026
// Modified By: noonchen
// -----
// Copyright (c) 2026 noonchen
//

use crate::database::operations::TestId;
use crate::database::schema::{
    FETCH_SELECT_DUT_HEAD_SITE, FETCH_SELECT_FILE_LIST, FETCH_SELECT_FTR_DATA,
    FETCH_SELECT_HEAD_LIST, FETCH_SELECT_MAX_DUT_INDEX, FETCH_SELECT_MPR_DATA,
    FETCH_SELECT_PTR_DATA, FETCH_SELECT_SITE_LIST, FETCH_SELECT_TEST_INFO,
};
use crate::generic::error::StdfHelperError;
use lru::LruCache;
use ndarray::{Array1, Array2};
use rusqlite::Connection;
use std::collections::HashMap;
use std::num::NonZeroUsize;

pub type HeadNum = u8;
pub type SiteNum = u8;
pub type TestNum = u32;

/// Single source of truth for the `SUB_CODE` column values (PTR/MPR/FTR),
/// defined with the STDF tracker and re-exported here so the database and
/// PyO3 layers never spell out the raw 10/15/20 codes.
pub use crate::stdf::record_tracker::TestSubCode;

#[derive(Debug, Clone)]
pub struct TestInfo {
    pub test_id: TestId,
    pub sub_code: TestSubCode,
    pub test_num: TestNum,
    pub test_name: String,
    pub res_scal: Option<i8>,
    pub llimit: Option<f32>,
    pub hlimit: Option<f32>,
    pub unit: Option<String>,
    pub opt_flag: Option<u8>,
    pub fail_count: i32,
    pub rtn_icnt: Option<u16>,
    pub rslt_pgm_cnt: Option<u16>,
    pub lspec: Option<f32>,
    pub hspec: Option<f32>,
    pub vect_nam: Option<String>,
    pub seq_name: Option<String>,
}

pub struct TestDataCacheEntry {
    pub sub_code: TestSubCode,
    pub data: Array2<f32>,
    pub flags: Array1<i16>,
    pub states: Option<Array2<u8>>,
    pub valid_test_idx: Vec<usize>,
}

pub struct FetchedTestData {
    pub sub_code: TestSubCode,
    pub dut_list: Array1<u32>,
    pub data: Array2<f32>,
    pub flags: Array1<i16>,
    pub states: Option<Array2<u8>>,
}

/// Default byte budget for the Tier-2 test-data LRU (see plan §3.3/§7).
const DEFAULT_TEST_CACHE_BUDGET_BYTES: usize = 128 * 1024 * 1024; // 128 MiB

/// Rough in-memory footprint of one cached test-data entry, in bytes.
/// Mirrors the plan §7 estimate: data f32 ×1, flags i16 ×2 (plan allows i16 or u8),
/// states u8 ×1 (MPR), valid_test_idx usize ×8, plus a small constant overhead.
fn estimate_entry_bytes(entry: &TestDataCacheEntry) -> usize {
    const ENTRY_OVERHEAD: usize = 64;
    entry.data.len() * 4
        + entry.flags.len() * 2
        + entry.states.as_ref().map_or(0, |s| s.len() * 1)
        + entry.valid_test_idx.len() * 8
        + ENTRY_OVERHEAD
}

/// Tier-2 test-data cache: LRU eviction ordered by recency but bounded by a
/// byte budget instead of an entry count (plan §3.3 "memory-bounded LRU").
/// Entries are stored per `(test_id, fid)` and aligned to the shared full-DUT
/// array, so MPR entries cost `rslt_cnt ×` more than PTR ones — a byte budget
/// is required, an entry count is not sufficient.
struct TestDataLru {
    cache: LruCache<(TestId, usize), TestDataCacheEntry>,
    budget_bytes: usize,
    used_bytes: usize,
}

impl TestDataLru {
    fn new(budget_bytes: usize) -> Self {
        // The byte budget is the binding constraint; the count capacity only
        // guards hashbrown bookkeeping. Every resident entry costs at least
        // ENTRY_OVERHEAD (64) bytes, so `budget_bytes / 64` is a safe upper
        // bound on the number of resident entries — a larger count capacity
        // (e.g. usize::MAX) overflows hashbrown's capacity arithmetic.
        // Clamped to keep the hash table allocation sane for huge budgets.
        let count_capacity = (budget_bytes / 64).clamp(1, 1 << 30);
        Self {
            cache: LruCache::new(NonZeroUsize::new(count_capacity).expect("capacity >= 1")),
            budget_bytes,
            used_bytes: 0,
        }
    }

    fn get(&mut self, key: &(TestId, usize)) -> Option<&TestDataCacheEntry> {
        self.cache.get(key)
    }

    /// Insert an entry and evict least-recently-used entries until the byte
    /// budget is satisfied again. Entries larger than the whole budget are not
    /// cached (they would evict everything and immediately re-blow the budget);
    /// the caller still returns the freshly computed data to Python.
    fn insert(&mut self, key: (TestId, usize), entry: TestDataCacheEntry) {
        let bytes = estimate_entry_bytes(&entry);
        if bytes > self.budget_bytes {
            return;
        }
        self.used_bytes += bytes;
        self.cache.put(key, entry);
        while self.used_bytes > self.budget_bytes {
            match self.cache.pop_lru() {
                Some((_, evicted)) => self.used_bytes -= estimate_entry_bytes(&evicted),
                None => break,
            }
        }
    }

    fn clear(&mut self) {
        self.cache.clear();
        self.used_bytes = 0;
    }
}

pub struct DataFetcher {
    conn: Connection,
    file_paths: Vec<Vec<String>>,
    full_dut: HashMap<usize, Array1<u32>>,
    head_site_idx: HashMap<(usize, HeadNum, Option<SiteNum>), Vec<usize>>,
    test_info: HashMap<(usize, TestNum, String), TestInfo>,
    test_data: TestDataLru,
}

impl DataFetcher {
    pub fn open(path: &str) -> Result<Self, StdfHelperError> {
        Self::open_with_budget(path, DEFAULT_TEST_CACHE_BUDGET_BYTES)
    }

    /// Open a database with a custom Tier-2 cache byte budget.
    pub fn open_with_budget(path: &str, budget_bytes: usize) -> Result<Self, StdfHelperError> {
        let conn = Connection::open(path)?;
        let mut fetcher = Self {
            conn,
            file_paths: Vec::new(),
            full_dut: HashMap::new(),
            head_site_idx: HashMap::new(),
            test_info: HashMap::new(),
            test_data: TestDataLru::new(budget_bytes),
        };
        fetcher.read_file_paths()?;
        fetcher.build_file_caches()?;
        Ok(fetcher)
    }

    pub fn close(&mut self) {
        self.file_paths.clear();
        self.full_dut.clear();
        self.head_site_idx.clear();
        self.test_info.clear();
        self.test_data.clear();
    }

    pub fn num_files(&self) -> usize {
        self.file_paths.len()
    }

    pub fn file_paths(&self) -> Vec<Vec<String>> {
        self.file_paths.clone()
    }

    pub fn read_file_paths(&mut self) -> Result<(), StdfHelperError> {
        let mut d: HashMap<usize, Vec<String>> = HashMap::new();
        {
            let mut stmt = self.conn.prepare_cached(FETCH_SELECT_FILE_LIST)?;
            let rows = stmt.query_map([], |row| {
                Ok((row.get::<_, i64>(0)? as usize, row.get::<_, String>(1)?))
            })?;
            for row in rows {
                let (fid, path) = row?;
                d.entry(fid).or_default().push(path);
            }
        }
        let mut keys: Vec<usize> = d.keys().copied().collect();
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
            let n: i64 = self
                .conn
                .query_row(FETCH_SELECT_MAX_DUT_INDEX, [fid as i64], |row| row.get(0))?;
            let n = n.max(0) as usize;
            self.full_dut.insert(fid, Array1::from_iter(1..=n as u32));

            let mut site_lists: HashMap<(HeadNum, SiteNum), Vec<usize>> = HashMap::new();
            let mut head_lists: HashMap<HeadNum, Vec<usize>> = HashMap::new();
            {
                let mut stmt = self.conn.prepare_cached(FETCH_SELECT_DUT_HEAD_SITE)?;
                let rows = stmt.query_map([fid as i64], |row| {
                    Ok((
                        row.get::<_, i64>(0)? as u32,
                        row.get::<_, i64>(1)? as u8,
                        row.get::<_, i64>(2)? as u8,
                    ))
                })?;
                for row in rows {
                    let (dut_index, head, site) = row?;
                    let idx = (dut_index as usize) - 1;
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

    pub fn get_site_list(&self) -> Result<Vec<SiteNum>, StdfHelperError> {
        let mut stmt = self.conn.prepare_cached(FETCH_SELECT_SITE_LIST)?;
        let sites = stmt
            .query_map([], |row| Ok(row.get::<_, i64>(0)? as u8))?
            .collect::<Result<Vec<_>, _>>()?;
        Ok(sites)
    }

    pub fn get_head_list(&self) -> Result<Vec<HeadNum>, StdfHelperError> {
        let mut stmt = self.conn.prepare_cached(FETCH_SELECT_HEAD_LIST)?;
        let heads = stmt
            .query_map([], |row| Ok(row.get::<_, i64>(0)? as u8))?
            .collect::<Result<Vec<_>, _>>()?;
        Ok(heads)
    }

    pub fn get_test_info(
        &mut self,
        test_tup: (TestNum, &str),
        file_id: usize,
    ) -> Result<Option<TestInfo>, StdfHelperError> {
        let key = (file_id, test_tup.0, test_tup.1.to_string());
        if let Some(info) = self.test_info.get(&key) {
            return Ok(Some(info.clone()));
        }
        let info = self.conn.query_row(
            FETCH_SELECT_TEST_INFO,
            rusqlite::params![file_id as i64, test_tup.0, test_tup.1],
            |row| {
                Ok(TestInfo {
                    test_id: row.get(0)?,
                    sub_code: TestSubCode::from_code(row.get(1)?),
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

    /// Make sure the full-length cached arrays for `(test_id, file_id)` exist.
    /// On a cache hit this only touches the LRU recency order — it does NOT
    /// clone the entry (plan §3.5/§3.6: gather with `select` on cached arrays;
    /// only the final result is an owned copy).
    ///
    /// Returns:
    /// - `Ok(None)` — the entry is now in the byte-budget LRU; callers read it
    ///   back with `self.test_data.get(&key)`.
    /// - `Ok(Some(entry))` — the entry is bigger than the whole budget and is
    ///   therefore not cached; callers must gather from this owned entry.
    fn ensure_test_data(
        &mut self,
        test_id: TestId,
        sub_code: TestSubCode,
        file_id: usize,
    ) -> Result<Option<TestDataCacheEntry>, StdfHelperError> {
        let key = (test_id, file_id);
        if self.test_data.get(&key).is_some() {
            return Ok(None);
        }

        let n = self.full_dut.get(&file_id).map(|a| a.len()).unwrap_or(0);
        let mut flags = Array1::from_elem(n, -1i16);
        let mut valid = Vec::new();

        let entry = match sub_code {
            TestSubCode::Ptr => {
                let mut data = Array2::from_elem((n, 1), f32::NAN);
                {
                    let mut stmt = self.conn.prepare_cached(FETCH_SELECT_PTR_DATA)?;
                    let rows = stmt.query_map([test_id], |row| {
                        Ok((
                            row.get::<_, i64>(0)? as u32,
                            row.get::<_, f32>(1)?,
                            row.get::<_, i64>(2)? as u8,
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
                    sub_code,
                    data,
                    flags,
                    states: None,
                    valid_test_idx: valid,
                }
            }
            TestSubCode::Ftr => {
                let data = Array2::from_elem((n, 0), 0.0f32);
                {
                    let mut stmt = self.conn.prepare_cached(FETCH_SELECT_FTR_DATA)?;
                    let rows = stmt.query_map([test_id], |row| {
                        Ok((row.get::<_, i64>(0)? as u32, row.get::<_, i64>(1)? as u8))
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
                    sub_code,
                    data,
                    flags,
                    states: None,
                    valid_test_idx: valid,
                }
            }
            TestSubCode::Mpr => {
                let rows_vec: Vec<(u32, String, String, u8)> = {
                    let mut stmt = self.conn.prepare_cached(FETCH_SELECT_MPR_DATA)?;
                    let rows = stmt.query_map([test_id], |row| {
                        Ok((
                            row.get::<_, i64>(0)? as u32,
                            row.get::<_, String>(1)?,
                            row.get::<_, String>(2)?,
                            row.get::<_, i64>(3)? as u8,
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
                        sub_code,
                        data: Array2::from_shape_fn((n, 0), |_| f32::NAN),
                        flags,
                        states: Some(Array2::from_shape_fn((n, 0), |_| 0xFu8)),
                        valid_test_idx: valid,
                    }
                } else {
                    let mut data = Array2::from_elem((n, rslt_cnt), f32::NAN);
                    let mut states = Array2::from_elem((n, rslt_cnt), 0xFu8);
                    for (dut_index, rslt_hex, stat_hex, flag) in rows_vec {
                        let pos = dut_index as usize - 1;
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
                        sub_code,
                        data,
                        flags,
                        states: Some(states),
                        valid_test_idx: valid,
                    }
                }
            }
            TestSubCode::Other => TestDataCacheEntry {
                sub_code,
                data: Array2::from_shape_fn((n, 0), |_| f32::NAN),
                flags,
                states: None,
                valid_test_idx: valid,
            },
        };

        let bytes = estimate_entry_bytes(&entry);
        if bytes > self.test_data.budget_bytes {
            // Single entry larger than the whole budget: caching it would evict
            // everything and immediately re-blow the budget, so hand it back to
            // the caller to use directly (it is still returned to Python).
            return Ok(Some(entry));
        }
        self.test_data.insert(key, entry);
        Ok(None)
    }

    pub fn get_test_data_from_head_site(
        &mut self,
        test_tup: (TestNum, &str),
        heads: &[HeadNum],
        sites: &[Option<SiteNum>],
        file_id: usize,
    ) -> Result<Option<FetchedTestData>, StdfHelperError> {
        let info = match self.get_test_info(test_tup, file_id)? {
            Some(info) => info,
            None => return Ok(None),
        };

        let mut selected: Vec<usize> = Vec::new();
        for &head in heads {
            if sites.contains(&None) {
                if let Some(list) = self.head_site_idx.get(&(file_id, head, None)) {
                    selected.extend_from_slice(list);
                }
            } else {
                for &site in sites {
                    if let Some(site) = site {
                        if let Some(list) = self.head_site_idx.get(&(file_id, head, Some(site))) {
                            selected.extend_from_slice(list);
                        }
                    }
                }
            }
        }
        selected.sort_unstable();
        selected.dedup();

        // Valid rows only (plan §3.4): intersect the head/site rows with the
        // rows that actually carry data for this test, so no NaN is returned.
        let oversized = self.ensure_test_data(info.test_id, info.sub_code, file_id)?;
        let fetched = match oversized {
            // Single entry bigger than the byte budget: use it directly.
            Some(entry) => {
                let idx = intersect_sorted(&selected, &entry.valid_test_idx);
                let full_dut = self.full_dut.get(&file_id).expect("fid cache exists");
                make_fetched_data(full_dut, &entry, &idx)
            }
            // Normal path: gather with select straight from the cached entry
            // (no per-call clone of the full cached arrays).
            None => {
                let key = (info.test_id, file_id);
                let entry = self.test_data.get(&key).expect("entry was just cached");
                let idx = intersect_sorted(&selected, &entry.valid_test_idx);
                let full_dut = self.full_dut.get(&file_id).expect("fid cache exists");
                make_fetched_data(full_dut, entry, &idx)
            }
        };
        Ok(Some(fetched))
    }

    pub fn get_test_data_from_dut_index(
        &mut self,
        test_tup: (TestNum, &str),
        duts: &[u64],
        file_id: usize,
    ) -> Result<Option<FetchedTestData>, StdfHelperError> {
        let info = match self.get_test_info(test_tup, file_id)? {
            Some(info) => info,
            None => return Ok(None),
        };
        if duts.is_empty() {
            return Ok(None);
        }

        let oversized = self.ensure_test_data(info.test_id, info.sub_code, file_id)?;
        let mut sorted_duts = duts.to_vec();
        sorted_duts.sort_unstable();
        let fetched = match oversized {
            // Single entry bigger than the byte budget: use it directly.
            Some(entry) => {
                let n = self.full_dut.get(&file_id).map(|a| a.len()).unwrap_or(0);
                gather_dut_rows(&entry, n, &sorted_duts)
            }
            // Normal path: read rows straight from the cached entry.
            None => {
                let key = (info.test_id, file_id);
                let entry = self.test_data.get(&key).expect("entry was just cached");
                let n = self.full_dut.get(&file_id).map(|a| a.len()).unwrap_or(0);
                gather_dut_rows(entry, n, &sorted_duts)
            }
        };
        Ok(Some(fetched))
    }
}

/// Gather rows for every requested DUT (plan §3.4).
///
/// Contract: EVERY requested DUT is returned, in ascending order, exactly like
/// the Python fetcher. Requested DUTs always come from `Dut_Info`, so they live
/// in `1..=n`; a DUT may still carry no data for this test (e.g. it failed an
/// earlier test and skipped this one), and its row then keeps the sentinel
/// values (NaN / -1 / 0xF) the cache already holds for it. DUTs outside
/// `1..=n` are not expected from callers but keep their sentinel row as well,
/// mirroring Python where such DUTs have no data rows. Duplicate DUTs in a
/// request are also not expected (request lists are dedup'd selections); each
/// duplicate row is filled from the same cache row.
fn gather_dut_rows(entry: &TestDataCacheEntry, n: usize, sorted_duts: &[u64]) -> FetchedTestData {
    let dut_count = sorted_duts.len();
    let dut_list: Array1<u32> = Array1::from_iter(sorted_duts.iter().map(|&d| d as u32));

    let width = entry.data.shape()[1];
    let mut data = Array2::from_elem((dut_count, width), f32::NAN);
    let mut flags = Array1::from_elem(dut_count, -1i16);
    let mut states = entry
        .states
        .as_ref()
        .map(|s| Array2::from_elem((dut_count, s.shape()[1]), 0xFu8));

    for (i, &dut) in sorted_duts.iter().enumerate() {
        if dut >= 1 && (dut as usize) <= n {
            let pos = dut as usize - 1;
            data.row_mut(i).assign(&entry.data.row(pos));
            if let (Some(dst), Some(src)) = (states.as_mut(), entry.states.as_ref()) {
                dst.row_mut(i).assign(&src.row(pos));
            }
            flags[i] = entry.flags[pos];
        }
        // DUT outside 1..=n keeps the pre-filled sentinel row (NaN / -1 / 0xF).
    }

    FetchedTestData {
        sub_code: entry.sub_code,
        dut_list,
        data,
        flags,
        states,
    }
}

fn make_fetched_data(
    full_dut: &Array1<u32>,
    entry: &TestDataCacheEntry,
    idx: &[usize],
) -> FetchedTestData {
    let dut_list: Array1<u32> = full_dut.select(ndarray::Axis(0), idx);

    match entry.sub_code {
        TestSubCode::Ptr => {
            let data2 = entry.data.select(ndarray::Axis(0), idx);
            let mut flat = Array1::from_elem(idx.len(), f32::NAN);
            for (i, row) in data2.outer_iter().enumerate() {
                flat[i] = row[0];
            }
            FetchedTestData {
                sub_code: entry.sub_code,
                dut_list,
                data: flat.into_shape((idx.len(), 1)).unwrap(),
                flags: entry.flags.select(ndarray::Axis(0), idx),
                states: None,
            }
        }
        TestSubCode::Mpr => {
            let data = entry.data.select(ndarray::Axis(0), idx);
            let states = entry
                .states
                .as_ref()
                .map(|s| s.select(ndarray::Axis(0), idx));
            FetchedTestData {
                sub_code: entry.sub_code,
                dut_list,
                data,
                flags: entry.flags.select(ndarray::Axis(0), idx),
                states,
            }
        }
        // FTR and any unknown/legacy code: flags only.
        TestSubCode::Ftr | TestSubCode::Other => FetchedTestData {
            sub_code: entry.sub_code,
            dut_list,
            data: Array2::from_shape_fn((idx.len(), 0), |_| 0.0f32),
            flags: entry.flags.select(ndarray::Axis(0), idx),
            states: None,
        },
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
        if let (Some(hi), Some(lo)) = (chars[i].to_digit(16), chars[i + 1].to_digit(16)) {
            bytes.push(((hi << 4) | lo) as u8);
        }
        i += 2;
    }
    bytes
}
