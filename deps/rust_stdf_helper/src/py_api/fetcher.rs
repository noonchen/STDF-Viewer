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

use crate::database::fetcher::{DataFetcher, FetchedTestData, FileId};
use crate::stdf::record_tracker::TestSubCode;
use numpy::ndarray::Array1;
use numpy::IntoPyArray;
use numpy::PyArray1;
use pyo3::prelude::*;
use pyo3::types::{PyAny, PyDict, PyTuple};
use pyo3::IntoPyObjectExt;

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
        // (plan §3.3/§7). Defaults to 128 MiB when not given.
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
        let info = py.detach(|| self.inner.get_test_info((test_num, test_name), file_id))?;
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
            dict.set_item("Unit", info.unit)?;
            dict.set_item("OPT_FLAG", info.opt_flag)?;
            dict.set_item("FailCount", info.fail_count)?;
            dict.set_item("RTN_ICNT", info.rtn_icnt)?;
            dict.set_item("RSLT_PGM_CNT", info.rslt_pgm_cnt)?;
            dict.set_item("LSpec", info.lspec.map(f64::from).unwrap_or(f64::NAN))?;
            dict.set_item("HSpec", info.hspec.map(f64::from).unwrap_or(f64::NAN))?;
            dict.set_item("VECT_NAM", info.vect_nam)?;
            dict.set_item("SEQ_NAME", info.seq_name)?;
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
        // All heavy lifting (first-time SQLite scan + hex decode, row gather)
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
        duts: Vec<i64>,
        file_id: FileId,
    ) -> PyResult<Option<Bound<'py, PyDict>>> {
        let duts_u64: Vec<u64> = duts.iter().map(|&d| d as u64).collect();
        let fetched = py.detach(|| {
            self.inner
                .get_test_data_from_dut_index((test_num, test_name), &duts_u64, file_id)
        })?;
        let dict = PyDict::new(py);
        if let Some(data) = fetched {
            fill_test_data_dict(&dict, data, py)?;
        }
        Ok(Some(dict))
    }

    // ----- Metadata / summary queries (port of remaining DatabaseFetcher methods) -----
    pub fn get_wafer_count(&self) -> PyResult<Vec<i64>> {
        Ok(self.inner.wafer_count()?)
    }

    pub fn get_byte_order(&self) -> PyResult<Vec<bool>> {
        Ok(self.inner.byte_order()?)
    }

    pub fn get_test_items(&self) -> PyResult<Vec<String>> {
        Ok(self.inner.test_items()?)
    }

    /// Rows of `(TEST_NUM, TEST_NAME, SUB_CODE)` in DB order.
    pub fn get_test_record_type_rows(&self) -> PyResult<Vec<(i64, String, u8)>> {
        Ok(self.inner.test_record_type_rows()?)
    }

    pub fn get_wafer_list(&self) -> PyResult<Vec<String>> {
        Ok(self.inner.wafer_list()?)
    }

    /// Rows of `(TEST_NUM, TEST_NAME, per-file FailCount list)`.
    pub fn get_test_fail_cnt(&self) -> PyResult<Vec<(i64, String, Vec<Option<i64>>)>> {
        Ok(self.inner.test_fail_cnt_rows()?)
    }

    pub fn get_bin_info_rows(
        &self,
        is_hbin: bool,
    ) -> PyResult<Vec<(i64, Option<String>, Option<String>)>> {
        Ok(self.inner.bin_info_rows(is_hbin)?)
    }

    pub fn get_bin_stats_rows(
        &self,
        head: i64,
        site: i64,
        is_hbin: bool,
    ) -> PyResult<Vec<(i64, i64, i64)>> {
        Ok(self.inner.bin_stats_rows(head, site, is_hbin)?)
    }

    pub fn is_dut_info_column_empty(&self, column: &str) -> PyResult<bool> {
        Ok(self.inner.is_dut_info_column_empty(column)?)
    }

    /// Rows of `(Fid, Field, Value)` ordered by `Fid, Field, SubFid`.
    pub fn get_file_info_rows(&self) -> PyResult<Vec<(i64, String, Option<String>)>> {
        Ok(self.inner.file_info_rows()?)
    }

    // ----- DUT-level summary queries (port batch A) -----

    pub fn get_dut_count_dict<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyDict>> {
        let counts = self.inner.dut_count_dict()?;
        let dict = PyDict::new(py);
        dict.set_item("Total", counts.total)?;
        dict.set_item("Pass", counts.pass)?;
        dict.set_item("Failed", counts.failed)?;
        dict.set_item("Superseded", counts.superseded)?;
        dict.set_item("Unknown", counts.unknown)?;
        Ok(dict)
    }

    pub fn get_dut_count_on_conditions(
        &self,
        head: i64,
        site: i64,
        waferid: i64,
        fid: i64,
    ) -> PyResult<Vec<i64>> {
        Ok(self
            .inner
            .dut_count_on_conditions(head, site, waferid, fid)?)
    }

    /// `getDutIndexDictFromHeadSite()` — `{fid: [dut_index, ...]}` built in
    /// Rust so Python never rebuilds it from row tuples.
    pub fn get_dut_index_dict_by_head_site<'py>(
        &self,
        py: Python<'py>,
        heads: Vec<i32>,
        sites: Vec<i32>,
        file_ids: Vec<FileId>,
    ) -> PyResult<Bound<'py, PyDict>> {
        let dict = PyDict::new(py);
        for fid in file_ids {
            let duts_in_fid = self.inner.get_dut_index_by_head_site(&heads, &sites, fid)?;

            dict.set_item(fid, duts_in_fid.into_pyarray(py))?;
        }
        Ok(dict)
    }

    /// `selections`: list of (fid, isHBIN, [bin numbers]).
    pub fn get_dut_index_rows_by_bin(
        &self,
        selections: Vec<(i64, bool, Vec<i64>)>,
    ) -> PyResult<Vec<(i64, i64)>> {
        Ok(self.inner.dut_index_rows_by_bin(&selections)?)
    }

    /// `selections`: list of (waferIndex, fid, (x, y)); waferIndex == -1
    /// means the stacked map (fid ignored).
    pub fn get_dut_index_rows_by_xy(
        &self,
        selections: Vec<(i64, i64, (i64, i64))>,
    ) -> PyResult<Vec<(i64, i64)>> {
        Ok(self.inner.dut_index_rows_by_xy(&selections)?)
    }

    pub fn get_wafer_bounds(
        &self,
        wafer_index: i64,
        fid: i64,
    ) -> PyResult<(Option<i64>, Option<i64>, Option<i64>, Option<i64>)> {
        Ok(self.inner.wafer_bounds(wafer_index, fid)?)
    }

    /// `getDynamicLimits()` — per-side arrays for the requested DUTs of one
    /// file: dynamic override where a row exists, else the static default.
    /// A side is empty when no requested DUT has a dynamic value.
    pub fn get_dynamic_limits<'py>(
        &mut self,
        py: Python<'py>,
        file_id: FileId,
        test_num: u32,
        test_name: &str,
        duts: Vec<i64>,
    ) -> PyResult<(Bound<'py, PyArray1<f32>>, Bound<'py, PyArray1<f32>>)> {
        let duts = unsafe { std::slice::from_raw_parts(duts.as_ptr() as *const u64, duts.len()) };
        let limits = py.detach(
            || -> Result<(Array1<f32>, Array1<f32>), crate::generic::error::StdfHelperError> {
                match self.inner.get_test_info((test_num, test_name), file_id)? {
                    Some(info) => self.inner.get_dynamic_limits(&info, file_id, duts),
                    None => Ok((Array1::zeros(0), Array1::zeros(0))),
                }
            },
        )?;
        Ok((limits.0.into_pyarray(py), limits.1.into_pyarray(py)))
    }

    /// `getPartialDUTInfoOnCondition()` — (DUTIndex, PartID,
    /// "Head h - Site s", PartText, "State - 0xFL").
    pub fn get_partial_dut_info(
        &mut self,
        heads: Vec<i32>,
        sites: Vec<i32>,
        file_id: FileId,
    ) -> PyResult<Vec<(i64, Option<String>, String, Option<String>, Option<String>)>> {
        Ok(self.inner.get_partial_dut_info(&heads, &sites, file_id)?)
    }

    /// DUT summary rows as python tuples `(DUTIndex, File ID, Part ID, ...)`
    /// with the same cell typing (int / str / None) as the Python reference.
    pub fn get_full_dut_summary_rows<'py>(
        &self,
        py: Python<'py>,
        fid: FileId,
    ) -> PyResult<Vec<Bound<'py, PyTuple>>> {
        let rows = self.inner.full_dut_summary_rows(fid)?;
        rows.into_iter()
            .map(|r| {
                let mut items: Vec<Bound<'py, PyAny>> = Vec::with_capacity(12);
                items.push(r.dut_index.into_bound_py_any(py)?);
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
                PyTuple::new(py, items)
            })
            .collect()
    }

    // ----- DUT/pin/wafer queries (port batch B) -----

    pub fn get_pin_name_rows(
        &self,
        test_num: u32,
        test_name: &str,
        is_rtn: bool,
        fid: FileId,
    ) -> PyResult<Vec<(i64, String, String, i64, i64, String)>> {
        Ok(self.inner.pin_name_rows(test_num, test_name, is_rtn, fid)?)
    }

    /// Wafer_Info rows as tuples in column order (ints / str / None).
    pub fn get_wafer_info_rows<'py>(&self, py: Python<'py>) -> PyResult<Vec<Bound<'py, PyTuple>>> {
        let rows = self.inner.wafer_info_rows()?;
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

    pub fn get_wafer_ext_rows(&self, fid: FileId) -> PyResult<Vec<(String, Option<String>)>> {
        Ok(self.inner.wafer_ext_rows(fid)?)
    }

    pub fn get_wafer_coord_rows(
        &self,
        wafer_index: u64,
        sites: Vec<i32>,
        fid: FileId,
    ) -> PyResult<Vec<(i64, i64, i64)>> {
        Ok(self.inner.wafer_coord_rows(wafer_index, &sites, fid)?)
    }

    pub fn get_stacked_wafer_rows(&self, sites: Vec<i32>) -> PyResult<Vec<(i64, i64, i64, i64)>> {
        Ok(self.inner.stacked_wafer_rows(&sites)?)
    }

    pub fn get_datalog_rows(&self) -> PyResult<Vec<(String, String, String)>> {
        Ok(self.inner.datalog_rows()?)
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

/// Shape the fetched arrays exactly like the Python reference fetcher:
///
/// - PTR (`TestSubCode::Ptr`): `dataList` is a flat 1-D f32 array.
/// - MPR (`TestSubCode::Mpr`): `dataList` / `stateList` are 2-D, transposed to
///   (rslt_cnt × dut) like `np.array(rows).T`. When there are no result
///   columns or no selected rows, Python produces plain empty 1-D arrays
///   (`np.array([])`, float64), so we mirror that instead of `(0, k)` shapes.
/// - FTR (everything else): only `flagList`.
///
/// `flagList` is always emitted as int16 (the DUT-index path needs the -1
/// sentinel; the head/site path's values are never negative and simply use the
/// same dtype for both paths).
fn fill_test_data_dict<'py>(
    dict: &Bound<'py, PyDict>,
    fetched: FetchedTestData,
    py: Python<'py>,
) -> PyResult<()> {
    let FetchedTestData {
        sub_code,
        dut_list,
        data,
        flags,
        states,
    } = fetched;
    dict.set_item("dutList", dut_list.into_pyarray(py))?;
    match sub_code {
        TestSubCode::Ptr => {
            let flat = numpy_1d_from_2d_single_col(&data);
            dict.set_item("dataList", flat.into_pyarray(py))?;
        }
        TestSubCode::Mpr => {
            if data.nrows() == 0 || data.ncols() == 0 {
                // Match Python's `np.array([])` for an MPR result with no rows /
                // no result columns: empty 1-D float64 arrays.
                let empty = Array1::<f64>::from_elem(0, f64::NAN);
                dict.set_item("dataList", empty.into_pyarray(py))?;
                let empty_state = Array1::<f64>::from_elem(0, f64::NAN);
                dict.set_item("stateList", empty_state.into_pyarray(py))?;
            } else {
                dict.set_item("dataList", data.t().to_owned().into_pyarray(py))?;
                if let Some(states) = states {
                    dict.set_item("stateList", states.t().to_owned().into_pyarray(py))?;
                }
            }
        }
        // FTR and any unknown/legacy code: no dataList / stateList keys.
        TestSubCode::Ftr | TestSubCode::Other => {}
    }
    dict.set_item("flagList", flags.into_pyarray(py))?;
    Ok(())
}

fn numpy_1d_from_2d_single_col(data: &numpy::ndarray::Array2<f32>) -> numpy::ndarray::Array1<f32> {
    data.column(0).to_owned()
}
