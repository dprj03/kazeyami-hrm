"""SQLite data layer for Kazeyami HRM."""
from __future__ import annotations

import os
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable, Optional

# Prefer env override, then /tmp for constrained filesystems, then local
_DB_CANDIDATES = [
    os.environ.get("KAZEYAMI_DB"),
    "/tmp/kazeyami.db",
    str(Path(__file__).resolve().parent / "kazeyami.db"),
]
DB_PATH = next((p for p in _DB_CANDIDATES if p), "kazeyami.db")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def get_db():
    conn = _connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def execute(sql: str, params: Iterable = ()) -> None:
    for attempt in range(5):
        try:
            with get_db() as conn:
                conn.execute(sql, tuple(params))
            return
        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower() and attempt < 4:
                time.sleep(0.15 * (attempt + 1))
                continue
            raise


def query(sql: str, params: Iterable = (), one: bool = False):
    for attempt in range(5):
        try:
            with get_db() as conn:
                cur = conn.execute(sql, tuple(params))
                if one:
                    row = cur.fetchone()
                    return dict(row) if row else None
                return [dict(r) for r in cur.fetchall()]
        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower() and attempt < 4:
                time.sleep(0.15 * (attempt + 1))
                continue
            raise


def row_to_dict(row) -> Optional[dict]:
    if row is None:
        return None
    return dict(row)


def rows_to_dicts(rows) -> list:
    return [dict(r) for r in rows]


def init_db() -> None:
    schema = """
    CREATE TABLE IF NOT EXISTS departments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE
    );

    CREATE TABLE IF NOT EXISTS shifts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        emp_code TEXT NOT NULL UNIQUE,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        phone TEXT,
        department_id INTEGER REFERENCES departments(id),
        shift_id INTEGER REFERENCES shifts(id),
        job_title TEXT,
        hire_date TEXT,
        basic_salary REAL DEFAULT 0,
        is_active INTEGER DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER REFERENCES employees(id),
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'employee',
        is_active INTEGER DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER NOT NULL REFERENCES employees(id),
        date TEXT NOT NULL,
        clock_in TEXT,
        clock_out TEXT,
        status TEXT DEFAULT 'absent',
        late_minutes INTEGER DEFAULT 0,
        ot_minutes INTEGER DEFAULT 0,
        notes TEXT,
        UNIQUE(employee_id, date)
    );

    CREATE TABLE IF NOT EXISTS leave_types (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        days_per_year REAL DEFAULT 0,
        color TEXT DEFAULT '#6b7280'
    );

    CREATE TABLE IF NOT EXISTS leave_balances (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER NOT NULL REFERENCES employees(id),
        leave_type_id INTEGER NOT NULL REFERENCES leave_types(id),
        balance REAL DEFAULT 0,
        UNIQUE(employee_id, leave_type_id)
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
        approved_by INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS payroll_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        period_start TEXT NOT NULL,
        period_end TEXT NOT NULL,
        status TEXT DEFAULT 'draft',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS payslips (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id INTEGER NOT NULL REFERENCES payroll_runs(id),
        employee_id INTEGER NOT NULL REFERENCES employees(id),
        basic REAL DEFAULT 0,
        allowances REAL DEFAULT 0,
        overtime REAL DEFAULT 0,
        deductions REAL DEFAULT 0,
        net REAL DEFAULT 0,
        details TEXT
    );

    CREATE TABLE IF NOT EXISTS announcements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        body TEXT NOT NULL,
        created_by INTEGER,
        is_active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id),
        message TEXT NOT NULL,
        is_read INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS holidays (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        date TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    );

    CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action TEXT NOT NULL,
        detail TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """
    with get_db() as conn:
        conn.executescript(schema)
