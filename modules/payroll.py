"""Payroll module for Kazeyami HRM."""
from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for

from helpers import can_manage, current_user, login_required, roles_required, audit
from models import execute, query

bp = Blueprint("payroll", __name__, url_prefix="/payroll")


def register(app):
    app.register_blueprint(bp)


@bp.route("/")
@login_required
@roles_required("admin", "hr")
 def index():
    runs = query("SELECT * FROM payroll_runs ORDER BY period_start DESC")
    return render_template("payroll/index.html", runs=runs)


@bp.route("/run", methods=["POST"])
@login_required
@roles_required("admin", "hr")
 def create_run():
    start = request.form.get("period_start")
    end = request.form.get("period_end")
    if not start or not end:
        flash("Period required", "error")
        return redirect(url_for("payroll.index"))
    execute(
        "INSERT INTO payroll_runs (period_start, period_end, status) VALUES (?,?, 'draft')",
        (start, end),
    )
    run_id = query("SELECT last_insert_rowid() AS id", one=True)["id"]
    emps = query("SELECT * FROM employees WHERE is_active=1")
    for e in emps:
        basic = float(e.get("basic_salary") or 0)
        # simple OT placeholder
        ot = 0.0
        deductions = round(basic * 0.05, 2)  # placeholder CPF-like
        net = basic + ot - deductions
        execute(
            """INSERT INTO payslips (run_id, employee_id, basic, allowances, overtime, deductions, net)
               VALUES (?,?,?,?,?,?,?)""",
            (run_id, e["id"], basic, 0, ot, deductions, net),
        )
    audit("payroll_run", f"Run {run_id} {start} to {end}")
    flash("Payroll run created", "success")
    return redirect(url_for("payroll.index"))


@bp.route("/payslip/<int:slip_id>")
@login_required
 def payslip(slip_id):
    slip = query(
        """SELECT p.*, e.first_name, e.last_name, e.emp_code, e.job_title,
                  r.period_start, r.period_end
           FROM payslips p
           JOIN employees e ON e.id = p.employee_id
           JOIN payroll_runs r ON r.id = p.run_id
           WHERE p.id = ?""",
        (slip_id,),
        one=True,
    )
    if not slip:
        flash("Not found", "error")
        return redirect(url_for("dashboard"))
    user = current_user()
    if not can_manage(user) and user["employee_id"] != slip["employee_id"]:
        flash("Access denied", "error")
        return redirect(url_for("dashboard"))
    return render_template("payroll/payslip.html", slip=slip)
