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
use std::collections::{BTreeSet, HashMap};

pub type HeadNum = u8;
pub type SiteNum = u8;
pub type FileId = u64;
pub type TestNum = u32;

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

/// Represents a cached entry of test data of PTR, MPR and FTR.
/// Each entry contains data of ALL DUTs,
/// and `valid_test_idx` indicates which DUTs have valid test data.
pub struct TestDataCacheEntry {
    pub sub_code: TestSubCode,
    /// 1d array for PTR test, 2d array for MPR (rows: pins, columns: DUTs)
    pub data: Array2<f32>,
    /// pin states from MPR (rows: pins, columns: DUTs)
    pub states: Option<Array2<u8>>,
    pub flags: Array1<i16>,
    pub valid_test_idx: Vec<usize>,
}

impl TestDataCacheEntry {
    /// Rough estimation of a current cache entry in bytes.
    fn entry_size(&self) -> usize {
        const ENTRY_OVERHEAD: usize = 64;
        self.data.len() * 4
            + self.flags.len() * 2
            + self.states.as_ref().map_or(0, |s| s.len())
            + self.valid_test_idx.len() * 8
            // TODO: what is this overhead?
            + ENTRY_OVERHEAD
    }
}

/// Test data fetched for DUTs of interest.
/// DUTs of interest are also included.
pub struct FetchedTestData {
    pub sub_code: TestSubCode,
    pub dut_list: Array1<u64>,
    pub data: Array2<f32>,
    pub flags: Array1<i16>,
    pub states: Option<Array2<u8>>,
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

/// Subset of DUT Summary row, used in DUT Data Table.
/// Raw fields only; formatted strings are built per call.
pub struct PartialDutInfoRow {
    pub dut_index: u64,
    pub part_id: Option<String>,
    pub part_text: Option<String>,
    pub head: HeadNum,
    pub site: SiteNum,
    pub superseded: bool,
    pub flag: u8,
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
    test_info: HashMap<(FileId, TestNum), HashMap<String, TestInfo>>,
    /// test_id -> dynamic limit cache.
    /// `None` cache means already queried but no dynamic limit found.
    dynamic_limits: HashMap<TestId, Option<DynamicLimitEntry>>,
    /// fid -> partial DUT info.
    partial_dut_info: HashMap<FileId, Vec<PartialDutInfoRow>>,
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
            partial_dut_info: HashMap::new(),
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
        self.partial_dut_info.clear();
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
            let max_dut: i64 =
                self.conn
                    .query_row(FETCH_SELECT_MAX_DUT_INDEX, [fid as i64], |row| row.get(0))?;
            let max_dut = max_dut.max(1) as usize;
            // DUT array starts from 1, and consecutive up to max_dut.
            self.full_dut
                .insert(fid, Array1::from_iter(1..=max_dut as u64));

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
                .insert(info.test_name.clone(), info);
        }
        Ok(())
    }

    pub fn get_test_info(
        &mut self,
        test_tup: (TestNum, &str),
        file_id: FileId,
    ) -> Result<Option<TestInfo>, StdfHelperError> {
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
        let sub_code = info.sub_code;
        let key = (test_id, file_id);
        if self.test_data.get(&key).is_some() {
            return Ok(None);
        }

        let dut_cnt = self.full_dut.get(&file_id).map(|a| a.len()).unwrap_or(0);
        let mut flags = Array1::from_elem(dut_cnt, -1i16);
        let mut valid = Vec::new();

        let entry = match sub_code {
            TestSubCode::Ptr => {
                let mut data = Array2::from_elem((1, dut_cnt), f32::NAN);
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
                        // pos = dut array idx (0-based) = dut_index - 1
                        let pos = dut_index.saturating_sub(1) as usize;
                        if pos < dut_cnt {
                            data[[0, pos]] = result;
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
                let data = Array2::from_elem((0, dut_cnt), f32::NAN);
                {
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
                // RTN_RSLT / RTN_STAT are stored as BLOBs (little-endian bytes).
                let rows_vec: Vec<(u64, Vec<u8>, Vec<u8>, u8)> = {
                    let mut stmt = self.conn.prepare_cached(FETCH_SELECT_MPR_DATA)?;
                    let rows = stmt.query_map([test_id], |row| {
                        Ok((
                            row.get::<_, i64>(0)? as u64,
                            row.get::<_, Vec<u8>>(1)?,
                            row.get::<_, Vec<u8>>(2)?,
                            row.get::<_, i64>(3)? as u8,
                        ))
                    })?;
                    rows.collect::<Result<Vec<_>, _>>()?
                };
                // Number of test data in MPR is determined by RSLT_PGM_CNT from Test_Info,
                // represents the number of tested pins.
                let rslt_cnt = info.rslt_pgm_cnt.unwrap_or(0) as usize;

                // use (row: dutIndex, col: pmr) to improve cache hit when updating,
                // transpose the layout when storing into the cache.
                let mut data = Array2::from_elem((dut_cnt, rslt_cnt), f32::NAN);
                let mut states = Array2::from_elem((dut_cnt, rslt_cnt), 0xFu8);
                for (dut_index, rslt, stat, flag) in rows_vec {
                    let pos = dut_index.saturating_sub(1) as usize;
                    if pos >= dut_cnt {
                        continue;
                    }
                    flags[pos] = flag as i16;
                    valid.push(pos);

                    if rslt_cnt > 0 {
                        let result = unsafe {
                            std::slice::from_raw_parts(
                                rslt.as_ptr() as *const f32,
                                rslt.len() / size_of::<f32>(),
                            )
                        };
                        if result.len() != rslt_cnt {
                            println!(
                                "Warning: MPR [{}] result count ({}) of DUTIndex {} differs from database MPR info ({})",
                                info.test_name,
                                result.len(),
                                dut_index,
                                rslt_cnt,
                            );
                        }
                        for (j, value) in result[..rslt_cnt].iter().enumerate() {
                            data[[pos, j]] = *value;
                        }
                        for (j, value) in stat[..rslt_cnt].iter().enumerate() {
                            states[[pos, j]] = *value;
                        }
                    }
                }
                TestDataCacheEntry {
                    sub_code,
                    data: data.reversed_axes(),
                    flags,
                    states: Some(states.reversed_axes()),
                    valid_test_idx: valid,
                }
            }
            TestSubCode::Other => TestDataCacheEntry {
                sub_code,
                data: Array2::from_shape_fn((0, dut_cnt), |_| f32::NAN),
                flags,
                states: None,
                valid_test_idx: valid,
            },
        };

        // if the entry has no valid test data, replace data with empty arrays to save memory,
        // it's safe because data will never be accessed.
        let entry = if entry.valid_test_idx.is_empty() {
            TestDataCacheEntry {
                sub_code: entry.sub_code,
                data: Array2::from_elem((0, dut_cnt), f32::NAN),
                flags: Array1::from_elem(0, -1i16),
                states: Some(Array2::from_elem((0, dut_cnt), 0xFu8)),
                valid_test_idx: Vec::new(),
            }
        } else {
            entry
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
        let valid_dut: Array1<u64> = full_dut.select(ndarray::Axis(0), &valid_idx);
        let fetched = match entry.sub_code {
            TestSubCode::Ptr => FetchedTestData {
                sub_code: entry.sub_code,
                dut_list: valid_dut,
                data: entry.data.select(ndarray::Axis(1), &valid_idx),
                flags: entry.flags.select(ndarray::Axis(0), &valid_idx),
                states: None,
            },
            TestSubCode::Mpr => {
                let states = entry
                    .states
                    .as_ref()
                    .map(|s| s.select(ndarray::Axis(1), &valid_idx));
                FetchedTestData {
                    sub_code: entry.sub_code,
                    dut_list: valid_dut,
                    data: entry.data.select(ndarray::Axis(1), &valid_idx),
                    flags: entry.flags.select(ndarray::Axis(0), &valid_idx),
                    states,
                }
            }
            // FTR and any unknown/legacy code: flags only.
            TestSubCode::Ftr | TestSubCode::Other => FetchedTestData {
                sub_code: entry.sub_code,
                dut_list: valid_dut,
                data: Array2::from_shape_fn((0, valid_idx.len()), |_| f32::NAN),
                flags: entry.flags.select(ndarray::Axis(1), &valid_idx),
                states: None,
            },
        };

        Ok(Some(fetched))
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
        if max_dut_index == 0 {
            return Ok(None);
        }

        // retrieve cache via test ID and file ID
        let oversized_entry = self.ensure_test_data(&info, file_id)?;
        let entry = match &oversized_entry {
            Some(big_entry) => {
                println!("Cache size of test [{} - {}] in file [{}] ({}) exceeds max cache size ({}), consider increase the cache limit", 
                    test_tup.0, test_tup.1, file_id,
                    big_entry.entry_size(),
                    self.test_data.budget_bytes
                );
                big_entry
            }
            None => {
                let key = (info.test_id, file_id);
                self.test_data.get(&key).ok_or_else(|| StdfHelperError {
                    msg: format!("test-data cache miss for {:?}", key),
                })?
            }
        };

        let mut req_duts = duts.to_vec();
        req_duts.sort_unstable();
        let req_duts: Array1<u64> = Array1::from_vec(req_duts);
        let dut_count = req_duts.len();

        // cannot use ndarray.select() to get test data of selected duts, because:
        // 1. requested DUTs may out of range or invalid.
        // 2. returned data must have same length as requested DUTs.
        let mut data = Array2::from_elem((entry.data.nrows(), dut_count), f32::NAN);
        let mut flags = Array1::from_elem(dut_count, -1i16);
        let mut states = entry
            .states
            .as_ref()
            .map(|s| Array2::from_elem((s.nrows(), dut_count), 0xFu8));

        for (i, &req_dut) in req_duts.iter().enumerate() {
            if 1 <= req_dut && req_dut <= max_dut_index {
                let pos = req_dut as usize - 1;

                data.column_mut(i).assign(&entry.data.column(pos));
                if let (Some(dst), Some(src)) = (states.as_mut(), entry.states.as_ref()) {
                    dst.column_mut(i).assign(&src.column(pos));
                }
                flags[i] = entry.flags[pos];
            }
        }

        Ok(Some(FetchedTestData {
            sub_code: entry.sub_code,
            dut_list: req_duts,
            data,
            flags,
            states,
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

        // check if there are any `duts` has dynamic limits
        let has_dynamic = |valid_idx: &[usize]| {
            duts.iter().any(|dut| {
                let p = *dut as usize - 1;
                valid_idx.binary_search(&p).is_ok()
            })
        };

        let get_dylim = |lim_arr: &Option<Array1<f32>>, lim_def: Option<f32>| -> Vec<f32> {
            if let (Some(arr), Some(def)) = (lim_arr, lim_def) {
                duts.iter()
                    .map(|dut| {
                        let p = *dut as usize - 1;
                        if p < arr.len() {
                            arr[p]
                        } else {
                            def
                        }
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

    /// Cache partial DUT info of a given file.
    fn ensure_partial_dut_info(&mut self, fid: FileId) -> Result<(), StdfHelperError> {
        if self.partial_dut_info.contains_key(&fid) {
            return Ok(());
        }
        let mut stmt = self.conn.prepare_cached(FETCH_SELECT_PARTIAL_RAW)?;
        let rows = stmt.query_map([fid as i64], |row| {
            Ok(PartialDutInfoRow {
                dut_index: row.get::<_, i64>(0)? as u64,
                part_id: row.get(1)?,
                part_text: row.get(2)?,
                head: row.get::<_, i64>(3)? as u8,
                site: row.get::<_, i64>(4)? as u8,
                superseded: row.get::<_, i64>(5)? != 0,
                flag: row.get::<_, i64>(6)? as u8,
            })
        })?;
        let mut all_info = Vec::new();
        for r in rows {
            all_info.push(r?);
        }
        self.partial_dut_info.insert(fid, all_info);
        Ok(())
    }

    /// `getPartialDUTInfoOnCondition()` — (DUTIndex, PartID,
    /// "Head h - Site s", PartText, "State - 0xFL") served from the raw row
    /// cache. PartText is a new field added to the DUT-info rows (Python
    /// consumers were updated to the 5-field tuple).
    pub fn get_partial_dut_info(
        &mut self,
        heads: &[i32],
        sites: &[i32],
        file_id: FileId,
    ) -> Result<Vec<(i64, Option<String>, String, Option<String>, Option<String>)>, StdfHelperError>
    {
        if heads.is_empty() || sites.is_empty() {
            return Ok(Vec::new());
        }
        self.ensure_partial_dut_info(file_id)?;

        let rows = self
            .partial_dut_info
            .get(&file_id)
            .ok_or_else(|| StdfHelperError {
                msg: format!(
                    "Cache missing for DUT info in file [{}] after ensuring test data, not should happen", 
                    file_id)
            })?;

        let duts = self.get_dut_index_by_head_site(&heads, &sites, file_id)?;
        let mut info_out = Vec::with_capacity(duts.len());
        // Cached dut info contains all DUTs in a file
        // and is sorted by DutIndex.
        //
        // `duts` is sorted subset array of complete DutIndex in a file.
        //
        // So it is safe to index cache info directly using `duts`.
        for dut in duts {
            let pos = dut.saturating_sub(1) as usize;
            let row = &rows[pos];
            info_out.push((
                row.dut_index as i64,
                row.part_id.clone(),
                format!("Head {} - Site {}", row.head, row.site),
                row.part_text.clone(),
                format_dut_flag(row.superseded, row.flag),
            ));
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
        let run = |sql: &str| -> Result<i64, StdfHelperError> {
            let sql = sql.replace("{extra}", &extra);
            Ok(self
                .conn
                .query_row(&sql, rusqlite::params_from_iter(params.iter()), |r| {
                    r.get::<_, i64>(0)
                })?)
        };
        Ok(vec![
            run(FETCH_COUNT_ON_COND_PASS)?,
            run(FETCH_COUNT_ON_COND_FAIL)?,
            run(FETCH_COUNT_ON_COND_UNKNOWN)?,
            run(FETCH_COUNT_ON_COND_SUPERSEDED)?,
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
    pub fn wafer_bounds(
        &self,
        wafer_index: i64,
        fid: i64,
    ) -> Result<(Option<i64>, Option<i64>, Option<i64>, Option<i64>), StdfHelperError> {
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
        let mut site_condition = String::new();
        let mut params = vec![wafer_index, fid];
        if sites.contains(&-1) {
            site_condition.push_str(" AND SITE_NUM >= 0");
        } else {
            site_condition.push_str(" AND SITE_NUM IN (");
            site_condition.push_str(&Self::in_clause_placeholders(sites.len()));
            site_condition.push(')');
            params.extend(sites.iter().map(|&s| s as u64));
        }
        let sql = FETCH_SELECT_WAFER_COORDS.replace("{site_condition}", &site_condition);
        let mut stmt = self.conn.prepare_cached(&sql)?;
        let rows = stmt
            .query_map(rusqlite::params_from_iter(params.iter()), |row| {
                Ok((
                    row.get::<_, i64>(0)?,
                    row.get::<_, i64>(1)?,
                    row.get::<_, i64>(2)?,
                ))
            })?
            .collect::<Result<Vec<_>, _>>()?;
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
        let mut site_condition = String::new();
        let mut params: Vec<i32> = Vec::new();
        if sites.contains(&-1) {
            site_condition.push_str(" AND SITE_NUM >= 0");
        } else {
            site_condition.push_str(" AND SITE_NUM IN (");
            site_condition.push_str(&Self::in_clause_placeholders(sites.len()));
            site_condition.push(')');
            params.extend_from_slice(sites);
        }
        let sql = FETCH_SELECT_STACKED_WAFER.replace("{site_condition}", &site_condition);
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
fn format_dut_flag(superseded: bool, flag: u8) -> Option<String> {
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
