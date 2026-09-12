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
use crate::database::schema::fetcher_queries::*;
use crate::generic::error::StdfHelperError;
use crate::generic::helper::intersect_sorted;
use crate::stdf::record_tracker::TestSubCode;
use lru::LruCache;
use ndarray::{Array1, Array2};
use rusqlite::Connection;
use std::{
    collections::{BTreeSet, HashMap},
    sync::Arc,
};

pub type HeadNum = u8;
pub type SiteNum = u8;
pub type FileId = u64;
pub type TestNum = u32;

/// One `getTestFailCnt()` row: `(TEST_NUM, TEST_NAME, per-file FailCount)`.
pub type TestFailCntRow = (i64, String, Vec<Option<i64>>);
/// One `getBinInfo()` row: `(BIN_NUM, BIN_NAME, BIN_PF)`.
pub type BinInfoRow = (i64, Option<String>, Option<String>);
/// `(max X, min X, max Y, min Y)`; a value is None when no DUT matches.
pub type WaferBounds = (Option<i64>, Option<i64>, Option<i64>, Option<i64>);
/// One `getPinNames()` row:
/// `(PMR_INDX, LOG_NAM, PHY_NAM, HEAD_NUM, SITE_NUM, CHAN_NAM)`.
pub type PinNameRow = (i64, String, String, i64, i64, String);
/// One `getPartialDUTInfoOnCondition()` row:
/// `(DUTIndex, PartID, PartText, "Head h - Site s", "State - 0xFL")`.
pub type PartialDutInfo = (i64, Option<String>, Option<String>, String, String);

/// Represents the cached information for a single test.
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

/// Test data of one test, keyed by record type.
pub enum TestData {
    /// PTR: 1d array, index = DUTIndex - 1.
    Ptr(Array1<f32>),
    /// MPR: `values` and `states` are 2d array,
    /// with shape of (XX_CNT, DUT_CNT).
    Mpr {
        values: Array2<f32>,
        states: Array2<u8>,
    },
    /// FTR: only flags, no payload.
    FlagsOnly,
}

impl TestData {
    /// clear data for an entry with no valid test data.
    /// MPR row count is preserved, but all columns are cleared.
    fn empty_like(&self) -> Self {
        match self {
            TestData::Ptr(_) => TestData::Ptr(Array1::zeros(0)),
            TestData::Mpr { values, states } => {
                let rslt_cnt = values.nrows(); // result count
                let stat_cnt = states.nrows(); // state count
                TestData::Mpr {
                    values: Array2::zeros((rslt_cnt, 0)),
                    states: Array2::zeros((stat_cnt, 0)),
                }
            }
            TestData::FlagsOnly => TestData::FlagsOnly,
        }
    }

    fn size_bytes(&self) -> usize {
        match self {
            TestData::Ptr(values) => values.len() * size_of::<f32>(),
            TestData::Mpr { values, states } => values.len() * size_of::<f32>() + states.len(),
            TestData::FlagsOnly => 0,
        }
    }
}

/// Represents a cached entry of test data of PTR, MPR and FTR.
/// Each entry contains data of ALL DUTs,
/// and `valid_test_idx` indicates which DUTs have valid test data.
pub struct TestDataCacheEntry {
    pub data: TestData,
    pub flags: Array1<i16>,
    pub valid_test_idx: Vec<usize>,
}

impl TestDataCacheEntry {
    /// Rough estimation of a current cache entry in bytes.
    fn entry_size(&self) -> usize {
        // fixed bookkeeping cost of the entry itself
        const ENTRY_OVERHEAD: usize = 64;
        self.data.size_bytes()
            + self.flags.len() * size_of::<i16>()
            + self.valid_test_idx.len() * 8
            + ENTRY_OVERHEAD
    }
}

/// Test data fetched for DUTs of interest.
/// DUTs of interest are also included.
pub struct FetchedTestData {
    pub dut_list: Array1<u64>,
    pub data: TestData,
    pub flags: Array1<i16>,
}

/// Represents a cached entry of dynamic limits for a single PTR test.
/// Each entry contains dynamic limits of ALL DUTs,
/// and `??_valid_idx` tracks DUTs that have valid dynamic limits.
pub struct DynamicLimitEntry {
    pub llimit: Option<Array1<f32>>,
    pub hlimit: Option<Array1<f32>>,
    pub ll_default: Option<f32>,
    pub hl_default: Option<f32>,
    pub ll_valid_idx: Vec<usize>,
    pub hl_valid_idx: Vec<usize>,
}

/// Default cache upper limit for test data LRU.
const DEFAULT_TEST_CACHE_LIMIT: usize = 128 * 1024 * 1024; // 128 MiB

/// LRU Test data cache with byte-budgeted eviction.
struct TestDataLru {
    cache: LruCache<(TestId, FileId), TestDataCacheEntry>,
    budget_bytes: usize,
    used_bytes: usize,
}

impl TestDataLru {
    fn new(budget_bytes: usize) -> Self {
        // Use an unbounded LRU to avoid prealloc huge number of slot.
        // Eviction will be handled manually by estimating
        // each entry's memory footprint in bytes.
        Self {
            cache: LruCache::unbounded(),
            budget_bytes,
            used_bytes: 0,
        }
    }

    fn get(&mut self, key: &(TestId, FileId)) -> Option<&TestDataCacheEntry> {
        self.cache.get(key)
    }

    /// Store a test data cache,
    /// evict least-used ones if not enough remaining budget.
    fn insert(&mut self, key: (TestId, FileId), entry: TestDataCacheEntry) {
        let bytes = entry.entry_size();
        if bytes > self.budget_bytes {
            // Entry is too large to fit in the cache, skip insertion.
            return;
        }
        // In case an entry with the same key already exists,
        // subtract old size first.
        if let Some(old) = self.cache.put(key, entry) {
            self.used_bytes = self.used_bytes.saturating_sub(old.entry_size());
        }
        // Add the new entry's size to the used bytes.
        self.used_bytes += bytes;
        // Evict least-used entries until the used bytes are within the budget.
        while self.used_bytes > self.budget_bytes {
            match self.cache.pop_lru() {
                Some((_, evicted)) => self.used_bytes -= evicted.entry_size(),
                None => break,
            }
        }
    }

    fn clear(&mut self) {
        self.cache.clear();
        self.used_bytes = 0;
    }
}

/// Rust version of DatabaseFetcher, owns the database connection
/// and manages caches for fast access.
pub struct DataFetcher {
    conn: Connection,
    file_paths: Vec<Vec<String>>,
    /// fid -> full dut array (starts from 1).
    full_dut: HashMap<FileId, Array1<u64>>,
    /// (fid, head, site?) -> sorted dut array indices of non-superseded DUTs.
    head_site_dutarr_idx: HashMap<(FileId, HeadNum, Option<SiteNum>), Vec<usize>>,
    /// (fid, head, site?) -> sorted dut array indices of all DUTs, including superseded ones.
    head_site_dutarr_idx_all: HashMap<(FileId, HeadNum, Option<SiteNum>), Vec<usize>>,
    /// (fid, test_num) -> test_name -> TestInfo.
    test_info: HashMap<(FileId, TestNum), HashMap<String, Arc<TestInfo>>>,
    /// test_id -> dynamic limit cache.
    /// `None` cache means already queried but no dynamic limit found.
    dynamic_limits: HashMap<TestId, Option<DynamicLimitEntry>>,
    site_list: Vec<SiteNum>,
    head_list: Vec<HeadNum>,
    /// LRU cache for test data.
    test_data: TestDataLru,
}

impl DataFetcher {
    /// Open a database, set test data cache with default budget.
    pub fn open(path: &str) -> Result<Self, StdfHelperError> {
        Self::open_with_budget(path, DEFAULT_TEST_CACHE_LIMIT)
    }

    /// Open a database, set test data cache with the specified budget.
    pub fn open_with_budget(path: &str, budget_bytes: usize) -> Result<Self, StdfHelperError> {
        let conn = Connection::open(path)?;
        let mut fetcher = Self {
            conn,
            file_paths: Vec::new(),
            full_dut: HashMap::new(),
            head_site_dutarr_idx: HashMap::new(),
            head_site_dutarr_idx_all: HashMap::new(),
            test_info: HashMap::new(),
            dynamic_limits: HashMap::new(),
            site_list: Vec::new(),
            head_list: Vec::new(),
            test_data: TestDataLru::new(budget_bytes),
        };
        fetcher.read_file_paths()?;
        fetcher.build_file_caches()?;
        fetcher.load_test_info()?;
        Ok(fetcher)
    }

    pub fn close(&mut self) {
        self.file_paths.clear();
        self.full_dut.clear();
        self.head_site_dutarr_idx.clear();
        self.head_site_dutarr_idx_all.clear();
        self.test_info.clear();
        self.dynamic_limits.clear();
        self.site_list.clear();
        self.head_list.clear();
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
        let mut fids: Vec<usize> = d.keys().copied().collect();
        fids.sort_unstable();
        let mut paths = Vec::new();
        for fid in fids {
            paths.push(d.remove(&fid).unwrap());
        }
        self.file_paths = paths;
        Ok(())
    }

    fn build_file_caches(&mut self) -> Result<(), StdfHelperError> {
        let mut all_heads: BTreeSet<HeadNum> = BTreeSet::new();
        let mut all_sites: BTreeSet<SiteNum> = BTreeSet::new();
        for fid in 0..self.num_files() {
            let fid = fid as FileId;
            // File without PIR/PRR is a valid state and MAX() can return NULL,
            // return an empty DUT array in that case.
            let max_dut = self
                .conn
                .query_row(FETCH_SELECT_MAX_DUT_INDEX, [fid as i64], |row| {
                    row.get::<_, Option<u64>>(0)
                })?
                .unwrap_or(0);
            // DUT array starts from 1, and consecutive up to max_dut.
            self.full_dut.insert(fid, Array1::from_iter(1..=max_dut));

            // Both queries ORDER BY DUTIndex, so the per-key subsequences are
            // already sorted and no explicit sort is needed.
            for (sql, target) in [
                (FETCH_SELECT_DUT_HEAD_SITE, &mut self.head_site_dutarr_idx),
                (
                    FETCH_SELECT_DUT_HEAD_SITE_ALL,
                    &mut self.head_site_dutarr_idx_all,
                ),
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
                        // Convert DUTIndex (1-based) to dut array index (0-based),
                        // simply subtract 1.
                        let idx = dut_index.saturating_sub(1) as usize;
                        all_heads.insert(head);
                        all_sites.insert(site);
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
        self.site_list = all_sites.into_iter().collect();
        self.head_list = all_heads.into_iter().collect();
        Ok(())
    }

    pub fn get_site_list(&self) -> Result<Vec<SiteNum>, StdfHelperError> {
        Ok(self.site_list.clone())
    }

    pub fn get_head_list(&self) -> Result<Vec<HeadNum>, StdfHelperError> {
        Ok(self.head_list.clone())
    }

    /// Eagerly cache the whole `Test_Info` table, small but frequently accessed,
    /// when database connection is established.
    fn load_test_info(&mut self) -> Result<(), StdfHelperError> {
        let mut stmt = self.conn.prepare_cached(FETCH_SELECT_ALL_TEST_INFO)?;
        let rows = stmt.query_map([], |row| {
            Ok((
                row.get::<_, i64>(0)? as FileId, // Fid
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
                .insert(info.test_name.clone(), info.into());
        }
        Ok(())
    }

    pub fn get_test_info(
        &mut self,
        test_tup: (TestNum, &str),
        file_id: FileId,
    ) -> Result<Option<Arc<TestInfo>>, StdfHelperError> {
        Ok(self
            .test_info
            .get(&(file_id, test_tup.0))
            .and_then(|by_name| by_name.get(test_tup.1))
            .cloned())
    }

    /// Cache the test data of given test info.
    /// If already cached, update the recent order of the test data entry in LRU.
    ///
    /// Returns:
    /// - `Ok(None)` — cache completed.
    /// - `Ok(Some(entry))` — super large entry, not cached..
    fn ensure_test_data(
        &mut self,
        info: &TestInfo,
        file_id: FileId,
    ) -> Result<Option<TestDataCacheEntry>, StdfHelperError> {
        let test_id = info.test_id;
        let key = (test_id, file_id);
        if self.test_data.get(&key).is_some() {
            return Ok(None);
        }

        let dut_cnt = self.full_dut.get(&file_id).map(|a| a.len()).unwrap_or(0);
        let mut flags = Array1::from_elem(dut_cnt, -1i16);
        let mut valid = Vec::new();

        let data = match info.sub_code {
            TestSubCode::Ptr => {
                let mut values = Array1::from_elem(dut_cnt, f32::NAN);
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
                    // pos = dut array idx (0-based) = dut_index - 1
                    let pos = dut_index.saturating_sub(1) as usize;
                    if pos < dut_cnt {
                        values[pos] = result;
                        flags[pos] = flag as i16;
                        valid.push(pos);
                    }
                }
                TestData::Ptr(values)
            }
            TestSubCode::Ftr => {
                let mut stmt = self.conn.prepare_cached(FETCH_SELECT_FTR_DATA)?;
                let rows = stmt.query_map([test_id], |row| {
                    Ok((row.get::<_, i64>(0)?, row.get::<_, i64>(1)? as u8))
                })?;
                for row in rows {
                    let (dut_index, flag) = row?;
                    let pos = dut_index.saturating_sub(1) as usize;
                    if pos < dut_cnt {
                        flags[pos] = flag as i16;
                        valid.push(pos);
                    }
                }
                TestData::FlagsOnly
            }
            TestSubCode::Mpr => {
                // RTN_RSLT / RTN_STAT are stored as BLOBs (little-endian bytes).
                let rslt_cnt = info.rslt_pgm_cnt.unwrap_or(0) as usize;
                // According to the STDF spec, rtn_icnt should be the same as rslt_pgm_cnt
                // for multi-pin test, but keep them separate for clarity.
                let stat_cnt = info.rtn_icnt.unwrap_or(0) as usize;
                // Write into (row: DUT, col: pmr) for better cache locality,
                // transpose 2d array in the end.
                let mut values = Array2::from_elem((dut_cnt, rslt_cnt), f32::NAN);
                let mut states = Array2::from_elem((dut_cnt, stat_cnt), 0xFu8);
                let mut stmt = self.conn.prepare_cached(FETCH_SELECT_MPR_DATA)?;
                let rows = stmt.query_map([test_id], |row| {
                    Ok((
                        row.get::<_, i64>(0)? as u64,
                        row.get::<_, Vec<u8>>(1)?,
                        row.get::<_, Vec<u8>>(2)?,
                        row.get::<_, i64>(3)? as u8,
                    ))
                })?;
                for row in rows {
                    let (dut_index, rslt, stat, flag) = row?;
                    let pos = dut_index.saturating_sub(1) as usize;
                    if pos >= dut_cnt {
                        continue;
                    }
                    flags[pos] = flag as i16;
                    valid.push(pos);

                    // BLOBs carry no alignment, decode little-endian bytes to f32
                    // via `f32::to_le_bytes` to avoid alignment issue.
                    for (j, chunk) in rslt.chunks_exact(4).take(rslt_cnt).enumerate() {
                        values[[pos, j]] =
                            f32::from_le_bytes([chunk[0], chunk[1], chunk[2], chunk[3]]);
                    }
                    for (j, &state) in stat.iter().take(stat_cnt).enumerate() {
                        states[[pos, j]] = state;
                    }
                }
                TestData::Mpr {
                    values: values.reversed_axes(),
                    states: states.reversed_axes(),
                }
            }
            TestSubCode::Other => TestData::FlagsOnly,
        };

        // If the entry has no valid test data, drop the value arrays to save memory.
        let entry = if valid.is_empty() {
            TestDataCacheEntry {
                data: data.empty_like(),
                flags: Array1::zeros(0),
                valid_test_idx: Vec::new(),
            }
        } else {
            TestDataCacheEntry {
                data,
                flags,
                valid_test_idx: valid,
            }
        };

        let bytes = entry.entry_size();
        if bytes > self.test_data.budget_bytes {
            // Not storing super large entry into the cache
            println!(
                "Test cache [{}] is too large ({}) to cache, increasing cache limit ({}) instead",
                info.test_name, bytes, self.test_data.budget_bytes
            );
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
        file_id: FileId,
    ) -> Result<Option<FetchedTestData>, StdfHelperError> {
        let info = match self.get_test_info(test_tup, file_id)? {
            Some(info) => info,
            None => return Ok(None),
        };

        let all_sites = sites.contains(&None);
        let mut selected_idx: Vec<usize> = Vec::new();
        for &head in heads {
            if all_sites {
                if let Some(list) = self.head_site_dutarr_idx.get(&(file_id, head, None)) {
                    merge_sorted_unique(&mut selected_idx, list);
                }
            } else {
                for &site in sites {
                    if let Some(list) = self.head_site_dutarr_idx.get(&(file_id, head, site)) {
                        merge_sorted_unique(&mut selected_idx, list);
                    }
                }
            }
        }

        // retrieve cache via test ID and file ID
        let oversized_entry = self.ensure_test_data(&info, file_id)?;
        let entry = match &oversized_entry {
            Some(big_entry) => big_entry,
            None => {
                let key = (info.test_id, file_id);
                self.test_data.get(&key).ok_or_else(|| StdfHelperError {
                    msg: format!(
                        "Cache miss for test [{}] in file [{}] after ensuring test data, not should happen", 
                        info.test_name,
                        file_id
                )})?
            }
        };

        let full_dut = self.full_dut.get(&file_id).ok_or_else(|| StdfHelperError {
            msg: format!(
                "Cache miss for full DUT array in file [{}], should not happen",
                file_id
            ),
        })?;
        // fetch non-superceded test data, mask is obtained by
        // intersecting dut array idx of selected with that of valid test idx.
        let valid_idx = intersect_sorted(&selected_idx, &entry.valid_test_idx);
        // `select` with an index vector never panics on an empty selection or
        // on an entry that was shrunk to zero columns, and it yields exactly
        // the subset the caller gets.
        let data = match &entry.data {
            TestData::Ptr(values) => TestData::Ptr(values.select(ndarray::Axis(0), &valid_idx)),
            TestData::Mpr { values, states } => TestData::Mpr {
                values: values.select(ndarray::Axis(1), &valid_idx),
                states: states.select(ndarray::Axis(1), &valid_idx),
            },
            TestData::FlagsOnly => TestData::FlagsOnly,
        };
        Ok(Some(FetchedTestData {
            dut_list: full_dut.select(ndarray::Axis(0), &valid_idx),
            data,
            flags: entry.flags.select(ndarray::Axis(0), &valid_idx),
        }))
    }

    pub fn get_test_data_from_dut_index(
        &mut self,
        test_tup: (TestNum, &str),
        duts: &[u64],
        file_id: FileId,
    ) -> Result<Option<FetchedTestData>, StdfHelperError> {
        if duts.is_empty() {
            return Ok(None);
        }
        let info = match self.get_test_info(test_tup, file_id)? {
            Some(info) => info,
            None => return Ok(None),
        };
        let max_dut_index = self
            .full_dut
            .get(&file_id)
            .map(|a| a.len() as u64)
            .unwrap_or(0);

        // retrieve cache via test ID and file ID
        let oversized_entry = self.ensure_test_data(&info, file_id)?;
        let entry = match &oversized_entry {
            Some(big_entry) => big_entry,
            None => {
                let key = (info.test_id, file_id);
                self.test_data.get(&key).ok_or_else(|| StdfHelperError {
                    msg: format!("test-data cache miss for {:?}", key),
                })?
            }
        };

        let mut req_duts = duts.to_vec();
        req_duts.sort_unstable();
        let dut_count = req_duts.len();

        // Cannot use ndarray.select() here, because requested DUTs may be out
        // of range or carry no test data, and the result must keep the same
        // length as the request.
        let mut flags = Array1::from_elem(dut_count, -1i16);
        let mut data = match &entry.data {
            TestData::Ptr(_) => TestData::Ptr(Array1::from_elem(dut_count, f32::NAN)),
            TestData::Mpr { values, states } => {
                // result and state counts are independent.
                TestData::Mpr {
                    values: Array2::from_elem((values.nrows(), dut_count), f32::NAN),
                    states: Array2::from_elem((states.nrows(), dut_count), 0xFu8),
                }
            }
            TestData::FlagsOnly => TestData::FlagsOnly,
        };

        if !entry.valid_test_idx.is_empty() {
            for (i, &req_dut) in req_duts.iter().enumerate() {
                if req_dut == 0 || req_dut > max_dut_index {
                    continue;
                }
                let pos = req_dut as usize - 1;
                match (&mut data, &entry.data) {
                    (TestData::Ptr(dst), TestData::Ptr(src)) => dst[i] = src[pos],
                    (
                        TestData::Mpr {
                            values: dst_values,
                            states: dst_states,
                        },
                        TestData::Mpr {
                            values: src_values,
                            states: src_states,
                        },
                    ) => {
                        dst_values.column_mut(i).assign(&src_values.column(pos));
                        dst_states.column_mut(i).assign(&src_states.column(pos));
                    }
                    _ => {}
                }
                flags[i] = entry.flags[pos];
            }
        }

        Ok(Some(FetchedTestData {
            dut_list: Array1::from_vec(req_duts),
            data,
            flags,
        }))
    }

    /// Cache the dynamic limits of given test info.
    /// If given test info has no valid limits,
    /// `None` is stored to avoid re-querying.
    fn ensure_dynamic_limits(
        &mut self,
        info: &TestInfo,
        fid: FileId,
    ) -> Result<(), StdfHelperError> {
        let test_id = info.test_id;
        if self.dynamic_limits.contains_key(&test_id) {
            return Ok(());
        }

        let ll_def = info.llimit.filter(|v| !v.is_nan());
        let hl_def = info.hlimit.filter(|v| !v.is_nan());
        let max_dut_index = self.full_dut.get(&fid).map(|a| a.len()).unwrap_or(0);
        // dynamic limits are invalidated if:
        // 1. default limits are NaN or omitted.
        // 2. no DUTs are available in given file id.
        if max_dut_index == 0 || (ll_def.is_none() && hl_def.is_none()) {
            self.dynamic_limits.insert(test_id, None);
            return Ok(());
        }

        let mut ll_arr = ll_def.map(|v| Array1::from_elem(max_dut_index, v));
        let mut hl_arr = hl_def.map(|v| Array1::from_elem(max_dut_index, v));
        let mut ll_valid: Vec<usize> = Vec::new();
        let mut hl_valid: Vec<usize> = Vec::new();

        {
            // query dynamic limits from the database
            let mut stmt = self
                .conn
                .prepare_cached(FETCH_SELECT_DYNAMIC_LIMITS_BY_TEST)?;
            let rows = stmt.query_map([test_id], |row| {
                Ok((
                    row.get::<_, i64>(0)?,
                    row.get::<_, Option<f32>>(1)?,
                    row.get::<_, Option<f32>>(2)?,
                ))
            })?;
            for r in rows {
                let (dut_index, ll, hl) = r?;
                let idx = dut_index.saturating_sub(1) as usize;
                if idx >= max_dut_index {
                    continue;
                }
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

        if ll_valid.is_empty() && hl_valid.is_empty() {
            // all dynamic limits are missing,
            // storing None for this test_id
            self.dynamic_limits.insert(test_id, None);
        } else {
            self.dynamic_limits.insert(
                test_id,
                Some(DynamicLimitEntry {
                    llimit: if ll_valid.is_empty() { None } else { ll_arr },
                    hlimit: if hl_valid.is_empty() { None } else { hl_arr },
                    ll_default: ll_def,
                    hl_default: hl_def,
                    ll_valid_idx: ll_valid,
                    hl_valid_idx: hl_valid,
                }),
            );
        }
        Ok(())
    }

    /// Returns dynamic (low_limits, high_limits) for
    /// requested DUTs of a given test.
    /// Default limits are used if request DUT has none.
    pub fn get_dynamic_limits(
        &mut self,
        info: &TestInfo,
        fid: FileId,
        duts: &[u64],
    ) -> Result<(Array1<f32>, Array1<f32>), StdfHelperError> {
        self.ensure_dynamic_limits(info, fid)?;
        let test_id = info.test_id;
        let Some(Some(entry)) = self.dynamic_limits.get(&test_id) else {
            return Ok((Array1::zeros(0), Array1::zeros(0)));
        };

        // check if there are any `duts` has dynamic limits.
        // DUTIndex is 1-based; `checked_sub` invalidates 0.
        let has_dynamic = |valid_idx: &[usize]| {
            duts.iter().any(|dut| {
                dut.checked_sub(1)
                    .is_some_and(|p| valid_idx.binary_search(&(p as usize)).is_ok())
            })
        };

        let get_dylim = |lim_arr: &Option<Array1<f32>>, lim_def: Option<f32>| -> Vec<f32> {
            if let (Some(arr), Some(def)) = (lim_arr, lim_def) {
                duts.iter()
                    .map(|dut| match dut.checked_sub(1) {
                        Some(p) if (p as usize) < arr.len() => arr[p as usize],
                        _ => def,
                    })
                    .collect()
            } else {
                Vec::new()
            }
        };
        let low = if has_dynamic(&entry.ll_valid_idx) {
            get_dylim(&entry.llimit, entry.ll_default)
        } else {
            Vec::new()
        };
        let high = if has_dynamic(&entry.hl_valid_idx) {
            get_dylim(&entry.hlimit, entry.hl_default)
        } else {
            Vec::new()
        };
        Ok((Array1::from_vec(low), Array1::from_vec(high)))
    }

    /// Returns a vec of (DUTIndex, PartID, PartText,
    /// "Head h - Site s", "State - 0xFL").
    pub fn get_partial_dut_info(
        &self,
        heads: &[i32],
        sites: &[i32],
        file_id: FileId,
    ) -> Result<Vec<PartialDutInfo>, StdfHelperError> {
        if heads.is_empty() || sites.is_empty() {
            return Ok(Vec::new());
        }
        let heads_json = json_int_array(heads.iter().map(|&h| h as i64))?;
        // `-1` means "all sites"; the reference then only excludes NULL/NULL-ish
        // rows with `SITE_NUM >= 0`.
        let all_sites = sites.contains(&-1);
        let sql = if all_sites {
            FETCH_SELECT_PARTIAL_ALL_SITES
        } else {
            FETCH_SELECT_PARTIAL_SITES
        };
        let sites_json = json_int_array(sites.iter().map(|&s| s as i64))?;
        let mut stmt = self.conn.prepare_cached(sql)?;

        let map_row = |row: &rusqlite::Row<'_>| -> rusqlite::Result<PartialDutInfo> {
            let dut_index = row.get::<_, i64>(0)?;
            let part_id = row.get::<_, Option<String>>(1)?;
            let part_text = row.get::<_, Option<String>>(2)?;
            let head_site = format!(
                "Head {} - Site {}",
                row.get::<_, i64>(3)?,
                row.get::<_, i64>(4)?
            );
            let superseded = row.get::<_, i64>(5)? != 0;
            let flag = row.get::<_, i64>(6)? as u8;
            Ok((
                dut_index,
                part_id,
                part_text,
                head_site,
                format_dut_flag(superseded, flag),
            ))
        };

        let mut info_out = Vec::new();
        if all_sites {
            let rows = stmt.query_map(rusqlite::params![file_id, heads_json], map_row)?;
            for row in rows {
                info_out.push(row?);
            }
        } else {
            let rows =
                stmt.query_map(rusqlite::params![file_id, heads_json, sites_json], map_row)?;
            for row in rows {
                info_out.push(row?);
            }
        }
        Ok(info_out)
    }
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
    pub fn test_fail_cnt_rows(&self) -> Result<Vec<TestFailCntRow>, StdfHelperError> {
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
    pub fn bin_info_rows(&self, is_hbin: bool) -> Result<Vec<BinInfoRow>, StdfHelperError> {
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
                    Ok(Some((row.get::<_, i64>(0)?, bin, row.get::<_, i64>(2)?)))
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
            && column
                .bytes()
                .all(|b| b.is_ascii_alphanumeric() || b == b'_');
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
    pub fn full_dut_summary_rows(
        &self,
        fid: FileId,
    ) -> Result<Vec<DutSummaryRow>, StdfHelperError> {
        let sql = format!(
            "{} WHERE Dut_Info.Fid=? ORDER BY DUTIndex",
            FETCH_SELECT_DUT_SUMMARY
        );
        let mut stmt = self.conn.prepare_cached(&sql)?;
        // The cells below are read by position; keep this in sync with
        // FETCH_SELECT_DUT_SUMMARY if its column list ever changes.
        debug_assert_eq!(stmt.column_count(), 12);
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
        let sql = FETCH_COUNT_ON_COND.replace("{extra}", &extra);
        let (pass, failed, unknown, superseded) =
            self.conn
                .query_row(&sql, rusqlite::params_from_iter(params.iter()), |r| {
                    Ok((
                        r.get::<_, i64>(0)?,
                        r.get::<_, i64>(1)?,
                        r.get::<_, i64>(2)?,
                        r.get::<_, i64>(3)?,
                    ))
                })?;
        Ok(vec![pass, failed, unknown, superseded])
    }

    /// `getDutIndexDictFromHeadSite()` rows — (Fid, DUTIndex) for non-empty
    /// head/site selections.
    ///
    /// Served from `head_site_dutarr_idx_all`: the Python method has *no* Supersede
    /// filter, so it must use the all-rows index (not the Supersede=0 cache).
    pub fn get_dut_index_by_head_site(
        &self,
        heads: &[i32],
        sites: &[i32],
        file_id: FileId,
    ) -> Result<Array1<u64>, StdfHelperError> {
        if heads.is_empty() || sites.is_empty() {
            return Ok(Array1::from(Vec::new()));
        }
        let all_sites = sites.contains(&-1);
        let mut duts: Vec<u64> = Vec::new();

        let mut acc: Vec<usize> = Vec::new();
        for &h in heads {
            let Ok(head) = u8::try_from(h) else {
                continue;
            };
            if all_sites {
                if let Some(list) = self.head_site_dutarr_idx_all.get(&(file_id, head, None)) {
                    merge_sorted_unique(&mut acc, list);
                }
            } else {
                for &s in sites {
                    let Ok(site) = u8::try_from(s) else {
                        continue;
                    };
                    if let Some(list) =
                        self.head_site_dutarr_idx_all
                            .get(&(file_id, head, Some(site)))
                    {
                        merge_sorted_unique(&mut acc, list);
                    }
                }
            }
        }
        duts.extend(acc.into_iter().map(|row| (row + 1) as u64));

        Ok(Array1::from(duts))
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
            let sql = if *is_hbin {
                FETCH_SELECT_DUT_INDEX_BY_HBIN
            } else {
                FETCH_SELECT_DUT_INDEX_BY_SBIN
            };
            let bins_json = json_int_array(bins.iter().copied())?;
            let mut stmt = self.conn.prepare_cached(sql)?;
            let rows = stmt.query_map(rusqlite::params![bins_json, fid], |row| {
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
        for (wafer_index, fid, (x, y)) in selections {
            if *wafer_index == -1 {
                let mut stmt = self.conn.prepare_cached(FETCH_SELECT_DUT_INDEX_BY_XY)?;
                let rows = stmt
                    .query_map(rusqlite::params![x, y], |row| {
                        Ok((row.get::<_, i64>(0)?, row.get::<_, i64>(1)?))
                    })?
                    .collect::<Result<Vec<_>, _>>()?;
                out.extend(rows);
            } else {
                let mut stmt = self
                    .conn
                    .prepare_cached(FETCH_SELECT_DUT_INDEX_BY_XY_WAFER)?;
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
    pub fn wafer_bounds(&self, wafer_index: i64, fid: i64) -> Result<WaferBounds, StdfHelperError> {
        if wafer_index == -1 {
            Ok(self
                .conn
                .query_row(FETCH_SELECT_WAFER_BOUNDS_STACKED, [], |row| {
                    Ok((
                        row.get::<_, Option<i64>>(0)?,
                        row.get::<_, Option<i64>>(1)?,
                        row.get::<_, Option<i64>>(2)?,
                        row.get::<_, Option<i64>>(3)?,
                    ))
                })?)
        } else {
            Ok(self.conn.query_row(
                FETCH_SELECT_WAFER_BOUNDS_WAFER,
                rusqlite::params![fid, wafer_index],
                |row| {
                    Ok((
                        row.get::<_, Option<i64>>(0)?,
                        row.get::<_, Option<i64>>(1)?,
                        row.get::<_, Option<i64>>(2)?,
                        row.get::<_, Option<i64>>(3)?,
                    ))
                },
            )?)
        }
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
        test_num: u32,
        test_name: &str,
        is_rtn: bool,
        fid: FileId,
    ) -> Result<Vec<PinNameRow>, StdfHelperError> {
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
    pub fn wafer_ext_rows(
        &self,
        fid: FileId,
    ) -> Result<Vec<(String, Option<String>)>, StdfHelperError> {
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
        wafer_index: u64,
        sites: &[i32],
        fid: FileId,
    ) -> Result<Vec<(i64, i64, i64)>, StdfHelperError> {
        if sites.is_empty() {
            return Ok(Vec::new());
        }
        let map_row = |row: &rusqlite::Row<'_>| -> rusqlite::Result<(i64, i64, i64)> {
            Ok((
                row.get::<_, i64>(0)?,
                row.get::<_, i64>(1)?,
                row.get::<_, i64>(2)?,
            ))
        };
        let rows = if sites.contains(&-1) {
            let mut stmt = self
                .conn
                .prepare_cached(FETCH_SELECT_WAFER_COORDS_ALL_SITES)?;
            let rows = stmt
                .query_map(rusqlite::params![wafer_index, fid], map_row)?
                .collect::<Result<Vec<_>, _>>()?;
            rows
        } else {
            let sites_json = json_int_array(sites.iter().map(|&s| s as i64))?;
            let mut stmt = self.conn.prepare_cached(FETCH_SELECT_WAFER_COORDS_SITES)?;
            let rows = stmt
                .query_map(rusqlite::params![wafer_index, fid, sites_json], map_row)?
                .collect::<Result<Vec<_>, _>>()?;
            rows
        };
        Ok(rows)
    }

    /// `getStackedWaferData()` rows — (X, Y, Flag, count) grouped by
    /// X/Y/Flag, skipping NULL coordinates/flags (mirrors the reference
    /// isinstance() guards; Flag & 24 == 8 filtering is done by the caller).
    pub fn stacked_wafer_rows(
        &self,
        sites: &[i32],
    ) -> Result<Vec<(i64, i64, i64, i64)>, StdfHelperError> {
        if sites.is_empty() {
            return Ok(Vec::new());
        }
        let map_row = |row: &rusqlite::Row<'_>| -> rusqlite::Result<(i64, i64, i64, i64)> {
            Ok((
                row.get::<_, i64>(0)?,
                row.get::<_, i64>(1)?,
                row.get::<_, i64>(2)?,
                row.get::<_, i64>(3)?,
            ))
        };
        let rows = if sites.contains(&-1) {
            let mut stmt = self
                .conn
                .prepare_cached(FETCH_SELECT_STACKED_WAFER_ALL_SITES)?;
            let rows = stmt.query_map([], map_row)?.collect::<Result<Vec<_>, _>>()?;
            rows
        } else {
            let sites_json = json_int_array(sites.iter().map(|&s| s as i64))?;
            let mut stmt = self.conn.prepare_cached(FETCH_SELECT_STACKED_WAFER_SITES)?;
            let rows = stmt
                .query_map(rusqlite::params![sites_json], map_row)?
                .collect::<Result<Vec<_>, _>>()?;
            rows
        };
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

/// Mirrors the SQL `printf("%s - 0x%02X", CASE …, Flag)`.
fn format_dut_flag(superseded: bool, flag: u8) -> String {
    let state = if superseded {
        "Superseded"
    } else {
        match flag & 24 {
            0 => "Pass",
            8 => "Failed",
            _ => "Unknown",
        }
    };
    format!("{} - 0x{:02X}", state, flag)
}

/// Serialize integers as a JSON array so a variable-length selection can be
/// bound as one parameter and read back with `json_each(?)`.
fn json_int_array<I: IntoIterator<Item = i64>>(values: I) -> Result<String, StdfHelperError> {
    serde_json::to_string(&values.into_iter().collect::<Vec<i64>>())
        .map_err(|e| StdfHelperError { msg: e.to_string() })
}
