//
// session.rs
//
// Session database validation and saving.
//
// Author: noonchen - chennoon233@foxmail.com
// Created Date: Tue Sep 01 2026
// -----
// Last Modified: Tue Sep 01 2026
// Modified By: noonchen
// -----
// Copyright (c) 2026 noonchen
//

use crate::database::schema::REQUIRED_TABLES;
use crate::generic::error::StdfHelperError;
use rusqlite::{Connection, OpenFlags};
use std::collections::HashSet;
use std::time::Duration;

pub struct SessionCheck {
    pub valid: bool,
    /// Empty when `valid`.
    pub message: String,
}

/// Validate a session database before loading it.
///
/// Checks, in order: the file opens read-only, `quick_check` reports the
/// database as intact, and the table set matches the expected schema (missing
/// or unexpected user tables are both rejected; SQLite's `sqlite_*` internals
/// are ignored).
pub fn validate_session(path: &str) -> Result<SessionCheck, StdfHelperError> {
    let invalid = |message: String| {
        Ok(SessionCheck {
            valid: false,
            message,
        })
    };
    let conn = match Connection::open_with_flags(path, OpenFlags::SQLITE_OPEN_READ_ONLY) {
        Ok(conn) => conn,
        Err(e) => return invalid(format!("cannot open database: {e}")),
    };

    let integrity: String = conn.query_row("PRAGMA quick_check", [], |row| row.get(0))?;
    if !integrity.eq_ignore_ascii_case("ok") {
        return invalid(format!("database is corrupted: {integrity}"));
    }

    let current: HashSet<String> = {
        let mut stmt = conn.prepare(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'",
        )?;
        let rows = stmt.query_map([], |row| row.get::<_, String>(0))?;
        rows.collect::<Result<HashSet<String>, _>>()?
    };
    let missing: Vec<&str> = REQUIRED_TABLES
        .iter()
        .copied()
        .filter(|table| !current.contains(*table))
        .collect();
    if !missing.is_empty() {
        return invalid(format!("missing tables: {}", missing.join(", ")));
    }
    let known: HashSet<&str> = REQUIRED_TABLES.iter().copied().collect();
    let mut extra: Vec<&str> = current
        .iter()
        .map(String::as_str)
        .filter(|table| !known.contains(table))
        .collect();
    extra.sort_unstable();
    if !extra.is_empty() {
        return invalid(format!("unexpected tables: {}", extra.join(", ")));
    }

    Ok(SessionCheck {
        valid: true,
        message: String::new(),
    })
}

/// Copy `src` into `dst` with SQLite's online backup API.
///
/// The result is a consistent, self-contained single file: the backup reads
/// through a connection, so content still sitting in the WAL is included, and
/// a concurrent writer cannot produce a torn copy. The destination is left in
/// rollback-journal mode so no `-wal`/`-shm` sidecars are created next to it.
pub fn save_session(src: &str, dst: &str) -> Result<(), StdfHelperError> {
    let src_conn = Connection::open_with_flags(src, OpenFlags::SQLITE_OPEN_READ_ONLY)?;
    let _ = src_conn.busy_timeout(Duration::from_secs(10));
    let mut dst_conn = Connection::open(dst)?;
    let _ = dst_conn.busy_timeout(Duration::from_secs(10));

    {
        let backup = rusqlite::backup::Backup::new(&src_conn, &mut dst_conn)?;
        backup.run_to_completion(1024, Duration::from_millis(20), None)?;
    }
    // the destination is a fresh file; make sure an existing WAL from a
    // previous save is folded in and removed
    let _ =
        dst_conn.execute_batch("PRAGMA wal_checkpoint(TRUNCATE); PRAGMA journal_mode = DELETE;");
    Ok(())
}
