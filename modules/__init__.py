"""Kazeyami HRM modules."""

from modules.leave import register as register_leave
from modules.payroll import register as register_payroll
from modules.reports import register as register_reports

__all__ = ["register_leave", "register_payroll", "register_reports"]
