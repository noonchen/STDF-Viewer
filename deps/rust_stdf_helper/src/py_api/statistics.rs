//
// statistics.rs
//
// Distribution functions for statistical analysis.
//
// Author: noonchen - chennoon233@foxmail.com
// Created Date: Tue Sep 01 2026
// -----
// Last Modified: Tue Sep 01 2026
// Modified By: noonchen
// -----
// Copyright (c) 2022 noonchen
//

use crate::generic::statistics_core;
use numpy::ndarray::{Array1, Zip};
use numpy::{IntoPyArray, PyArray1, PyReadonlyArray1};
use pyo3::prelude::*;

/// Cumulative Distribution Function, used in PP plot.
#[pyfunction]
#[pyo3(name = "norm_cdf")]
pub fn norm_cdf<'py>(
    py: Python<'py>,
    data: PyReadonlyArray1<f64>,
    mean: f64,
    stddev: f64,
) -> PyResult<Bound<'py, PyArray1<f64>>> {
    let data = data.as_array();
    let mut p = Array1::from_elem(data.len(), f64::NAN);

    if stddev != 0.0 && !stddev.is_nan() {
        Zip::from(&data).and(&mut p).par_for_each(|d, prob| {
            let d_norm = (*d - mean) / stddev;
            *prob = statistics_core::ndtr(d_norm)
        });
    }
    Ok(p.into_pyarray(py))
}

/// Empirical CDF, used in PP plot.
#[pyfunction]
#[pyo3(name = "empirical_cdf")]
pub fn empirical_cdf<'py>(
    py: Python<'py>,
    data: PyReadonlyArray1<f64>,
) -> PyResult<Bound<'py, PyArray1<f64>>> {
    // equivalent to scipy.stats.rankdata() in 'max' mode
    let data = data.as_array();
    let dsz = data.len();
    let mut p = Array1::from_elem(dsz, 0.0f64);
    if dsz == 0 {
        return Ok(p.into_pyarray(py));
    }

    let mut idx_sort: Vec<usize> = (0usize..dsz).collect();
    idx_sort.sort_by(|&i, &j| data[i].total_cmp(&data[j]));

    // for same values in data, returns same rank_max
    // need to count repeated number
    let mut i = 0;
    while i < dsz {
        let mut j = i + 1;
        while j < dsz && data[idx_sort[i]] == data[idx_sort[j]] {
            // found duplicates
            j += 1;
        }
        // position of duplicates: [i, j-1]
        // rank begins at 1, and we are in max mode, so:
        let rank = (j - 1) as f64 + 1.0f64;
        for &orig_index in &idx_sort[i..j] {
            p[orig_index] = rank / (dsz as f64);
        }
        i = j;
    }

    Ok(p.into_pyarray(py))
}

/// Inverse of Cumulative Distribution Function, used in QQ plot
#[pyfunction]
#[pyo3(name = "norm_ppf")]
pub fn norm_ppf<'py>(
    py: Python<'py>,
    p: PyReadonlyArray1<f64>,
    mean: f64,
    stddev: f64,
) -> PyResult<Bound<'py, PyArray1<f64>>> {
    let p = p.as_array();
    let init = if stddev == 0.0 { mean } else { f64::NAN };
    let mut q = Array1::from_elem(p.len(), init);

    if stddev != 0.0 && !stddev.is_nan() {
        Zip::from(&p).and(&mut q).par_for_each(|prob, quantile| {
            let q_norm = statistics_core::ndtri(*prob);
            *quantile = q_norm * stddev + mean
        });
    }
    Ok(q.into_pyarray(py))
}
