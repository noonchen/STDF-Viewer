//
// fetcher.rs
//
// PyO3 wrapper around the pure Rust DataFetcher.
//
// Author: noonchen - chennoon233@foxmail.com
// Created Date: Tue Sep 01 2026
// -----
// Last Modified: Tue Sep 01 2026
// Modified By: noonchen
// -----
// Copyright (c) 2026 noonchen
//

use crate::database::fetcher::{
    DataFetcher, FetchedTestData, FileId, PinNameRow, TestData, WaferBounds,
};
use crate::generic::error::StdfHelperError;
use numpy::ndarray::Array1;
use numpy::IntoPyArray;
use numpy::PyArray1;
use pyo3::prelude::*;
use pyo3::types::{PyAny, PyDict, PyList, PyTuple};
use pyo3::IntoPyObjectExt;
use std::collections::HashSet;

/// `(lower_limits, upper_limits)` for the requested DUTs, as numpy arrays.
type LimitArrays<'py> = (Bound<'py, PyArray1<f32>>, Bound<'py, PyArray1<f32>>);

#[pyclass(name = "DataFetcher", module = "rust_stdf_helper", unsendable)]
pub struct PyDataFetcher {
    inner: DataFetcher,
}

#[pymethods]
impl PyDataFetcher {
    #[new]
    #[pyo3(signature = (path, cache_budget_mb=None))]
    pub fn new(py: Python<'_>, path: &str, cache_budget_mb: Option<usize>) -> PyResult<Self> {
        // cache_budget_mb: Tier-2 test-data LRU byte budget in MiB
        // Defaults to 128 MiB when not given.
        // DB open scans Dut_Info/Test_Info per file, so release the GIL while
        // the caches are built.
        let inner = py.detach(|| match cache_budget_mb {
            Some(mb) => DataFetcher::open_with_budget(path, mb.saturating_mul(1024 * 1024)),
            None => DataFetcher::open(path),
        })?;
        Ok(Self { inner })
    }

    pub fn close(&mut self) {
        self.inner.close();
    }

    pub fn num_files(&self) -> PyResult<usize> {
        Ok(self.inner.num_files())
    }

    pub fn get_file_paths(&self) -> PyResult<Vec<Vec<String>>> {
        Ok(self.inner.file_paths())
    }

    pub fn get_site_list(&self) -> PyResult<Vec<i64>> {
        Ok(self
            .inner
            .get_site_list()?
            .into_iter()
            .map(|v| v as i64)
            .collect())
    }

    pub fn get_head_list(&self) -> PyResult<Vec<i64>> {
        Ok(self
            .inner
            .get_head_list()?
            .into_iter()
            .map(|v| v as i64)
            .collect())
    }

    pub fn get_test_info<'py>(
        &mut self,
        py: Python<'py>,
        test_num: u32,
        test_name: &str,
        file_id: FileId,
    ) -> PyResult<Option<Bound<'py, PyDict>>> {
        // Quick single-row lookup; still run it GIL-free so the SQLite hit
        // never stalls the UI thread.
        let inner = &mut self.inner;
        let info = py.detach(move || inner.get_test_info((test_num, test_name), file_id))?;
        let dict = PyDict::new(py);
        if let Some(info) = info {
            dict.set_item("Fid", file_id as i64)?;
            dict.set_item("TEST_ID", info.test_id)?;
            dict.set_item("TEST_NUM", info.test_num)?;
            dict.set_item("SUB_CODE", info.sub_code.code())?;
            dict.set_item("TEST_NAME", &info.test_name)?;
            dict.set_item("RES_SCAL", info.res_scal)?;
            dict.set_item("LLimit", info.llimit.map(f64::from).unwrap_or(f64::NAN))?;
            dict.set_item("HLimit", info.hlimit.map(f64::from).unwrap_or(f64::NAN))?;
            dict.set_item("Unit", info.unit.as_deref())?;
            dict.set_item("OPT_FLAG", info.opt_flag)?;
            dict.set_item("FailCount", info.fail_count)?;
            dict.set_item("RTN_ICNT", info.rtn_icnt)?;
            dict.set_item("RSLT_PGM_CNT", info.rslt_pgm_cnt)?;
            dict.set_item("LSpec", info.lspec.map(f64::from).unwrap_or(f64::NAN))?;
            dict.set_item("HSpec", info.hspec.map(f64::from).unwrap_or(f64::NAN))?;
            dict.set_item("VECT_NAM", info.vect_nam.as_deref())?;
            dict.set_item("SEQ_NAME", info.seq_name.as_deref())?;
            Ok(Some(dict))
        } else {
            Ok(None)
        }
    }

    pub fn get_test_data_from_head_site<'py>(
        &mut self,
        py: Python<'py>,
        test_num: u32,
        test_name: &str,
        heads: Vec<i64>,
        sites: Vec<i64>,
        file_id: FileId,
    ) -> PyResult<Option<Bound<'py, PyDict>>> {
        let heads_u8: Vec<u8> = heads.iter().map(|&h| h as u8).collect();
        let sites_opt: Vec<Option<u8>> = sites
            .iter()
            .map(|&s| if s < 0 { None } else { Some(s as u8) })
            .collect();
        // All heavy lifting (first-time SQLite scan, blob decode, row gather)
        // runs with the GIL released; Python objects are only touched after.
        let fetched = py.detach(|| {
            self.inner.get_test_data_from_head_site(
                (test_num, test_name),
                &heads_u8,
                &sites_opt,
                file_id,
            )
        })?;
        let dict = PyDict::new(py);
        if let Some(data) = fetched {
            fill_test_data_dict(&dict, data, py)?;
        }
        Ok(Some(dict))
    }

    pub fn get_test_data_from_dut_index<'py>(
        &mut self,
        py: Python<'py>,
        test_num: u32,
        test_name: &str,
        duts: Vec<u64>,
        file_id: FileId,
    ) -> PyResult<Option<Bound<'py, PyDict>>> {
        let fetched = py.detach(|| {
            self.inner
                .get_test_data_from_dut_index((test_num, test_name), &duts, file_id)
        })?;
        let dict = PyDict::new(py);
        if let Some(data) = fetched {
            fill_test_data_dict(&dict, data, py)?;
        }
        Ok(Some(dict))
    }

    // ----- Metadata / summary queries -----
    // Every query below runs with the GIL released. The inner methods take
    // `&self`, and `&DataFetcher` is not `Send` (`rusqlite::Connection` is
    // `!Sync`), so each closure moves in a `&mut` borrow (`let inner = &mut
    // self.inner`) that `py.detach` accepts.

    pub fn get_wafer_count(&mut self, py: Python<'_>) -> PyResult<Vec<i64>> {
        let inner = &mut self.inner;
        Ok(py.detach(move || inner.wafer_count())?)
    }

    pub fn get_byte_order(&mut self, py: Python<'_>) -> PyResult<Vec<bool>> {
        let inner = &mut self.inner;
        Ok(py.detach(move || inner.byte_order())?)
    }

    pub fn get_test_items(&mut self, py: Python<'_>) -> PyResult<Vec<String>> {
        let inner = &mut self.inner;
        Ok(py.detach(move || inner.test_items())?)
    }

    /// Rows of `(TEST_NUM, TEST_NAME, SUB_CODE)` in DB order.
    pub fn get_test_record_type_rows(
        &mut self,
        py: Python<'_>,
    ) -> PyResult<Vec<(i64, String, u8)>> {
        let inner = &mut self.inner;
        Ok(py.detach(move || inner.test_record_type_rows())?)
    }

    pub fn get_wafer_list(&mut self, py: Python<'_>) -> PyResult<Vec<String>> {
        let inner = &mut self.inner;
        Ok(py.detach(move || inner.wafer_list())?)
    }

    /// `getTestFailCnt()` — `{(TEST_NUM, TEST_NAME): [per-file FailCount]}`,
    /// built here so Python never loops over the rows.
    pub fn get_test_fail_cnt<'py>(&mut self, py: Python<'py>) -> PyResult<Bound<'py, PyDict>> {
        let inner = &mut self.inner;
        let rows = py.detach(move || inner.test_fail_cnt_rows())?;
        let dict = PyDict::new(py);
        for (test_num, test_name, per_file) in rows {
            let key: [Bound<'py, PyAny>; 2] = [
                test_num.into_bound_py_any(py)?,
                test_name.into_bound_py_any(py)?,
            ];
            dict.set_item(PyTuple::new(py, key)?, per_file)?;
        }
        Ok(dict)
    }

    /// `getBinInfo()` — `{BIN_NUM: {"BIN_NAME": ..., "BIN_PF": ...}}`, built
    /// here so Python never loops over the rows.
    pub fn get_bin_info<'py>(
        &mut self,
        py: Python<'py>,
        is_hbin: bool,
    ) -> PyResult<Bound<'py, PyDict>> {
        let inner = &mut self.inner;
        let rows = py.detach(move || inner.bin_info_rows(is_hbin))?;
        let dict = PyDict::new(py);
        for (bin_num, bin_name, bin_pf) in rows {
            let info = PyDict::new(py);
            info.set_item("BIN_NAME", bin_name)?;
            info.set_item("BIN_PF", bin_pf)?;
            dict.set_item(bin_num, info)?;
        }
        Ok(dict)
    }

    pub fn get_bin_stats_rows(
        &mut self,
        py: Python<'_>,
        head: i64,
        site: i64,
        is_hbin: bool,
    ) -> PyResult<Vec<(i64, i64, i64)>> {
        let inner = &mut self.inner;
        Ok(py.detach(move || inner.bin_stats_rows(head, site, is_hbin))?)
    }

    pub fn is_dut_info_column_empty(&mut self, py: Python<'_>, column: &str) -> PyResult<bool> {
        let inner = &mut self.inner;
        Ok(py.detach(move || inner.is_dut_info_column_empty(column))?)
    }

    /// Rows of `(Fid, Field, Value)` ordered by `Fid, Field, SubFid`.
    pub fn get_file_info_rows(
        &mut self,
        py: Python<'_>,
    ) -> PyResult<Vec<(i64, String, Option<String>)>> {
        let inner = &mut self.inner;
        Ok(py.detach(move || inner.file_info_rows())?)
    }

    // ----- DUT-level summary queries -----

    pub fn get_dut_count_dict<'py>(&mut self, py: Python<'py>) -> PyResult<Bound<'py, PyDict>> {
        let inner = &mut self.inner;
        let counts = py.detach(move || inner.dut_count_dict())?;
        let dict = PyDict::new(py);
        dict.set_item("Total", counts.total)?;
        dict.set_item("Pass", counts.pass)?;
        dict.set_item("Failed", counts.failed)?;
        dict.set_item("Superseded", counts.superseded)?;
        dict.set_item("Unknown", counts.unknown)?;
        Ok(dict)
    }

    pub fn get_dut_count_on_conditions(
        &mut self,
        py: Python<'_>,
        head: i64,
        site: i64,
        waferid: i64,
        fid: i64,
    ) -> PyResult<Vec<i64>> {
        let inner = &mut self.inner;
        Ok(py.detach(move || inner.dut_count_on_conditions(head, site, waferid, fid))?)
    }

    /// Returns `{fid: [dut_index, ...]}`
    pub fn get_dut_index_dict_by_head_site<'py>(
        &mut self,
        py: Python<'py>,
        heads: Vec<i32>,
        sites: Vec<i32>,
        mut file_ids: Vec<FileId>,
    ) -> PyResult<Bound<'py, PyDict>> {
        let dict = PyDict::new(py);
        if heads.is_empty() || sites.is_empty() {
            return Ok(dict);
        }
        // Ascending fid order (SQL orders by Fid, DUTIndex),
        // and no repeated work when a caller passes duplicates.
        file_ids.sort_unstable();
        file_ids.dedup();
        let heads_ref = &heads;
        let sites_ref = &sites;
        for fid in file_ids {
            let inner = &mut self.inner;
            let duts_in_fid =
                py.detach(move || inner.get_dut_index_by_head_site(heads_ref, sites_ref, fid))?;
            if duts_in_fid.is_empty() {
                continue;
            }
            dict.set_item(fid, duts_in_fid.into_pyarray(py))?;
        }
        Ok(dict)
    }

    /// `selections`: list of (fid, isHBIN, [bin numbers]).
    pub fn get_dut_index_rows_by_bin(
        &mut self,
        py: Python<'_>,
        selections: Vec<(i64, bool, Vec<i64>)>,
    ) -> PyResult<Vec<(i64, i64)>> {
        let inner = &mut self.inner;
        Ok(py.detach(move || inner.dut_index_rows_by_bin(&selections))?)
    }

    /// `selections`: list of (waferIndex, fid, (x, y)); waferIndex == -1
    /// means the stacked map (fid ignored).
    pub fn get_dut_index_rows_by_xy(
        &mut self,
        py: Python<'_>,
        selections: Vec<(i64, i64, (i64, i64))>,
    ) -> PyResult<Vec<(i64, i64)>> {
        let inner = &mut self.inner;
        Ok(py.detach(move || inner.dut_index_rows_by_xy(&selections))?)
    }

    pub fn get_wafer_bounds(
        &mut self,
        py: Python<'_>,
        wafer_index: i64,
        fid: i64,
    ) -> PyResult<WaferBounds> {
        let inner = &mut self.inner;
        Ok(py.detach(move || inner.wafer_bounds(wafer_index, fid))?)
    }

    /// Returns `(lower_limits, upper_limits)` as numpy arrays,
    /// same order as requested DUTs, use default limits
    /// where dynamic limits are not found.
    pub fn get_dynamic_limits<'py>(
        &mut self,
        py: Python<'py>,
        file_id: FileId,
        test_num: u32,
        test_name: &str,
        duts: Vec<u64>,
    ) -> PyResult<LimitArrays<'py>> {
        let limits = py.detach(|| -> Result<(Array1<f32>, Array1<f32>), StdfHelperError> {
            match self.inner.get_test_info((test_num, test_name), file_id)? {
                Some(info) => self.inner.get_dynamic_limits(&info, file_id, &duts),
                None => Ok((Array1::zeros(0), Array1::zeros(0))),
            }
        })?;
        Ok((limits.0.into_pyarray(py), limits.1.into_pyarray(py)))
    }

    /// Returns a dict, `dut_index -> (PartID, PartText, "Head h - Site s",
    /// "State - 0xFL")`.
    pub fn get_partial_dut_info<'py>(
        &mut self,
        py: Python<'py>,
        heads: Vec<i32>,
        sites: Vec<i32>,
        file_id: FileId,
    ) -> PyResult<Bound<'py, PyDict>> {
        let inner = &mut self.inner;
        let rows = py.detach(move || inner.get_partial_dut_info(&heads, &sites, file_id))?;
        let dict = PyDict::new(py);
        for (dut_index, part_id, part_text, hs_str, flag) in rows {
            let items: [Bound<'py, PyAny>; 4] = [
                part_id.into_bound_py_any(py)?,
                part_text.into_bound_py_any(py)?,
                hs_str.into_bound_py_any(py)?,
                flag.into_bound_py_any(py)?,
            ];
            dict.set_item(dut_index, PyTuple::new(py, items)?)?;
        }
        Ok(dict)
    }

    /// `getFullDUTInfoFromDutArray()` — `{dut_index: [File ID, Part ID, Part
    /// Text, head-site, tests executed, test time, HBIN, SBIN, wafer id, XY,
    /// DUT flag]}`. A requested DUT without a row maps to `()`.
    pub fn get_full_dut_info<'py>(
        &mut self,
        py: Python<'py>,
        duts: Vec<u64>,
        fid: FileId,
    ) -> PyResult<Bound<'py, PyDict>> {
        let mut wanted: HashSet<u64> = duts.iter().copied().collect();
        let inner = &mut self.inner;
        let rows = py.detach(move || inner.full_dut_summary_rows(fid))?;
        let dict = PyDict::new(py);
        for dut in &duts {
            dict.set_item(*dut, PyTuple::empty(py))?;
        }
        for r in rows {
            if !wanted.remove(&(r.dut_index as u64)) {
                continue;
            }
            let mut items: Vec<Bound<'py, PyAny>> = Vec::with_capacity(11);
            items.push(fid.into_bound_py_any(py)?);
            push_opt_str(&mut items, r.part_id, py)?;
            push_opt_str(&mut items, r.part_text, py)?;
            items.push(r.head_site.into_bound_py_any(py)?);
            match r.tests_executed {
                Some(v) => items.push(v.into_bound_py_any(py)?),
                None => items.push(py.None().into_bound(py)),
            }
            push_opt_str(&mut items, r.test_time, py)?;
            push_opt_str(&mut items, r.hbin, py)?;
            push_opt_str(&mut items, r.sbin, py)?;
            push_opt_str(&mut items, r.wafer_id, py)?;
            push_opt_str(&mut items, r.xy, py)?;
            push_opt_str(&mut items, r.dut_flag, py)?;
            dict.set_item(r.dut_index, PyList::new(py, items)?)?;
        }
        Ok(dict)
    }

    // ----- DUT/pin/wafer queries -----

    pub fn get_pin_name_rows(
        &mut self,
        py: Python<'_>,
        test_num: u32,
        test_name: &str,
        is_rtn: bool,
        fid: FileId,
    ) -> PyResult<Vec<PinNameRow>> {
        let inner = &mut self.inner;
        Ok(py.detach(move || inner.pin_name_rows(test_num, test_name, is_rtn, fid))?)
    }

    /// Wafer_Info rows as tuples in column order (ints / str / None).
    pub fn get_wafer_info_rows<'py>(
        &mut self,
        py: Python<'py>,
    ) -> PyResult<Vec<Bound<'py, PyTuple>>> {
        let inner = &mut self.inner;
        let rows = py.detach(move || inner.wafer_info_rows())?;
        rows.into_iter()
            .map(|r| {
                let mut items: Vec<Bound<'py, PyAny>> = Vec::with_capacity(14);
                items.push(r.fid.into_bound_py_any(py)?);
                push_opt_i64(&mut items, r.head_num, py)?;
                items.push(r.wafer_index.into_bound_py_any(py)?);
                push_opt_i64(&mut items, r.part_cnt, py)?;
                push_opt_i64(&mut items, r.rtst_cnt, py)?;
                push_opt_i64(&mut items, r.abrt_cnt, py)?;
                push_opt_i64(&mut items, r.good_cnt, py)?;
                push_opt_i64(&mut items, r.func_cnt, py)?;
                push_opt_str(&mut items, r.wafer_id, py)?;
                push_opt_str(&mut items, r.fabwf_id, py)?;
                push_opt_str(&mut items, r.frame_id, py)?;
                push_opt_str(&mut items, r.mask_id, py)?;
                push_opt_str(&mut items, r.usr_desc, py)?;
                push_opt_str(&mut items, r.exc_desc, py)?;
                PyTuple::new(py, items)
            })
            .collect()
    }

    pub fn get_wafer_ext_rows(
        &mut self,
        py: Python<'_>,
        fid: FileId,
    ) -> PyResult<Vec<(String, Option<String>)>> {
        let inner = &mut self.inner;
        Ok(py.detach(move || inner.wafer_ext_rows(fid))?)
    }

    pub fn get_wafer_coord_rows(
        &mut self,
        py: Python<'_>,
        wafer_index: u64,
        sites: Vec<i32>,
        fid: FileId,
    ) -> PyResult<Vec<(i64, i64, i64)>> {
        let inner = &mut self.inner;
        Ok(py.detach(move || inner.wafer_coord_rows(wafer_index, &sites, fid))?)
    }

    pub fn get_stacked_wafer_rows(
        &mut self,
        py: Python<'_>,
        sites: Vec<i32>,
    ) -> PyResult<Vec<(i64, i64, i64, i64)>> {
        let inner = &mut self.inner;
        Ok(py.detach(move || inner.stacked_wafer_rows(&sites))?)
    }

    pub fn get_datalog_rows(&mut self, py: Python<'_>) -> PyResult<Vec<(String, String, String)>> {
        let inner = &mut self.inner;
        Ok(py.detach(move || inner.datalog_rows())?)
    }
}

fn push_opt_i64<'py>(
    items: &mut Vec<Bound<'py, PyAny>>,
    value: Option<i64>,
    py: Python<'py>,
) -> PyResult<()> {
    match value {
        Some(v) => items.push(v.into_bound_py_any(py)?),
        None => items.push(py.None().into_bound(py)),
    }
    Ok(())
}

fn push_opt_str<'py>(
    items: &mut Vec<Bound<'py, PyAny>>,
    value: Option<String>,
    py: Python<'py>,
) -> PyResult<()> {
    match value {
        Some(s) => items.push(s.into_bound_py_any(py)?),
        None => items.push(py.None().into_bound(py)),
    }
    Ok(())
}

/// Test data for different record types:
/// - PTR: `dataList` is the flat f32 array, one entry per DUT.
/// - MPR: `dataList` / `stateList` are 2-D f32. When there are no returned
///   DUTs or no result columns, an empty 1-D f32 array is returned.
/// - FTR: only `flagList`.
///
/// `flagList` is always emitted as int16 (the DUT-index path needs the -1
/// sentinel; the head/site path simply uses the same dtype).
fn fill_test_data_dict<'py>(
    dict: &Bound<'py, PyDict>,
    fetched: FetchedTestData,
    py: Python<'py>,
) -> PyResult<()> {
    let FetchedTestData {
        dut_list,
        data,
        flags,
    } = fetched;
    dict.set_item("dutList", dut_list.into_pyarray(py))?;
    match data {
        TestData::Ptr(values) => {
            dict.set_item("dataList", values.into_pyarray(py))?;
        }
        TestData::Mpr { values, states } => {
            if values.nrows() == 0 || values.ncols() == 0 {
                // Use empty 1d f32 for MPR result
                // without any DUTs or result columns.
                dict.set_item("dataList", Array1::<f32>::zeros(0).into_pyarray(py))?;
                dict.set_item("stateList", Array1::<f32>::zeros(0).into_pyarray(py))?;
            } else {
                dict.set_item("dataList", values.into_pyarray(py))?;
                dict.set_item("stateList", states.into_pyarray(py))?;
            }
        }
        // FTR: no dataList / stateList
        TestData::FlagsOnly => {}
    }
    dict.set_item("flagList", flags.into_pyarray(py))?;
    Ok(())
}
