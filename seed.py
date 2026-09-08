"""Seed Kazeyami Innovations demo data."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from werkzeug.security import generate_password_hash

from models import executemany, execute, get_db, init_db, query


def setting(key, value):
    execute("INSERT OR REPLACE INTO settings(key, value) VALUES (?, ?)", (key, value))


def seed():
    init_db()
    existing = query("SELECT COUNT(*) AS c FROM users", one=True)
    if existing and existing["c"]:
        return

    setting("company_name", "Kazeyami Innovations Pte. Ltd.")
    setting("company_short", "Kazeyami")
    setting("tagline", "People systems for ambitious teams")
    setting("timezone", "Asia/Singapore")
    setting("work_start", "09:00")
    setting("work_end", "18:00")
    setting("grace_minutes", "10")
    setting("late_policy", "Arrival after shift start + grace is marked Late.")
    setting("overtime_after_minutes", "480")
    setting("overtime_rate", "1.5")
    setting("weekends", "Sat,Sun")
    setting("currency", "SGD")
    setting("address", "12 Marina View, #18-01 Asia Square Tower 2, Singapore 018961")
    setting("phone", "+65 6910 4400")
    setting("email", "people@kazeyami.com")
    setting("website", "https://kazeyami.com")

    depts = [
        ("Engineering", "ENG", "Product engineering and platform"),
        ("Product", "PRD", "Product strategy and delivery"),
        ("Design", "DSN", "Brand, product and research"),
        ("People & Culture", "PPL", "Talent, HR operations and culture"),
        ("Finance", "FIN", "Finance, payroll and control"),
        ("Operations", "OPS", "Workplace and internal systems"),
        ("Growth", "GRW", "Sales, partnerships and marketing"),
    ]
    for name, code, desc in depts:
        execute(
            "INSERT INTO departments(name, code, description) VALUES (?,?,?)",
            (name, code, desc),
        )

    designations = [
        ("Chief Executive Officer", None, "EL"),
        ("Head of Engineering", 1, "L2"),
        ("Staff Engineer", 1, "L1"),
        ("Software Engineer", 1, "IC"),
        ("Head of Product", 2, "L2"),
        ("Product Manager", 2, "IC"),
        ("Head of Design", 3, "L2"),
        ("Product Designer", 3, "IC"),
        ("Head of People", 4, "L2"),
        ("People Partner", 4, "IC"),
        ("Finance Manager", 5, "L1"),
        ("Operations Lead", 6, "L1"),
        ("Growth Lead", 7, "L1"),
        ("Account Executive", 7, "IC"),
    ]
    for title, dept, level in designations:
        execute(
            "INSERT INTO designations(title, department_id, level) VALUES (?,?,?)",
            (title, dept, level),
        )

    execute(
        "INSERT INTO shifts(name, start_time, end_time, break_minutes, grace_minutes, is_default) VALUES (?,?,?,?,?,?)",
        ("General", "09:00", "18:00", 60, 10, 1),
    )
    execute(
        "INSERT INTO shifts(name, start_time, end_time, break_minutes, grace_minutes, is_default) VALUES (?,?,?,?,?,?)",
        ("Early", "08:00", "17:00", 60, 10, 0),
    )
    execute(
        "INSERT INTO shifts(name, start_time, end_time, break_minutes, grace_minutes, is_default) VALUES (?,?,?,?,?,?)",
        ("Flexible", "10:00", "19:00", 60, 15, 0),
    )

    holidays_2026 = [
        ("New Year's Day", "2026-01-01", "public", "Public holiday"),
        ("Chinese New Year", "2026-02-17", "public", "CNY Day 1"),
        ("Chinese New Year", "2026-02-18", "public", "CNY Day 2"),
        ("Good Friday", "2026-04-03", "public", ""),
        ("Labour Day", "2026-05-01", "public", ""),
        ("Vesak Day", "2026-05-31", "public", ""),
        ("Hari Raya Haji", "2026-05-27", "public", ""),
        ("National Day", "2026-08-09", "public", "Singapore National Day"),
        ("Deepavali", "2026-11-08", "public", ""),
        ("Christmas Day", "2026-12-25", "public", ""),
        ("Kazeyami Founding Day", "2026-03-12", "company", "Company anniversary — half day celebration"),
        ("Year-end Shutdown", "2026-12-31", "company", "Office closed"),
    ]
    for name, dt, typ, desc in holidays_2026:
        execute(
            "INSERT INTO holidays(name, date, type, description) VALUES (?,?,?,?)",
            (name, dt, typ, desc),
        )

    leave_types = [
        ("Annual Leave", "AL", 18, 1, "#C9A227"),
        ("Sick Leave", "SL", 14, 1, "#3D7A6A"),
        ("Casual Leave", "CL", 5, 1, "#6B5B3E"),
        ("Unpaid Leave", "UL", 0, 0, "#8A6A4A"),
        ("Work From Home", "WFH", 24, 1, "#2F5D73"),
    ]
    for name, code, days, paid, color in leave_types:
        execute(
            "INSERT INTO leave_types(name, code, days_per_year, paid, color, requires_approval) VALUES (?,?,?,?,?,1)",
            (name, code, days, paid, color),
        )

    people = [
        # emp_code, first, last, email, phone, dob, gender, dept, desig, manager_idx, shift, join, type, loc, city, basic, hra, allow, role
        ("KZI-001", "Aiko", "Nakamura", "admin@kazeyami.com", "+65 9000 1001", "1986-04-12", "F", 2, 1, None, 1, "2019-03-12", "full_time", "Singapore HQ", "Singapore", 18000, 4000, 2000, "admin"),
        ("KZI-002", "Rafael", "Tan", "hr@kazeyami.com", "+65 9000 1002", "1990-08-03", "M", 4, 9, 1, 1, "2020-01-06", "full_time", "Singapore HQ", "Singapore", 9500, 2200, 800, "hr"),
        ("KZI-003", "Mei", "Wong", "manager@kazeyami.com", "+65 9000 1003", "1988-11-21", "F", 1, 2, 1, 1, "2020-06-15", "full_time", "Singapore HQ", "Singapore", 12000, 2800, 1200, "manager"),
        ("KZI-004", "Arjun", "Mehta", "employee@kazeyami.com", "+65 9000 1004", "1996-02-14", "M", 1, 4, 3, 1, "2023-04-03", "full_time", "Singapore HQ", "Singapore", 6200, 1400, 500, "employee"),
        ("KZI-005", "Sofia", "Reyes", "sofia.reyes@kazeyami.com", "+65 9000 1005", "1994-07-09", "F", 2, 6, 1, 3, "2022-09-12", "full_time", "Singapore HQ", "Singapore", 7800, 1800, 600, "employee"),
        ("KZI-006", "Kenji", "Sato", "kenji.sato@kazeyami.com", "+65 9000 1006", "1992-01-28", "M", 1, 3, 3, 1, "2021-02-01", "full_time", "Singapore HQ", "Singapore", 9800, 2200, 900, "employee"),
        ("KZI-007", "Lina", "Okoro", "lina.okoro@kazeyami.com", "+65 9000 1007", "1995-05-19", "F", 3, 8, 1, 3, "2022-03-21", "full_time", "Singapore HQ", "Singapore", 7100, 1600, 550, "employee"),
        ("KZI-008", "Daniel", "Lim", "daniel.lim@kazeyami.com", "+65 9000 1008", "1989-12-02", "M", 5, 11, 1, 1, "2021-08-16", "full_time", "Singapore HQ", "Singapore", 8800, 2000, 700, "manager"),
        ("KZI-009", "Priya", "Nair", "priya.nair@kazeyami.com", "+65 9000 1009", "1997-09-30", "F", 4, 10, 2, 1, "2024-01-08", "full_time", "Singapore HQ", "Singapore", 5400, 1200, 400, "hr"),
        ("KZI-010", "Jonas", "Berg", "jonas.berg@kazeyami.com", "+65 9000 1010", "1993-06-11", "M", 7, 13, 1, 2, "2022-11-01", "full_time", "Singapore HQ", "Singapore", 8200, 1800, 700, "manager"),
        ("KZI-011", "Hana", "Ishikawa", "hana.ishikawa@kazeyami.com", "+65 9000 1011", "1998-03-07", "F", 3, 7, 1, 3, "2023-07-17", "full_time", "Singapore HQ", "Singapore", 9000, 2100, 800, "employee"),
        ("KZI-012", "Marcus", "Chen", "marcus.chen@kazeyami.com", "+65 9000 1012", "1991-10-23", "M", 6, 12, 1, 2, "2021-05-10", "full_time", "Singapore HQ", "Singapore", 7600, 1700, 600, "employee"),
        ("KZI-013", "Amelia", "Cruz", "amelia.cruz@kazeyami.com", "+65 9000 1013", "1999-08-16", "F", 7, 14, 10, 1, "2024-06-03", "full_time", "Remote — Manila", "Manila", 4800, 900, 300, "employee"),
        ("KZI-014", "Yusuf", "Rahman", "yusuf.rahman@kazeyami.com", "+65 9000 1014", "1994-04-25", "M", 1, 4, 3, 1, "2023-10-02", "full_time", "Singapore HQ", "Singapore", 6000, 1300, 450, "employee"),
        ("KZI-015", "Claire", "Ng", "claire.ng@kazeyami.com", "+65 9000 1015", "1996-12-19", "F", 2, 6, 1, 3, "2025-02-10", "contract", "Singapore HQ", "Singapore", 6500, 0, 400, "employee"),
    ]

    emp_ids = []
    for p in people:
        eid = execute(
            """INSERT INTO employees(
                emp_code, first_name, last_name, email, phone, dob, gender,
                department_id, designation_id, manager_id, shift_id, join_date,
                employment_type, work_location, city, country,
                emergency_name, emergency_phone, emergency_relation,
                bank_name, bank_account, bank_code,
                basic_salary, hra, allowance, status
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?, 'active')""",
            (
                p[0], p[1], p[2], p[3], p[4], p[5], p[6],
                p[7], p[8], p[9], p[10], p[11],
                p[12], p[13], p[14], "Singapore" if p[14] != "Manila" else "Philippines",
                "Family contact", p[4].replace("100", "200"), "Spouse / Parent",
                "DBS Bank", "0" + p[0][-3:] + "889921", "DBSSSGSG",
                p[15], p[16], p[17],
            ),
        )
        emp_ids.append(eid)

    # set department heads
    execute("UPDATE departments SET head_id=? WHERE id=1", (emp_ids[2],))  # Mei Eng
    execute("UPDATE departments SET head_id=? WHERE id=2", (emp_ids[0],))  # Aiko also product for seed
    execute("UPDATE departments SET head_id=? WHERE id=3", (emp_ids[10],))
    execute("UPDATE departments SET head_id=? WHERE id=4", (emp_ids[1],))
    execute("UPDATE departments SET head_id=? WHERE id=5", (emp_ids[7],))
    execute("UPDATE departments SET head_id=? WHERE id=6", (emp_ids[11],))
    execute("UPDATE departments SET head_id=? WHERE id=7", (emp_ids[9],))

    passwords = {
        "admin@kazeyami.com": "Admin@123",
        "hr@kazeyami.com": "Hr@12345",
        "manager@kazeyami.com": "Manager@123",
        "employee@kazeyami.com": "Employee@123",
    }
    for idx, p in enumerate(people):
        email = p[3]
        role = p[18]
        pwd = passwords.get(email, "Welcome@123")
        execute(
            "INSERT INTO users(email, password_hash, role, employee_id, is_active) VALUES (?,?,?,?,1)",
            (email, generate_password_hash(pwd), role, emp_ids[idx]),
        )

    year = 2026
    types = query("SELECT id, days_per_year FROM leave_types")
    for eid in emp_ids:
        for lt in types:
            execute(
                "INSERT INTO leave_balances(employee_id, leave_type_id, year, allocated, used, pending) VALUES (?,?,?,?,0,0)",
                (eid, lt["id"], year, lt["days_per_year"]),
            )

    # leave requests
    execute(
        """INSERT INTO leave_requests(employee_id, leave_type_id, start_date, end_date, days, reason, status, approver_id, decided_at)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (emp_ids[3], 1, "2026-09-14", "2026-09-16", 3, "Family visit", "pending", None, None),
    )
    execute(
        "UPDATE leave_balances SET pending = pending + 3 WHERE employee_id=? AND leave_type_id=1 AND year=2026",
        (emp_ids[3],),
    )
    execute(
        """INSERT INTO leave_requests(employee_id, leave_type_id, start_date, end_date, days, reason, status, approver_id, decided_at, comments)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (emp_ids[4], 1, "2026-08-20", "2026-08-21", 2, "Long weekend", "approved", emp_ids[0], "2026-08-12 10:00:00", "Approved"),
    )
    execute(
        "UPDATE leave_balances SET used = used + 2 WHERE employee_id=? AND leave_type_id=1 AND year=2026",
        (emp_ids[4],),
    )
    execute(
        """INSERT INTO leave_requests(employee_id, leave_type_id, start_date, end_date, days, reason, status, approver_id, decided_at)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (emp_ids[13], 2, "2026-09-07", "2026-09-07", 1, "Fever", "approved", emp_ids[2], "2026-09-07 08:30:00"),
    )

    # attendance for last 14 weekdays
    today = date(2026, 9, 8)
    for eid in emp_ids:
        d = today
        days_added = 0
        while days_added < 12:
            if d.weekday() < 5:
                late = 0
                status = "present"
                cin = "09:02:00"
                cout = "18:08:00"
                work = 486
                ot = 6
                if eid in (emp_ids[3], emp_ids[13]) and days_added % 4 == 0:
                    cin = "09:22:00"
                    late = 12
                    status = "late"
                    work = 466
                    ot = 0
                if eid == emp_ids[4] and d.isoformat() in ("2026-08-20", "2026-08-21"):
                    status = "on_leave"
                    cin = None
                    cout = None
                    work = 0
                    ot = 0
                    late = 0
                execute(
                    """INSERT OR IGNORE INTO attendance_logs(
                        employee_id, work_date, clock_in, clock_out, shift_id, status,
                        late_minutes, overtime_minutes, work_minutes
                    ) VALUES (?,?,?,?,1,?,?,?,?)""",
                    (eid, d.isoformat(), cin, cout, status, late, ot, work),
                )
                days_added += 1
            d -= timedelta(days=1)

    execute(
        """INSERT INTO announcements(title, body, author_id, audience, pinned)
           VALUES (?,?,?,?,1)""",
        (
            "Q3 all-hands — 12 Sep",
            "Join Aiko in the Marina room at 16:00 SGT for the Q3 review. Remote team: link will be posted in #general.",
            1,
            "all",
        ),
    )
    execute(
        """INSERT INTO announcements(title, body, author_id, audience, pinned)
           VALUES (?,?,?,?,0)""",
        (
            "New leave calendar live",
            "Annual leave balances have been refreshed for 2026. Please review your balance before planning travel in December.",
            2,
            "all",
        ),
    )
    execute(
        """INSERT INTO announcements(title, body, author_id, audience, pinned)
           VALUES (?,?,?,?,0)""",
        (
            "Office closed 31 Dec",
            "Kazeyami HQ will be closed on 31 December for year-end shutdown. Clock-in is not required.",
            2,
            "all",
        ),
    )

    # sample payslips for August 2026
    emps = query("SELECT id, basic_salary, hra, allowance FROM employees")
    for e in emps:
        basic = e["basic_salary"] or 0
        hra = e["hra"] or 0
        allow = e["allowance"] or 0
        ot = 180
        tax = round((basic + hra + allow) * 0.05, 2)
        gross = basic + hra + allow + ot
        net = gross - tax
        execute(
            """INSERT INTO payslips(employee_id, period_year, period_month, basic, hra, allowance,
               overtime_pay, unpaid_deduction, tax, other_deduction, gross, net, status)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?, 'published')""",
            (e["id"], 2026, 8, basic, hra, allow, ot, 0, tax, 0, gross, net),
        )

    execute(
        "INSERT INTO audit_log(user_id, action, entity, entity_id, details) VALUES (1,'seed','system','0','Initial Kazeyami dataset loaded')",
    )


if __name__ == "__main__":
    seed()
    print("Seed complete.")
