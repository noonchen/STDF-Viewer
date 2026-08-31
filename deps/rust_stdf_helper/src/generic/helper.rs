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
