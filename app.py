from flask import Flask, request, redirect, url_for, render_template, session, send_file, send_from_directory
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from pymongo import MongoClient
import pandas as pd
from bson.objectid import ObjectId
from flask import  flash
import os
import smtplib
from email.message import EmailMessage
from flask_mail import Mail, Message
UPLOAD_FOLDER = "static/profile_pics"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
import random
import json
import re
from datetime import datetime, timedelta
from flask_pymongo import PyMongo
import mysql.connector
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
app = Flask(__name__)
# 2️⃣ THEN INITIALIZE LIMITER
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["100 per hour"]
)

def get_current_role():
    return session.get("impersonate_role") or session.get("role")

def get_current_email():
    return session.get("impersonate_email") or session.get("email")
# ------------------- Helper Functions -------------------
def get_current_user():
    return session.get("user")

def get_db_connection():
    return mysql.connector.connect(
        host='localhost',
        user='root',
        password='@STHA980',
        database='e_learning_platform'
    )

import certifi

try:
    client = MongoClient(
        "mongodb+srv://asthasengar2088_db_user:doDAhNNwDORHXevA@cluster0.kqc1eal.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0",
        tls=True,
        tlsCAFile=certifi.where()
    )
    db = client["e_learning_platform"]
    print("✅ MongoDB Connected Successfully!")
except Exception as e:
    print("❌ MongoDB Connection Failed:", e)
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')

# Create the folder if it doesn’t exist
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])
# after db = client['e_learning_platform']
users_collection        = db['users']
courses_collection      = db['courses']
assignments_collection  = db['assignments']
announcements_collection= db['announcements']
feedback_collection     = db['feedback']
timetable_collection    = db['timetable']
doubts_collection       = db['doubts']
quiz_results_collection = db['quiz_results']
enrollments_collection  = db['enrollments']
progress_collection     = db['progress']
gamification_collection = db['gamification']
deadlines_collection    = db['deadlines']
badges_collection       = db['badges']
attendance_otp_collection=db['attendance_otp']
attendance_sessions=db['attendance_sessions']
attendance_records=db['attendance_records']

app.secret_key = 'your_secret_key_here'

@app.route('/')
def home():
    return redirect(url_for('login'))
@app.route('/signup_selection')
def signup_selection():
    return render_template('signup_selection.html')

app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = "asthasengar2088@gmail.com"
app.config["MAIL_PASSWORD"] = "fmegfxybmsvevgmc"
EMAIL = "asthasengar2088@gmail.com"
EMAIL_PASSWORD = "fmegfxybmsvevgmc"
mail = Mail(app)
def send_otp(email, otp):
    msg = EmailMessage()
    msg["Subject"] = "Your Login OTP"
    msg["From"] = EMAIL
    msg["To"] = email
    msg.set_content(f"Your OTP is {otp}.It is valid for 5 minutes.")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL, EMAIL_PASSWORD)
        smtp.send_message(msg)

def generate_otp():
    return str(random.randint(100000, 999999))
# ---------- EMAIL SECURITY ----------
BLOCKED_DOMAINS = [
    "mailinator.com",
    "tempmail.com",
    "10minutemail.com",
    "guerrillamail.com"
]

def is_valid_email(email):
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return re.match(pattern, email)

def is_disposable_email(email):
    domain = email.split("@")[1]
    return domain in BLOCKED_DOMAINS
# ------------------------ Signup ------------------------
import random
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        role = request.form["role"]
        background = request.form["background"]

        # 🔐 Layer 1: Email format
        if not is_valid_email(email):
            return render_template("signup.html", error="Invalid email format")

        # 🔐 Layer 2: Disposable email block
        if is_disposable_email(email):
            return render_template("signup.html", error="Temporary emails are not allowed")

        # Check if already exists
        if users_collection.find_one({"Email": email}):
            return render_template("signup.html", error="Email already registered")

        # 🔐 OTP creation
        otp = generate_otp()
        otp_expiry = datetime.utcnow() + timedelta(minutes=5)

        users_collection.insert_one({
            "Name": name,
            "Email": email,
            "Password": generate_password_hash(password),
            "Role": role,
            "Background": background,
            "is_verified": False,
            "otp": otp,
            "otp_expiry": otp_expiry,
            "otp_sent_at": datetime.utcnow(),
            # ✅ Dashboard Default Values
            "level": 1,
            "xp": 0,
            "xp_needed": 100,
            "streak_days": 0,
            "badges": [],
            "deadlines": [],
            "quizzes_taken": 0,
            "avg_score": 0
        })

        send_otp(email, otp)

        session["verify_email"] = email
        return redirect(url_for("verify_otp"))

    return render_template("signup.html")
# ------------------------ Verify OTP ------------------------
@app.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():
    email = session.get("verify_email")

    if not email:
        return redirect(url_for("login"))

    user = users_collection.find_one({"Email": email})

    if request.method == "POST":
        entered_otp = request.form["otp"]

        if datetime.utcnow() > user["otp_expiry"]:
            return render_template("verify_otp.html", error="OTP expired")

        if entered_otp == user["otp"]:
            users_collection.update_one(
                {"Email": email},
                {"$set": {"is_verified": True}, "$unset": {"otp": "", "otp_expiry": ""}}
            )
            session.pop("verify_email")
            return redirect(url_for("login"))

        return render_template("verify_otp.html", error="Invalid OTP")

    return render_template("verify_otp.html")
@app.route("/resend-otp")
def resend_otp():
    email = session.get("verify_email")
    user = users_collection.find_one({"Email": email})

    if datetime.utcnow() - user["otp_sent_at"] < timedelta(seconds=60):
        return "Wait before requesting OTP again"

    otp = generate_otp()
    users_collection.update_one(
        {"Email": email},
        {"$set": {
            "otp": otp,
            "otp_expiry": datetime.utcnow() + timedelta(minutes=5),
            "otp_sent_at": datetime.utcnow()
        }}
    )

    send_otp(email, otp)
    return "OTP resent successfully"
# ------------------------ Login (Unified for All Roles) ------------------------
@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():
    if request.method == 'POST':
        email = request.form['username'].strip().lower()
        password = request.form['password']
        role_input = request.form['role'].strip().lower()

        # 1. Find user by email ONLY
        user = users_collection.find_one({'Email': email})

        # 2. Check if user exists and password is correct
        if user and check_password_hash(user["Password"], password):
            
            # 3. Check if the role matches (case-insensitive)
            if user["Role"].lower() != role_input:
                return render_template('login.html', error="Incorrect role selected")

            # 4. Handle unverified users
            if not user.get("is_verified", False):
                otp = generate_otp()
                users_collection.update_one(
                    {"Email": email},
                    {"$set": {
                        "otp": otp,
                        "otp_expiry": datetime.utcnow() + timedelta(minutes=5),
                        "otp_sent_at": datetime.utcnow()
                    }}
                )
                send_otp(email, otp)
                session["verify_email"] = email
                return redirect(url_for("verify_otp"))
            
            # 5. Success! Log them in
            session['user'] = user['Name']
            session['email'] = user['Email']
            session['role'] = user['Role'].lower()
            
            # Redirect logic...
            if session['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif session['role'] == 'student':
                return redirect(url_for('student_dashboard'))
            elif session['role'] == 'instructor':
                return redirect(url_for('instructor_dashboard'))

        return render_template('login.html', error="Invalid email or password")

    return render_template('login.html')
# ------------------------ Forgot Password ------------------------
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        user = users_collection.find_one({"Email": email})

        if not user:
            return render_template('forgot_password.html', error="Email not found")

        # FIX: Generate the OTP and pass it to the function
        otp = generate_otp()
        otp_expiry = datetime.utcnow() + timedelta(minutes=5)
        
        users_collection.update_one(
            {"Email": email},
            {"$set": {"otp": otp, "otp_expiry": otp_expiry}}
        )
        
        send_otp(email, otp) # Added the 'otp' argument here
        session["reset_email"] = email
        return redirect(url_for("reset_password"))

    return render_template('forgot_password.html')

@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    email = session.get("reset_email")
    if not email:
        return redirect(url_for("login"))

    user = users_collection.find_one({"Email": email})

    if request.method == 'POST':
        otp = request.form['otp']
        new_password = request.form['password']

        if user["otp"] == otp and user["otp_expiry"] > datetime.utcnow():
            users_collection.update_one(
                {"Email": email},
                {"$set": {
                    "Password": generate_password_hash(new_password),
                    "otp": None,
                    "otp_expiry": None
                }}
            )
            session.pop("reset_email")
            return redirect(url_for("login"))

        return render_template("reset_password.html", error="Invalid OTP")

    return render_template("reset_password.html")
# ------------------------ Logout ------------------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))
# ------------------------ Student Dashboard ------------------------
@app.route('/student_dashboard')
def student_dashboard():
    role = get_current_role()
    email = get_current_email()

    if role != 'student':
        return render_template('access_denied.html')

    # -------- Fetch user document --------
    user = users_collection.find_one({"Email": email})

    if not user:
        return redirect(url_for('login'))

    # -------- Quiz Progress (Already Dynamic) --------
    user_quizzes = list(quiz_results_collection.find({'Email': email}))

    quizzes_taken = len(user_quizzes)
    avg_score = sum(q['Percentage'] for q in user_quizzes) / quizzes_taken if quizzes_taken > 0 else 0
    percent_complete = min(avg_score, 100)

    progress = {
        "quizzes_taken": quizzes_taken,
        "avg_score": round(avg_score, 2),
        "percent_complete": round(percent_complete, 2)
    }

    # -------- Gamification (FROM DATABASE) --------
    xp = user.get("xp", 0)
    xp_needed = user.get("xp_needed", 100)

    gamification = {
        "level": user.get("level", 1),
        "xp": xp,
        "xp_needed": xp_needed,
        "percent_to_next_level": int((xp / xp_needed) * 100) if xp_needed > 0 else 0,
        "streak_days": user.get("streak_days", 0)
    }

    # -------- Deadlines (FROM DATABASE) --------
    deadlines = user.get("deadlines", [])

    # -------- Badges (FROM DATABASE) --------
    badges = user.get("badges", [])

    # -------- Live Session (Optional - Can Keep Static) --------
    live_session = db["live_sessions"].find_one({}, {"_id": 0}) or {}

    # -------- Downloads (Optional - Can Keep Static) --------
    downloads = list(db["resources"].find({}, {"_id": 0}))

    return render_template("student_dashboard.html",
                           user=session.get('user'),
                           deadlines=deadlines,
                           progress=progress,
                           gamification=gamification,
                           badges=badges,
                           live_session=live_session,
                           downloads=downloads)
# ------------------------ Admin Dashboard ------------------------
@app.route('/access_dashboard/<email>')
def access_dashboard(email):
    user = users_collection.find_one({"Email": email})

    if not user:
        flash("User not found!", "danger")
        return redirect(url_for('manage_users'))

    # Store session details temporarily
    session['user'] = user['Name']
    session['email'] = user['Email']
    session['role'] = user['Role']
    session['background'] = user.get('Background', 'Non-IT')

    # Redirect based on role
    role = user['Role'].lower()

    if role == 'student':
        return redirect(url_for('student_dashboard'))
    elif role == 'instructor':
        return redirect(url_for('instructor_dashboard'))
    elif role == 'admin':
        return redirect(url_for('admin_dashboard'))
    else:
        flash("Invalid role for this user!", "warning")
        return redirect(url_for('manage_users'))
@app.route('/quiz', methods=['GET', 'POST'])
def quiz():
    role = session.get('role')

    # If POST (submit), only student can submit quiz
    if request.method == 'POST':
        if role != 'student':
            return render_template("access_denied.html")

        quiz_file = 'quiz_questions.json'
        email = get_current_email()
        name = session.get('user')
        background = session.get('background', 'Non-IT')

        with open(quiz_file, 'r') as f:
            questions = json.load(f)
        question_set = questions['IT'] if background == 'IT' else questions['Non-IT']

        data = request.form
        correct = sum(1 for i, q in enumerate(question_set[:10]) if data.get(f'q{i}') == q['answer'])
        total = len(question_set[:10])
        percentage = (correct / total) * 100
        level = "Beginner" if percentage < 50 else "Intermediate" if percentage < 80 else "Advanced"

        quiz_results_collection.insert_one({
            "Name": name,
            "Email": email,
            "Background": background,
            "Score": correct,
            "Total": total,
            "Percentage": percentage,
            "Level": level,
            "DateTime": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })

        return render_template('result.html', level=level, score=correct, total=total, background=background)

    # GET request (view questions)
    if role not in ['student', 'admin']:
        return redirect(url_for('login'))

    quiz_file = 'quiz_questions.json'
    background = session.get('background', 'Non-IT')

    with open(quiz_file, 'r') as f:
        questions = json.load(f)
    question_set = questions['IT'] if background == 'IT' else questions['Non-IT']

    random.shuffle(question_set)
    return render_template('quiz.html', questions=question_set[:10], background=background, role=role)
@app.route('/quiz_history')
def quiz_history():
    role = session.get('role')

    if role == 'student':
        email = get_current_email()
        records = list(quiz_results_collection.find({'Email': email}).sort('DateTime', -1))

    elif role == 'admin':
        # Admin sees all quiz history
        records = list(quiz_results_collection.find().sort('DateTime', -1))

    else:
        return redirect(url_for('login'))

    return render_template('quiz_history.html', records=records, role=role)
# ------------------------ Admin View User Dashboard ------------------------
# The route that starts impersonation (Example: /admin/open_dashboard/student@email.com)
@app.route("/admin/open_dashboard/<email>")
def admin_open_dashboard(email):
    # ... logic to check admin role ...
    
    # 1. Fetch the target user
    target_user = users_collection.find_one({"Email": email})
    
    # 2. Set the impersonation session variables
    session['impersonate_role'] = session['role'] # Admin
    session['impersonate_email'] = session['email'] # Admin email
    
    # 3. Overwrite the main session with the target user's details
    session['role'] = target_user['Role']
    session['email'] = target_user['Email']
    session['user'] = target_user['Name']
    
    # 4. Redirect to the standard, role-specific dashboard
    if target_user['Role'].lower() == 'student':
        return redirect(url_for('student_dashboard'))
    elif target_user['Role'].lower() == 'instructor':
        return redirect(url_for('instructor_dashboard'))
    # ... handle other roles ...
# ------------------------ Admin View User Dashboard ------------------------
@app.route("/admin/view_user_dashboard/<email>")
def admin_view_user_dashboard(email):
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    # Fetch user by email
    user = users_collection.find_one({"Email": email})
    if not user:
        return "User not found."

    # --------- Load student dashboard data ---------

    # Deadlines (example or empty if none)
    deadlines = [
        {"name": "Assignment 1", "due": "2025-12-20", "status": "Pending"},
        {"name": "Project Report", "due": "2025-12-25", "status": "Pending"}
    ]

    # Timetable
    timetable = list(timetable_collection.find({"student_email": user["Email"]}))

    # Progress (if no record found → use defaults)
    progress = progress_collection.find_one({"email": user["Email"]}) or {
        "quizzes_taken": 0,
        "avg_score": 0,
        "percent_complete": 0
    }

    # Gamification (fallback defaults)
    gamification = gamification_collection.find_one({"email": user["Email"]}) or {
        "level": 1,
        "xp": 0,
        "xp_needed": 100,
        "percent_to_next_level": 0,
        "streak_days": 0
    }

    # Badges (if none, return empty list)
    badges = list(badges_collection.find({"email": user["Email"]}))

    # ---------- Render Student Dashboard for Admin ----------
    return render_template(
        "student_dashboard.html",
        user=user,
        deadlines=deadlines,
        progress=progress,
        timetable=timetable,
        gamification=gamification,
        badges=badges,
        impersonate=True   # <--- Very important!
    )
@app.route("/admin/view_student_profile/<email>")
def admin_view_student_profile(email):
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    student = users_collection.find_one({"Email": email, "Role": "student"})
    if not student:
        return "Student not found."

    return render_template("admin_view_student_profile.html", student=student)
@app.route("/admin/view_instructor_profile/<email>")
def admin_view_instructor_profile(email):
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    instructor = users_collection.find_one({"Email": email, "Role": "instructor"})
    if not instructor:
        return "Instructor not found."

    return render_template("admin_view_instructor_profile.html", instructor=instructor)
# ------------------------ Profile ------------------------
@app.route("/profile/<email>")
def profile_page(email):

    # get target user
    user = users_collection.find_one({"Email": email})
    if not user:
        return "User not found", 404

    current_role = session.get("role")
    current_email = session.get("email")

    # Check permissions
    is_admin = (current_role == "admin")
    is_owner = (current_email == email)    # student or instructor viewing own profile

    # send dynamic data
    data = {
        "is_admin": is_admin,
        "is_owner": is_owner,
        "user": user
    }

    return render_template("profile.html", **data)
'''@app.route('/profile', methods=['GET', 'POST'])
def profile():

    # ✅ Allow both admin & student
    if 'email' not in session or session.get('role') not in ['student', 'admin']:
        return redirect(url_for('login'))

    # ✅ If ADMIN is viewing someone else's profile
    viewed_email = request.args.get('email')  # admin passes ?email=student@mail.com

    if session.get('role') == 'admin' and viewed_email:
        email = viewed_email
    else:
        email = session.get('email')

    user = users_collection.find_one({'Email': email})

    if not user:
        return redirect(url_for('login'))

    # ✅ Only student can UPDATE their own profile
    if request.method == 'POST' and session.get('role') == 'student':

        users_collection.update_one(
            {'Email': email},
            {'$set': {
                'Name': request.form.get('name'),
                'Password': request.form.get('password') or user.get('Password'),
                'Background': request.form.get('background'),
                'Phone': request.form.get('phone'),
                'Gender': request.form.get('gender'),
                'Bio': request.form.get('bio')
            }}
        )

        session['user'] = request.form.get('name')
        session['background'] = request.form.get('background')

        return redirect(url_for('profile'))

    return render_template('profile.html', user=user)'''

# ------------------- Helper: normalize email -------------------
def _norm_email(e):
    return e.strip().lower() if e else e

# ------------------- Route: logged-in user's profile -------------------
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    # require login
    if 'email' not in session:
        flash("Please login.", "danger")
        return redirect(url_for('login'))

    current_email = _norm_email(session.get('email'))
    # fetch latest from DB
    user = users_collection.find_one({'Email': current_email})
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for('login'))

    if request.method == 'POST':
        # fields from form
        name = request.form.get('name', user.get('Name'))
        password = request.form.get('password', '').strip()
        background = request.form.get('background', user.get('Background'))
        phone = request.form.get('phone', user.get('Phone'))
        bio = request.form.get('bio', user.get('Bio'))

        # if password blank => keep old
        if not password:
            password = user.get('Password', '')

        update = {
            "Name": name,
            "Password": password,
            "Background": background,
            "Phone": phone,
            "Bio": bio
        }
        users_collection.update_one({'Email': current_email}, {'$set': update})
        # update session name/background
        session['user'] = name
        session['background'] = background
        return redirect(url_for('profile'))

    # GET -> render profile page for current user
    return render_template('profile.html', user=user, admin_view=False)

# ------------------- Route: Admin view/edit another user's profile -------------------
@app.route('/admin/view_profile/<email>', methods=['GET', 'POST'])
def admin_view_profile(email):
    # only admin allowed
    if session.get('role') != 'admin':
        flash("Access denied.", "danger")
        return redirect(url_for('login'))

    email = _norm_email(email)
    user = users_collection.find_one({'Email': email})
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for('manage_users'))

    if request.method == 'POST':
        # admin editing target user
        name = request.form.get('name', user.get('Name'))
        role = request.form.get('role', user.get('Role'))
        password = request.form.get('password', '').strip()
        background = request.form.get('background', user.get('Background'))
        phone = request.form.get('phone', user.get('Phone'))
        bio = request.form.get('bio', user.get('Bio'))

        if not password:
            password = user.get('Password', '')

        updated = {
            "Name": name,
            "Role": role,
            "Password": password,
            "Background": background,
            "Phone": phone,
            "Bio": bio
        }
        users_collection.update_one({'Email': email}, {'$set': updated})
        flash("User profile updated by admin.", "success")
        return redirect(url_for('admin_view_profile', email=email))

    # GET -> render profile page with admin_view True
    return render_template('profile.html', user=user, admin_view=True)

@app.route('/student/attendance', methods=['GET', 'POST'])
def mark_attendance():
    if request.method == 'POST':
        entered_otp = request.form.get("otp")

        # 🔍 Check OTP in DB
        otp_data = otp_collection.find_one({"otp": entered_otp})

        if not otp_data:
            return render_template("mark_attendance.html", error="❌ Invalid OTP")

        # ⏱️ Check expiry
        if datetime.utcnow() > otp_data["expires_at"]:
            return render_template("mark_attendance.html", error="❌ OTP Expired")

        # ✅ Mark attendance
        attendance_collection.insert_one({
            "student": session.get("user"),
            "subject": otp_data["subject"],
            "teacher": otp_data["teacher"],
            "date": datetime.utcnow()
        })

        return render_template("mark_attendance.html", success="✅ Attendance marked!")

    return render_template("mark_attendance.html")

# FIXED: Moved to top level and separated from previous function
@app.route("/admin/attendance")
def admin_attendance_view():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    records = list(attendance_records.find())

    return render_template("admin_attendance_view.html", records=records)
# ------------------- Route: Admin deletes a user -------------------
@app.route('/admin/delete_user/<email>', methods=['POST'])
def admin_delete_user(email):
    if session.get('role') != 'admin':
        flash("Access denied.", "danger")
        return redirect(url_for('login'))

    email = _norm_email(email)
    users_collection.delete_one({'Email': email})
    flash("User deleted.", "info")
    return redirect(url_for('manage_users'))

# ------------------------ Instructor Dashboard ------------------------
@app.route('/instructor_dashboard')
def instructor_dashboard():
    if session.get('role') not in ['instructor', 'admin']:
        return render_template("access_denied.html")

    # Fetch courses from MongoDB
    courses = list(db.courses.find({}))
    total_courses = len(courses)

    # Fetch doubts from MongoDB
    doubts_count = db.doubts.count_documents({})

    # Read recent activities (optional)
    recent_activity = read_recent_activities() if os.path.exists("activity.log") else []

    return render_template(
        'instructor_dashboard.html',
        courses=courses,
        total=total_courses,
        username=session.get('user'),
        role=session.get('role'),
        doubts_count=doubts_count,
        recent_activity=recent_activity
    )

# ------------------------ Create Course ------------------------
@app.route('/create_course', methods=['GET', 'POST'])
def create_course():
    if session.get('role') != 'instructor':
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')

        db.courses.insert_one({
            'title': title,
            'description': description,
            'instructor': session.get('user'),
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })

        log_activity(f"Instructor {session.get('user')} created course: {title}")
        return redirect(url_for('instructor_dashboard'))

    return render_template('create_course.html')
# ------------------------ Export Enrollments ------------------------
@app.route('/export_enrollments')
def export_enrollments():
    if session.get('role') != 'instructor':
        return "Access Denied", 403

    # Fetch enrollments from MongoDB
    enrollments = list(db.enrollments.find({}, {'_id': 0}))  # Exclude MongoDB _id
    if not enrollments:
        return "No enrollments found.", 404

    # Convert to DataFrame and export to Excel temporarily
    df = pd.DataFrame(enrollments)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'enrollments_export.xlsx')
    df.to_excel(file_path, index=False)

    return send_file(file_path, as_attachment=True)

# ------------------------ View Course ------------------------
@app.route('/view_course/<course_title>')
def view_course(course_title):
    if session.get('role') != 'instructor':
        return "Access Denied", 403

    # Find the course by title in MongoDB
    course = db.courses.find_one({'title': course_title}, {'_id': 0})
    if not course:
        return "Course not found.", 404

    # Fetch enrollments for this course (optional)
    enrollments = list(db.enrollments.find({'course_title': course_title}, {'_id': 0}))

    return render_template('view_course.html', course=course, enrollments=enrollments)
# ✅ Route to serve uploaded files
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
# ------------------------ Update Course ------------------------
@app.route('/update_course/<course_title>', methods=['GET', 'POST'])
def update_course(course_title):
    if session.get('role') != 'instructor':
        return "Access Denied", 403

    # Find the course in MongoDB
    course = db.courses.find_one({'title': course_title})
    if not course:
        return "Course not found.", 404

    if request.method == 'POST':
        new_title = request.form.get('title').strip()
        new_description = request.form.get('description').strip()

        # Update course in MongoDB
        db.courses.update_one(
            {'title': course_title},
            {'$set': {'title': new_title, 'description': new_description}}
        )

        log_activity(f"Instructor {session.get('user')} updated course: {new_title}")
        return redirect(url_for('instructor_dashboard'))

    return render_template('update_course.html', course=course)
# ------------------------ Delete Course ------------------------
@app.route('/delete_course/<course_title>', methods=['POST'])
def delete_course(course_title):
    if session.get('role') != 'instructor':
        return "Access Denied", 403
    

    result = db.courses.delete_one({'title': course_title})

    if result.deleted_count == 0:
        return "Course not found.", 404

    log_activity(f"Instructor {session.get('user')} deleted course: {course_title}")
    return redirect(url_for('instructor_dashboard'))
# ------------------------ Enroll Student ------------------------
@app.route('/enroll_student', methods=['POST'])
def enroll_student():
    if session.get('role') != 'student':
        return "Access Denied", 403

    course_title = request.form.get('course_title')
    student_name = session.get('user')
    student_email = get_current_email()

    # Check if course exists
    course = db.courses.find_one({'title': course_title})
    if not course:
        return "Course not found.", 404

    # Prevent duplicate enrollment
    existing = db.enrollments.find_one({
        'course_title': course_title,
        'student_email': student_email
    })
    if existing:
        return "You are already enrolled in this course.", 400

    # Insert enrollment record
    enrollment = {
        'course_title': course_title,
        'student_name': student_name,
        'student_email': student_email,
        'enrolled_on': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    db.enrollments.insert_one(enrollment)

    log_activity(f"Student {student_name} enrolled in course: {course_title}")
    return redirect(url_for('student_dashboard'))


# ------------------------ Manage Students ------------------------
@app.route('/manage_students')
def manage_students():
    if session.get('role') != 'instructor':
        return "Access Denied", 403

    # Fetch all students from MongoDB
    students = list(db.users.find({'role': 'student'}, {'_id': 0, 'username': 1, 'email': 1}))

    # Fetch all enrollments
    enrollments = list(db.enrollments.find({}, {'_id': 0}))

    return render_template('manage_students.html', students=students, enrollments=enrollments)


# ------------------------ View Analytics ------------------------
@app.route('/view_analytics')
def view_analytics():
    if session.get('role') != 'instructor':
        return "Access Denied", 403

    total_students = db.users.count_documents({'role': 'student'})
    total_courses = db.courses.count_documents({})
    total_enrollments = db.enrollments.count_documents({})
    total_quizzes = db.quiz_results.count_documents({})

    analytics = {
        'total_students': total_students,
        'total_courses': total_courses,
        'total_enrollments': total_enrollments,
        'total_quizzes': total_quizzes
    }

    return render_template('view_analytics.html', analytics=analytics)

#######################################################################################
#AYUSH DASBOARD FEATURES
# ------------------------ Enrollments ------------------------
@app.route('/my_enrollments')
def my_enrollments():
    if session.get('role') != 'student':
        return redirect(url_for('login'))
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'enrollments.xlsx')
    email = get_current_email()
    records = []
    if os.path.exists(file_path):
        df = pd.read_excel(file_path)
        df['Email'] = df['Email'].str.lower().str.strip()
        student_courses = df[df['Email'] == email]
        records = student_courses.to_dict(orient='records')
    return render_template('enrollments.html', records=records)

# ------------------------ My Level ------------------------
@app.route('/my_level')
def my_level():
    if session.get('role') != 'student':
        return redirect(url_for('login'))
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'quiz_results.xlsx')
    email = get_current_email()
    level = None
    if os.path.exists(file_path):
        df = pd.read_excel(file_path)
        df['Email'] = df['Email'].str.lower().str.strip()
        student_data = df[df['Email'] == email]
        if not student_data.empty:
            latest = student_data.sort_values(by="DateTime", ascending=False).iloc[0]
            level = latest.get("Level")
    return render_template("my_level.html", level=level)
###########################################################################################
# ------------------------ Skill Suggestions ------------------------
@app.route('/skill_suggestions')
def skill_suggestions():
    if session.get('role') != 'student':
        return redirect(url_for('login'))

    email = get_current_email().lower().strip()
    suggestions = []

    user_quizzes = list(mongo.db.quiz_results.find({"email": email}).sort("DateTime", -1))

    if user_quizzes:
        latest = user_quizzes[0]
        level = latest.get('Level', 'Beginner')

        if level == 'Beginner':
            suggestions = ['Learn Python Basics', 'Practice Logical Thinking']
        elif level == 'Intermediate':
            suggestions = ['Learn Flask', 'Work on Real-World Projects']
        elif level == 'Advanced':
            suggestions = ['Explore Machine Learning', 'Contribute to Open Source']

    return render_template('skill_suggestions.html', suggestions=suggestions)
# ------------------------ View Assignments ------------------------
@app.route('/view_assignments')
def view_assignments():
    if session.get('role') != 'student':
        return redirect(url_for('login'))

    # Fetch assignments from MongoDB and sort by Deadline (latest first)
    assignments = list(db.assignments.find().sort("Deadline", -1))

    return render_template('manage_assignments.html', assignments=assignments)


# ------------------------ View Announcements (STUDENT) ------------------------
@app.route('/view_announcements')
def view_announcements():
    if session.get('role') != 'student':
        return redirect(url_for('login'))

    # Fetch announcements sorted by latest first
    announcements = list(announcements_collection.find().sort("created_at", -1))

    # Convert datetime to readable format
    for a in announcements:
        created_at = a.get("created_at")

        if isinstance(created_at, datetime):
            a["created_at"] = created_at.strftime("%d %b %Y, %I:%M %p")
        else:
            a["created_at"] = "N/A"

    return render_template('view_announcements.html', announcements=announcements)

# ------------------------ Download Assignment File ------------------------
@app.route('/download_assignment/<filename>')
def download_assignment(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)

    return "File not found", 404
# ------------------------ Ask a Doubt ------------------------
@app.route('/ask_doubt', methods=['GET', 'POST'])
def ask_doubt():
    user=session.get('user')
    role = get_current_role()
    email = get_current_email()

    if role != 'student':
        return render_template('access_denied.html')

    if request.method == 'POST':
        doubt = request.form.get('doubt')

        doubt_record = {
            "Name": user,
            "Email": email,
            "Doubt": doubt,
            "Timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        db.doubts.insert_one(doubt_record)

        return render_template('ask_doubt.html', message="✅ Your doubt has been submitted successfully!")
    
    return render_template('ask_doubt.html')
# ------------------------ Feedback ------------------------
@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    user=session.get('user')
    role = get_current_role()
    email = get_current_email()
    

    # Only students can access feedback page
    if role != 'student':
        return render_template('access_denied.html')

    if request.method == 'POST':
        rating = request.form.get('rating')
        comments = request.form.get('comments')

        record = {
            "Name": user,
            "Email": email,
            "Rating": rating,
            "Comments": comments,
            "DateTime": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        feedback_collection.insert_one(record)

        flash("Thank you! Your feedback has been submitted.", "success")
        return redirect(url_for('student_dashboard'))

    return render_template('feedback.html')
# ------------------------ Student Assignments ------------------------
@app.route("/student/assignments")
def student_assignments():
    if "email" not in session or session.get("role") != "student":
        return redirect(url_for("login"))

    assignments = list(assignments_collection.find())

    return render_template("student_assignments.html", assignments=assignments)
@app.route('/student/assignments/submit/<assignment_id>', methods=['POST'])
def submit_assignment(assignment_id):
    assignment = assignments_collection.find_one({"_id": ObjectId(assignment_id)})
    # handle submission
    return redirect(url_for('student_assignments'))
# ------------------------ Leaderboard ------------------------
@app.route('/leaderboard')
def leaderboard():
    role = get_current_role()
    email = get_current_email()
    
    if role != 'student':
        return render_template('access_denied.html')

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'quiz_results.xlsx')
    leaderboard_data = []
    your_rank = None
    top_three = []

    if os.path.exists(file_path):
        df = pd.read_excel(file_path)
        df['Email'] = df['Email'].str.lower().str.strip()

        grouped = df.groupby('Email').agg({
            'Name': 'first',
            'Score': 'sum',
            'Total': 'sum'
        }).reset_index()

        grouped['Percentage'] = (grouped['Score'] / grouped['Total']) * 100
        leaderboard_data = grouped.sort_values(by='Percentage', ascending=False).to_dict(orient='records')

        top_three = leaderboard_data[:3]

        # Find user rank
        for index, student in enumerate(leaderboard_data, start=1):
            if student['Email'] == email:
                your_rank = index
                break

    return render_template(
        'leaderboard.html',
        leaderboard=leaderboard_data,
        your_rank=your_rank,
        top_three=top_three,
        current_user_email=email
    )
# -------------------- ADMIN DASHBOARD --------------------
@app.route('/admin_dashboard')
def admin_dashboard():
    role = session['role']  # NEW

    if role != "admin":  # NEW CHECK
        flash("Access Denied", "danger")
        return redirect(url_for('login'))

    # Ensure user exists in session
    if 'user' not in session:   # NEW FIX
        session['user'] = {"Name": "Admin"}

    stats = {
        "total_users": users_collection.count_documents({}),
        "total_courses": courses_collection.count_documents({}),
        "total_assignments": assignments_collection.count_documents({}),
        "total_announcements": announcements_collection.count_documents({})
    }

    recent_users = list(users_collection.find().sort('_id', -1).limit(5))
    recent_courses = list(courses_collection.find().sort('_id', -1).limit(5))

    return render_template(
        'admin_dashboard.html',
        user=session['user'],
        stats=stats,
        recent_users=recent_users,
        recent_courses=recent_courses
    )
# -------------------- ROUTE: Manage Users + Search --------------------
@app.route("/manage_users", methods=["GET"])
def manage_users():
    if session.get("role") != "admin":
        return render_template("access_denied.html")

    search_query = request.args.get("search", "").strip()
    role_filter = request.args.get("role", "").strip()

    query = {}

    # Search by email only
    if search_query:
        query["Email"] = {"$regex": search_query, "$options": "i"}

    # Filter by Role
    if role_filter and role_filter != "all":
        query["Role"] = role_filter

    users = list(users_collection.find(query))
    return render_template("manage_users.html", users=users, search_query=search_query, role_filter=role_filter)
# ---------------------- STUDENT: Browse Courses ----------------------
@app.route("/browse_courses")
def browse_courses():
    if "email" not in session or session.get("role") != "student":
        return redirect(url_for("login"))

    # Fetch all courses
    all_courses = list(courses_collection.find())

    # Fetch courses the student is enrolled in
    enrolled = enrollments_collection.find({"email": session["email"]})
    enrolled_ids = [str(e["course_id"]) for e in enrolled]

    return render_template("browse_courses.html",
                           courses=all_courses,
                           enrolled_ids=enrolled_ids)
# ---------------------- Enroll in Course ----------------------
@app.route("/enroll/<course_id>")
def enroll(course_id):
    if "email" not in session or session.get("role") != "student":
        return redirect(url_for("login"))

    # Prevent duplicate enrollment
    exists = enrollments_collection.find_one({
        "email": session["email"],
        "course_id": ObjectId(course_id)
    })

    if exists:
        return redirect(url_for("browse_courses"))

    enrollments_collection.insert_one({
        "email": session["email"],
        "course_id": ObjectId(course_id)
    })

    return redirect(url_for("browse_courses"))
# -------------------- ADMIN OPEN DASHBOARD --------------------
'''@app.route('/admin_open_dashboard/<user_id>')
def admin_open_dashboard(user_id):
    if session.get('role') != 'admin':
        return render_template('access_denied.html')

    user = users_collection.find_one({"_id": ObjectId(user_id)})

    if not user:
        return "User not found"

    # Set impersonation session
    session['impersonate_email'] = user['Email']
    session['impersonate_role'] = user['Role']

    # Redirect to the correct dashboard
    if user['Role'] == "student":
        return redirect(url_for("student_dashboard"))
    elif user['Role'] == "instructor":
        return redirect(url_for("instructor_dashboard"))
    else:
        return redirect(url_for("admin_dashboard"))'''
# -------------------- STOP IMPERSONATION --------------------
@app.route('/stop_impersonate')
def stop_impersonate():
    session.pop('impersonate_email', None)
    session.pop('impersonate_role', None)
    return redirect(url_for('admin_dashboard'))
# -------------------- ADD, EDIT, DELETE USERS --------------------
@app.route('/add_user', methods=['GET', 'POST'])
def add_user():
    # Only admin can add users
    if session.get('role') != 'admin':
        return render_template('access_denied.html')

    if request.method == 'POST':
        new_user = {
            "Name": request.form['Name'],
            "Email": request.form['Email'],
            "Password": request.form['Password'],
            "Role": request.form['Role'],
            "Background": request.form.get('Background', 'Non-IT')  # default
        }

        users_collection.insert_one(new_user)
        flash("✅ User added successfully!", "success")
        return redirect(url_for('manage_users'))

    return render_template('add_edit_user.html', action="Add", user={})


@app.route('/edit_user/<user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    # Only admin can edit users
    if session.get('role') != 'admin':
        return render_template('access_denied.html')

    user = users_collection.find_one({"_id": ObjectId(user_id)})

    if request.method == 'POST':
        updated_data = {
            "Name": request.form['Name'],
            "Email": request.form['Email'],
            "Password": request.form['Password'],
            "Role": request.form['Role'],
            "Background": request.form.get('Background', 'Non-IT')
        }

        users_collection.update_one({"_id": ObjectId(user_id)}, {"$set": updated_data})

        flash("✅ User updated successfully!", "success")
        return redirect(url_for('manage_users'))

    return render_template('add_edit_user.html', action="Edit", user=user)


@app.route('/delete_user/<user_id>')
def delete_user(user_id):
    # Only admin can delete
    if session.get('role') != 'admin':
        return render_template('access_denied.html')

    user_to_delete = users_collection.find_one({"_id": ObjectId(user_id)})

    # Prevent deleting own admin account
    if user_to_delete and user_to_delete['Email'] == session.get('email'):
        flash("⚠ You cannot delete your own admin account!", "danger")
        return redirect(url_for('manage_users'))

    users_collection.delete_one({"_id": ObjectId(user_id)})
    flash("🗑 User deleted successfully!", "info")

    return redirect(url_for('manage_users'))
# -------------------- IMPERSONATED STUDENT DASHBOARD --------------------
@app.route('/imp_student_dashboard')
def imp_student_dashboard():
    if get_current_role() != "admin":
        return render_template("access_denied.html")

    email = session.get("impersonate_email")
    if not email:
        return "No user selected"

    # Load quiz results using impersonated email
    user_quizzes = list(quiz_results_collection.find({'Email': email}))

    quizzes_taken = len(user_quizzes)
    avg_score = sum(q['Percentage'] for q in user_quizzes) / quizzes_taken if quizzes_taken > 0 else 0

    progress = {
        "quizzes_taken": quizzes_taken,
        "avg_score": round(avg_score, 2),
        "percent_complete": round(min(avg_score, 100), 2)
    }

    deadlines = [
        {"name": "Assignment 1", "due": "2025-07-10", "status": "Pending"},
        {"name": "Quiz 2", "due": "2025-07-15", "status": "Upcoming"}
    ]

    gamification = {
        "level": 5,
        "xp": 150,
        "xp_needed": 200,
        "percent_to_next_level": int((150 / 200) * 100),
        "streak_days": 3
    }

    badges = [{"name": "First Quiz"}, {"name": "80% Club"}]

    live_session = {
        "title": "Python Live Doubt Session",
        "link": "https://meet.google.com/xyz-live-link",
        "time": "July 10, 2025 - 6:00 PM"
    }

    downloads = [
        {"title": "Python Notes", "file": "/static/resources/python_notes.pdf"},
        {"title": "Quiz Prep Material", "file": "/static/resources/quiz_prep.pdf"},
        {"title": "Assignment Samples", "file": "/static/resources/assignment_sample.pdf"}
    ]

    return render_template("student_dashboard.html",
                           user=email + " (Admin View)",
                           deadlines=deadlines,
                           progress=progress,
                           gamification=gamification,
                           badges=badges,
                           live_session=live_session,
                           downloads=downloads)
# -------------------- MANAGE COURSES --------------------
@app.route('/manage_courses')
def manage_courses():
    if session.get('role') not in ['admin']:
        return render_template('access_denied.html')

    courses = list(courses_collection.find())
    return render_template('manage_courses.html', courses=courses)


@app.route('/add_course', methods=['GET', 'POST'])
def add_course():
    if session.get('role') not in ['admin']:
        return render_template('access_denied.html')

    if request.method == 'POST':
        new_course = {
            "CourseName": request.form['CourseName'],
            "Instructor": request.form['Instructor'],
            "Duration": request.form['Duration'],
            "Description": request.form['Description']
        }

        courses_collection.insert_one(new_course)
        flash("✅ Course added successfully!", "success")
        return redirect(url_for('manage_courses'))

    return render_template('add_edit_course.html', action="Add", course={})


@app.route('/edit_course/<id>', methods=['GET', 'POST'])
def edit_course(id):
    if session.get('role') not in ['admin']:
        return render_template('access_denied.html')

    course = courses_collection.find_one({"_id": ObjectId(id)})

    if request.method == 'POST':
        updated_data = {
            "CourseName": request.form['CourseName'],
            "Instructor": request.form['Instructor'],
            "Duration": request.form['Duration'],
            "Description": request.form['Description']
        }

        courses_collection.update_one(
            {"_id": ObjectId(id)},
            {"$set": updated_data}
        )

        flash("✏ Course updated successfully!", "success")
        return redirect(url_for('manage_courses'))

    return render_template('add_edit_course.html', action="Edit", course=course)


@app.route('/delete_course/<id>')
def delete_course_route(id):
    if session.get('role') not in ['admin']:
        return render_template('access_denied.html')

    courses_collection.delete_one({"_id": ObjectId(id)})
    flash("🗑 Course deleted successfully!", "info")

    return redirect(url_for('manage_courses'))
@app.template_filter('timeago')
def timeago(value):
    if not value:
        return ""
    if isinstance(value, str):
        try:
            value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
        except:
            return value

    now = datetime.now()
    diff = now - value

    if diff.total_seconds() < 60:
        return "Just now"
    elif diff.total_seconds() < 3600:
        minutes = int(diff.total_seconds() / 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif diff.total_seconds() < 86400:
        hours = int(diff.total_seconds() / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif diff.days == 1:
        return "Yesterday"
    elif diff.days < 7:
        return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
    else:
        return value.strftime('%d %b %Y, %I:%M %p')
# -------------------- ROUTE: View + Post Announcements --------------------
@app.route("/announcements", methods=["GET", "POST"])
def announcements():
    if session.get("role") not in ['admin']:
        return redirect(url_for("login"))

    if request.method == "POST":
        message = request.form["message"].strip()
        if message:
            announcements_collection.insert_one({
                "message": message,
                "created_at": datetime.utcnow()
            })
            flash("✅ Announcement posted successfully!", "success")
        else:
            flash("⚠ Message cannot be empty.", "danger")
        return redirect(url_for("announcements"))

    announcements_list = list(announcements_collection.find().sort("created_at", -1))

    for a in announcements_list:
        dt = a.get("created_at")
        if isinstance(dt, datetime):
            a["created_at"] = dt.strftime("%d %b %Y, %I:%M %p")
        else:
            a["created_at"] = "N/A"

    return render_template("announcements.html", announcements=announcements_list)
# -------------------- Delete Announcement --------------------
@app.route("/announcements/delete/<id>")
def delete_announcement(id):
    if session.get("role") not in ['admin']:
        return redirect(url_for("login"))

    announcements_collection.delete_one({"_id": ObjectId(id)})
    flash("🗑 Announcement deleted successfully!", "success")
    return redirect(url_for("announcements"))
# -------------------- Edit Announcement --------------------
@app.route("/announcements/edit/<id>", methods=["GET", "POST"])
def edit_announcement(id):
    if session.get("role") not in ['admin']:
        return redirect(url_for("login"))

    announcement = announcements_collection.find_one({"_id": ObjectId(id)})
    if not announcement:
        flash("Announcement not found!", "danger")
        return redirect(url_for("announcements"))

    if request.method == "POST":
        new_message = request.form["message"].strip()
        if new_message:
            announcements_collection.update_one(
                {"_id": ObjectId(id)},
                {"$set": {"message": new_message}}
            )
            flash("✏ Announcement updated successfully!", "success")
        else:
            flash("⚠ Message cannot be empty.", "danger")

        return redirect(url_for("announcements"))

    return render_template("edit_announcement.html", announcement=announcement)
# ---------- FEEDBACK MANAGEMENT (ADMIN) ----------
@app.route('/manage_feedback')
def manage_feedback():
    if session.get('role') not in ['admin']:
        return render_template('access_denied.html')

    feedbacks = list(feedback_collection.find().sort('DateTime', -1))

    for f in feedbacks:
        dt = f.get('DateTime')
        if isinstance(dt, datetime):
            f['DateTime_str'] = dt.strftime('%Y-%m-%d %H:%M')
        else:
            f['DateTime_str'] = dt or "N/A"

    return render_template('manage_feedback.html', feedbacks=feedbacks)
# ---------- TIMETABLE (ADMIN) ----------
@app.route('/manage_timetable', methods=['GET', 'POST'])
def manage_timetable():
    if session.get('role') != 'admin':
        return render_template('access_denied.html')

    if request.method == 'POST':
        rec = {
            'course_name': request.form['course_name'],
            'instructor_name': request.form['instructor_name'],
            'day_of_week': request.form['day_of_week'],
            'start_time': request.form['start_time'],
            'end_time': request.form['end_time'],
            'location': request.form.get('location','')
        }
        timetable_collection.insert_one(rec)
        flash("Timetable entry added.", "success")
        return redirect(url_for('manage_timetable'))

    entries = list(timetable_collection.find().sort('day_of_week', 1))
    return render_template('manage_timetable.html', entries=entries)

@app.route('/delete_timetable/<id>')
def delete_timetable(id):
    if session.get('role') != 'admin':
        return render_template('access_denied.html')
    timetable_collection.delete_one({'_id': ObjectId(id)})
    flash("Timetable entry deleted.", "danger")
    return redirect(url_for('manage_timetable'))
# ---------- DOUBTS / QUERIES ----------
@app.route('/manage_doubts')
def manage_doubts():
    if session.get('role') != 'admin':
        return render_template('access_denied.html')
    doubts = list(doubts_collection.find().sort('Timestamp', -1))
    for d in doubts:
        if isinstance(d.get('Timestamp'), datetime):
            d['Timestamp_str'] = d['Timestamp'].strftime('%Y-%m-%d %H:%M')
    return render_template('manage_doubts.html', doubts=doubts)
@app.route('/assign_doubt/<id>', methods=['POST'])
def assign_doubt(id):
    if session.get('role') != 'admin':
        return render_template('access_denied.html')
    instructor = request.form.get('instructor')
    doubts_collection.update_one({'_id': ObjectId(id)}, {'$set': {'assigned_to': instructor, 'status': 'assigned'}})
    flash("Doubt assigned.", "info")
    return redirect(url_for('manage_doubts'))
@app.route('/resolve_doubt/<id>')
def resolve_doubt(id):
    if session.get('role') != 'admin':
        return render_template('access_denied.html')
    doubts_collection.update_one({'_id': ObjectId(id)}, {'$set': {'status': 'resolved'}})
    flash("Doubt marked resolved.", "success")
    return redirect(url_for('manage_doubts'))
# ----------------------- ASSIGNMENTS (ADMIN) -------------------------
@app.route("/admin/manage_assignments", methods=["GET", "POST"])
def admin_manage_assignments():
    if "role" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

    if request.method == "POST":
        course = request.form["course"].strip()
        title = request.form["title"].strip()
        due_date = request.form["due_date"].strip()
        description = request.form["description"].strip()

        if course and title:
            assignments_collection.insert_one({
                "course": course,
                "title": title,
                "due_date": due_date,
                "description": description,
                "created_at": datetime.utcnow()
            })
            flash("Assignment added successfully!", "success")
        else:
            flash("Course and title are required.", "danger")

        return redirect(url_for("admin_manage_assignments"))

    assignments = list(assignments_collection.find().sort("created_at", -1))

    # FIXED: convert only for display, NOT overwrite in database
    for a in assignments:
        created_at_value = a.get("created_at")
        if isinstance(created_at_value, datetime):
            a["created_at_str"] = created_at_value.strftime("%Y-%m-%d %H:%M")
        else:
            a["created_at_str"] = created_at_value  # string already

    return render_template("admin_manage_assignments.html", assignments=assignments)
# ---------- QUIZ RESULTS (ADMIN view + export) ----------
@app.route('/admin_quiz_results')
def admin_quiz_results():
    if session.get('role') != 'admin':
        return render_template('access_denied.html')
    q = list(quiz_results_collection.find().sort('DateTime', -1))
    for r in q:
        if isinstance(r.get('DateTime'), datetime):
            r['DateTime_str'] = r['DateTime'].strftime('%Y-%m-%d %H:%M')
    return render_template('quiz_results_admin.html', records=q)
@app.route('/export_quiz_results_csv')
def export_quiz_results_csv():
    if session.get('role') != 'admin':
        return render_template('access_denied.html')

    cursor = quiz_results_collection.find().sort('DateTime', -1)
    si = BytesIO()
    cw = csv.writer(si)
    cw.writerow(['Name','Email','Background','Score','Total','Percentage','Level','DateTime'])
    for r in cursor:
        dt = r.get('DateTime')
        dtstr = dt.strftime('%Y-%m-%d %H:%M') if isinstance(dt, datetime) else str(dt)
        cw.writerow([r.get('Name',''), r.get('Email',''), r.get('Background',''),
                     r.get('Score',''), r.get('Total',''), r.get('Percentage',''), r.get('Level',''), dtstr])
    si.seek(0)
    return send_file(si, mimetype='text/csv', as_attachment=True, download_name='quiz_results.csv')
# -------------------- SWITCH DASHBOARD --------------------
@app.route('/switch_dashboard/<role>')
def switch_dashboard(role):
    session['role'] = role
    if role == 'student':
        return redirect(url_for('student_dashboard'))
    elif role == 'instructor':
        return redirect(url_for('instructor_dashboard'))
    else:
        return redirect(url_for('admin_dashboard'))
# Dummy routes for student/instructor
@app.route('/student_dashboard_v2')
def student_dashboard_v2():
    return "<h2>Student Dashboard</h2>"

@app.route('/instructor_dashboard_v2')
def instructor_dashboard_v2():
    return "<h2>Instructor Dashboard</h2>"
'''#----------------------Performance Analytics-----------------------
@app.route('/admin_analytics')
def admin_analytics():
    if session.get('role') != 'admin':
        return render_template('access_denied.html')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Example: total students and instructors
    cursor.execute("SELECT COUNT(*) AS total_students FROM students")
    total_students = cursor.fetchone()['total_students']

    cursor.execute("SELECT COUNT(*) AS total_instructors FROM instructors")
    total_instructors = cursor.fetchone()['total_instructors']

    # Example: average quiz performance
    cursor.execute("SELECT AVG(percentage) AS avg_score FROM quiz_results")
    avg_score = cursor.fetchone()['avg_score'] or 0

    # Example: top performing students
    cursor.execute("""
        SELECT name, percentage FROM quiz_results
        ORDER BY percentage DESC LIMIT 5
    """)
    top_students = cursor.fetchall()

    conn.close()

    return render_template('admin_analytics.html',
                           total_students=total_students,
                           total_instructors=total_instructors,
                           avg_score=round(avg_score, 2),
                           top_students=top_students)
'''
# -------------------------------- Run App -----------------------------
if __name__ == '__main__':
   #app.run(debug=True)
    app.run(host='0.0.0.0',port=5000,debug=True)
