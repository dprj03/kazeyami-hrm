"""Payroll lite — generate and view payslips."""
from __future__ import annotations

from datetime import date
from flask import Blueprint, flash, redirect, render_template, request, url_for

from helpers import can_manage, current_user, full_name, login_required, roles_required
from models import execute, query, row_to_dict, rows_to_dicts

bp = Blueprint("payroll", __name__)


@bp.route("/payroll")
@bp.route("/payslips")
@login_required
def payslips_page():
    user = current_user()
    year = request.args.get("year", type=int) or date.today().year
    month = request.args.get("month", type=int) or date.today().month

    if can_manage(user):
        rows = query(
            """SELECT p.*, e.first_name, e.last_name, e.emp_code
               FROM payslips p
               JOIN employees e ON e.id = p.employee_id
               WHERE p.year = ? AND p.month = ?
               ORDER BY e.first_name""",
            (year, month),
        )
    else:
        emp = query("SELECT id FROM employees WHERE user_id = ?", (user["id"],), one=True)
        if not emp:
            rows = []
        else:
            rows = query(
                """SELECT p.*, e.first_name, e.last_name, e.emp_code
                   FROM payslips p
                   JOIN employees e ON e.id = p.employee_id
                   WHERE p.employee_id = ? AND p.year = ? AND p.month = ?""",
                (emp["id"], year, month),
            )

    return render_template(
        "payroll/index.html",
        payslips=rows_to_dicts(rows),
        year=year,
        month=month,
        can_manage=can_manage(user),
    )


@bp.route("/payroll/<int:pid>")
@login_required
def payslip_view(pid):
    user = current_user()
    row = query(
        """SELECT p.*, e.first_name, e.last_name, e.emp_code, e.basic_salary,
                  d.name AS dept_name
           FROM payslips p
           JOIN employees e ON e.id = p.employee_id
           LEFT JOIN departments d ON d.id = e.department_id
           WHERE p.id = ?""",
        (pid,),
        one=True,
    )
    if not row:
        flash("Payslip not found.", "error")
        return redirect(url_for("payroll.payslips_page"))
    if not can_manage(user):
        emp = query("SELECT id FROM employees WHERE user_id = ?", (user["id"],), one=True)
        if not emp or emp["id"] != row["employee_id"]:
            flash("Access denied.", "error")
            return redirect(url_for("payroll.payslips_page"))
    return render_template("payroll/payslip.html", p=row_to_dict(row), print_mode=False)


@bp.route("/payroll/<int:pid>/print")
@login_required
def payslip_print(pid):
    user = current_user()
    row = query(
        """SELECT p.*, e.first_name, e.last_name, e.emp_code, e.basic_salary,
                  d.name AS dept_name
           FROM payslips p
           JOIN employees e ON e.id = p.employee_id
           LEFT JOIN departments d ON d.id = e.department_id
           WHERE p.id = ?""",
        (pid,),
        one=True,
    )
    if not row:
        flash("Payslip not found.", "error")
        return redirect(url_for("payroll.payslips_page"))
    if not can_manage(user):
        emp = query("SELECT id FROM employees WHERE user_id = ?", (user["id"],), one=True)
        if not emp or emp["id"] != row["employee_id"]:
            flash("Access denied.", "error")
            return redirect(url_for("payroll.payslips_page"))
    return render_template("payroll/payslip.html", p=row_to_dict(row), print_mode=True)


@bp.route("/payroll/generate", methods=["POST"])
@login_required
@roles_required("admin", "hr")
def payslip_generate():
    from helpers import generate_payslip

    year = int(request.form.get("year") or date.today().year)
    month = int(request.form.get("month") or date.today().month)
    emp_id = request.form.get("employee_id")

    if emp_id:
        generate_payslip(int(emp_id), year, month)
        flash("Payslip generated.", "ok")
    else:
        emps = query("SELECT id FROM employees WHERE status = 'active'")
        for e in emps:
            generate_payslip(e["id"], year, month)
        flash(f"Generated payslips for {len(emps)} employees.", "ok")
    return redirect(url_for("payroll.payslips_page", year=year, month=month))
