# Kazeyami Innovations — People OS

Human resource management and attendance for **Kazeyami Innovations Pte. Ltd.**  
Singapore HQ · Asia/Singapore.

A single Flask app with a SQLite database, distinctive paper-and-ink interface, and seeded demo data so the workspace is alive on first launch.

## Features

- Role-based access: Admin, HR, Manager, Employee
- Employee directory, profiles, departments and designations
- Web clock-in / clock-out with late, overtime and half-day rules
- Monthly attendance sheet and CSV export
- Shifts and holiday calendar
- Leave types, balances, apply / approve / reject / cancel, leave calendar
- Payroll lite — generate and print payslips
- Reports: attendance, leave utilisation, headcount, late arrivals + CSV
- Announcements, notifications, company settings, user roles, audit log

## Quick start

```bash
cd kazeyami-hrm
python3 -m pip install -r requirements.txt
python3 app.py
```

Open [http://127.0.0.1:5050](http://127.0.0.1:5050).

The database `kazeyami.db` is created and seeded automatically on first run.

## Demo accounts

| Role     | Email                   | Password     |
|----------|-------------------------|--------------|
| Admin    | admin@kazeyami.com      | Admin@123    |
| HR       | hr@kazeyami.com         | Hr@12345     |
| Manager  | manager@kazeyami.com    | Manager@123  |
| Employee | employee@kazeyami.com   | Employee@123 |

Other seeded people sign in with their work email and `Welcome@123`.

## Layout

```
app.py              Flask app, auth, employees, org, settings
models.py           SQLite schema and helpers
seed.py             Kazeyami demo dataset
helpers.py          Attendance math, payroll, auth decorators
modules/            Attendance, leave, payroll, reports
templates/          Jinja pages
static/css/app.css  Kazeyami design system
```

## Policy defaults

- Core shift 09:00–18:00, 10 minute grace
- Saturday and Sunday are week-offs
- Singapore public holidays for 2026 plus company days
- Unpaid leave prorates basic salary on generated payslips
