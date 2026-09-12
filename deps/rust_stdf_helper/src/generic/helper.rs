//
// helper.rs
//
// Uncategorised helper functions
//
// Author: noonchen - chennoon233@foxmail.com
// Created Date: Tue Sep 01 2026
// -----
// Last Modified: Tue Sep 01 2026
// Modified By: noonchen
// -----
// Copyright (c) 2022 noonchen
//

use crate::generic::error::StdfHelperError;
use chrono::{DateTime, Local};
use std::io::{Read, Seek, SeekFrom};
use std::{fs, io};
use zip::ZipArchive;

#[inline(always)]
pub fn u32_to_localtime(timestamp: u32) -> String {
    let utc_time = DateTime::from_timestamp(timestamp as i64, 0).unwrap();
    // convert UTC datetime to Local datetime
    let local_time: DateTime<Local> = DateTime::from(utc_time);

    format!(
        "{} (UTC{})",
        local_time.format("%Y-%m-%d %H:%M:%S"),
        local_time.format("%:z")
    )
}

#[inline(always)]
pub fn get_file_size(file_path: &str) -> io::Result<u64> {
    let mut fp = fs::File::open(file_path)?;
    if file_path.ends_with(".gz") {
        // gz file, read last 4 bytes as uncompressed data size
        // although it's inaccurate for > 4GB file, are there
        // anyone really going to open that large file using
        // my app? don't think so~
        fp.seek(SeekFrom::End(-4))?;
        let mut buffer = [0u8; 4];
        fp.read_exact(&mut buffer)?;
        Ok(u32::from_le_bytes(buffer).into())
    } else if file_path.ends_with(".zip") {
        let mut za = ZipArchive::new(fp)?;
        let fst_file = za.by_index(0)?;
        Ok(fst_file.size())
    } else {
        // binary file
        Ok(fp.metadata()?.len())
    }
}

#[inline]
/// takes sorted slice `a` and `b` and produce sorted intersect.
pub fn intersect_sorted(a: &[usize], b: &[usize]) -> Vec<usize> {
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

/// Merge a sorted unique `b` into a sorted unique `a`; the result stays sorted
/// and duplicate-free.
pub fn merge_sorted_unique(a: &mut Vec<usize>, b: &[usize]) {
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

/// Serialize integers as a JSON array, so a variable-length selection can be
/// bound as one SQL parameter and read back with `json_each(?)`.
pub fn json_int_array<I: IntoIterator<Item = i64>>(values: I) -> Result<String, StdfHelperError> {
    serde_json::to_string(&values.into_iter().collect::<Vec<i64>>())
        .map_err(|e| StdfHelperError { msg: e.to_string() })
}
