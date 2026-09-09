"""Payroll — generate, list, view, print payslips."""
from __future__ import annotations

from datetime import date

from flask import flash, redirect, render_template, request, url_for

from helpers import (
    MONTHS,
    audit,
    can_manage,
    current_user,
    generate_payslip,
    login_required,
    money,
    roles_required,
)
from models import query, row_to_dict, rows_to_dicts


def _emp_id(user):
    return user.get("emp_id") or user.get("employee_id")


def list_payslips(user, year=None):
    year = year or date.today().year
    sql = """
        SELECT p.*, e.first_name || ' ' || e.last_name AS employee_name,
               e.emp_code, d.name AS department_name
        FROM payslips p
        JOIN employees e ON e.id = p.employee_id
        LEFT JOIN departments d ON d.id = e.department_id
        WHERE p.period_year = ?
    """
    args = [year]
    if user["role"] not in ("admin", "hr"):
        eid = _emp_id(user)
        sql += " AND p.employee_id = ?"
        args.append(eid)
    sql += " ORDER BY p.period_month DESC, e.emp_code"
    return rows_to_dicts(query(sql, args))


def get_payslip(pid: int):
    return row_to_dict(
        query(
            """
            SELECT p.*, e.first_name || ' ' || e.last_name AS employee_name,
                   e.emp_code, e.bank_name, e.bank_account, e.work_location,
                   e.basic_salary, d.name AS department_name, g.title AS designation_title
            FROM payslips p
            JOIN employees e ON e.id = p.employee_id
            LEFT JOIN departments d ON d.id = e.department_id
            LEFT JOIN designations g ON g.id = e.designation_id
            WHERE p.id = ?
            """,
            (pid,),
            one=True,
        )
    )


def can_view_payslip(user, slip) -> bool:
    if not slip:
        return False
    if user["role"] in ("admin", "hr"):
        return True
    return slip["employee_id"] == _emp_id(user)


def register(app):
    @app.route("/payroll")
    @app.route("/payslips")
    @login_required
    def payslips_page():
        user = current_user()
        year = int(request.args.get("year", date.today().year))
        slips = list_payslips(user, year)
        employees = []
        if can_manage(user):
            employees = rows_to_dicts(
                query(
                    "SELECT id, emp_code, first_name, last_name FROM employees WHERE status='active' ORDER BY emp_code"
                )
            )
        years = [r["y"] for r in query("SELECT DISTINCT period_year AS y FROM payslips ORDER BY y DESC")]
        if year not in years:
            years = [year] + years
        return render_template(
            "payroll/index.html",
            slips=slips,
            employees=employees,
            year=year,
            years=years,
            months=MONTHS,
            can_generate=can_manage(user),
            today=date.today(),
        )

    @app.route("/payroll/generate", methods=["POST"])
    @roles_required("admin", "hr")
    def payslip_generate():
        user = current_user()
        year = int(request.form["year"])
        month = int(request.form["month"])
        target = request.form.get("employee_id", "all")
        count = 0
        errors = 0
        if target == "all":
            emps = query("SELECT id FROM employees WHERE status='active'")
            ids = [e["id"] for e in emps]
        else:
            ids = [int(target)]
        for eid in ids:
            try:
                generate_payslip(eid, year, month, user["id"])
                count += 1
            except Exception:
                errors += 1
        audit("payslip_generate", "payslips", None, f"{count} slips {year}-{month:02d}")
        flash(f"Generated {count} payslip(s)" + (f" · {errors} skipped" if errors else "") + ".", "ok" if count else "bad")
        return redirect(url_for("payslips_page", year=year))

    @app.route("/payroll/<int:pid>")
    @login_required
    def payslip_view(pid):
        user = current_user()
        slip = get_payslip(pid)
        if not can_view_payslip(user, slip):
            flash("Payslip not found.", "bad")
            return redirect(url_for("payslips_page"))
        return render_template("payroll/payslip.html", slip=slip, months=MONTHS, print_mode=False)

    @app.route("/payroll/<int:pid>/print")
    @login_required
    def payslip_print(pid):
        user = current_user()
        slip = get_payslip(pid)
        if not can_view_payslip(user, slip):
            flash("Payslip not found.", "bad")
            return redirect(url_for("payslips_page"))
        return render_template("payroll/payslip.html", slip=slip, months=MONTHS, print_mode=True)
