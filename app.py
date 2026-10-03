# =================================================
# MERGED APP (PART 1 + PART 2) — Google Sheets removed
# =================================================

# Common imports
from flask import (
    Flask, request, send_file, jsonify, render_template,
    flash, redirect, url_for, session
)
from werkzeug.utils import secure_filename
from flask_mysqldb import MySQL
from MySQLdb.cursors import DictCursor
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
import time

from datetime import datetime, timedelta, time
from io import BytesIO
import os
import re
import pandas as pd
import calendar
from datetime import datetime

# =================================================
# App & Config
# =================================================
app = Flask(__name__)
app.secret_key = "replace_with_strong_secret"  # change for production

# Upload folders
UPLOAD_FOLDER = "static/boq_est_uploads"
PROFILE_PHOTO_FOLDER = os.path.join("static", "profile_photos")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROFILE_PHOTO_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["PROFILE_PHOTO_FOLDER"] = PROFILE_PHOTO_FOLDER

# MySQL config - per your request use alcovedb_2024 as default DB
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Sagar1290'
app.config['MYSQL_DB'] = 'alcovedb_2024'

mysql = MySQL(app)


def _dict_cur_fms_new_format():
    """Return a DictCursor on the *default* connection."""
    return mysql.connection.cursor(DictCursor)


# =================================================
# ========== PART 1: LOGIN / MAIN DASHBOARD / HELPERS
# =================================================
# This is your original PART 1 login, upload photo, forgot password, main dashboard.
# The login authenticates against Employee_Master in default DB (alcovedb_2024),
# and then enriches session by looking up fms_con_purchase_bad.users (so emp_code matches users.emp_code).

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        emp_code = request.form['emp_code']
        password = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute(
            "SELECT Emp_Code, password, Designation, Department, Admin, Photo_Link, Email_ID_Official, Contact_number, user_Access, Person_Accountable,Reporting_DOER FROM Employee_Master WHERE Emp_Code=%s and STATUS='ACTIVE'",
            (emp_code,))
        user = cur.fetchone()
        cur.close()

        if user and user[1] == password:
            session['emp_code'] = user[0]
            session['designation'] = user[2]
            session['department'] = user[3]
            session['admin'] = user[4]
            session['photo'] = get_default_photo(user[5])
            session['email'] = user[6]
            session['contact'] = user[7]
            session['user_Access'] = user[8]
            session['person_Accountable'] = user[9]
            session['Reporting_DOER'] = user[10]
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid Credentials', 'danger')
            return render_template('login.html')

    return render_template('login.html')


def get_default_photo(param):
    pass


@app.route('/dashboard')
def dashboard():
    if 'emp_code' not in session:
        return redirect(url_for('login'))
    # -------------------------------------------------------------------------
    # 11) Build your fixed menus (unchanged)
    # -------------------------------------------------------------------------
    fixed_menus = {

        # "HR Recruitment Process": [
        #     ("HR Dashboard", url_for('dashboard_hrrec'))
        # ],
        "FMS NAME": [
            ("NEW CONTRACTOR REGISTRATION", url_for('dashboard_fms_new_format')),
            # ("FMS Estimation", url_for('dashboard_fms_estimation'))
        ]

    }
    return render_template(
        'dashboard.html',
        fixed_menus=fixed_menus,
    )


@app.route('/upload_photo', methods=['POST'])
def upload_photo():
    if 'emp_code' not in session:
        return redirect(url_for('login'))

    if 'photo' not in request.files:
        flash('No file uploaded', 'danger')
        return redirect(url_for('dashboard'))

    file = request.files['photo']
    if file.filename == '':
        flash('No selected file', 'danger')
        return redirect(url_for('dashboard'))

    if file:
        filename = secure_filename(file.filename)
        # Save to PROFILE_PHOTO_FOLDER
        filepath = os.path.join(app.config['PROFILE_PHOTO_FOLDER'], filename)
        file.save(filepath)

        # Update DB
        cur = mysql.connection.cursor()
        cur.execute("UPDATE Employee_Master SET Photo_Link=%s WHERE Emp_Code=%s",
                    (filepath, session['emp_code']))
        mysql.connection.commit()
        cur.close()

        # Update session with new photo path
        session['photo'] = filepath
        flash('Photo uploaded successfully!', 'success')

    return redirect(url_for('dashboard'))


@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    emp_code = session.get('emp_code', '')  # Prefill if logged in
    is_logged_in = 'readonly' if emp_code else ''  # Set read-only if logged in

    if request.method == 'POST':
        emp_code = request.form['emp_code']
        old_password = request.form['old_password']
        new_password = request.form['new_password']

        cur = mysql.connection.cursor()
        cur.execute("SELECT password FROM Employee_Master WHERE Emp_Code=%s", (emp_code,))
        user = cur.fetchone()

        if not user:
            flash('Employee ID not found!', 'danger')
            return redirect(url_for('forgot_password'))

        if user[0] != old_password:
            flash('Old password is incorrect!', 'danger')
            return redirect(url_for('forgot_password'))

        # Update the password in the Employee_Master table
        cur.execute("UPDATE Employee_Master SET password=%s WHERE Emp_Code=%s", (new_password, emp_code))

        # Insert a record into the Password_Records table to keep history
        cur.execute("INSERT INTO Password_Records (Emp_Code, New_Password) VALUES (%s, %s)",
                    (emp_code, new_password))

        mysql.connection.commit()
        cur.close()

        flash('Password reset successfully', 'success')
        return redirect(url_for('login'))

    return render_template('forgot_password.html', emp_code=emp_code, is_logged_in=is_logged_in)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))
# =================================================
# ========== PART 2:
# =================================================

# ==========================================================
# TASK FIELD CONFIGURATION
# ==========================================================

TASK_FIELDS_fms_new_format = {

    # ======================================================
    # CREATE TASK FIELDS
    # ======================================================

    "task_name": {
        "label": "Task",
        "type": "text",
        "db_column": "task_name",
        "required": False,
        "create": True,
        "view": False
    },

    "attachment": {
        "label": "Attachment",
        "type": "file",
        "db_column": "tg_attachment_path",
        "required": True,
        "create": True,
        "view": False
    },

    "task_remarks": {
        "label": "Remarks",
        "type": "textarea",
        "db_column": "task_remarks",
        "required": False,
        "create": True,
        "view": False
    },

    "store_name": {
        "label": "Store",
        "type": "textarea",
        "db_column": "store_name",
        "required": True,
        "create": True,
        "view": False
    },

    # ======================================================
    # VIEW MODAL FIELDS
    # ======================================================

    "Step": {
        "label": "Step",
        "type": "textarea",
        "db_column": "current_stage",
        "required": False,
        "create": False,
        "view": True
    },

    "task_id": {
        "label": "Task ID",
        "type": "number",
        "db_column": "task_id",
        "required": False,
        "create": False,
        "view": True
    },

    "remark": {
        "label": "Previous Step Remarks",
        "type": "textarea",
        "db_column": "remark",
        "required": False,
        "create": False,
        "view": True
    },

    "attachment_path": {
        "label": "FMS Step Attachment",
        "type": "file",
        "db_column": "attachment_path",
        "required": False,
        "create": False,
        "view": True
    },

    "tg_attachment_path": {
        "label": "Raiser Attachment",
        "type": "file",
        "db_column": "tg_attachment_path",
        "required": False,
        "create": False,
        "view": True
    },
}

USERS_fms_new_format = {
    "AR001145": {"username": "Subhash Chandra Karmakar", "roles": "P2,P3,P4", "project": ""},
    "AR001603": {"username": "SOURAV DUTTA", "roles": "P5,P7", "project": ""},
    "AR000425": {"username": "SANDEEP JAIN", "roles": "P6", "project": ""},
    "AR000260": {"username": "Tapas Kumar Pal", "roles": "P5,P6,P7", "project": ""},
    "AR000773": {"username": "Admin",
                 "roles": "P2,P3,P4,P5,P6,P7",
                 "project": ""},
    "AR000623": {"username": "Admin",
                 "roles": "P2,P3,P4,P5,P6,P7",
                 "project": ""},
    "AR001816": {"username": "Admin",
                 "roles": "P2,P3,P4,P5,P6,P7",
                 "project": ""}
}

Step_fms_new_format = {

    'P2': {
        'Step Details': "IS ALL DATA CORRECT AS PER ATTACHED DOCUMENT ?",
        'emp_code': ['AR001145', 'AR000773', 'AR000623'],
        'actual_emp_code': "AR001145",
        'location': "Office"
    },

    'P3': {
        'Step Details': "REQUEST CONTRACTOR TO REFILL FORM WITH CORRECT DATA",
        'emp_code': ['AR001145', 'AR000773', 'AR000623'],
        'actual_emp_code': "AR001145",
        'location': "Office"
    },

    'P4': {
        'Step Details': "ASSIGN LABOUR NAME AND CATEGORY",
        'emp_code': ['AR001145', 'AR000773', 'AR000623'],
        'actual_emp_code': "AR001145",
        'location': "Office"
    },

    'P5': {
        'Step Details': "IS NEW CONTRACTOR CREATION DATA CORRECT ? PREPARE NEW CONTRACTOR CREATION REPORT",
        'emp_code': ['AR001603', 'AR000153', 'AR000773', 'AR000623'],
        'actual_emp_code': "AR001603",
        'location': "Office"
    },

    'P6': {
        'Step Details': "IS NEW CONTRACTOR CREATION APPROVED ?",
        'emp_code': ['AR000425', 'AR000153', 'AR000773', 'AR000623'],
        'actual_emp_code': "AR000425",
        'location': "Office"
    },
    'P7': {
        'Step Details': "CREATE CONTRACTOR",
        'emp_code': ['AR001603', 'AR000153', 'AR000773', 'AR000623'],
        'actual_emp_code': "AR001603",
        'location': "Office"
    }
}

WORKFLOW_MAIN_fms_new_format = {
# --------------------New task Creation-------------------------
    "P0": [
        {
            "tasks": {"c.name": "none", "value": "null"},
            "next": "P2",
            "hours": {"first": "11:00", "rework": 0},
            "cutoff_minutes": 60,
            "decision": False
        }
    ],
    "P2": [
        {
            "tasks": {"c.name": "none", "value": "null"},
            "yes": "P4",
            "no": "P3",
            "hours": {
                "yes": {"first": 3, "rework": 0},
                "no": {"first": 2, "rework": 0}
            },
            "cutoff_minutes": {"yes": 0, "no": 0},
            "decision": True
        }
    ],
    "P3": [
        {
            "tasks": {"c.name": "none", "value": "null"},
            "next": "STOP",
            "hours": {"first": 0, "rework": 0},
            "cutoff_minutes": 0,
            "decision": False
        }
    ],
    "P4": [
        {
            "tasks": {"c.name": "none", "value": "null"},
            "next": "P5",
            "hours": {"first": 16, "rework": 0},
            "cutoff_minutes": 0,
            "decision": False
        }
    ],
    "P5": [
        {
            "tasks": {"c.name": "none", "value": "null"},
            "yes": "P6",
            "no": "P4",
            "hours": {
                "yes": {"first": 3, "rework": 0},
                "no": {"first": 3, "rework": 0}
            },
            "cutoff_minutes": {"yes": 0, "no": 0},
            "decision": True
        }
    ],
    "P6": [
        {
            "tasks": {"c.name": "none", "value": "null"},
            "yes": "P7",
            "no": "P4",
            "hours": {
                "yes": {"first": 4, "rework": 0},
                "no": {"first": 3, "rework": 0}
            },
            "cutoff_minutes": {"yes": 0, "no": 0},
            "decision": True
        }
    ],
    "P7": [
        {
            "tasks": {"c.name": "none", "value": "null"},
            "next": "Completed",
            "hours": {"first": 0, "rework": 0},
            "cutoff_minutes": 0,
            "decision": False
        }
    ],

}

# Creator-visible steps
CREATOR_VISIBLE_STEPS_fms_new_format = ['P0']
# Creator-visible steps
ALLOCATION_VISIBLE_STEPS_fms_new_format = ['P0']
# Actual-visible steps
ACTUAL_VISIBLE_STEPS_fms_new_format = ['P0']


STEP_UI_CONFIG_fms_new_format = {
    "decision": {
        "visible": ['P2', 'P3', 'P4', 'P5', 'P6'],
        "mandatory": ['P2', 'P5', 'P6']
    },
    "attachment": {
        "visible": ['P2', 'P3', 'P4', 'P5', 'P6', 'P7'],
        "mandatory": ['P0']
    },
    "remark": {
        "visible": "ALL",
        "mandatory": "ALL"
    }
}

ALLOCATION_MAP_fms_new_format = {
    "NAME": "AR000001",


}


# ==========================================
# PREVIOUS ID SOURCE CONFIG
# ==========================================

PREVIOUS_ID_RULES_fms_new_format = {

    "P0": "created_emp_code",
}


def get_holidays_by_location_fms_new_format(location):
    """
    Load holidays based on step location.
    Office -> holidays_office
    Site   -> holidays_site
    """

    if str(location).lower() == "site":
        table = "alcovedb_2024.holidays_site"
    else:
        table = "alcovedb_2024.holidays_office"

    cur = _dict_cur_fms_new_format()
    cur.execute(f"SELECT holiday_date FROM {table}")
    holidays = {row["holiday_date"] for row in cur.fetchall()}
    cur.close()

    return holidays


# def is_working_hour_fms_new_format(dt, holidays):
#     if dt.weekday() == 6 or dt.date() in holidays:
#         return False
#     return time(10, 0) <= dt.time() < time(18, 30)

def is_working_hour_fms_new_format(dt, holidays):

    if dt.weekday() == 6 or dt.date() in holidays:
        return False

    current_time = datetime.strftime(dt, "%H:%M")

    return "10:00" <= current_time < "18:30"


def add_working_hours_fms_new_format(start_time, hours, location):
    holidays = get_holidays_by_location_fms_new_format(location)

    current = start_time
    remaining = int(hours * 60)

    while remaining > 0:
        if is_working_hour_fms_new_format(current, holidays):
            remaining -= 1

        current += timedelta(minutes=1)

    return current.replace(second=0, microsecond=0)


def parse_dynamic_datetime_fms_new_format(expr, now, location, task):
    """
    Supports:
    +D2TPM6:30
    -D1TAM10:30   ✅ NEW
    C.requirement_date+D1TAM11:30
    C.po_revised_delivery_date-D1TAM10:30  ✅ NEW
    """

    import re

    base_date = now

    # ✅ COLUMN BASE (C.)
    if expr.startswith("C."):
        parts = re.split(r"(\+D|\-D)", expr, maxsplit=1)

        col_part = parts[0]  # C.po_revised_delivery_date
        column_name = col_part.replace("C.", "").strip()

        base_date = task.get(column_name)

        if isinstance(base_date, datetime):
            pass
        elif base_date:
            base_date = datetime.combine(base_date, datetime.min.time())
        else:
            base_date = now

        expr_part = "".join(parts[1:]) if len(parts) > 1 else ""

    else:
        expr_part = expr

    # ✅ SUPPORT +D and -D
    pattern = r"([+-])D(\d+)T(AM|PM)(\d{1,2}):(\d{2})"
    match = re.match(pattern, expr_part.upper())

    if not match:
        return base_date

    sign = match.group(1)  # + or -
    days = int(match.group(2))
    am_pm = match.group(3)
    hh = int(match.group(4))
    mm = int(match.group(5))

    # ✅ Convert to 24-hour
    if am_pm == "PM" and hh != 12:
        hh += 12
    elif am_pm == "AM" and hh == 12:
        hh = 0

    # ==============================
    # ✅ HANDLE +D (WORKING DAYS)
    # ==============================
    if sign == "+":
        target_date = base_date

        for _ in range(days):
            target_date += timedelta(days=1)
            target_date = get_next_working_day_fms_new_format(target_date, location)

        planned = target_date.replace(hour=hh, minute=mm, second=0, microsecond=0)

        # ✅ Final holiday adjust
        planned = get_next_working_day_fms_new_format(planned, location)

        return planned

    # ==============================
    # ✅ HANDLE -D (NORMAL DAYS, NO HOLIDAY SKIP)
    # ==============================
    elif sign == "-":
        target_date = base_date - timedelta(days=days)

        planned = target_date.replace(hour=hh, minute=mm, second=0, microsecond=0)

        return planned

    return base_date

def resolve_dynamic_value_fms_new_format(value, task):
    """
    If value matches a task column name,
    return task[column_name]
    else return original value
    """

    if not value:
        return value

    # task table column check
    if isinstance(value, str) and value in task:
        return task.get(value)

    return value

def get_step_data_fms_new_format(stage, task=None):

    if not stage:
        return {}

    stage = str(stage).upper().strip()

    main_stage = get_main_stage_fms_new_format(stage)

    step = Step_fms_new_format.get(stage) or Step_fms_new_format.get(main_stage)

    if not step:
        return {}

    # =========================
    # DYNAMIC emp_code
    # =========================

    emp_codes = []

    for code in step.get("emp_code", []):

        if task:
            code = resolve_dynamic_value_fms_new_format(code, task)

        emp_codes.append(code)

    # =========================
    # DYNAMIC actual_emp_code
    # =========================

    actual_emp_code = step.get("actual_emp_code")

    if task:
        actual_emp_code = resolve_dynamic_value_fms_new_format(
            actual_emp_code,
            task
        )

    # =========================
    # FETCH EMPLOYEE DETAILS
    # =========================

    actual_emp_name = ""
    hod_emp_code = ""
    hod_name = ""

    if actual_emp_code:

        cur = _dict_cur_fms_new_format()

        cur.execute("""
            SELECT
                Person_Accountable,
                HOD_ID,
                HOD
            FROM alcovedb_2024.Employee_Master
            WHERE Emp_Code=%s
            LIMIT 1
        """, (actual_emp_code,))

        row = cur.fetchone()

        cur.close()

        if row:
            actual_emp_name = row.get("Person_Accountable") or ""
            hod_emp_code = row.get("HOD_ID") or ""
            hod_name = row.get("HOD") or ""

    return {

        "emp_code": ",".join(
            [str(x) for x in emp_codes if x]
        ),

        "actual_emp_code": actual_emp_code,
        "actual_emp_name": actual_emp_name,

        "hod_emp_code": hod_emp_code,
        "hod_name": hod_name,

        "task_details": step.get("Step Details"),
        "location": step.get("location")
    }

def user_access_fms_new_format():
    if "emp_code" not in session:
        return

    emp_code = session["emp_code"]

    user = USERS_fms_new_format.get(emp_code)

    if not user:
        # default limited access
        session["roles"] = "P0"
        session["projects"] = ""
        session["username"] = emp_code
        return

    session["roles"] = user.get("roles", "P0")
    session["projects"] = user.get("project", "")
    session["username"] = user.get("username", emp_code)


def normalize_roles_fms_new_format(roles):
    if not roles:
        return set()
    if isinstance(roles, str):
        return {r.strip().upper() for r in roles.split(",") if r.strip()}
    return {r.upper() for r in roles}


def get_main_stage_fms_new_format(task_stage):
    if not task_stage:
        return ""
    m = re.search(r"(P\d+)", str(task_stage).upper())
    if m:
        return m.group(1)
    return str(task_stage).upper()


def check_rework_fms_new_format(task, next_stage):
    cur = _dict_cur_fms_new_format()

    cur.execute("""
        SELECT 1
        FROM fms_new_format_2026.task_updates
        WHERE task_id=%s
          AND task_name=%s
          AND from_stage=%s
          AND to_stage=%s
        LIMIT 1
    """, (
        task.get("task_id"),
        task.get("task_name"),
        task.get("current_stage"),
        next_stage
    ))

    result = cur.fetchone()
    cur.close()

    return result is not None  # ✅ SAFE


def get_next_step_and_time_fms_new_format(task, workflow, now):
    current_stage = task["current_stage"]

    wf_list = workflow.get(current_stage)

    if not wf_list:
        return None, None, None

    # ✅ LOOP THROUGH CONDITIONS
    for wf in wf_list:

        column = wf["tasks"]["c.name"]
        value = wf["tasks"]["value"]

        match = False

        if column == "none":
            match = True
        else:
            db_value = task.get(column)

            if value == "null":
                match = (db_value is None or db_value == "")
            elif value == "not null":
                match = (db_value is not None and db_value != "")
            # else:
            #     match = str(db_value) == str(value)
            else:

                # ✅ MULTI VALUE SUPPORT

                if isinstance(value, list):

                    match = str(db_value) in [str(v) for v in value]

                else:

                    match = str(db_value) == str(value)

        # ✅ FIRST MATCH WILL EXECUTE
        if match:

            # 🔹 DECISION
            if wf["decision"]:
                decision = task.get("decision")

                next_stage = wf["yes"] if decision == "Yes" else wf["no"]
                hours = wf["hours"][decision.lower()]
                cutoff = wf["cutoff_minutes"][decision.lower()]

            else:
                next_stage = wf["next"]
                hours = wf["hours"]
                cutoff = wf.get("cutoff_minutes", 0)

            # 🔹 REWORK (OPTIMIZED - QUERY ONLY IF NEEDED)

            if isinstance(hours, dict):

                rework_hours = hours.get("rework", 0)

                # ✅ CASE 1: rework is 0 → skip DB
                if rework_hours == 0 or rework_hours == "0":
                    hours = hours.get("first")

                else:
                    # ✅ CASE 2: check rework only if needed
                    is_rework = check_rework_fms_new_format(task, next_stage)

                    if is_rework:
                        hours = rework_hours  # can be "11:40" OR 8.5
                    else:
                        hours = hours.get("first")

            # 🔹 TIME LOGIC
            if isinstance(hours, str):
                # if hours.startswith("+D"):
                #     step_data = get_step_data_fms_new_format(next_stage)
                #     location = step_data.get("location")
                #
                #     planned = parse_dynamic_datetime_fms_new_format(hours, now, location)

                if hours.startswith("+D") or hours.startswith("C."):
                    step_data = get_step_data_fms_new_format(next_stage)
                    location = step_data.get("location")

                    planned = parse_dynamic_datetime_fms_new_format(
                        hours, now, location, task)

                elif ":" in hours:

                    step_data = get_step_data_fms_new_format(next_stage)
                    location = step_data.get("location")

                    hh, mm = map(int, hours.split(":"))

                    # 👉 today target
                    today_target = now.replace(hour=hh, minute=mm, second=0)

                    cutoff_time = today_target - timedelta(minutes=cutoff)

                    holidays = get_holidays_by_location_fms_new_format(location)

                    # ❌ if today is holiday → move to next working day
                    if now.weekday() == 6 or now.date() in holidays:
                        next_work_day = get_next_working_day_fms_new_format(now + timedelta(days=1), location)
                        planned = next_work_day.replace(hour=hh, minute=mm, second=0)

                    else:
                        if now <= cutoff_time:
                            planned = today_target
                        else:
                            next_work_day = get_next_working_day_fms_new_format(now + timedelta(days=1), location)
                            planned = next_work_day.replace(hour=hh, minute=mm, second=0)
                # date LOGIC
                elif hours.startswith("d"):

                    target_day = int(hours.replace("d", ""))  # ✅ dynamic day (26, 20, etc.)
                    created = task.get(wf["date_month"])  # ✅ dynamic column

                    last_day = calendar.monthrange(created.year, created.month)[1]
                    target_day = min(target_day, last_day)

                    if not created:
                        created = now  # fallback safety

                    step_data = get_step_data_fms_new_format(next_stage)
                    location = step_data.get("location")

                    # ✅ IMPORTANT: compare with (target_day - 1)
                    if now.day <= (target_day - 1):

                        # 👉 create planned date using created_at month/year
                        planned = datetime(created.year, created.month, target_day, 18, 30)

                        # ✅ adjust if holiday
                        planned = get_next_working_day_fms_new_format(planned, location)
                        planned = planned.replace(hour=18, minute=30)

                    else:
                        # ❌ after cutoff → use "next" hours
                        next_hours = wf["hours"].get("next", 8.5)

                        planned = add_working_hours_fms_new_format(now, next_hours, location)

                else:
                    planned = now

            else:
                step_data = get_step_data_fms_new_format(next_stage)
                planned = add_working_hours_fms_new_format(now, hours, step_data.get("location"))

            return next_stage, planned, wf["decision"]

    # ❌ No condition matched
    return None, None, None


@app.route("/dashboard_fms_new_format")
def dashboard_fms_new_format():

    if "emp_code" not in session:
        return redirect(url_for("login"))

    user_access_fms_new_format()
    # ==========================================================
    # DASHBOARD TEMPLATE
    # ==========================================================
    session["dashboard_template"] = "fms_new_format_dashboard.html"
    session["dashboard_stage_prefix"] = None

    # ==========================================================
    # USER NAME
    # ==========================================================

    name = session.get("username") or session.get("emp_code")

    # ==========================================================
    # DATABASE
    # ==========================================================

    cur = _dict_cur_fms_new_format()

    # # ==========================================================
    # # HOD CREATE TASK ACCESS
    # # ==========================================================
    #
    # cur.execute("""
    #     SELECT 1
    #     FROM alcovedb_2024.Employee_Master
    #     WHERE TRIM(HOD_ID) = %s
    #     LIMIT 1
    # """, (
    #     session["emp_code"].strip(),
    # ))
    #
    # hod_can_create_task = cur.fetchone() is not None

    # ==========================================================
    # CREATE TASK ACCESS
    # ==========================================================

    CREATE_TASK_USERS_fms_new_format = {
        "AR000773",
        "AR000623",
        "AR000638",
    }

    login_emp_code = session.get("emp_code", "").strip().upper()

    can_create_task = login_emp_code in CREATE_TASK_USERS_fms_new_format

    # ==========================================================
    # EMPLOYEE MASTER
    # ==========================================================

    cur.execute("""
        SELECT Person_Accountable
        FROM alcovedb_2024.Employee_Master
        WHERE Emp_Code = %s
    """, (
        session["emp_code"],
    ))

    row = cur.fetchone()

    login_person_name = ""
    auto_department_head_emp_code = ""

    if row and row["Person_Accountable"]:

        login_person_name = row["Person_Accountable"]

        cur.execute("""
            SELECT Emp_Code
            FROM alcovedb_2024.Employee_Master
            WHERE Person_Accountable = %s
            LIMIT 1
        """, (
            login_person_name,
        ))

        dh = cur.fetchone()

        if dh:
            auto_department_head_emp_code = dh["Emp_Code"]

    cur.close()

    # ==========================================================
    # DASHBOARD TASKS
    # ==========================================================

    tasks = fetch_all_tasks_for_dashboard_fms_new_format()

    pending_count = len(tasks)

    # ==========================================================
    # FILTER DATA
    # ==========================================================

    task_ids = sorted({
        int(t.get("task_id") or t.get("parallel_id"))
        for t in tasks
        if t.get("task_id") or t.get("parallel_id")
    })

    task_names = sorted({
        t.get("task_name")
        for t in tasks
        if t.get("task_name")
    })

    steps = sorted({
        t.get("current_stage")
        for t in tasks
        if t.get("current_stage")
    })

    projects = sorted({
        t.get("project")
        for t in tasks
        if t.get("project")
    })

    # ==========================================================
    # TEMPLATE
    # ==========================================================

    template_name = session.get(
        "dashboard_template"
    )

    return render_template(

        template_name,

        login_emp_code=session["emp_code"],
        login_name=login_person_name,

        name=login_person_name,

        # hod_can_create_task=hod_can_create_task,
        can_create_task=can_create_task,

        tasks=tasks,

        steps=steps,
        projects=projects,

        task_ids=task_ids,
        task_names=task_names,

        pending_count=pending_count,

        STEP_UI_CONFIG_fms_new_format=STEP_UI_CONFIG_fms_new_format,

        # NORMAL ALLOCATION
        ALLOCATION_MAP_fms_new_format=ALLOCATION_MAP_fms_new_format,

        TASK_FIELDS_fms_new_format=TASK_FIELDS_fms_new_format,

        # DEPARTMENT HEAD
        auto_department_head=login_person_name,
        auto_department_head_emp_code=auto_department_head_emp_code,

    )

# @app.route("/get_task_details_fms_new_format/<int:task_id>")
# def get_task_details_fms_new_format(task_id):
#
#     if "emp_code" not in session:
#         return jsonify({"error": "Unauthorized"}), 403
#
#     try:
#         cur = _dict_cur_fms_new_format()
#
#         cur.execute("""
#             SELECT
#                 task_id,
#                 task_name,
#                 current_stage,
#                 from_stage,
#                 project,
#                 planned_end_time,
#                 task_remarks,
#                 contractor_category,
#                 contractor_type,
#                 contractor_name,
#                 contractor_mobile,
#                 contractor_email,
#                 billing_name,
#                 deals_in,
#
#                 registered_address,
#                 permanent_address_nri,
#                 billing_address,
#
#                 sales_contact_name,
#                 sales_contact_mobile,
#                 sales_contact_email,
#
#                 operation_contact_name,
#                 operation_contact_mobile,
#                 operation_contact_email,
#
#                 accounts_contact_name,
#                 accounts_contact_mobile,
#                 accounts_contact_email,
#
#                 referred_by,
#
#                 pan_ref,
#                 pan_number,
#                 pan_attachment_path,
#
#                 tan_no,
#
#                 msme_ref,
#                 msme_number,
#
#                 gst_ref,
#                 gst_no,
#                 gst_attachment_path,
#                 msme_attachment_path,
#                 attachment_path,
#                 remark,
#
#                 pf_registration_no,
#                 esic_registration_no,
#
#                 bank_name,
#                 branch_name,
#                 account_name,
#                 account_type,
#                 account_number,
#                 ifsc_code,
#                 swift_code,
#
#                 cancelled_cheque_or_passbook_attachment
#
#             FROM fms_new_format_2026.tasks
#
#             WHERE task_id = %s
#
#         """, (task_id,))
#
#         task = cur.fetchone()
#
#         cur.close()
#
#         if not task:
#             return jsonify({
#                 "success": False,
#                 "message": "Task not found"
#             })
#
#         # DATETIME FORMAT
#         if task.get("planned_end_time"):
#             task["planned_end_time"] = (
#                 task["planned_end_time"]
#                 .strftime("%d/%m/%Y %H:%M")
#             )
#
#         return jsonify({
#             "success": True,
#             "task": task
#         })
#
#     except Exception as e:
#
#         print("ERROR IN VIEW MODAL:", str(e))
#
#         return jsonify({
#             "success": False,
#             "message": str(e)
#         }), 500

@app.route("/get_task_details_fms_new_format/<int:task_id>")
def get_task_details_fms_new_format(task_id):

    if "emp_code" not in session:
        return jsonify({"error": "Unauthorized"}), 403

    try:
        cur = _dict_cur_fms_new_format()

        # ==========================================================
        # BUILD VIEW COLUMNS FROM TASK FIELD DICTIONARY
        # ==========================================================

        view_columns = [
            field["db_column"]
            for field in TASK_FIELDS_fms_new_format.values()
            if field.get("view")
        ]

        # Remove duplicate database columns
        view_columns = list(dict.fromkeys(view_columns))

        # Build SQL column list
        select_columns = ", ".join(
            f"`{column}`"
            for column in view_columns
        )

        cur.execute(
            f"""
                SELECT
                    {select_columns}

                FROM fms_new_format_2026.tasks

                WHERE task_id = %s
            """,
            (task_id,)
        )

        task = cur.fetchone()

        cur.close()

        if not task:
            return jsonify({
                "success": False,
                "message": "Task not found"
            })

        return jsonify({
            "success": True,
            "task": task
        })

    except Exception as e:

        print("ERROR IN VIEW MODAL:", str(e))

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500

# ---------- export_excel ----------
@app.route("/export_excel_fms_new_format")
def export_excel_fms_new_format():
    pass

def fetch_all_tasks_for_dashboard_fms_new_format():
    # ✅ Load user roles
    user_access_fms_new_format()

    roles = normalize_roles_fms_new_format(session.get("roles", []))
    emp_code = session.get("emp_code")

    cur = _dict_cur_fms_new_format()
    tasks = []

    # ==========================================================
    # FETCH ALL PENDING TASKS
    # ==========================================================

    query = """
        SELECT
            t.task_id,
            t.task_name,
            t.current_stage,
            t.from_stage,
            t.status,
            t.remark,
            t.attachment_path,
            t.tg_attachment_path,
            t.last_attachment_step,
            t.planned_end_time,
            t.emp_code,
            t.created_at,
            t.allocate_to,
            t.allocate_emp_code,
            t.created_emp_code,
            t.project,
            t.task_details,
            t.`1st_planned_end_time`,
            t.pc_update_stage,
            t.submit_id,
            t.emp_name,
            t.actual_emp_code,
            t.actual_emp_name,
            t.hod_emp_code,
            t.hod_name,
            t.task_created_by,
            t.task_remarks,
            t.submit_time,
            t.fms_name

        FROM fms_new_format_2026.tasks t

        WHERE t.status = 'Pending'

        ORDER BY t.task_id ASC
    """

    cur.execute(query)

    rows = cur.fetchall()
    cur.close()

    # ==========================================================
    # VISIBILITY LOGIC
    # ==========================================================

    for r in rows:

        stage = (r.get("current_stage") or "").strip().upper()

        if (
            # User has the role for this stage
            stage in roles

            # Creator visibility
            or (
                stage in CREATOR_VISIBLE_STEPS_fms_new_format
                and r.get("created_emp_code") == emp_code
            )

            # Allocation visibility
            or (
                stage in ALLOCATION_VISIBLE_STEPS_fms_new_format
                and r.get("allocate_emp_code") == emp_code
            )

            # Actual employee visibility
            or (
                stage in ACTUAL_VISIBLE_STEPS_fms_new_format
                and r.get("actual_emp_code") == emp_code
            )
        ):
            tasks.append(r)

    return tasks

@app.route("/create_task_fms_new_format", methods=["POST"])
def create_task_fms_new_format():

    if "emp_code" not in session:
        return redirect(url_for("login"))

    cur = _dict_cur_fms_new_format()

    emp_code = session["emp_code"]
    emp_name = session.get("username", "")

    # ==========================================================
    # BASIC FORM DATA
    # ==========================================================

    # 1. TASK NAME - NON MANDATORY
    task_name = request.form.get("task_name", "").strip()

    # 2. REMARKS - NON MANDATORY
    task_remarks = request.form.get("task_remarks", "").strip()

    # ==========================================================
    # 3. ATTACHMENT - MANDATORY
    # ==========================================================

    file = request.files.get("attachment")

    if not file or not file.filename:
        cur.close()

        flash(
            "Attachment is required.",
            "danger"
        )

        return redirect(
            url_for("dashboard_fms_new_format")
        )

    filename = secure_filename(file.filename)

    if not filename:
        cur.close()

        flash(
            "Invalid attachment.",
            "danger"
        )

        return redirect(
            url_for("dashboard_fms_new_format")
        )

    # ==========================================================
    # FILE UPLOAD
    # ==========================================================

    upload_dir = app.config["UPLOAD_FOLDER"]

    os.makedirs(
        upload_dir,
        exist_ok=True
    )

    # ----------------------------------------------------------
    # Add timestamp to filename
    # ----------------------------------------------------------

    name, ext = os.path.splitext(filename)

    unique_filename = (
        f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        f"_attachment"
        f"{ext}"
    )

    file_path = os.path.join(
        upload_dir,
        unique_filename
    )

    file.save(file_path)

    # ==========================================================
    # WORKFLOW
    # ==========================================================

    project = "Alcove"

    task_data = {
        "current_stage": "P0",
        "project": project,
        "created_emp_code": emp_code,
        "allocate_emp_code": None,
        "allocate_to": None,
    }

    now = datetime.now()

    # ----------------------------------------------------------
    # FIND FIRST WORKFLOW STEP
    # ----------------------------------------------------------

    next_stage, planned_end_time, _ = (
        get_next_step_and_time_fms_new_format(
            task_data,
            WORKFLOW_MAIN_fms_new_format,
            now
        )
    )

    if not next_stage:

        cur.close()

        flash(
            "Unable to determine next workflow stage.",
            "danger"
        )

        return redirect(
            url_for("dashboard_fms_new_format")
        )

    # ----------------------------------------------------------
    # STEP DATA
    # ----------------------------------------------------------

    step_data = get_step_data_fms_new_format(
        next_stage,
        task_data
    )

    # ==========================================================
    # INSERT TASK
    # ==========================================================

    cur.execute("""
        INSERT INTO fms_new_format_2026.tasks (

            task_name,

            current_stage,
            from_stage,
            status,

            attachment_path,
            tg_attachment_path,
            last_attachment_step,

            planned_end_time,
            `1st_planned_end_time`,

            emp_code,
            emp_name,
            created_emp_code,
            created_at,
            submit_time,

            task_created_by,

            project,
            task_details,

            actual_emp_code,
            actual_emp_name,

            hod_emp_code,
            hod_name,

            task_remarks,

            fms_name
        )

        VALUES (

            %s,

            %s,
            %s,
            %s,

            %s,
            %s,
            %s,

            %s,
            %s,

            %s,
            %s,
            %s,
            NOW(),
            NOW(),

            %s,

            %s,
            %s,

            %s,
            %s,

            %s,
            %s,

            %s,

            %s
        )

    """, (

        # ======================================================
        # TASK NAME
        # ======================================================

        task_name,

        # ======================================================
        # WORKFLOW
        # ======================================================

        next_stage,
        "New",
        "Pending",

        # ======================================================
        # ATTACHMENT
        # ======================================================

        unique_filename,
        unique_filename,
        "P0",

        # ======================================================
        # PLANNED TIME
        # ======================================================

        planned_end_time,
        planned_end_time,

        # ======================================================
        # EMPLOYEE
        # ======================================================

        emp_code,
        emp_name,
        emp_code,

        # created_at -> NOW()
        # submit_time -> NOW()

        # ======================================================
        # TASK CREATED BY
        # ======================================================

        emp_code,

        # ======================================================
        # PROJECT
        # ======================================================

        project,
        step_data.get("task_details"),

        # ======================================================
        # ACTUAL EMPLOYEE
        # ======================================================

        step_data.get("actual_emp_code"),
        step_data.get("actual_emp_name"),

        # ======================================================
        # HOD
        # ======================================================

        step_data.get("hod_emp_code"),
        step_data.get("hod_name"),

        # ======================================================
        # REMARKS
        # ======================================================

        task_remarks,

        # ======================================================
        # FMS NAME
        # ======================================================

        "NEW_FMS_FORMAT"
    ))

    # ==========================================================
    # TASK ID
    # ==========================================================

    task_id = cur.lastrowid

    # ==========================================================
    # TASK NAME FALLBACK
    # ==========================================================

    # If user entered Task Name:
    #     Keep entered Task Name
    #
    # If user left Task Name blank:
    #     VENDOR-{task_id}

    if not task_name:

        task_name = f"VENDOR-{task_id}"

        cur.execute("""
            UPDATE fms_new_format_2026.tasks

            SET task_name = %s

            WHERE task_id = %s

        """, (
            task_name,
            task_id
        ))

    # ==========================================================
    # COMMIT
    # ==========================================================

    mysql.connection.commit()

    cur.close()

    # ==========================================================
    # SUCCESS MESSAGE
    # ==========================================================

    flash(
        f"Task {task_name} Created Successfully",
        "success"
    )

    # ==========================================================
    # REDIRECT
    # ==========================================================

    return redirect(
        url_for("dashboard_fms_new_format")
    )

def get_next_working_day_fms_new_format(dt, location):
    holidays = get_holidays_by_location_fms_new_format(location)

    next_day = dt

    while next_day.weekday() == 6 or next_day.date() in holidays:
        next_day += timedelta(days=1)

    return next_day

@app.route("/complete_task_fms_new_format/<int:task_id>", methods=["POST"])
def complete_task_fms_new_format(task_id):

    if "emp_code" not in session:
        return redirect(url_for("login"))

    # ==========================================================
    # FORM INPUT
    # ==========================================================

    remark = request.form.get("remark", "")
    decision = request.form.get("decision")

    # Normal allocation only
    allocation_name_raw = request.form.get("allocation")

    allocation_code_raw = (
        ALLOCATION_MAP_fms_new_format.get(allocation_name_raw)
        if allocation_name_raw
        else None
    )

    # ==========================================================
    # DATABASE
    # ==========================================================

    cur = _dict_cur_fms_new_format()

    cur.execute("""
        SELECT *
        FROM fms_new_format_2026.tasks
        WHERE task_id = %s
    """, (task_id,))

    task = cur.fetchone()

    if not task:
        cur.close()
        return "Task not found"

    # ==========================================================
    # PREVIOUS ID
    # ==========================================================

    current_stage = (
        task.get("current_stage") or ""
    ).strip().upper()

    rule = PREVIOUS_ID_RULES_fms_new_format.get(current_stage)

    if rule:

        # If rule is a column in tasks table
        if rule in task:
            previous_id = task.get(rule)

        # Otherwise treat rule as fixed employee code
        else:
            previous_id = rule

    else:

        # Default previous ID
        previous_id = task.get("submit_id")

    # ==========================================================
    # LAST SUBMIT TIME
    # ==========================================================

    # IMPORTANT:
    # Get this BEFORE updating the tasks table
    last_submit_time = task.get("submit_time")

    # ==========================================================
    # FILE ATTACHMENT
    # ==========================================================

    file = request.files.get("attachment")

    # Keep old attachment if no new file
    filename = task.get("attachment_path")

    # Keep old attachment stage
    last_attachment_step = task.get("last_attachment_step")

    # New attachment uploaded
    if file and file.filename:

        filename = secure_filename(file.filename)

        file.save(
            os.path.join(
                app.config["UPLOAD_FOLDER"],
                filename
            )
        )

        # Save current stage where attachment was uploaded
        last_attachment_step = task.get("current_stage")

    # ==========================================================
    # NORMAL ALLOCATION
    # ==========================================================

    if allocation_name_raw:

        allocation_name = allocation_name_raw

        allocation_code = (
            ALLOCATION_MAP_fms_new_format.get(
                allocation_name_raw
            )
        )

    else:

        allocation_name = task.get("allocate_to")

        allocation_code = task.get("allocate_emp_code")

    # ==========================================================
    # UPDATE TASK OBJECT
    # ==========================================================

    task["allocate_emp_code"] = allocation_code
    task["allocate_to"] = allocation_name

    # Decision required by workflow
    task["decision"] = decision

    # ==========================================================
    # CURRENT TIME
    # ==========================================================

    now = datetime.now()

    # Current stage planned time
    current_planned_time = task.get("planned_end_time")

    # ==========================================================
    # FIND NEXT STEP
    # ==========================================================

    next_stage, planned_next, is_decision = (
        get_next_step_and_time_fms_new_format(
            task,
            WORKFLOW_MAIN_fms_new_format,
            now
        )
    )

    if not next_stage:

        cur.close()

        return "Workflow error"

    # ==========================================================
    # STATUS
    # ==========================================================

    status = (
        "Completed"
        if next_stage == "Completed"
        else "Pending"
    )

    # ==========================================================
    # NEXT STEP DATA
    # ==========================================================

    step_data = get_step_data_fms_new_format(
        next_stage,
        task
    )

    # ==========================================================
    # UPDATE TASK TABLE
    # ==========================================================

    cur.execute("""
        UPDATE fms_new_format_2026.tasks

        SET
            current_stage = %s,
            from_stage = %s,

            remark = %s,

            attachment_path = %s,
            last_attachment_step = %s,

            planned_end_time = %s,
            `1st_planned_end_time` = %s,

            submit_id = %s,
            status = %s,

            task_details = %s,

            emp_code = %s,

            actual_emp_code = %s,
            actual_emp_name = %s,

            hod_emp_code = %s,
            hod_name = %s,

            allocate_to = %s,
            allocate_emp_code = %s,

            submit_time = %s

        WHERE task_id = %s

    """, (

        next_stage,
        task["current_stage"],

        remark,

        filename,
        last_attachment_step,

        planned_next,
        planned_next,

        session["emp_code"],
        status,

        step_data.get("task_details"),

        step_data.get("emp_code"),

        step_data.get("actual_emp_code"),
        step_data.get("actual_emp_name"),

        step_data.get("hod_emp_code"),
        step_data.get("hod_name"),

        allocation_name,
        allocation_code,

        now,

        task_id
    ))

    # ==========================================================
    # INSERT TASK UPDATE HISTORY
    # ==========================================================

    cur.execute("""
        INSERT INTO fms_new_format_2026.task_updates
        (
            task_id,
            task_name,
            from_stage,
            to_stage,
            remark,
            attachment_path,
            planned_end_time,
            decision,
            submit_id,
            actual_time,
            project,
            allocate_to,
            allocate_emp_code,
            previous_id,
            last_submit_time
        )

        VALUES (
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s
        )

    """, (

        task_id,

        task["task_name"],

        task["current_stage"],
        next_stage,

        remark,

        filename,

        current_planned_time,

        decision,

        session["emp_code"],

        now,

        task["project"],

        allocation_name_raw,
        allocation_code_raw,

        # ==========================================
        # VALUES FROM OLD TASK RECORD
        # ==========================================

        previous_id,
        last_submit_time
    ))

    # ==========================================================
    # COMMIT
    # ==========================================================

    mysql.connection.commit()

    cur.close()

    # ==========================================================
    # REDIRECT
    # ==========================================================

    return redirect(
        url_for("dashboard_fms_new_format")
    )

@app.route("/bulk_complete_task_fms_new_format", methods=["POST"])
def bulk_complete_task_fms_new_format():
    pass

# =================================================
# Run
# =================================================
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5111)