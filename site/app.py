from flask import Flask, render_template, request, redirect, url_for, flash
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# -------------------------------
# Temporary in-memory user store
# -------------------------------
users = {}

# -------------------------------
# Upload folder for parent marksheets
# -------------------------------
UPLOAD_FOLDER = "uploads"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# =========================================================
# MAIN ROUTES
# =========================================================
@app.route('/')
def home():
    return render_template('front.html')


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/contact')
def contact():
    return render_template('contact.html')


# =========================================================
# AUTHENTICATION ROUTES (General LMS)
# =========================================================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if email in users and users[email] == password:
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password', 'danger')

    return render_template('login.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if email in users:
            flash('User already exists!', 'danger')
        else:
            users[email] = password
            flash('Signup successful! Please login.', 'success')
            return redirect(url_for('login'))

    return render_template('signup.html')


@app.route('/dashboard')
def dashboard():
    return "<h2>Welcome to your LMS Dashboard</h2>"


# =========================================================
# FEATURES SECTION
# =========================================================
@app.route('/student-login')
def student_login():
    return render_template('student_login.html')


@app.route('/higher-ed')
def higher_ed():
    return render_template('higher_ed.html')


@app.route('/professionals')
def professionals():
    return render_template('professionals.html')


# =========================================================
# FOOTER ROUTES
# =========================================================
@app.route('/beginner-course')
def beginner_course():
    return "<h2>Beginner Course Page</h2>"


@app.route('/intermediate-path')
def intermediate_path():
    return "<h2>Intermediate Path Page</h2>"


@app.route('/advanced-training')
def advanced_training():
    return "<h2>Advanced Training Page</h2>"


@app.route('/master-class')
def master_class():
    return "<h2>Master Class Page</h2>"


@app.route('/study-material')
def study_material():
    return "<h2>Study Material Page</h2>"


@app.route('/video-tutorials')
def video_tutorials():
    return "<h2>Video Tutorials Page</h2>"


@app.route('/practice-quizzes')
def practice_quizzes():
    return "<h2>Practice Quizzes Page</h2>"


@app.route('/community')
def community():
    return "<h2>Community Page</h2>"


@app.route('/help-center')
def help_center():
    return "<h2>Help Center Page</h2>"


@app.route('/privacy-policy')
def privacy_policy():
    return "<h2>Privacy Policy Page</h2>"


@app.route('/terms-of-service')
def terms_of_service():
    return "<h2>Terms of Service Page</h2>"


# =========================================================
# ⭐ PARENT PANEL BACKEND (Added Successfully)
# =========================================================

# Parent login page
@app.route('/parent-login', methods=['GET', 'POST'])
def parent_login():
    if request.method == 'POST':
        parent_email = request.form.get("email")
        parent_pass = request.form.get("password")

        # For demo — hardcoded parent user
        if parent_email == "parent@gmail.com" and parent_pass == "12345":
            return redirect(url_for('parent_dashboard'))
        else:
            flash("Invalid parent login!", "danger")

    return render_template("parent_login.html")


# Parent dashboard
@app.route('/parent-dashboard')
def parent_dashboard():
    return render_template("parent_dashboard.html")


# Parent information page
@app.route('/parent-info')
def parent_info():
    return render_template("parent_info.html")


# Marksheet upload page
@app.route('/upload-marksheet')
def upload_marksheet():
    return render_template("upload_marksheet.html")


# File upload handler
@app.route('/upload-file', methods=['POST'])
def upload_file():
    file = request.files['marksheet']
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], file.filename))
    return "Marksheet uploaded successfully!"


# =========================================================
# Run Server
# =========================================================
if __name__ == '__main__':
    app.run(debug=True)

