"""Reports module for Kazeyami HRM."""
from __future__ import annotations

from flask import Blueprint, render_template, request

from helpers import login_required, roles_required, today
from models import query

bp = Blueprint("reports", __name__, url_prefix="/reports")


def register(app):
    app.register_blueprint(bp)


@bp.route("/")
@login_required
@roles_required("admin", "hr", "manager")
 def index():
    month = request.args.get("month") or today().strftime("%Y-%m")
    # attendance summary
    att = query(
        """SELECT status, COUNT(*) AS n FROM attendance
           WHERE date LIKE ? GROUP BY status""",
        (f"{month}%",),
    )
    # leave usage
    leave = query(
        """SELECT lt.name, SUM(lr.days) AS days
           FROM leave_requests lr
           JOIN leave_types lt ON lt.id = lr.leave_type_id
           WHERE lr.status = 'approved' AND lr.start_date LIKE ?
           GROUP BY lt.name""",
        (f"{month}%",),
    )
    # headcount by dept
    depts = query(
        """SELECT d.name, COUNT(e.id) AS n
           FROM departments d
           LEFT JOIN employees e ON e.department_id = d.id AND e.is_active=1
           GROUP BY d.id ORDER BY n DESC"""
    )
    return render_template(
        "reports/index.html",
        month=month,
        att=att,
        leave=leave,
        depts=depts,
    )
