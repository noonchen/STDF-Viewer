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
    FETCH_EXISTS_DUT_COLUMN, FETCH_SELECT_BIN_INFO, FETCH_SELECT_BIN_STATS_H_HEAD,
    FETCH_SELECT_BIN_STATS_H_HEAD_SITE, FETCH_SELECT_BIN_STATS_S_HEAD,
    FETCH_SELECT_BIN_STATS_S_HEAD_SITE, FETCH_SELECT_BYTE_ORDER,
    FETCH_SELECT_DATALOG, FETCH_SELECT_DUT_COUNTS, FETCH_SELECT_DUT_HEAD_SITE,
    FETCH_SELECT_DUT_HEAD_SITE_ALL, FETCH_SELECT_DUT_SUMMARY, FETCH_SELECT_DYNAMIC_LIMITS_ALL,
    FETCH_SELECT_FILE_INFO, FETCH_SELECT_FILE_LIST, FETCH_SELECT_FTR_DATA,
    FETCH_SELECT_HEAD_LIST, FETCH_SELECT_MAX_DUT_INDEX, FETCH_SELECT_MPR_DATA,
    FETCH_SELECT_PARTIAL_RAW, FETCH_SELECT_PIN_NAMES, FETCH_SELECT_PTR_DATA,
    FETCH_SELECT_ALL_TEST_INFO, FETCH_SELECT_SITE_LIST, FETCH_SELECT_TEST_FAIL_CNT,
    FETCH_SELECT_TEST_ITEMS, FETCH_SELECT_TEST_RECORD_TYPES,
    FETCH_SELECT_WAFER_COUNT, FETCH_SELECT_WAFER_EXT, FETCH_SELECT_WAFER_INFO,
    FETCH_SELECT_WAFER_LIST,
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
    pub dut_list: Array1<u64>,
    pub data: Array2<f32>,
    pub flags: Array1<i16>,
    pub states: Option<Array2<u8>>,
}

/// Per-test dynamic-limit cache entry, aligned to the file's full-DUT array.
///
/// Values are *fill-first*: a side array exists only when the test has a
/// static default for that side (`Test_Info.LLimit/HLimit`, f32 as stored in
/// the STDF file); elements start as that default and `Dynamic_Limits` rows
/// overwrite their DUT. A side whose index set stayed empty is discarded (it
/// can never be returned), and a side without a static default has no array at
/// all — mirroring Python, where a NaN static default disables that side.
/// `ll_valid_idx` / `hl_valid_idx` record which DUTs carry a *dynamic*
/// override and gate whether a side's output is empty (`hasDynamicLow/High`).
pub struct DynamicLimitEntry {
    pub llimit: Option<Array1<f32>>,
    pub hlimit: Option<Array1<f32>>,
    pub ll_default: Option<f32>,
    pub hl_default: Option<f32>,
    pub ll_valid_idx: Vec<usize>,
    pub hl_valid_idx: Vec<usize>,
}

/// One raw `Dut_Info` row used by the partial-DUT-info cache
/// (`getPartialDUTInfoOnCondition`), including superseded rows. Formatted
/// strings ("Head h - Site s", "State - 0x%02X") are built per call so the
/// cache only keeps raw fields.
pub struct PartialDutRow {
    pub row_index: usize,
    pub part_id: Option<String>,
    pub part_text: Option<String>,
    pub head: HeadNum,
    pub site: SiteNum,
    pub superseded: bool,
    pub flag: Option<i64>,
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
    // fid -> [1, 2, .., N]; u64 matches the db-gen counter type.
    full_dut: HashMap<usize, Array1<u64>>,
    // (fid, head, site/None) -> sorted row indices of non-superseded DUTs.
    head_site_idx: HashMap<(usize, HeadNum, Option<SiteNum>), Vec<usize>>,
    // Same shape but *including* superseded rows: getDutIndexDictFromHeadSite
    // has no Supersede filter, so it cannot reuse head_site_idx.
    head_site_idx_all: HashMap<(usize, HeadNum, Option<SiteNum>), Vec<usize>>,
    // (fid, test_num) -> test_name -> TestInfo, so lookups borrow the &str key.
    test_info: HashMap<(usize, TestNum), HashMap<String, TestInfo>>,
    // Eager, permanent dynamic-limit cache (no LRU; cleared on close).
    dynamic_limits: HashMap<TestId, DynamicLimitEntry>,
    // Per-file raw Dut_Info rows for the partial-DUT-info cache.
    partial_info: HashMap<usize, Vec<PartialDutRow>>,
    // Lazily cached distinct site/head lists (immutable DB).
    site_list_cache: Option<Vec<SiteNum>>,
    head_list_cache: Option<Vec<HeadNum>>,
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
            head_site_idx_all: HashMap::new(),
            test_info: HashMap::new(),
            dynamic_limits: HashMap::new(),
            partial_info: HashMap::new(),
            site_list_cache: None,
            head_list_cache: None,
            test_data: TestDataLru::new(budget_bytes),
        };
        fetcher.read_file_paths()?;
        fetcher.build_file_caches()?;
        fetcher.load_test_info()?;
        fetcher.load_dynamic_limits()?;
        Ok(fetcher)
    }

    pub fn close(&mut self) {
        self.file_paths.clear();
        self.full_dut.clear();
        self.head_site_idx.clear();
        self.head_site_idx_all.clear();
        self.test_info.clear();
        self.dynamic_limits.clear();
        self.partial_info.clear();
        self.site_list_cache = None;
        self.head_list_cache = None;
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
            // u64 matches the db-gen counter type (see TODO-resolved decision).
            self.full_dut.insert(fid, Array1::from_iter(1..=n as u64));

            // Both queries ORDER BY DUTIndex, so the per-key subsequences are
            // already sorted and no explicit sort is needed.
            for (sql, target) in [
                (FETCH_SELECT_DUT_HEAD_SITE, &mut self.head_site_idx),
                (FETCH_SELECT_DUT_HEAD_SITE_ALL, &mut self.head_site_idx_all),
            ] {
                let mut site_lists: HashMap<(HeadNum, SiteNum), Vec<usize>> = HashMap::new();
                let mut head_lists: HashMap<HeadNum, Vec<usize>> = HashMap::new();
                {
                    let mut stmt = self.conn.prepare_cached(sql)?;
                    let rows = stmt.query_map([fid as i64], |row| {
                        Ok((
                            row.get::<_, i64>(0)?,
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
                for ((head, site), vals) in site_lists {
                    target.insert((fid, head, Some(site)), vals);
                }
                for (head, vals) in head_lists {
                    target.insert((fid, head, None), vals);
                }
            }
        }
        Ok(())
    }

    pub fn get_site_list(&mut self) -> Result<Vec<SiteNum>, StdfHelperError> {
        if let Some(sites) = &self.site_list_cache {
            return Ok(sites.clone());
        }
        let mut stmt = self.conn.prepare_cached(FETCH_SELECT_SITE_LIST)?;
        let sites = stmt
            .query_map([], |row| Ok(row.get::<_, i64>(0)? as u8))?
            .collect::<Result<Vec<_>, _>>()?;
        self.site_list_cache = Some(sites.clone());
        Ok(sites)
    }

    pub fn get_head_list(&mut self) -> Result<Vec<HeadNum>, StdfHelperError> {
        if let Some(heads) = &self.head_list_cache {
            return Ok(heads.clone());
        }
        let mut stmt = self.conn.prepare_cached(FETCH_SELECT_HEAD_LIST)?;
        let heads = stmt
            .query_map([], |row| Ok(row.get::<_, i64>(0)? as u8))?
            .collect::<Result<Vec<_>, _>>()?;
        self.head_list_cache = Some(heads.clone());
        Ok(heads)
    }

    /// Eagerly cache the whole `Test_Info` table at open — the smallest but
    /// most-used cache. `get_test_info` and the dynamic-limit defaults both
    /// read from it, so no further `Test_Info` queries happen.
    fn load_test_info(&mut self) -> Result<(), StdfHelperError> {
        let mut stmt = self.conn.prepare_cached(FETCH_SELECT_ALL_TEST_INFO)?;
        let rows = stmt.query_map([], |row| {
            Ok((
                row.get::<_, i64>(0)? as usize, // Fid
                TestInfo {
                    test_id: row.get(1)?,
                    sub_code: TestSubCode::from_code(row.get(2)?),
                    test_num: row.get(3)?,
                    test_name: row.get(4)?,
                    res_scal: row.get(5)?,
                    llimit: row.get(6)?,
                    hlimit: row.get(7)?,
                    unit: row.get(8)?,
                    opt_flag: row.get(9)?,
                    fail_count: row.get(10)?,
                    rtn_icnt: row.get(11)?,
                    rslt_pgm_cnt: row.get(12)?,
                    lspec: row.get(13)?,
                    hspec: row.get(14)?,
                    vect_nam: row.get(15)?,
                    seq_name: row.get(16)?,
                },
            ))
        })?;
        for r in rows {
            let (fid, info) = r?;
            self.test_info
                .entry((fid, info.test_num))
                .or_default()
                .insert(info.test_name.clone(), info);
        }
        Ok(())
    }

    pub fn get_test_info(
        &mut self,
        test_tup: (TestNum, &str),
        file_id: usize,
    ) -> Result<Option<TestInfo>, StdfHelperError> {
        // Nested map allows the &str test_name lookup without cloning the key.
        Ok(self
            .test_info
            .get(&(file_id, test_tup.0))
            .and_then(|by_name| by_name.get(test_tup.1))
            .cloned())
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
                            row.get::<_, i64>(0)?,
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
                        Ok((row.get::<_, i64>(0)?, row.get::<_, i64>(1)? as u8))
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
                let rows_vec: Vec<(i64, String, String, u8)> = {
                    let mut stmt = self.conn.prepare_cached(FETCH_SELECT_MPR_DATA)?;
                    let rows = stmt.query_map([test_id], |row| {
                        Ok((
                            row.get::<_, i64>(0)?,
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
    let dut_list: Array1<u64> = Array1::from_iter(sorted_duts.iter().copied());

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
    full_dut: &Array1<u64>,
    entry: &TestDataCacheEntry,
    idx: &[usize],
) -> FetchedTestData {
    let dut_list: Array1<u64> = full_dut.select(ndarray::Axis(0), idx);

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
    let mut result = Vec::with_capacity(a.len().min(b.len()));
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

// ---------------------------------------------------------------------------
// Metadata / summary queries.
//
// Each method below mirrors one public method of the Python reference fetcher
// (deps/DatabaseFetcher.py): identical SQL and identical per-row semantics.
// Final Python container shaping (dict/tuple/set assembly) happens in the
// PyO3 wrapper / DatabaseFetcherRust, per plan §3.1.
// ---------------------------------------------------------------------------

impl DataFetcher {
    /// `getWaferCount()` — per-file wafer counts (`File_List` LEFT JOIN
    /// `Wafer_Info`); 0 when a file has no wafer rows.
    pub fn wafer_count(&self) -> Result<Vec<i64>, StdfHelperError> {
        let n = self.file_paths.len();
        let mut counts = vec![0i64; n];
        let mut stmt = self.conn.prepare_cached(FETCH_SELECT_WAFER_COUNT)?;
        let rows = stmt.query_map([], |row| {
            Ok((row.get::<_, i64>(0)?, row.get::<_, Option<i64>>(1)?))
        })?;
        for r in rows {
            let (fid, cnt) = r?;
            if let Ok(pos) = usize::try_from(fid) {
                if pos < n {
                    counts[pos] = cnt.unwrap_or(0);
                }
            }
        }
        Ok(counts)
    }

    /// `getByteOrder()` — one bool per `File_Info` row with `BYTE_ORD`,
    /// ordered by `Fid`.
    pub fn byte_order(&self) -> Result<Vec<bool>, StdfHelperError> {
        let mut stmt = self.conn.prepare_cached(FETCH_SELECT_BYTE_ORDER)?;
        let rows = stmt
            .query_map([], |row| Ok(row.get::<_, i64>(0)? == 1))?
            .collect::<Result<Vec<_>, _>>()?;
        Ok(rows)
    }

    /// `getTestItemsList()` — `test_num [(#pmr)] test_name` items in the same
    /// order as the reference join, deduplicated keeping the first occurrence.
    pub fn test_items(&self) -> Result<Vec<String>, StdfHelperError> {
        let mut stmt = self.conn.prepare_cached(FETCH_SELECT_TEST_ITEMS)?;
        let rows = stmt.query_map([], |row| {
            Ok((
                row.get::<_, i64>(0)?,
                row.get::<_, String>(1)?,
                row.get::<_, Option<i64>>(2)?,
            ))
        })?;
        let mut items = Vec::new();
        let mut seen = std::collections::HashSet::new();
        for row in rows {
            let (test_num, test_name, pmr_indx) = row?;
            let item = match pmr_indx {
                Some(p) => format!("{}\t#{}\t{}", test_num, p, test_name),
                None => format!("{}\t{}", test_num, test_name),
            };
            if seen.insert(item.clone()) {
                items.push(item);
            }
        }
        Ok(items)
    }

    /// `getTestRecordTypeDict()` row source — one row per `Test_Info` entry,
    /// in DB order (the same order the Python reference iterates).
    pub fn test_record_type_rows(&self) -> Result<Vec<(i64, String, u8)>, StdfHelperError> {
        let mut stmt = self.conn.prepare_cached(FETCH_SELECT_TEST_RECORD_TYPES)?;
        let rows = stmt
            .query_map([], |row| {
                Ok((
                    row.get::<_, i64>(0)?,
                    row.get::<_, String>(1)?,
                    row.get::<_, i64>(2)? as u8,
                ))
            })?
            .collect::<Result<Vec<_>, _>>()?;
        Ok(rows)
    }

    /// `getWaferList()` — "File{fid}-#{waferIndex}\t{WAFER_ID}" rows plus the
    /// leading "- Stacked Wafer Map" entry, ordered by `WaferIndex`.
    pub fn wafer_list(&self) -> Result<Vec<String>, StdfHelperError> {
        let mut stmt = self.conn.prepare_cached(FETCH_SELECT_WAFER_LIST)?;
        let rows = stmt.query_map([], |row| {
            Ok((
                row.get::<_, i64>(0)?,
                row.get::<_, i64>(1)?,
                row.get::<_, Option<String>>(2)?,
            ))
        })?;
        let mut list = vec![String::from("-\tStacked Wafer Map")];
        for row in rows {
            let (fid, wafer_index, wafer_id) = row?;
            // Python formats the raw value with an f-string, so NULL becomes
            // the literal string "None".
            let id = match wafer_id {
                Some(s) => s,
                None => String::from("None"),
            };
            list.push(format!("File{}-#{}\t{}", fid, wafer_index, id));
        }
        Ok(list)
    }

    /// `getTestFailCnt()` rows — keyed by (test_num, test_name), per-file
    /// `FailCount` (None when the column is NULL), files without an entry
    /// stay 0.
    pub fn test_fail_cnt_rows(
        &self,
    ) -> Result<Vec<(i64, String, Vec<Option<i64>>)>, StdfHelperError> {
        let n = self.file_paths.len();
        let mut stmt = self.conn.prepare_cached(FETCH_SELECT_TEST_FAIL_CNT)?;
        let rows = stmt.query_map([], |row| {
            Ok((
                row.get::<_, i64>(0)?,
                row.get::<_, String>(1)?,
                row.get::<_, i64>(2)?,
                row.get::<_, Option<i64>>(3)?,
            ))
        })?;
        let mut keys: Vec<(i64, String)> = Vec::new();
        let mut pos: std::collections::HashMap<(i64, String), usize> =
            std::collections::HashMap::new();
        let mut out: Vec<Vec<Option<i64>>> = Vec::new();
        for row in rows {
            let (num, name, fid, fail_count) = row?;
            let key = (num, name);
            let i = match pos.get(&key) {
                Some(&i) => i,
                None => {
                    pos.insert(key.clone(), keys.len());
                    keys.push(key);
                    out.push(vec![Some(0); n]);
                    keys.len() - 1
                }
            };
            if let Ok(f) = usize::try_from(fid) {
                if f < n {
                    out[i][f] = fail_count;
                }
            }
        }
        Ok(keys
            .into_iter()
            .zip(out)
            .map(|((num, name), vals)| (num, name, vals))
            .collect())
    }

    /// `getBinInfo()` rows — `(BIN_NUM, BIN_NAME, BIN_PF)` ordered by
    /// `BIN_NUM` for the requested bin type ('H' or 'S').
    pub fn bin_info_rows(
        &self,
        is_hbin: bool,
    ) -> Result<Vec<(i64, Option<String>, Option<String>)>, StdfHelperError> {
        let mut stmt = self.conn.prepare_cached(FETCH_SELECT_BIN_INFO)?;
        let rows = stmt
            .query_map([if is_hbin { "H" } else { "S" }], |row| {
                Ok((
                    row.get::<_, i64>(0)?,
                    row.get::<_, Option<String>>(1)?,
                    row.get::<_, Option<String>>(2)?,
                ))
            })?
            .collect::<Result<Vec<_>, _>>()?;
        Ok(rows)
    }

    /// `getBinStats()` rows — `(Fid, BIN_NUM, count)` for non-superseded DUTs
    /// of one head (and optionally one site); rows whose bin is NULL are
    /// skipped, matching the Python reference.
    pub fn bin_stats_rows(
        &self,
        head: i64,
        site: i64,
        is_hbin: bool,
    ) -> Result<Vec<(i64, i64, i64)>, StdfHelperError> {
        let (sql, params): (&str, Vec<i64>) = match (is_hbin, site < 0) {
            (true, true) => (FETCH_SELECT_BIN_STATS_H_HEAD, vec![head]),
            (true, false) => (FETCH_SELECT_BIN_STATS_H_HEAD_SITE, vec![head, site]),
            (false, true) => (FETCH_SELECT_BIN_STATS_S_HEAD, vec![head]),
            (false, false) => (FETCH_SELECT_BIN_STATS_S_HEAD_SITE, vec![head, site]),
        };
        let mut stmt = self.conn.prepare_cached(sql)?;
        let rows = stmt
            .query_map(rusqlite::params_from_iter(params.iter()), |row| {
                let bin = row.get::<_, Option<i64>>(1)?;
                if let Some(bin) = bin {
                    Ok(Some((
                        row.get::<_, i64>(0)?,
                        bin,
                        row.get::<_, i64>(2)?,
                    )))
                } else {
                    Ok(None)
                }
            })?
            .filter_map(|r| r.transpose())
            .collect::<Result<Vec<_>, _>>()?;
        Ok(rows)
    }

    /// `isDutInfoColumnEmpty(column)` — True when the given `Dut_Info` column
    /// has no valid value. Only a fixed set of column names is accepted (the
    /// Python reference is called with a hard-coded column name as well).
    pub fn is_dut_info_column_empty(&self, column: &str) -> Result<bool, StdfHelperError> {
        // The fetcher is the only reader of these DBs; a plain identifier guard
        // is enough. The query template itself lives in schema.rs.
        let is_ident = !column.is_empty()
            && (column.as_bytes()[0].is_ascii_alphabetic() || column.as_bytes()[0] == b'_')
            && column.bytes().all(|b| b.is_ascii_alphanumeric() || b == b'_');
        if !is_ident {
            return Err(StdfHelperError {
                msg: format!("Invalid Dut_Info column name: {}", column),
            });
        }
        let sql = FETCH_EXISTS_DUT_COLUMN.replace("{column}", column);
        let valid_data_exists: i64 = self.conn.query_row(&sql, [], |row| row.get(0))?;
        Ok(valid_data_exists == 0)
    }

    /// `getFileInfo()` row source — `(Fid, Field, Value)` ordered by
    /// `Fid, Field, SubFid` (per-field processing is done by the caller).
    pub fn file_info_rows(&self) -> Result<Vec<(i64, String, Option<String>)>, StdfHelperError> {
        let mut stmt = self.conn.prepare_cached(FETCH_SELECT_FILE_INFO)?;
        let rows = stmt
            .query_map([], |row| {
                Ok((
                    row.get::<_, i64>(0)?,
                    row.get::<_, String>(1)?,
                    row.get::<_, Option<String>>(2)?,
                ))
            })?
            .collect::<Result<Vec<_>, _>>()?;
        Ok(rows)
    }
}

// ---------------------------------------------------------------------------
// DUT-level summary queries (port batch A).
// ---------------------------------------------------------------------------

/// One `DUT_SUMMARY_QUERY` row. The reference returns the SQLite cells as
/// plain Python values; column types are static, so each is typed explicitly.
pub struct DutSummaryRow {
    pub dut_index: i64,
    pub part_id: Option<String>,
    pub part_text: Option<String>,
    pub head_site: String,
    pub tests_executed: Option<i64>,
    pub test_time: Option<String>,
    pub hbin: Option<String>,
    pub sbin: Option<String>,
    pub wafer_id: Option<String>,
    pub xy: Option<String>,
    pub dut_flag: Option<String>,
}

impl DataFetcher {
    /// `getFullDUTInfoFromDutArray()` row source — DUT summary rows for one
    /// file, mirroring SharedSrc.DUT_SUMMARY_QUERY (typed cells).
    pub fn full_dut_summary_rows(&self, fid: i64) -> Result<Vec<DutSummaryRow>, StdfHelperError> {
        let sql = format!(
            "{} WHERE Dut_Info.Fid=? ORDER BY DUTIndex",
            FETCH_SELECT_DUT_SUMMARY
        );
        let mut stmt = self.conn.prepare_cached(&sql)?;
        let rows = stmt.query_map([fid], |row| {
            Ok(DutSummaryRow {
                dut_index: row.get(0)?,
                // column 1 is Dut_Info.Fid ("File ID"), injected by the wrapper
                part_id: row.get(2)?,
                part_text: row.get(3)?,
                head_site: row.get(4)?,
                tests_executed: row.get(5)?,
                test_time: row.get(6)?,
                hbin: row.get(7)?,
                sbin: row.get(8)?,
                wafer_id: row.get(9)?,
                xy: row.get(10)?,
                dut_flag: row.get(11)?,
            })
        })?;
        let out: rusqlite::Result<Vec<DutSummaryRow>> = rows.collect();
        Ok(out?)
    }
}


/// Typed result of the single-pass `getDUTCountDict()` query — one vector per
/// category, aligned by file position.
pub struct DutCounts {
    pub total: Vec<i64>,
    pub pass: Vec<i64>,
    pub failed: Vec<i64>,
    pub unknown: Vec<i64>,
    pub superseded: Vec<i64>,
}

impl DataFetcher {
    /// `getDUTCountDict()` — all five per-file counts from one scan of
    /// `Dut_Info` using conditional aggregation (plan §4.1).
    pub fn dut_count_dict(&self) -> Result<DutCounts, StdfHelperError> {
        let n = self.file_paths.len();
        let mut counts = DutCounts {
            total: vec![0; n],
            pass: vec![0; n],
            failed: vec![0; n],
            unknown: vec![0; n],
            superseded: vec![0; n],
        };
        let mut stmt = self.conn.prepare_cached(FETCH_SELECT_DUT_COUNTS)?;
        let rows = stmt.query_map([], |row| {
            Ok((
                row.get::<_, i64>(0)?,
                row.get::<_, Option<i64>>(1)?,
                row.get::<_, Option<i64>>(2)?,
                row.get::<_, Option<i64>>(3)?,
                row.get::<_, Option<i64>>(4)?,
                row.get::<_, Option<i64>>(5)?,
            ))
        })?;
        for row in rows {
            let (fid, total, pass, failed, unknown, superseded) = row?;
            if let Ok(pos) = usize::try_from(fid) {
                if pos < n {
                    counts.total[pos] = total.unwrap_or(0);
                    counts.pass[pos] = pass.unwrap_or(0);
                    counts.failed[pos] = failed.unwrap_or(0);
                    counts.unknown[pos] = unknown.unwrap_or(0);
                    counts.superseded[pos] = superseded.unwrap_or(0);
                }
            }
        }
        Ok(counts)
    }

    /// `getDUTCountOnConditions()` — [Pass, Failed, Unknown, Superseded].
    pub fn dut_count_on_conditions(
        &self,
        head: i64,
        site: i64,
        wafer_index: i64,
        fid: i64,
    ) -> Result<Vec<i64>, StdfHelperError> {
        use crate::database::schema as s;
        let mut extra = String::new();
        let mut params: Vec<i64> = Vec::new();
        if head != -1 {
            extra.push_str(" AND HEAD_NUM=?");
            params.push(head);
        }
        if site != -1 {
            extra.push_str(" AND SITE_NUM=?");
            params.push(site);
        }
        if wafer_index != -1 {
            extra.push_str(" AND WaferIndex=?");
            params.push(wafer_index);
        }
        if fid != -1 {
            extra.push_str(" AND Fid=?");
            params.push(fid);
        }
        let run = |sql: &str| -> Result<i64, StdfHelperError> {
            let sql = sql.replace("{extra}", &extra);
            Ok(self
                .conn
                .query_row(&sql, rusqlite::params_from_iter(params.iter()), |r| {
                    r.get::<_, i64>(0)
                })?)
        };
        Ok(vec![
            run(s::FETCH_COUNT_ON_COND_PASS)?,
            run(s::FETCH_COUNT_ON_COND_FAIL)?,
            run(s::FETCH_COUNT_ON_COND_UNKNOWN)?,
            run(s::FETCH_COUNT_ON_COND_SUPERSEDED)?,
        ])
    }

    fn in_clause_placeholders(count: usize) -> String {
        if count == 0 {
            String::new()
        } else {
            let mut s = String::with_capacity(count * 2);
            for i in 0..count {
                if i > 0 {
                    s.push(',');
                }
                s.push('?');
            }
            s
        }
    }

    /// `getDutIndexDictFromHeadSite()` rows — (Fid, DUTIndex) for non-empty
    /// head/site selections, ordered by Fid then DUTIndex.
    ///
    /// Served from `head_site_idx_all`: the Python method has *no* Supersede
    /// filter, so it must use the all-rows index (not the Supersede=0 cache).
    pub fn dut_index_rows_by_head_site(
        &self,
        heads: &[i64],
        sites: &[i64],
        file_ids: &[i64],
    ) -> Result<Vec<(i64, i64)>, StdfHelperError> {
        if heads.is_empty() || sites.is_empty() {
            return Ok(Vec::new());
        }
        let all_sites = sites.contains(&-1);
        let mut out: Vec<(i64, i64)> = Vec::new();
        for &fid64 in file_ids {
            let Ok(fid) = usize::try_from(fid64) else { continue };
            let mut acc: Vec<usize> = Vec::new();
            for &h64 in heads {
                let Ok(head) = u8::try_from(h64) else { continue };
                if all_sites {
                    if let Some(list) = self.head_site_idx_all.get(&(fid, head, None)) {
                        merge_sorted_unique(&mut acc, list);
                    }
                } else {
                    for &s64 in sites {
                        let Ok(site) = u8::try_from(s64) else { continue };
                        if let Some(list) = self.head_site_idx_all.get(&(fid, head, Some(site))) {
                            merge_sorted_unique(&mut acc, list);
                        }
                    }
                }
            }
            out.extend(
                acc.into_iter()
                    .map(|row| (fid as i64, (row + 1) as i64)),
            );
        }
        Ok(out)
    }

    /// `getDUTIndexFromBin()` — unique (Fid, DUTIndex) pairs in the order the
    /// Python reference appends them (per selection, dedup across selections).
    pub fn dut_index_rows_by_bin(
        &self,
        selections: &[(i64, bool, Vec<i64>)],
    ) -> Result<Vec<(i64, i64)>, StdfHelperError> {
        let mut out: Vec<(i64, i64)> = Vec::new();
        let mut seen = std::collections::HashSet::new();
        for (fid, is_hbin, bins) in selections {
            if bins.is_empty() {
                continue;
            }
            let bin_col = if *is_hbin { "HBIN" } else { "SBIN" };
            let sql = format!(
                "SELECT Fid, DUTIndex FROM Dut_Info WHERE {} IN ({}) AND Fid=?",
                bin_col,
                Self::in_clause_placeholders(bins.len())
            );
            let mut params: Vec<i64> = bins.clone();
            params.push(*fid);
            let mut stmt = self.conn.prepare_cached(&sql)?;
            let rows = stmt.query_map(rusqlite::params_from_iter(params.iter()), |row| {
                Ok((row.get::<_, i64>(0)?, row.get::<_, i64>(1)?))
            })?;
            for row in rows {
                let pair = row?;
                if seen.insert(pair) {
                    out.push(pair);
                }
            }
        }
        Ok(out)
    }

    /// `getDUTIndexFromXY()` — every (Fid, DUTIndex) row matching each
    /// (waferIndex, fid, (x, y)) selection, in selection order (no dedup).
    pub fn dut_index_rows_by_xy(
        &self,
        selections: &[(i64, i64, (i64, i64))],
    ) -> Result<Vec<(i64, i64)>, StdfHelperError> {
        let mut out: Vec<(i64, i64)> = Vec::new();
        // Kept inline: the WHERE clause grows appended conditions per call
        // (site lists), which does not fit the fixed-constant schema.rs rule.
        for (wafer_index, fid, (x, y)) in selections {
            if *wafer_index == -1 {
                let sql = "SELECT Fid, DUTIndex FROM Dut_Info WHERE XCOORD=? AND YCOORD=?";
                let mut stmt = self.conn.prepare_cached(sql)?;
                let rows = stmt
                    .query_map(rusqlite::params![x, y], |row| {
                        Ok((row.get::<_, i64>(0)?, row.get::<_, i64>(1)?))
                    })?
                    .collect::<Result<Vec<_>, _>>()?;
                out.extend(rows);
            } else {
                let sql = "SELECT Fid, DUTIndex FROM Dut_Info WHERE XCOORD=? AND YCOORD=?                            AND WaferIndex=? AND Fid=?";
                let mut stmt = self.conn.prepare_cached(sql)?;
                let rows = stmt
                    .query_map(rusqlite::params![x, y, wafer_index, fid], |row| {
                        Ok((row.get::<_, i64>(0)?, row.get::<_, i64>(1)?))
                    })?
                    .collect::<Result<Vec<_>, _>>()?;
                out.extend(rows);
            }
        }
        Ok(out)
    }

    /// `getWaferBounds()` — (max X, min X, max Y, min Y); wafer_index == -1
    /// covers the stacked map. Each value may be NULL when no DUT matches.
    pub fn wafer_bounds(
        &self,
        wafer_index: i64,
        fid: i64,
    ) -> Result<(Option<i64>, Option<i64>, Option<i64>, Option<i64>), StdfHelperError> {
        let condition = if wafer_index == -1 {
            "Fid >= 0 AND WaferIndex > 0".to_string()
        } else {
            format!("Fid = {} AND WaferIndex = {}", fid, wafer_index)
        };
        let sql =
            crate::database::schema::FETCH_SELECT_WAFER_BOUNDS.replace("{condition}", &condition);
        Ok(self.conn.query_row(&sql, [], |row| {
            Ok((
                row.get::<_, Option<i64>>(0)?,
                row.get::<_, Option<i64>>(1)?,
                row.get::<_, Option<i64>>(2)?,
                row.get::<_, Option<i64>>(3)?,
            ))
        })?)
    }

    /// Eagerly load every `Dynamic_Limits` row into per-TEST_ID arrays
    /// (permanent cache, no LRU; cleared on close).
    ///
    /// Defaults come from the eagerly cached `Test_Info` map, so no extra DB
    /// read is needed. Rows are ORDER BY TEST_ID, DUTIndex, so one merge pass
    /// fills each test's arrays directly (no per-test staging map). A side is
    /// only kept when it has a static default *and* at least one dynamic row;
    /// tests without any valid dynamic side are not cached at all.
    fn load_dynamic_limits(&mut self) -> Result<(), StdfHelperError> {
        let mut defaults: HashMap<TestId, (usize, Option<f32>, Option<f32>)> = HashMap::new();
        for (&(fid, _), by_name) in &self.test_info {
            for info in by_name.values() {
                defaults.insert(info.test_id, (fid, info.llimit, info.hlimit));
            }
        }

        let mut limits: HashMap<TestId, DynamicLimitEntry> = HashMap::new();
        let mut active: Option<TestId> = None;
        let mut n = 0usize;
        let mut ll_arr: Option<Array1<f32>> = None;
        let mut hl_arr: Option<Array1<f32>> = None;
        let mut ll_def: Option<f32> = None;
        let mut hl_def: Option<f32> = None;
        let mut ll_valid: Vec<usize> = Vec::new();
        let mut hl_valid: Vec<usize> = Vec::new();

        let mut stmt = self.conn.prepare_cached(FETCH_SELECT_DYNAMIC_LIMITS_ALL)?;
        let rows = stmt.query_map([], |row| {
            Ok((
                row.get::<_, i64>(0)?,
                row.get::<_, i64>(1)?,
                row.get::<_, Option<f32>>(2)?,
                row.get::<_, Option<f32>>(3)?,
            ))
        })?;
        for r in rows {
            let (test_id, dut_index, ll, hl) = r?;
            if active != Some(test_id) {
                flush_dynamic_entry(
                    &mut limits,
                    &mut active,
                    &mut n,
                    &mut ll_arr,
                    &mut hl_arr,
                    &mut ll_def,
                    &mut hl_def,
                    &mut ll_valid,
                    &mut hl_valid,
                );
                active = Some(test_id);
                ll_arr = None;
                hl_arr = None;
                ll_def = None;
                hl_def = None;
                match defaults.get(&test_id) {
                    Some(&(fid, lld, hld)) => {
                        n = self.full_dut.get(&fid).map(|a| a.len()).unwrap_or(0);
                        ll_def = lld;
                        hl_def = hld;
                        // No static default -> no side array (Python treats a
                        // NaN default as "no dynamic limits" for that side).
                        ll_arr = ll_def.map(|v| Array1::from_elem(n, v));
                        hl_arr = hl_def.map(|v| Array1::from_elem(n, v));
                    }
                    None => n = 0,
                }
            }
            if n > 0 {
                let idx = (dut_index as usize).saturating_sub(1);
                if idx < n {
                    if let (Some(arr), Some(v)) = (ll_arr.as_mut(), ll) {
                        arr[idx] = v;
                        ll_valid.push(idx);
                    }
                    if let (Some(arr), Some(v)) = (hl_arr.as_mut(), hl) {
                        arr[idx] = v;
                        hl_valid.push(idx);
                    }
                }
            }
        }
        flush_dynamic_entry(
            &mut limits,
            &mut active,
            &mut n,
            &mut ll_arr,
            &mut hl_arr,
            &mut ll_def,
            &mut hl_def,
            &mut ll_valid,
            &mut hl_valid,
        );
        self.dynamic_limits = limits;
        Ok(())
    }

    /// `getDynamicLimits()` — for each requested DUT and side, the dynamic
    /// override where a row exists, otherwise the static default fill. A side
    /// is empty when none of the requested DUTs carries a dynamic value
    /// (mirrors the Python `hasDynamicLow/High` contract). The returned arrays
    /// always have the same length as `duts` (out-of-range requests fall back
    /// to the static default, exactly like the dict-based reference).
    pub fn dynamic_limits_for(&self, test_id: TestId, duts: &[u64]) -> (Vec<f32>, Vec<f32>) {
        let Some(entry) = self.dynamic_limits.get(&test_id) else {
            return (Vec::new(), Vec::new());
        };
        // requested row positions (may include out-of-range entries, kept so
        // the output length always matches the request)
        let req: Vec<usize> = duts
            .iter()
            .filter_map(|&d| (d >= 1).then(|| (d as usize) - 1))
            .collect();
        // any() + binary_search: req is unsorted, the valid sets are sorted;
        // intersect_sorted would only add a sort for a yes/no answer.
        let has = |valid: &[usize]| req.iter().any(|p| valid.binary_search(p).is_ok());
        // No DUTs are filtered out, so a direct per-DUT read is the simplest
        // correct fill (ndarray select() would add machinery for nothing here).
        // Requested DUTs are always within 1..=N on real lots; an out-of-range
        // request, if ever passed, falls back to the static default exactly
        // like the dict-based reference.
        let values = |arr: &Array1<f32>, default: Option<f32>| -> Vec<f32> {
            duts.iter()
                .map(|&d| {
                    if d >= 1 {
                        let p = d as usize - 1;
                        if p < arr.len() {
                            arr[p]
                        } else {
                            default.unwrap_or(f32::NAN)
                        }
                    } else {
                        default.unwrap_or(f32::NAN)
                    }
                })
                .collect()
        };
        let low = if has(&entry.ll_valid_idx) {
            match (&entry.llimit, entry.ll_default) {
                (Some(arr), def) => values(arr, def),
                (None, _) => Vec::new(),
            }
        } else {
            Vec::new()
        };
        let high = if has(&entry.hl_valid_idx) {
            match (&entry.hlimit, entry.hl_default) {
                (Some(arr), def) => values(arr, def),
                (None, _) => Vec::new(),
            }
        } else {
            Vec::new()
        };
        (low, high)
    }

    /// Lazily build (once per file) the raw `Dut_Info` row cache used by the
    /// partial-DUT-info query. Keeps raw fields only; formatted strings are
    /// produced per call for the filtered subset.
    fn ensure_partial_info(&mut self, fid: usize) -> Result<(), StdfHelperError> {
        if self.partial_info.contains_key(&fid) {
            return Ok(());
        }
        let mut stmt = self.conn.prepare_cached(FETCH_SELECT_PARTIAL_RAW)?;
        let rows = stmt.query_map([fid as i64], |row| {
            Ok(PartialDutRow {
                row_index: (row.get::<_, i64>(0)? as usize) - 1,
                part_id: row.get(1)?,
                part_text: row.get(2)?,
                head: row.get(3)?,
                site: row.get(4)?,
                superseded: row.get::<_, i64>(5)? != 0,
                flag: row.get(6)?,
            })
        })?;
        let mut all = Vec::new();
        for r in rows {
            all.push(r?);
        }
        self.partial_info.insert(fid, all);
        Ok(())
    }

    /// `getPartialDUTInfoOnCondition()` — (DUTIndex, PartID,
    /// "Head h - Site s", PartText, "State - 0xFL") served from the raw row
    /// cache. PartText is a new field added to the DUT-info rows (Python
    /// consumers were updated to the 5-field tuple).
    pub fn partial_dut_info_rows(
        &mut self,
        heads: &[i64],
        sites: &[i64],
        file_id: i64,
    ) -> Result<Vec<(i64, Option<String>, String, Option<String>, Option<String>)>, StdfHelperError>
    {
        if heads.is_empty() || sites.is_empty() {
            return Ok(Vec::new());
        }
        let Ok(fid) = usize::try_from(file_id) else {
            return Ok(Vec::new());
        };
        self.ensure_partial_info(fid)?;
        let all_sites = sites.contains(&-1);
        let mut out = Vec::new();
        let rows = self.partial_info.get(&fid).expect("just ensured");
        for row in rows {
            if !heads.contains(&(row.head as i64)) {
                continue;
            }
            if !all_sites && !sites.contains(&(row.site as i64)) {
                continue;
            }
            out.push((
                (row.row_index + 1) as i64,
                row.part_id.clone(),
                format!("Head {} - Site {}", row.head, row.site),
                row.part_text.clone(),
                format_dut_flag(row.superseded, row.flag),
            ));
        }
        Ok(out)
    }
}

// ---------------------------------------------------------------------------
// DUT/pin/wafer queries (port batch B).
// ---------------------------------------------------------------------------

/// One `Wafer_Info` row for `getWaferInfo()`.
pub struct WaferInfoRow {
    pub fid: i64,
    pub head_num: Option<i64>,
    pub wafer_index: i64,
    pub part_cnt: Option<i64>,
    pub rtst_cnt: Option<i64>,
    pub abrt_cnt: Option<i64>,
    pub good_cnt: Option<i64>,
    pub func_cnt: Option<i64>,
    pub wafer_id: Option<String>,
    pub fabwf_id: Option<String>,
    pub frame_id: Option<String>,
    pub mask_id: Option<String>,
    pub usr_desc: Option<String>,
    pub exc_desc: Option<String>,
}

impl DataFetcher {
    /// One row of `getPinNames()` for a single file: PMR/LOC/PHY names are
    /// filled with "" for NULL (as the Python reference does) and rows keep
    /// the TestPin_Map.ROWID order.
    pub fn pin_name_rows(
        &self,
        test_num: i64,
        test_name: &str,
        is_rtn: bool,
        fid: i64,
    ) -> Result<Vec<(i64, String, String, i64, i64, String)>, StdfHelperError> {
        let pin_type = if is_rtn { "RTN" } else { "PGM" };
        let mut stmt = self.conn.prepare_cached(FETCH_SELECT_PIN_NAMES)?;
        let rows = stmt
            .query_map(
                rusqlite::params![pin_type, test_num, test_name, fid, fid],
                |row| {
                    let none_to_empty = |v: Option<String>| v.unwrap_or_default();
                    Ok((
                        row.get::<_, i64>(0)?,
                        none_to_empty(row.get::<_, Option<String>>(2)?),
                        none_to_empty(row.get::<_, Option<String>>(1)?),
                        row.get::<_, i64>(3)?,
                        row.get::<_, i64>(4)?,
                        none_to_empty(row.get::<_, Option<String>>(5)?),
                    ))
                },
            )?
            .collect::<Result<Vec<_>, _>>()?;
        Ok(rows)
    }

    /// All `Wafer_Info` rows ordered by `WaferIndex` (as the reference query).
    pub fn wafer_info_rows(&self) -> Result<Vec<WaferInfoRow>, StdfHelperError> {
        let mut stmt = self.conn.prepare_cached(FETCH_SELECT_WAFER_INFO)?;
        let rows = stmt
            .query_map([], |row| {
                Ok(WaferInfoRow {
                    fid: row.get(0)?,
                    head_num: row.get(1)?,
                    wafer_index: row.get(2)?,
                    part_cnt: row.get(3)?,
                    rtst_cnt: row.get(4)?,
                    abrt_cnt: row.get(5)?,
                    good_cnt: row.get(6)?,
                    func_cnt: row.get(7)?,
                    wafer_id: row.get(8)?,
                    fabwf_id: row.get(9)?,
                    frame_id: row.get(10)?,
                    mask_id: row.get(11)?,
                    usr_desc: row.get(12)?,
                    exc_desc: row.get(13)?,
                })
            })?
            .collect::<Result<Vec<_>, _>>()?;
        Ok(rows)
    }

    /// `File_Info` rows used to extend `getWaferInfo()` (SubFid=0 die fields).
    pub fn wafer_ext_rows(&self, fid: i64) -> Result<Vec<(String, Option<String>)>, StdfHelperError> {
        let mut stmt = self.conn.prepare_cached(FETCH_SELECT_WAFER_EXT)?;
        let rows = stmt
            .query_map([fid], |row| {
                Ok((row.get::<_, String>(0)?, row.get::<_, Option<String>>(1)?))
            })?
            .collect::<Result<Vec<_>, _>>()?;
        Ok(rows)
    }

    /// `getWaferCoordsDict()` rows — (SBIN, XCOORD, YCOORD) skipping DUTs with
    /// NULL coordinates, matching the Python reference.
    pub fn wafer_coord_rows(
        &self,
        wafer_index: i64,
        sites: &[i64],
        fid: i64,
    ) -> Result<Vec<(i64, i64, i64)>, StdfHelperError> {
        let mut sql = String::from(
            "SELECT SBIN, XCOORD, YCOORD FROM Dut_Info \
             WHERE WaferIndex=? AND Fid=? AND Supersede=0 AND XCOORD IS NOT NULL \
             AND YCOORD IS NOT NULL",
        );
        let mut params: Vec<i64> = vec![wafer_index, fid];
        if sites.contains(&-1) {
            sql.push_str(" AND SITE_NUM >= 0");
        } else {
            sql.push_str(" AND SITE_NUM IN (");
            sql.push_str(&Self::in_clause_placeholders(sites.len()));
            sql.push(')');
            params.extend_from_slice(sites);
        }
        let mut stmt = self.conn.prepare_cached(&sql)?;
        let rows = stmt
            .query_map(rusqlite::params_from_iter(params.iter()), |row| {
                Ok((row.get::<_, i64>(0)?, row.get::<_, i64>(1)?, row.get::<_, i64>(2)?))
            })?
            .collect::<Result<Vec<_>, _>>()?;
        Ok(rows)
    }

    /// `getStackedWaferData()` rows — (X, Y, Flag, count) grouped by
    /// X/Y/Flag, skipping NULL coordinates/flags (mirrors the reference
    /// isinstance() guards; Flag & 24 == 8 filtering is done by the caller).
    pub fn stacked_wafer_rows(&self, sites: &[i64]) -> Result<Vec<(i64, i64, i64, i64)>, StdfHelperError> {
        let mut sql = String::from(
            "SELECT XCOORD, YCOORD, Flag, count(Flag) FROM Dut_Info \
             WHERE HEAD_NUM>=0 AND Supersede=0 AND XCOORD IS NOT NULL \
             AND YCOORD IS NOT NULL AND Flag IS NOT NULL",
        );
        let mut params: Vec<i64> = Vec::new();
        if sites.contains(&-1) {
            sql.push_str(" AND SITE_NUM >= 0");
        } else {
            sql.push_str(" AND SITE_NUM IN (");
            sql.push_str(&Self::in_clause_placeholders(sites.len()));
            sql.push(')');
            params.extend_from_slice(sites);
        }
        sql.push_str(" GROUP By XCOORD, YCOORD, Flag");
        let mut stmt = self.conn.prepare_cached(&sql)?;
        let rows = stmt
            .query_map(rusqlite::params_from_iter(params.iter()), |row| {
                Ok((
                    row.get::<_, i64>(0)?,
                    row.get::<_, i64>(1)?,
                    row.get::<_, i64>(2)?,
                    row.get::<_, i64>(3)?,
                ))
            })?
            .collect::<Result<Vec<_>, _>>()?;
        Ok(rows)
    }

    /// `getDTR_GDRs()` rows — (Record Type, Value, Approx. Location) formatted
    /// like the reference DATALOG_QUERY (the reference iterates three columns).
    pub fn datalog_rows(&self) -> Result<Vec<(String, String, String)>, StdfHelperError> {
        let mut stmt = self.conn.prepare_cached(FETCH_SELECT_DATALOG)?;
        let rows = stmt
            .query_map([], |row| {
                Ok((
                    row.get::<_, String>(0)?,
                    row.get::<_, String>(1)?,
                    row.get::<_, String>(2)?,
                ))
            })?
            .collect::<Result<Vec<_>, _>>()?;
        Ok(rows)
    }
}

/// Merge a sorted unique `b` into a sorted unique `a` (result stays sorted,
/// no duplicates) — used to combine per-head/per-site index lists.
fn merge_sorted_unique(a: &mut Vec<usize>, b: &[usize]) {
    if b.is_empty() {
        return;
    }
    if a.is_empty() {
        *a = b.to_vec();
        return;
    }
    let mut out = Vec::with_capacity(a.len() + b.len());
    let (mut i, mut j) = (0, 0);
    while i < a.len() && j < b.len() {
        if a[i] == b[j] {
            out.push(a[i]);
            i += 1;
            j += 1;
        } else if a[i] < b[j] {
            out.push(a[i]);
            i += 1;
        } else {
            out.push(b[j]);
            j += 1;
        }
    }
    out.extend_from_slice(&a[i..]);
    out.extend_from_slice(&b[j..]);
    *a = out;
}

/// Mirrors the SQL `printf("%s - 0x%02X", CASE …, Flag)`: NULL Flag yields
/// NULL, exactly like the Python reference query.
fn format_dut_flag(superseded: bool, flag: Option<i64>) -> Option<String> {
    let flag = flag?;
    let state = if superseded {
        "Superseded"
    } else {
        match flag & 24 {
            0 => "Pass",
            8 => "Failed",
            _ => "Unknown",
        }
    };
    Some(format!("{} - 0x{:02X}", state, flag))
}

/// Finalize one test group of the dynamic-limit loader. Sides whose index set
/// stayed empty are discarded (they can never be queried), and a test without
/// any valid dynamic side is not cached at all.
fn flush_dynamic_entry(
    limits: &mut HashMap<TestId, DynamicLimitEntry>,
    active: &mut Option<TestId>,
    n: &mut usize,
    ll_arr: &mut Option<Array1<f32>>,
    hl_arr: &mut Option<Array1<f32>>,
    ll_def: &mut Option<f32>,
    hl_def: &mut Option<f32>,
    ll_valid: &mut Vec<usize>,
    hl_valid: &mut Vec<usize>,
) {
    let Some(test_id) = active.take() else {
        return;
    };
    *n = 0;
    let ll_arr = if ll_valid.is_empty() { None } else { ll_arr.take() };
    let hl_arr = if hl_valid.is_empty() { None } else { hl_arr.take() };
    let ll_def = if ll_arr.is_some() { ll_def.take() } else { None };
    let hl_def = if hl_arr.is_some() { hl_def.take() } else { None };
    if ll_arr.is_none() && hl_arr.is_none() {
        ll_valid.clear();
        hl_valid.clear();
        return;
    }
    limits.insert(
        test_id,
        DynamicLimitEntry {
            llimit: ll_arr,
            hlimit: hl_arr,
            ll_default: ll_def,
            hl_default: hl_def,
            ll_valid_idx: std::mem::take(ll_valid),
            hl_valid_idx: std::mem::take(hl_valid),
        },
    );
}
