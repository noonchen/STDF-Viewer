//
// rust_functions.rs
// Author: noonchen - chennoon233@foxmail.com
// Created Date: October 29th 2022
// -----
// Last Modified: Sat Oct 29 2022
// Modified By: noonchen
// -----
// Copyright (c) 2022 noonchen
//

use crate::{database_context::DataBaseCtx, StdfHelperError};
use rust_stdf::*;

pub struct RecordTracker {
    //
}

impl RecordTracker {
    pub fn new() -> Self {
        RecordTracker {}
    }
}

#[inline(always)]
pub fn process_incoming_record(
    db_ctx: &DataBaseCtx,
    rec_tracker: &RecordTracker,
    rec_info: (usize, ByteOrder, u64, usize, StdfRecord),
) -> Result<(), StdfHelperError> {
    // unpack info
    let (file_id, order, offset, data_len, rec) = rec_info;
    match rec {
        StdfRecord::PTR(_) => (), //TODO
        _ => (),
    }
    Ok(())
}
