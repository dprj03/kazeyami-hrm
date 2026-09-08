"""Kazeyami Innovations — Human Resource & Attendance OS."""
from __future__ import annotations

from datetime import date, datetime
from types import SimpleNamespace

from flask import Flask, flash, redirect, render_template, request, session, url_for

from helpers import (
    audit,
    can_manage,
    current_user,
    full_name,
    hash_password,
    login_required,
    next_emp_code,
    roles_required,
    today,
    verify_password,
)
from models import execute, init_db, query, row_to_dict, rows_to_dicts
from seed import seed

from modules import attendance as attendance_mod
from modules import leave as leave_mod
from modules import payroll as payroll_mod
from modules import reports as reports_mod


def load_settings() -> SimpleNamespace:
    rows = query("SELECT key, value FROM settings")
    data = {r["key"]: r["value"] for r in rows}
    defaults = {
        "company_name": "Kazeyami Innovations Pte. Ltd.",
        "company_short": "Kazeyami",
        "tagline": "People systems for ambitious teams",
        "timezone": "Asia/Singapore",
        "currency": "SGD",
        "email": "people@kazeyami.com",
        "phone": "+65 6910 4400",
        "address": "12 Marina View, Singapore",
        "work_start": "09:00",
        "work_end": "18:00",
        "grace_minutes": "10",
        "overtime_after_minutes": "480",
        "overtime_rate": "1.5",
        "late_policy": "",
        "website": "https://kazeyami.com",
    }
    for k, v in defaults.items():
        data.setdefault(k, v)
    return SimpleNamespace(**data)


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "kazeyami-innovations-people-os-2026"
    app.config["TEMPLATES_AUTO_RELOAD"] = True

    init_db()
    seed()

    @app.context_processor
    def inject_globals():
        user = current_user() if session.get("user_id") else None
        unread = 0
        if user:
            row = query(
                "SELECT COUNT(*) AS n FROM notifications WHERE user_id = ? AND is_read = 0",
                (user["id"],),
                one=True,
            )
            unread = row["n"] if row else 0
        return {
            "company": load_settings(),
            "current": user,
            "unread": unread,
            "today": today().isoformat(),
        }

    @app.template_filter("when")
    def when_filter(value):
        if not value:
            return "—"
        text = str(value)
        if " " in text:
            return text.split(" ")[-1][:5]
        if len(text) >= 5 and ":" in text:
            return text[:5]
        return text

    @app.template_filter("money")
    def money_filter(value):
        try:
            return f"{float(value):,.2f}"
        except (TypeError, ValueError):
            return "0.00"

    # ------------------------------------------------------------------ auth
    @app.route("/login", methods=["GET", "POST"])
    def login():
        if session.get("user_id"):
            return redirect(url_for("dashboard"))
        error = None
        if request.method == "POST":
            email = (request.form.get("email") or "").strip().lower()
            password = request.form.get("password") or ""
            row = query(
                "SELECT * FROM users WHERE email = ? AND is_active = 1",
                (email,),
                one=True,
            )
            if row and verify_password(password, row["password_hash"]):
                session.clear()
                session["user_id"] = row["id"]
                session["role"] = row["role"]
                audit("login", f"User {email} logged in")
                return redirect(url_for("dashboard"))
            error = "Invalid email or password"
        return render_template("login.html", error=error)

    @app.route("/logout")
    def logout():
        if session.get("user_id"):
            audit("logout", "User logged out")
        session.clear()
        return redirect(url_for("login"))

    # ------------------------------------------------------------------ dashboard
    @app.route("/")
    @app.route("/dashboard")
    @login_required
    def dashboard():
        user = current_user()
        today_str = today().isoformat()
        # attendance today
        att = query(
            "SELECT * FROM attendance WHERE employee_id = ? AND date = ?",
            (user["employee_id"], today_str),
            one=True,
        )
        # leave balances
        balances = query(
            """SELECT lt.name, lb.balance, lt.color
               FROM leave_balances lb
               JOIN leave_types lt ON lt.id = lb.leave_type_id
               WHERE lb.employee_id = ?""",
            (user["employee_id"],),
        )
        # recent announcements
        announcements = query(
            "SELECT * FROM announcements WHERE is_active = 1 ORDER BY created_at DESC LIMIT 5"
        )
        # team present if manager+
        present_count = None
        if can_manage(user):
            row = query(
                "SELECT COUNT(*) AS n FROM attendance WHERE date = ? AND status IN ('present','late')",
                (today_str,),
                one=True,
            )
            present_count = row["n"] if row else 0
        return render_template(
            "dashboard.html",
            att=att,
            balances=balances,
            announcements=announcements,
            present_count=present_count,
        )

    # ------------------------------------------------------------------ employees
    @app.route("/employees")
    @login_required
    @roles_required("admin", "hr", "manager")
    def employees_list():
        q = (request.args.get("q") or "").strip()
        dept = request.args.get("dept") or ""
        sql = """
            SELECT e.*, d.name AS department_name, s.name AS shift_name
            FROM employees e
            LEFT JOIN departments d ON d.id = e.department_id
            LEFT JOIN shifts s ON s.id = e.shift_id
            WHERE e.is_active = 1
        """
        params = []
        if q:
            sql += " AND (e.first_name LIKE ? OR e.last_name LIKE ? OR e.email LIKE ? OR e.emp_code LIKE ?)"
            like = f"%{q}%"
            params.extend([like, like, like, like])
        if dept:
            sql += " AND e.department_id = ?"
            params.append(dept)
        sql += " ORDER BY e.first_name, e.last_name"
        rows = query(sql, params)
        depts = query("SELECT * FROM departments ORDER BY name")
        return render_template("employees/list.html", employees=rows, depts=depts, q=q, dept=dept)

    @app.route("/employees/new", methods=["GET", "POST"])
    @login_required
    @roles_required("admin", "hr")
    def employees_new():
        depts = query("SELECT * FROM departments ORDER BY name")
        shifts = query("SELECT * FROM shifts ORDER BY name")
        if request.method == "POST":
            data = {
                "emp_code": next_emp_code(),
                "first_name": request.form.get("first_name", "").strip(),
                "last_name": request.form.get("last_name", "").strip(),
                "email": request.form.get("email", "").strip().lower(),
                "phone": request.form.get("phone", "").strip(),
                "department_id": request.form.get("department_id") or None,
                "shift_id": request.form.get("shift_id") or None,
                "job_title": request.form.get("job_title", "").strip(),
                "hire_date": request.form.get("hire_date") or None,
                "basic_salary": float(request.form.get("basic_salary") or 0),
                "is_active": 1,
            }
            execute(
                """INSERT INTO employees
                   (emp_code, first_name, last_name, email, phone, department_id, shift_id,
                    job_title, hire_date, basic_salary, is_active)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    data["emp_code"], data["first_name"], data["last_name"], data["email"],
                    data["phone"], data["department_id"], data["shift_id"], data["job_title"],
                    data["hire_date"], data["basic_salary"], data["is_active"],
                ),
            )
            emp_id = query("SELECT last_insert_rowid() AS id", one=True)["id"]
            # create user account
            pwd = request.form.get("password") or "Employee@123"
            execute(
                "INSERT INTO users (employee_id, email, password_hash, role, is_active) VALUES (?,?,?,?,1)",
                (emp_id, data["email"], hash_password(pwd), request.form.get("role") or "employee"),
            )
            audit("employee_create", f"Created {data['emp_code']} {data['first_name']} {data['last_name']}")
            flash("Employee created", "success")
            return redirect(url_for("employees_list"))
        return render_template("employees/form.html", employee=None, depts=depts, shifts=shifts)

    @app.route("/employees/<int:emp_id>")
    @login_required
    def employees_profile(emp_id):
        emp = query(
            """SELECT e.*, d.name AS department_name, s.name AS shift_name
               FROM employees e
               LEFT JOIN departments d ON d.id = e.department_id
               LEFT JOIN shifts s ON s.id = e.shift_id
               WHERE e.id = ?""",
            (emp_id,),
            one=True,
        )
        if not emp:
            flash("Employee not found", "error")
            return redirect(url_for("employees_list"))
        user = current_user()
        if not can_manage(user) and user["employee_id"] != emp_id:
            flash("Access denied", "error")
            return redirect(url_for("dashboard"))
        att_recent = query(
            "SELECT * FROM attendance WHERE employee_id = ? ORDER BY date DESC LIMIT 10",
            (emp_id,),
        )
        return render_template("employees/profile.html", employee=emp, att_recent=att_recent)

    @app.route("/employees/<int:emp_id>/edit", methods=["GET", "POST"])
    @login_required
    @roles_required("admin", "hr")
    def employees_edit(emp_id):
        emp = query("SELECT * FROM employees WHERE id = ?", (emp_id,), one=True)
        if not emp:
            flash("Not found", "error")
            return redirect(url_for("employees_list"))
        depts = query("SELECT * FROM departments ORDER BY name")
        shifts = query("SELECT * FROM shifts ORDER BY name")
        if request.method == "POST":
            execute(
                """UPDATE employees SET
                   first_name=?, last_name=?, email=?, phone=?, department_id=?,
                   shift_id=?, job_title=?, hire_date=?, basic_salary=?
                   WHERE id=?""",
                (
                    request.form.get("first_name", "").strip(),
                    request.form.get("last_name", "").strip(),
                    request.form.get("email", "").strip().lower(),
                    request.form.get("phone", "").strip(),
                    request.form.get("department_id") or None,
                    request.form.get("shift_id") or None,
                    request.form.get("job_title", "").strip(),
                    request.form.get("hire_date") or None,
                    float(request.form.get("basic_salary") or 0),
                    emp_id,
                ),
            )
            audit("employee_update", f"Updated employee {emp_id}")
            flash("Employee updated", "success")
            return redirect(url_for("employees_profile", emp_id=emp_id))
        return render_template("employees/form.html", employee=emp, depts=depts, shifts=shifts)

    # ------------------------------------------------------------------ departments & shifts
    @app.route("/departments", methods=["GET", "POST"])
    @login_required
    @roles_required("admin", "hr")
    def departments():
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            if name:
                execute("INSERT INTO departments (name) VALUES (?)", (name,))
                audit("department_create", name)
                flash("Department added", "success")
            return redirect(url_for("departments"))
        rows = query("SELECT d.*, (SELECT COUNT(*) FROM employees e WHERE e.department_id = d.id AND e.is_active=1) AS emp_count FROM departments d ORDER BY name")
        return render_template("departments.html", departments=rows)

    @app.route("/shifts", methods=["GET", "POST"])
    @login_required
    @roles_required("admin", "hr")
    def shifts():
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            start = request.form.get("start_time", "09:00")
            end = request.form.get("end_time", "18:00")
            if name:
                execute("INSERT INTO shifts (name, start_time, end_time) VALUES (?,?,?)", (name, start, end))
                audit("shift_create", name)
                flash("Shift added", "success")
            return redirect(url_for("shifts"))
        rows = query("SELECT * FROM shifts ORDER BY name")
        return render_template("shifts.html", shifts=rows)

    # ------------------------------------------------------------------ attendance (delegated)
    attendance_mod.register(app)

    # ------------------------------------------------------------------ leave (delegated)
    leave_mod.register(app)

    # ------------------------------------------------------------------ payroll (delegated)
    payroll_mod.register(app)

    # ------------------------------------------------------------------ reports (delegated)
    reports_mod.register(app)

    # ------------------------------------------------------------------ announcements
    @app.route("/announcements", methods=["GET", "POST"])
    @login_required
    def announcements():
        user = current_user()
        if request.method == "POST" and can_manage(user):
            title = request.form.get("title", "").strip()
            body = request.form.get("body", "").strip()
            if title and body:
                execute(
                    "INSERT INTO announcements (title, body, created_by, is_active) VALUES (?,?,?,1)",
                    (title, body, user["id"]),
                )
                audit("announcement_create", title)
                flash("Announcement published", "success")
            return redirect(url_for("announcements"))
        rows = query(
            "SELECT a.*, u.email AS author FROM announcements a LEFT JOIN users u ON u.id = a.created_by WHERE a.is_active=1 ORDER BY a.created_at DESC"
        )
        return render_template("announcements.html", announcements=rows)

    # ------------------------------------------------------------------ profile / settings / users / holidays / audit
    @app.route("/profile", methods=["GET", "POST"])
    @login_required
    def profile():
        user = current_user()
        if request.method == "POST":
            # password change
            cur = request.form.get("current_password") or ""
            new = request.form.get("new_password") or ""
            if cur and new:
                row = query("SELECT password_hash FROM users WHERE id=?", (user["id"],), one=True)
                if row and verify_password(cur, row["password_hash"]):
                    execute("UPDATE users SET password_hash=? WHERE id=?", (hash_password(new), user["id"]))
                    flash("Password updated", "success")
                else:
                    flash("Current password incorrect", "error")
            return redirect(url_for("profile"))
        return render_template("profile.html")

    @app.route("/settings", methods=["GET", "POST"])
    @login_required
    @roles_required("admin")
    def settings():
        if request.method == "POST":
            keys = [
                "company_name", "company_short", "tagline", "timezone", "currency",
                "email", "phone", "address", "work_start", "work_end",
                "grace_minutes", "overtime_after_minutes", "overtime_rate", "late_policy", "website",
            ]
            for k in keys:
                v = request.form.get(k)
                if v is not None:
                    execute(
                        "INSERT INTO settings (key, value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                        (k, v),
                    )
            audit("settings_update", "Company settings updated")
            flash("Settings saved", "success")
            return redirect(url_for("settings"))
        return render_template("settings.html")

    @app.route("/users", methods=["GET", "POST"])
    @login_required
    @roles_required("admin")
    def users():
        if request.method == "POST":
            # simple role toggle or activate
            uid = request.form.get("user_id")
            role = request.form.get("role")
            if uid and role:
                execute("UPDATE users SET role=? WHERE id=?", (role, uid))
                audit("user_role", f"User {uid} -> {role}")
                flash("Role updated", "success")
            return redirect(url_for("users"))
        rows = query(
            """SELECT u.*, e.first_name, e.last_name, e.emp_code
               FROM users u LEFT JOIN employees e ON e.id = u.employee_id
               ORDER BY u.role, e.first_name"""
        )
        return render_template("users.html", users=rows)

    @app.route("/holidays", methods=["GET", "POST"])
    @login_required
    @roles_required("admin", "hr")
    def holidays():
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            d = request.form.get("date")
            if name and d:
                execute("INSERT INTO holidays (name, date) VALUES (?,?)", (name, d))
                audit("holiday_create", f"{name} {d}")
                flash("Holiday added", "success")
            return redirect(url_for("holidays"))
        rows = query("SELECT * FROM holidays ORDER BY date")
        return render_template("holidays.html", holidays=rows)

    @app.route("/audit")
    @login_required
    @roles_required("admin")
    def audit_log():
        rows = query("SELECT * FROM audit_log ORDER BY created_at DESC LIMIT 200")
        return render_template("audit.html", logs=rows)

    @app.route("/notifications/read", methods=["POST"])
    @login_required
    def notifications_read():
        execute("UPDATE notifications SET is_read=1 WHERE user_id=?", (session["user_id"],))
        return redirect(request.referrer or url_for("dashboard"))

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=True)
