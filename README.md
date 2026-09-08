# Kazeyami Innovations — Human Resource & Attendance OS

A complete, self-contained People / HR / Attendance system built with Flask, Jinja2 and SQLite.
Distinctive paper-and-ink UI (Instrument Serif + Figtree).

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
python3 app.py
```

Open http://127.0.0.1:5050

Database is created and seeded automatically on first launch.
Override path with `KAZEYAMI_DB=/path/to/file.db`.

## Demo accounts

| Role     | Email                 | Password     |
|----------|-----------------------|--------------|
| Admin    | admin@kazeyami.com    | Admin@123    |
| HR       | hr@kazeyami.com       | Hr@12345     |
| Manager  | manager@kazeyami.com  | Manager@123  |
| Employee | employee@kazeyami.com | Employee@123 |

## Features

- Authentication & role-based access (Admin / HR / Manager / Employee)
- Employee directory, profiles, departments, shifts
- Daily attendance clock-in / clock-out, attendance sheet, late & OT rules
- Leave requests, approvals, balance, calendar
- Payroll runs, payslips, basic statutory deductions
- Reports & analytics
- Announcements, notifications, audit log
- Company settings, holidays, users management

## Stack

- Python 3.10+
- Flask + Jinja2
- SQLite (WAL mode, retry-hardened)
- Vanilla JS + custom CSS (no heavy frontend framework)

## Project layout

```
app.py          # Application factory & routes
helpers.py      # Auth, utilities, audit
models.py       # DB layer
seed.py         # Demo data
modules/        # attendance, leave, payroll, reports
static/         # css, js
templates/      # Jinja templates
```

Built for Kazeyami Innovations.
