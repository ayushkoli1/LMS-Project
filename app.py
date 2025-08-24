from flask import Flask, request, redirect, url_for, render_template, session, send_file
import pandas as pd
import os
import io
import random
import json
from datetime import datetime
from db import get_db_connection

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

RECENT_ACTIVITY_LOG = 'recent_activity.log'

def log_activity(message: str):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"{timestamp} - {message}\n"
    with open(RECENT_ACTIVITY_LOG, 'a', encoding='utf-8') as f:
        f.write(log_entry)

def read_recent_activities(limit=10):
    if not os.path.exists(RECENT_ACTIVITY_LOG):
        return []
    with open(RECENT_ACTIVITY_LOG, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    return [line.strip() for line in lines[-limit:]]

@app.route('/')
def home():
    return redirect(url_for('login'))

# ------------------------ Signup ------------------------
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email'].strip().lower()
        password = request.form['password']
        role = request.form['role']
        background = request.form['background']

        # CAPTCHA temporarily removed

        new_user = {
            "Name": name, "Email": email, "Password": password,
            "Role": role, "Background": background
        }

        file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'users.xlsx')

        if os.path.exists(file_path):
            df = pd.read_excel(file_path)
            df['Email'] = df['Email'].str.lower().str.strip()
            if email in df['Email'].values:
                return render_template('signup.html', error="Email already registered.")
            df = pd.concat([df, pd.DataFrame([new_user])], ignore_index=True)
        else:
            df = pd.DataFrame([new_user])
        df.to_excel(file_path, index=False)

        return redirect(url_for('login'))

    return render_template('signup.html')

# ------------------------ Login ------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        role = request.form['role'].strip().lower()
        username = request.form['username'].strip().lower()
        password = request.form['password'].strip()

        if role == 'admin':
            try:
                # SAFELY load JSON from correct location
                admin_file_path = os.path.join(os.path.dirname(__file__), 'admin_credentials.json')

                with open(admin_file_path, 'r') as file:
                    admins = json.load(file)

                for admin in admins:
                    if admin['username'].strip().lower() == username and admin['password'].strip() == password:
                        session['user'] = admin.get('name', 'Admin')
                        session['email'] = username
                        session['role'] = 'admin'
                        return redirect(url_for('admin_dashboard'))

                return render_template('login.html', error="Invalid admin credentials.")
            except Exception as e:
                return render_template('login.html', error=f"Error loading admin credentials: {e}")
    
        # ----------- Student / Instructor Login -----------
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'users.xlsx')
        df = pd.read_excel(file_path)
        df['Email'] = df['Email'].str.strip().str.lower()
        df['Password'] = df['Password'].astype(str).str.strip()
        df['Role'] = df['Role'].str.strip().str.lower()

        matched_user = df[
            (df['Email'] == username) &
            (df['Password'] == password) &
            (df['Role'] == role)
        ]

        if not matched_user.empty:
            session['user'] = matched_user.iloc[0]['Name']
            session['email'] = username
            session['role'] = role
            session['background'] = matched_user.iloc[0].get('Background', 'Non-IT')

            if role == 'student':
                quiz_file = os.path.join(app.config['UPLOAD_FOLDER'], 'quiz_results.xlsx')
                if os.path.exists(quiz_file):
                    quiz_df = pd.read_excel(quiz_file)
                    quiz_df['Email'] = quiz_df['Email'].str.strip().str.lower()
                    if username not in quiz_df['Email'].values:
                        return redirect(url_for('quiz'))
                else:
                    return redirect(url_for('quiz'))

                return redirect(url_for('student_dashboard'))

            elif role == 'instructor':
                return redirect(url_for('instructor_dashboard'))

        return render_template('login.html', error="Invalid credentials or role.")

    return render_template('login.html')
# ------------------------ Forgot Password ------------------------
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'users.xlsx')
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        new_password = request.form['new_password'].strip()

        # CAPTCHA temporarily removed

        if os.path.exists(file_path):
            df = pd.read_excel(file_path)
            df['Email'] = df['Email'].str.lower().str.strip()
            if email in df['Email'].values:
                df.loc[df['Email'] == email, 'Password'] = new_password
                df.to_excel(file_path, index=False)
                return redirect(url_for('login'))
            else:
                return render_template('forgot_password.html', error="Email not found.")
        return "User data file not found."

    return render_template('forgot_password.html')

# ------------------------ Logout ------------------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ------------------------ Student Dashboard ------------------------
@app.route('/student_dashboard')
def student_dashboard():
    if session.get('role') not in ['student', 'admin']:
        return render_template('access_denied.html')

    # Fetch timetable data
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM timetable ORDER BY day_of_week, start_time")
    timetable_data = cursor.fetchall()
    conn.close()

    email = session.get('email')
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'quiz_results.xlsx')

    quizzes_taken = 0
    avg_score = 0
    percent_complete = 0

    if os.path.exists(file_path):
        df = pd.read_excel(file_path)
        df['Email'] = df['Email'].str.lower().str.strip()
        student_data = df[df['Email'] == email]

        if not student_data.empty:
            quizzes_taken = len(student_data)
            avg_score = student_data['Percentage'].mean()
            percent_complete = min(avg_score, 100)

    progress = {
        "quizzes_taken": quizzes_taken,
        "avg_score": round(avg_score, 2),
        "percent_complete": round(percent_complete, 2)
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

    badges = [
        {"name": "First Quiz"},
        {"name": "80% Club"}
    ]

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
                           user=session.get('user'),
                           deadlines=deadlines,
                           progress=progress,
                           gamification=gamification,
                           badges=badges,
                           live_session=live_session,
                           downloads=downloads,
                           timetable=timetable_data)

# ------------------------ Quiz ------------------------
@app.route('/quiz', methods=['GET', 'POST'])
def quiz():
    if session.get('role') != 'student':
        return redirect(url_for('login'))

    quiz_file = 'quiz_questions.json'
    result_file = os.path.join(app.config['UPLOAD_FOLDER'], 'quiz_results.xlsx')
    email = session.get('email')
    name = session.get('user')
    background = session.get('background', 'Non-IT')

    if request.method == 'POST':
        data = request.form
        with open(quiz_file, 'r') as f:
            questions = json.load(f)
        question_set = questions['IT'] if background == 'IT' else questions['Non-IT']

        correct = sum(1 for i, q in enumerate(question_set[:10]) if data.get(f'q{i}') == q['answer'])
        total = len(question_set[:10])
        percentage = (correct / total) * 100

        level = "Beginner"
        if percentage >= 80:
            level = "Advanced"
        elif percentage >= 50:
            level = "Intermediate"

        record = {
            "Name": name, "Email": email, "Background": background,
            "Score": int(correct), "Total": int(total), "Percentage": float(percentage),
            "Level": level, "DateTime": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        df = pd.read_excel(result_file) if os.path.exists(result_file) else pd.DataFrame(columns=["Name", "Email", "Background", "Score", "Total", "Percentage", "Level", "DateTime"])
        df = pd.concat([df, pd.DataFrame([record])], ignore_index=True)
        df.to_excel(result_file, index=False)

        return render_template('result.html', level=level, score=correct, total=total, background=background)

    with open(quiz_file, 'r') as f:
        questions = json.load(f)

    selected_questions = questions['IT'] if background == 'IT' else questions['Non-IT']
    random.shuffle(selected_questions)
    return render_template('quiz.html', questions=selected_questions[:10], background=background)

# ------------------------ Quiz History ------------------------
@app.route('/quiz_history')
def quiz_history():
    if session.get('role') != 'student':
        return redirect(url_for('login'))

    result_path = os.path.join(app.config['UPLOAD_FOLDER'], 'quiz_results.xlsx')
    email = session.get('email')

    if os.path.exists(result_path):
        df = pd.read_excel(result_path)
        df = df[df['Email'].str.lower().str.strip() == email]
        df = df.sort_values(by='DateTime', ascending=False)
        return render_template('quiz_history.html', records=df.to_dict(orient='records'))

    return render_template('quiz_history.html', records=[])

# ------------------------ Profile ------------------------
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if session.get('role') != 'student':
        return redirect(url_for('login'))

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'users.xlsx')
    email = session.get('email')

    if os.path.exists(file_path):
        df = pd.read_excel(file_path)
        df['Email'] = df['Email'].str.strip().str.lower()
        user_row = df[df['Email'] == email]

        if user_row.empty:
            return "User not found."

        index = user_row.index[0]
        if request.method == 'POST':
            df.at[index, 'Name'] = request.form['name']
            df.at[index, 'Password'] = request.form['password']
            df.at[index, 'Background'] = request.form['background']
            session['user'] = df.at[index, 'Name']
            session['background'] = df.at[index, 'Background']
            df.to_excel(file_path, index=False)

        return render_template('profile.html', user=df.loc[index].to_dict())

    return "User data file not found."

# ------------------------ Browse Courses ------------------------
@app.route('/courses')
def browse_courses():
    if session.get('role') != 'student':
        return redirect(url_for('login'))

    # Removed pre-made default courses
    # default_courses = [
    #     {"title": "Introduction to Python", "description": "Learn the basics of Python programming"},
    #     {"title": "Web Development with Flask", "description": "Build web apps using Flask"},
    #     {"title": "Database Design", "description": "Master SQL and ER diagrams"}
    # ]

    dynamic_courses = []
    if os.path.exists('courses.xlsx'):
        df = pd.read_excel('courses.xlsx')
        dynamic_courses = df.to_dict(orient='records')

    all_courses = dynamic_courses
    return render_template('courses.html', courses=all_courses)

# ------------------------ Enroll in Course ------------------------
@app.route('/enroll/<course_title>')
def enroll(course_title):
    if session.get('role') != 'student':
        return redirect(url_for('login'))

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'enrollments.xlsx')
    record = {
        "Student": session.get('user'),
        "Email": session.get('email'),
        "Course": course_title,
        "DateTime": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

    df = pd.read_excel(file_path) if os.path.exists(file_path) else pd.DataFrame()
    df = pd.concat([df, pd.DataFrame([record])], ignore_index=True)
    df.to_excel(file_path, index=False)

    return redirect(url_for('browse_courses'))

# ------------------------ Instructor Dashboard ------------------------
@app.route('/instructor_dashboard')
def instructor_dashboard():
    if session.get('role') not in ['instructor', 'admin']:
        return render_template("access_denied.html")

    # Removed pre-made default courses
    # default_courses = [
    #     {"title": "Introduction to Python", "description": "Learn the basics of Python programming"},
    #     {"title": "Web Development with Flask", "description": "Build web apps using Flask"},
    #     {"title": "Database Design", "description": "Master SQL and ER diagrams"}
    # ]

    dynamic_courses = []
    if os.path.exists('courses.xlsx'):
        df = pd.read_excel('courses.xlsx')
        dynamic_courses = df.to_dict(orient='records')

    all_courses = dynamic_courses

    # User info
    username = session.get('user')
    role = session.get('role')
    total_courses = len(all_courses)

    # Doubts count
    doubts_file = os.path.join(app.config['UPLOAD_FOLDER'], 'doubts.xlsx')
    doubts_count = 0
    if os.path.exists(doubts_file):
        df_doubts = pd.read_excel(doubts_file)
        doubts_count = len(df_doubts)

    # Recent activity - read from log file
    recent_activity = read_recent_activities()

    return render_template('instructor_dashboard.html',
                           courses=all_courses,
                           total=total_courses,
                           username=username,
                           role=role,
                           doubts_count=doubts_count,
                           recent_activity=recent_activity)

# ------------------------ Export Enrollments ------------------------
@app.route('/export_enrollments')
def export_enrollments():
    if session.get('role') != 'instructor':
        return "Access Denied", 403

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'enrollments.xlsx')
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    return "Enrollments data file not found.", 404

# ------------------------ View Course ------------------------
@app.route('/view_course/<course_title>')
def view_course(course_title):
    if session.get('role') != 'instructor':
        return "Access Denied", 403

    path = 'courses.xlsx'
    if not os.path.exists(path):
        return "Courses data not found.", 404

    df = pd.read_excel(path)
    course_row = df[df['title'] == course_title]

    if course_row.empty:
        return "Course not found.", 404

    course = course_row.iloc[0].to_dict()
    return render_template('view_course.html', course=course)

# ------------------------ Update Course ------------------------
@app.route('/update_course/<course_title>', methods=['GET', 'POST'])
def update_course(course_title):
    if session.get('role') != 'instructor':
        return "Access Denied", 403

    path = 'courses.xlsx'
    if not os.path.exists(path):
        return "Courses data not found.", 404

    df = pd.read_excel(path)
    course_row = df[df['title'] == course_title]

    if course_row.empty:
        return "Course not found.", 404

    if request.method == 'POST':
        new_title = request.form.get('title')
        new_description = request.form.get('description')

        # Update the course details
        df.loc[df['title'] == course_title, 'title'] = new_title
        df.loc[df['title'] == course_title, 'description'] = new_description
        df.to_excel(path, index=False)

        log_activity(f"Instructor {session.get('user')} updated course: {new_title}")

        return redirect(url_for('instructor_dashboard'))

    course = course_row.iloc[0].to_dict()
    return render_template('update_course.html', course=course)

# ------------------------ Manage Students ------------------------
@app.route('/manage_students')
def manage_students():
    if session.get('role') != 'instructor':
        return "Access Denied", 403

    return render_template('manage_students.html')

# ------------------------ Delete Course ------------------------
@app.route('/delete_course/<course_title>', methods=['POST'])
def delete_course(course_title):
    if session.get('role') != 'instructor':
        return "Access Denied", 403

    path = 'courses.xlsx'
    if not os.path.exists(path):
        return "Courses data not found.", 404

    df = pd.read_excel(path)
    df = df[df['title'] != course_title]
    df.to_excel(path, index=False)

    log_activity(f"Instructor {session.get('user')} deleted course: {course_title}")

    return redirect(url_for('instructor_dashboard'))

# ------------------------ View Analytics ------------------------
@app.route('/view_analytics')
def view_analytics():
    if session.get('role') != 'instructor':
        return "Access Denied", 403

    return render_template('view_analytics.html')

# ------------------------ Quiz Results (Instructor) ------------------------
@app.route('/quiz_results')
def quiz_results():
    if session.get('role') != 'instructor':
        return "Access Denied", 403

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'quiz_results.xlsx')
    records = []
    if os.path.exists(file_path):
        df = pd.read_excel(file_path)
        records = df.to_dict(orient='records')

    return render_template('quiz_results.html', records=records)

# ------------------------ View Doubts (Instructor) ------------------------
@app.route('/view_doubts')
def view_doubts():
    if session.get('role') != 'instructor':
        return "Access Denied", 403

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'doubts.xlsx')
    records = []
    if os.path.exists(file_path):
        df = pd.read_excel(file_path)
        records = df.to_dict(orient='records')

    return render_template('view_doubts.html', records=records)
#---------------------export users-----------------------------------
@app.route('/export_users')
def export_users():
    if session.get('role') != 'instructor':
        return "Access Denied", 403

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'users.xlsx')
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    return "User data file not found.", 404

# ------------------------ Create Course ------------------------
@app.route('/create_course', methods=['GET', 'POST'])
def create_course():
    if session.get('role') != 'instructor':
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        path = 'courses.xlsx'
        df = pd.read_excel(path) if os.path.exists(path) else pd.DataFrame(columns=['title', 'description'])
        df = pd.concat([df, pd.DataFrame([{'title': title, 'description': description}])], ignore_index=True)
        df.to_excel(path, index=False)

        log_activity(f"Instructor {session.get('user')} created course: {title}")

        return redirect(url_for('instructor_dashboard'))

    return render_template('create_course.html')

# ------------------------ Create Quiz ------------------------
@app.route('/create_quiz', methods=['GET', 'POST'])
def create_quiz():
    if session.get('role') != 'instructor':
        return redirect(url_for('login'))

    path = 'courses.xlsx'
    course_titles = []
    if os.path.exists(path):
        df = pd.read_excel(path)
        course_titles = df['title'].tolist()

    if request.method == 'POST':
        subject = request.form.get('subject')
        questions = request.form.getlist('question')
        options = request.form.getlist('option')
        answers = request.form.getlist('answer')

        quiz_data = {
            subject: []
        }

        for i in range(len(questions)):
            quiz_data[subject].append({
                'question': questions[i],
                'options': options[i].split(';'),  # options separated by semicolon
                'answer': answers[i]
            })

        quiz_file = 'quiz_questions.json'
        if os.path.exists(quiz_file):
            with open(quiz_file, 'r') as f:
                existing_data = json.load(f)
        else:
            existing_data = {}

        existing_data.update(quiz_data)

        with open(quiz_file, 'w') as f:
            json.dump(existing_data, f, indent=4)

        log_activity(f"Instructor {session.get('user')} created quiz for subject: {subject}")

        return redirect(url_for('instructor_dashboard'))

    return render_template('create_quiz.html', course_titles=course_titles)
# ------------------------ Enrollments ------------------------
@app.route('/my_enrollments')
def my_enrollments():
    if session.get('role') != 'student':
        return redirect(url_for('login'))
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'enrollments.xlsx')
    email = session.get('email')
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
    email = session.get('email')
    level = None
    if os.path.exists(file_path):
        df = pd.read_excel(file_path)
        df['Email'] = df['Email'].str.lower().str.strip()
        student_data = df[df['Email'] == email]
        if not student_data.empty:
            latest = student_data.sort_values(by="DateTime", ascending=False).iloc[0]
            level = latest.get("Level")
    return render_template("my_level.html", level=level)

# ------------------------ Skill Suggestions ------------------------
@app.route('/skill_suggestions')
def skill_suggestions():
    if session.get('role') != 'student':
        return redirect(url_for('login'))
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'quiz_results.xlsx')
    email = session.get('email')
    suggestions = []
    if os.path.exists(file_path):
        df = pd.read_excel(file_path)
        df['Email'] = df['Email'].str.lower().str.strip()
        user_data = df[df['Email'] == email]
        if not user_data.empty:
            latest = user_data.sort_values(by='DateTime', ascending=False).iloc[0]
            level = latest.get('Level')
            if level == 'Beginner':
                suggestions = ['Learn Python Basics', 'Practice Logical Thinking']
            elif level == 'Intermediate':
                suggestions = ['Learn Flask', 'Work on Projects']
            elif level == 'Advanced':
                suggestions = ['Explore Machine Learning', 'Contribute to Open Source']
    return render_template('skill_suggestions.html', suggestions=suggestions)

# ------------------------ View Assignments ------------------------
@app.route('/view_assignments')
def view_assignments():
    if session.get('role') != 'student':
        return redirect(url_for('login'))
    assignment_file = os.path.join(app.config['UPLOAD_FOLDER'], 'assignments.xlsx')
    assignments = []
    if os.path.exists(assignment_file):
        df = pd.read_excel(assignment_file)
        assignments = df.to_dict(orient='records')
    return render_template('view_assignments.html', assignments=assignments)

# ------------------------ Download Assignment File ------------------------
@app.route('/download_assignment/<filename>')
def download_assignment(filename):
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True)
    return "File not found", 404

# ------------------------ View Announcements ------------------------
@app.route('/view_announcements')
def view_announcements():
    if session.get('role') != 'student':
        return redirect(url_for('login'))
    announcement_file = os.path.join(app.config['UPLOAD_FOLDER'], 'announcements.xlsx')
    announcements = []
    if os.path.exists(announcement_file):
        df = pd.read_excel(announcement_file)
        df = df.sort_values(by='Date', ascending=False)
        announcements = df.to_dict(orient='records')
    return render_template('view_announcements.html', announcements=announcements)
# ------------------------ Ask a Doubt ------------------------
@app.route('/ask_doubt', methods=['GET', 'POST'])
def ask_doubt():
    if session.get('role') != 'student':
        return redirect(url_for('login'))
    if request.method == 'POST':
        doubt = request.form.get('doubt')
        name = session.get('user')
        email = session.get('email')

        # Save doubt to a file (or database)
        doubt_record = {
            'Name': name,
            'Email': email,
            'Doubt': doubt,
            'Timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        doubt_file = os.path.join(app.config['UPLOAD_FOLDER'], 'doubts.xlsx')
        df = pd.read_excel(doubt_file) if os.path.exists(doubt_file) else pd.DataFrame()
        df = pd.concat([df, pd.DataFrame([doubt_record])], ignore_index=True)
        df.to_excel(doubt_file, index=False)

        return render_template('ask_doubt.html', message="Your doubt has been submitted.")
    return render_template('ask_doubt.html')

# ------------------------ Feedback ------------------------
@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    if session.get('role') != 'student':
        return redirect(url_for('login'))

    feedback_file = os.path.join(app.config['UPLOAD_FOLDER'], 'feedback.xlsx')
    email = session.get('email')
    name = session.get('user')

    if request.method == 'POST':
        rating = request.form.get('rating')
        comments = request.form.get('comments')

        record = {
            "Name": name,
            "Email": email,
            "Rating": rating,
            "Comments": comments,
            "DateTime": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        df = pd.read_excel(feedback_file) if os.path.exists(feedback_file) else pd.DataFrame()
        df = pd.concat([df, pd.DataFrame([record])], ignore_index=True)
        df.to_excel(feedback_file, index=False)

        return redirect(url_for('student_dashboard'))

    return render_template('feedback.html')

# ------------------------ Leaderboard ------------------------
@app.route('/leaderboard')
def leaderboard():
    if session.get('role') != 'student':
        return redirect(url_for('login'))

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], 'quiz_results.xlsx')
    leaderboard_data = []

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

    return render_template('leaderboard.html', leaderboard=leaderboard_data)

# ------------------------ Admin Dashboard ------------------------@app.route('/admin_dashboard')
from db import get_db_connection  

@app.route('/admin_dashboard')
def admin_dashboard():
    if session.get('role') != 'admin':
        return render_template('access_denied.html')

    student_data = []
    instructor_data = []
    student_count = 0
    instructor_count = 0

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Fetch students
        cursor.execute("SELECT * FROM students")
        student_data = cursor.fetchall()
        student_count = len(student_data)

        # Fetch instructors
        cursor.execute("SELECT * FROM instructors")
        instructor_data = cursor.fetchall()
        instructor_count = len(instructor_data)

        cursor.close()
        conn.close()

    except Exception as e:
        return f"Database error: {e}"

    # Prepare pie chart data
    total_users = student_count + instructor_count
    student_percentage = round((student_count / total_users) * 100, 2) if total_users else 0
    instructor_percentage = 100 - student_percentage if total_users else 0

    return render_template('admin_dashboard.html',
                           user=session.get('user'),
                           students=student_data,
                           instructors=instructor_data,
                           student_count=student_count,
                           instructor_count=instructor_count,
                           student_percentage=student_percentage,
                           instructor_percentage=instructor_percentage)

#----------------------------TIMETABLE-----------------------------
@app.route('/add_timetable', methods=['GET', 'POST'])
def add_timetable():
    if request.method == 'POST':
        course = request.form['course']
        instructor_id = request.form['instructor_id']
        day = request.form['day']
        start = request.form['start_time']
        end = request.form['end_time']
        location = request.form['location']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO timetable (course_name, instructor_id, day_of_week, start_time, end_time, location)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (course, instructor_id, day, start, end, location))
        conn.commit()
        conn.close()

        return redirect('/admin_dashboard')  # or wherever you show it
    else:
        return render_template('add_timetable.html')
    
#-----------------------addmin assign timetable-----------------------
@app.route('/assign_timetable', methods=['POST'])
def assign_timetable():
    # Get data from form
    course_name = request.form['course_name']
    instructor_name = request.form['instructor_name']
    day_of_week = request.form['day_of_week']
    start_time = request.form['start_time']
    end_time = request.form['end_time']
    location = request.form['location']

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO timetable (course_name, instructor_name, day_of_week, start_time, end_time, location)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (course_name, instructor_name, day_of_week, start_time, end_time, location))
    conn.commit()
    conn.close()

    return redirect(url_for('admin_dashboard'))
#------------------------- Admin View Dashboard ------------------------
@app.route('/admin/view_dashboard', methods=['POST'])
def view_dashboard():
    role = request.form['role']
    email = request.form['email']
    session['admin_preview'] = True
    session['preview_email'] = email
    session['preview_role'] = role

    if role == 'student':
        return redirect('/student_dashboard')
    elif role == 'instructor':
        return redirect('/instructor_dashboard')
# -------------------------------- Run App -----------------------------
if __name__ == '__main__':
   #app.run(debug=True)
    app.run(host='0.0.0.0',port=5000,debug=True)
