"""Kazeyami HRM data layer — SQLite."""
from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
import time
from pathlib import Path

DB_PATH = Path(os.environ.get("KAZEYAMI_DB", Path(__file__).resolve().parent / "kazeyami.db"))

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS departments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    code TEXT UNIQUE NOT NULL,
    head_id INTEGER,
    description TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS designations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    department_id INTEGER REFERENCES departments(id),
    level TEXT DEFAULT 'IC',
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    emp_code TEXT UNIQUE NOT NULL,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    phone TEXT,
    dob TEXT,
    gender TEXT,
    department_id INTEGER REFERENCES departments(id),
    designation_id INTEGER REFERENCES designations(id),
    manager_id INTEGER REFERENCES employees(id),
    shift_id INTEGER,
    join_date TEXT,
    status TEXT DEFAULT 'active',
    employment_type TEXT DEFAULT 'full_time',
    work_location TEXT DEFAULT 'Singapore HQ',
    address TEXT,
    city TEXT,
    country TEXT DEFAULT 'Singapore',
    emergency_name TEXT,
    emergency_phone TEXT,
    emergency_relation TEXT,
    bank_name TEXT,
    bank_account TEXT,
    bank_code TEXT,
    basic_salary REAL DEFAULT 0,
    hra REAL DEFAULT 0,
    allowance REAL DEFAULT 0,
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('admin','hr','manager','employee')),
    employee_id INTEGER REFERENCES employees(id),
    is_active INTEGER DEFAULT 1,
    last_login TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS shifts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    break_minutes INTEGER DEFAULT 60,
    grace_minutes INTEGER DEFAULT 10,
    is_default INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS holidays (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    date TEXT NOT NULL,
    type TEXT DEFAULT 'public',
    description TEXT
);

CREATE TABLE IF NOT EXISTS attendance_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL REFERENCES employees(id),
    work_date TEXT NOT NULL,
    clock_in TEXT,
    clock_out TEXT,
    shift_id INTEGER REFERENCES shifts(id),
    status TEXT DEFAULT 'present',
    late_minutes INTEGER DEFAULT 0,
    early_leave_minutes INTEGER DEFAULT 0,
    overtime_minutes INTEGER DEFAULT 0,
    work_minutes INTEGER DEFAULT 0,
    notes TEXT,
    ip_address TEXT,
    latitude REAL,
    longitude REAL,
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(employee_id, work_date)
);

CREATE TABLE IF NOT EXISTS leave_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    code TEXT UNIQUE NOT NULL,
    days_per_year REAL NOT NULL DEFAULT 0,
    paid INTEGER DEFAULT 1,
    color TEXT DEFAULT '#C9A227',
    requires_approval INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS leave_balances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL REFERENCES employees(id),
    leave_type_id INTEGER NOT NULL REFERENCES leave_types(id),
    year INTEGER NOT NULL,
    allocated REAL DEFAULT 0,
    used REAL DEFAULT 0,
    pending REAL DEFAULT 0,
    UNIQUE(employee_id, leave_type_id, year)
);

CREATE TABLE IF NOT EXISTS leave_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL REFERENCES employees(id),
    leave_type_id INTEGER NOT NULL REFERENCES leave_types(id),
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    days REAL NOT NULL,
    reason TEXT,
    status TEXT DEFAULT 'pending',
    approver_id INTEGER REFERENCES employees(id),
    decided_at TEXT,
    comments TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS payslips (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL REFERENCES employees(id),
    period_year INTEGER NOT NULL,
    period_month INTEGER NOT NULL,
    basic REAL DEFAULT 0,
    hra REAL DEFAULT 0,
    allowance REAL DEFAULT 0,
    overtime_pay REAL DEFAULT 0,
    unpaid_deduction REAL DEFAULT 0,
    tax REAL DEFAULT 0,
    other_deduction REAL DEFAULT 0,
    gross REAL DEFAULT 0,
    net REAL DEFAULT 0,
    status TEXT DEFAULT 'generated',
    generated_at TEXT DEFAULT (datetime('now')),
    UNIQUE(employee_id, period_year, period_month)
);

CREATE TABLE IF NOT EXISTS announcements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    author_id INTEGER REFERENCES users(id),
    audience TEXT DEFAULT 'all',
    pinned INTEGER DEFAULT 0,
    published_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    title TEXT NOT NULL,
    body TEXT,
    link TEXT,
    is_read INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action TEXT NOT NULL,
    entity TEXT,
    entity_id TEXT,
    details TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
"""


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), timeout=60)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    # WAL is more resilient on overlay / constrained filesystems
    try:
        conn.execute("PRAGMA journal_mode = WAL")
    except Exception:
        conn.execute("PRAGMA journal_mode = DELETE")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA busy_timeout = 60000")
    return conn


@contextmanager
def get_db():
    conn = connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    global DB_PATH
    last_err = None
    for attempt in range(5):
        try:
            with get_db() as conn:
                conn.executescript(SCHEMA)
            return
        except Exception as exc:
            last_err = exc
            msg = str(exc).lower()
            if "disk i/o" in msg or "locked" in msg or "busy" in msg:
                time.sleep(0.1 * (attempt + 1))
                continue
            raise
    fallback = Path("/tmp/kazeyami.db")
    if Path(DB_PATH) != fallback:
        DB_PATH = fallback
        with get_db() as conn:
            conn.executescript(SCHEMA)
        return
    raise last_err


def query(sql: str, args=(), one=False):
    with get_db() as conn:
        cur = conn.execute(sql, args)
        rows = cur.fetchall()
    if one:
        return rows[0] if rows else None
    return rows


def execute(sql: str, args=()):
    last_err = None
    for attempt in range(10):
        try:
            with get_db() as conn:
                cur = conn.execute(sql, args)
                return cur.lastrowid
        except Exception as exc:
            last_err = exc
            msg = str(exc).lower()
            if "disk i/o" in msg or "locked" in msg or "busy" in msg or "unable to open" in msg:
                time.sleep(0.05 * (attempt + 1) + 0.05)
                continue
            raise
    raise last_err


def executemany(sql: str, seq):
    last_err = None
    for attempt in range(8):
        try:
            with get_db() as conn:
                conn.executemany(sql, seq)
                return
        except Exception as exc:
            last_err = exc
            msg = str(exc).lower()
            if "disk i/o" in msg or "locked" in msg or "busy" in msg:
                time.sleep(0.08 * (attempt + 1))
                continue
            raise
    raise last_err


def row_to_dict(row):
    if row is None:
        return None
    return dict(row)


def rows_to_dicts(rows):
    return [dict(r) for r in rows]
