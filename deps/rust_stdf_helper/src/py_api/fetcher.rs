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

use crate::database::fetcher::DataFetcher;
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
    pub fn new(path: &str) -> PyResult<Self> {
        let inner = DataFetcher::open(path)?;
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
        let info = self.inner.get_test_info((test_num, test_name), file_id)?;
        let dict = PyDict::new(py);
        if let Some(info) = info {
            dict.set_item("Fid", file_id as i64)?;
            dict.set_item("TEST_ID", info.test_id)?;
            dict.set_item("TEST_NUM", info.test_num)?;
            dict.set_item("recHeader", info.rec_header)?;
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
        let fetched = self.inner.get_test_data_from_head_site(
            (test_num, test_name),
            &heads_u8,
            &sites_opt,
            file_id,
        )?;
        let dict = PyDict::new(py);
        match fetched {
            Some(data) => {
                dict.set_item("dutList", data.dut_list.into_pyarray(py))?;
                if data.rec_header == 10 {
                    let flat = numpy_1d_from_2d_single_col(&data.data);
                    dict.set_item("dataList", flat.into_pyarray(py))?;
                    let flags: numpy::ndarray::Array1<u8> = data.flags.mapv(|v| v as u8);
                    dict.set_item("flagList", flags.into_pyarray(py))?;
                } else if data.rec_header == 15 {
                    dict.set_item("dataList", data.data.t().to_owned().into_pyarray(py))?;
                    if let Some(states) = data.states {
                        dict.set_item("stateList", states.t().to_owned().into_pyarray(py))?;
                    }
                    let flags: numpy::ndarray::Array1<u8> = data.flags.mapv(|v| v as u8);
                    dict.set_item("flagList", flags.into_pyarray(py))?;
                } else {
                    let flags: numpy::ndarray::Array1<u8> = data.flags.mapv(|v| v as u8);
                    dict.set_item("flagList", flags.into_pyarray(py))?;
                }
            }
            None => {}
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
        let fetched =
            self.inner
                .get_test_data_from_dut_index((test_num, test_name), &duts_u64, file_id)?;
        let dict = PyDict::new(py);
        match fetched {
            Some(data) => {
                dict.set_item("dutList", data.dut_list.into_pyarray(py))?;
                if data.rec_header == 10 {
                    let flat = numpy_1d_from_2d_single_col(&data.data);
                    dict.set_item("dataList", flat.into_pyarray(py))?;
                    dict.set_item("flagList", data.flags.into_pyarray(py))?;
                } else if data.rec_header == 15 {
                    dict.set_item("dataList", data.data.t().to_owned().into_pyarray(py))?;
                    if let Some(states) = data.states {
                        dict.set_item("stateList", states.t().to_owned().into_pyarray(py))?;
                    }
                    dict.set_item("flagList", data.flags.into_pyarray(py))?;
                } else {
                    dict.set_item("flagList", data.flags.into_pyarray(py))?;
                }
            }
            None => {}
        }
        Ok(Some(dict))
    }
}

fn numpy_1d_from_2d_single_col(data: &numpy::ndarray::Array2<f32>) -> numpy::ndarray::Array1<f32> {
    data.column(0).to_owned()
}
