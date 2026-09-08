"""Shared helpers: time, auth, attendance math, payroll, audit."""
from __future__ import annotations

import calendar
import functools
from datetime import date, datetime, timedelta
from typing import Optional

from flask import redirect, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from models import execute, query


def today() -> date:
    return date.today()


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def hash_password(password: str) -> str:
    return generate_password_hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    return check_password_hash(password_hash, password)


def full_name(emp) -> str:
    if not emp:
        return ""
    return f"{emp['first_name']} {emp['last_name']}".strip()


def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    return query("SELECT * FROM users WHERE id=?", (uid,), one=True)


def login_required(f):
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login", next=request.path))
        return f(*args, **kwargs)
    return wrapped


def roles_required(*roles):
    def decorator(f):
        @functools.wraps(f)
        def wrapped(*args, **kwargs):
            u = current_user()
            if not u or u["role"] not in roles:
                return redirect(url_for("dashboard"))
            return f(*args, **kwargs)
        return wrapped
    return decorator


def can_manage(user, emp_id=None):
    if not user:
        return False
    if user["role"] in ("admin", "hr"):
        return True
    if user["role"] == "manager" and emp_id:
        # simple: manager can manage direct reports
        row = query("SELECT manager_id FROM employees WHERE id=?", (emp_id,), one=True)
        return row and row["manager_id"] == user["employee_id"]
    return False


def next_emp_code() -> str:
    row = query("SELECT emp_code FROM employees ORDER BY id DESC LIMIT 1", one=True)
    if not row:
        return "KZI-001"
    try:
        n = int(row["emp_code"].split("-")[-1]) + 1
    except Exception:
        n = 1
    return f"KZI-{n:03d}"


def parse_time(t: str):
    if not t:
        return None
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(t, fmt).time()
        except ValueError:
            continue
    return None


def minutes_between(start, end):
    if not start or not end:
        return 0
    s = datetime.combine(date.today(), start)
    e = datetime.combine(date.today(), end)
    if e < s:
        e += timedelta(days=1)
    return int((e - s).total_seconds() // 60)


def compute_attendance(clock_in, clock_out, shift_start="09:00", shift_end="18:00", grace=10, break_min=60):
    """Return status, late_minutes, work_minutes, overtime_minutes."""
    if not clock_in:
        return "absent", 0, 0, 0
    cin = parse_time(clock_in)
    cout = parse_time(clock_out) if clock_out else None
    ss = parse_time(shift_start)
    se = parse_time(shift_end)
    if not cin or not ss:
        return "present", 0, 0, 0
    late = 0
    status = "present"
    # late calculation
    expected = datetime.combine(date.today(), ss) + timedelta(minutes=grace)
    actual = datetime.combine(date.today(), cin)
    if actual > expected:
        late = int((actual - datetime.combine(date.today(), ss)).total_seconds() // 60)
        status = "late"
    work = 0
    ot = 0
    if cout and se:
        work = minutes_between(cin, cout) - break_min
        if work < 0:
            work = 0
        expected_work = minutes_between(ss, se) - break_min
        if work > expected_work:
            ot = work - expected_work
    return status, late, work, ot


def is_weekend(d: date, weekends="Sat,Sun") -> bool:
    names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    return names[d.weekday()] in [w.strip() for w in weekends.split(",")]


def is_holiday(d: date) -> bool:
    row = query("SELECT id FROM holidays WHERE date=?", (d.isoformat(),), one=True)
    return bool(row)


def working_days_in_month(year, month, weekends="Sat,Sun"):
    days = calendar.monthrange(year, month)[1]
    count = 0
    for day in range(1, days + 1):
        d = date(year, month, day)
        if not is_weekend(d, weekends) and not is_holiday(d):
            count += 1
    return count


def generate_payslip_data(emp, year, month, settings=None):
    basic = emp.get("basic_salary") or 0
    hra = emp.get("hra") or 0
    allow = emp.get("allowance") or 0
    # simple OT from attendance
    logs = query(
        "SELECT overtime_minutes FROM attendance_logs WHERE employee_id=? AND strftime('%Y', work_date)=? AND strftime('%m', work_date)=?",
        (emp["id"], str(year), f"{month:02d}"),
    )
    ot_min = sum(r["overtime_minutes"] or 0 for r in logs)
    ot_rate = 1.5
    if settings:
        try:
            ot_rate = float(settings.get("overtime_rate", 1.5))
        except Exception:
            pass
    hourly = basic / 22 / 8 if basic else 0
    ot_pay = round(ot_min / 60 * hourly * ot_rate, 2)
    # unpaid leave deduction
    unpaid = query(
        """SELECT COALESCE(SUM(days),0) AS d FROM leave_requests
           WHERE employee_id=? AND status='approved' AND leave_type_id IN
           (SELECT id FROM leave_types WHERE paid=0)
           AND strftime('%Y', start_date)=? AND strftime('%m', start_date)=?""",
        (emp["id"], str(year), f"{month:02d}"),
        one=True,
    )
    unpaid_days = unpaid["d"] if unpaid else 0
    daily = basic / 22 if basic else 0
    unpaid_ded = round(unpaid_days * daily, 2)
    tax = round((basic + hra + allow) * 0.05, 2)
    gross = basic + hra + allow + ot_pay
    net = gross - tax - unpaid_ded
    return {
        "basic": basic,
        "hra": hra,
        "allowance": allow,
        "overtime_pay": ot_pay,
        "unpaid_deduction": unpaid_ded,
        "tax": tax,
        "other_deduction": 0,
        "gross": gross,
        "net": net,
    }


def audit(user_id, action, entity, entity_id=None, details=None):
    execute(
        "INSERT INTO audit_log(user_id, action, entity, entity_id, details) VALUES (?,?,?,?,?)",
        (user_id, action, entity, str(entity_id) if entity_id is not None else None, details),
    )
