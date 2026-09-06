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

use crate::database::fetcher::{DataFetcher, FetchedTestData, TestSubCode};
use numpy::ndarray::Array1;
use numpy::IntoPyArray;
use pyo3::prelude::*;
use pyo3::types::PyDict;

#[pyclass(name = "DataFetcher", module = "rust_stdf_helper", unsendable)]
pub struct PyDataFetcher {
    inner: DataFetcher,
}

#[pymethods]
impl PyDataFetcher {
    #[new]
    #[pyo3(signature = (path, cache_budget_mb=None))]
    pub fn new(path: &str, cache_budget_mb: Option<usize>) -> PyResult<Self> {
        // cache_budget_mb: Tier-2 test-data LRU byte budget in MiB
        // (plan §3.3/§7). Defaults to 128 MiB when not given.
        let inner = match cache_budget_mb {
            Some(mb) => DataFetcher::open_with_budget(path, mb.saturating_mul(1024 * 1024))?,
            None => DataFetcher::open(path)?,
        };
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
        file_id: usize,
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
        file_id: usize,
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
        file_id: usize,
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
