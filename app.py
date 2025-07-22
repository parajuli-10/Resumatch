import json
from flask import Flask, request, render_template, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
import os
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import io
from PyPDF2 import PdfReader
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from flask import send_from_directory


app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = 'your_secret_key_here'


app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///itcapstone.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Define where uploaded files will be stored and JSON file paths
UPLOAD_FOLDER = 'uploads'
MATCHES_FILE = 'matches.json'
JOBS_FILE = 'jobs.json'

# Ensure the uploads directory and JSON files exist
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
if not os.path.exists(MATCHES_FILE):
    with open(MATCHES_FILE, "w") as f:
        json.dump([], f)
if not os.path.exists(JOBS_FILE):
    with open(JOBS_FILE, "w") as f:
        json.dump([], f)

# Update app config
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), default='user')
    

with app.app_context():
    db.create_all()

# Routes
@app.route('/')
@app.route('/login', methods=['GET'])
def login_page():
    return render_template('login.html')

@app.route('/register-page', methods=['GET'])
def register_page():
    return render_template('register.html')

@app.route('/employer-login', methods=['GET'])
def employer_login_page():
    return render_template('employer-login.html')

@app.route('/user-dashboard')
def user_dashboard():
    if 'user_id' not in session or session.get('role') != 'user':
        return redirect(url_for('login_page'))

    # Load job descriptions only from current employers
    try:
        with open(JOBS_FILE, 'r') as f:
            all_jobs = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        all_jobs = []

    job_descriptions = [entry['job_description'] for entry in all_jobs]

    # Remove duplicates in case of any
    job_descriptions = list(dict.fromkeys(job_descriptions))

    # Get user's comparison history from session
    comparison_history = session.get('comparison_history', [])

    # Retrieve similarity score (if any) for display, then remove it from session
    similarity_score = session.pop('similarity_score', 0)

    return render_template('user-dashboard.html',
                           job_descriptions=job_descriptions,
                           comparison_history=comparison_history,
                           similarity_score=similarity_score)


@app.route('/employer-dashboard')
def employer_dashboard():
    if 'user_id' not in session or session.get('role') != 'employer':
        return redirect(url_for('employer_login_page'))
    # Load job descriptions uploaded by this employer
    try:
        with open(JOBS_FILE, 'r') as f:
            all_jobs = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        all_jobs = []
    job_descriptions = [entry['job_description'] for entry in all_jobs if entry.get('employer_id') == session['user_id']]
    # Remove duplicates in case of any
    job_descriptions = list(dict.fromkeys(job_descriptions))
    # Prepare matches list and candidate counts for this employer's jobs
    matches = []
    candidate_counts = {}
    try:
        with open(MATCHES_FILE, 'r') as f:
            saved_matches = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        saved_matches = []
    for match in saved_matches:
        if match.get('employer_id') == session['user_id']:
            job_desc = match.get('job_description', 'Unknown Job Description')
            name = match.get('candidate_name', 'Unknown Candidate')
            email = match.get('candidate_email', 'Unknown Email')

            try:
                score_val = float(match.get('score', 0) or 0)
            except ValueError:
                score_val = 0.0
            similarity_val = round(score_val, 2)

            matches.append({
                "job_description": job_desc,
                "candidate_name": name,
                "candidate_email": email,
                "similarity_score": similarity_val
            })
            candidate_counts[job_desc] = candidate_counts.get(job_desc, 0) + 1
    return render_template('employer-dashboard.html',
                           job_descriptions=job_descriptions,
                           matches=matches,
                           candidate_counts=candidate_counts)

@app.route('/register', methods=['POST'])
def register():
    email = request.form.get('email')
    full_name = request.form.get('full_name')
    if not full_name:
        flash("Full Name is required.", "danger")
        return redirect(url_for('register_page'))
    password = request.form.get('password')
    role = request.form.get('role')
    # Check if user already exists
    if User.query.filter_by(email=email).first():
        flash("User already exists.", "danger")
        return redirect(url_for('register_page'))
    # Create new user and save to database
    hashed_password = generate_password_hash(password)
    user = User(email=email, full_name=full_name, password_hash=hashed_password, role=role)
    db.session.add(user)
    db.session.commit()
    flash("Registered successfully! Please log in.", "success")
    return redirect(url_for('login_page'))

@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email')
    password = request.form.get('password')
    user = User.query.filter_by(email=email).first()
    if user and check_password_hash(user.password_hash, password):
        session['user_id'] = user.id
        session['role'] = user.role
        session['user_name'] = user.full_name
        session['user_email'] = user.email
        if user.role == 'employer':
            return redirect(url_for('employer_dashboard'))
        else:
            return redirect(url_for('user_dashboard'))
    flash("Invalid email or password.", "danger")
    return redirect(url_for('login_page'))

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for('login_page'))

@app.route('/upload-job', methods=['POST'])
def upload_job():
    if 'user_id' not in session or session.get('role') != 'employer':
        flash('Please log in first.', 'danger')
        return redirect(url_for('employer_login_page'))
    job_file = request.files.get('job_description')
    if not job_file:
        flash('Please select a job description file.', 'danger')
        return redirect(url_for('employer_dashboard'))
    filename = secure_filename(job_file.filename)
    if not filename.lower().endswith('.pdf'):
        flash('Only PDF files are allowed.', 'danger')
        return redirect(url_for('employer_dashboard'))
    # Ensure uploads folder exists
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    job_file.save(file_path)
    # Record this job upload in jobs.json with employer association
    try:
        with open(JOBS_FILE, 'r') as f:
            jobs_list = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        jobs_list = []
    job_entry = {
        "job_description": filename,
        "employer_id": session['user_id'],
        "date": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    }
    # Avoid duplicate job entries
    if not any(j.get('job_description') == filename and j.get('employer_id') == session['user_id'] for j in jobs_list):
        jobs_list.append(job_entry)
        with open(JOBS_FILE, 'w') as f:
            json.dump(jobs_list, f, indent=4)
    flash(f"Job Description '{filename}' uploaded successfully!", 'success')
    return redirect(url_for('employer_dashboard'))

@app.route('/upload-resume', methods=['POST'])
def upload_resume():
    if 'user_id' not in session:
        flash('Please log in first.', 'danger')
        return redirect(url_for('login_page'))
    user = User.query.get(session['user_id'])
    resume_file = request.files.get('resume')
    selected_jd = request.form.get('job_description_choice')
    uploaded_jd = request.files.get('job_description')
    if not resume_file:
        flash('Please upload a resume file.', 'danger')
        return redirect(url_for('user_dashboard'))
    # Handle job description input (either an existing selection or a new upload)
    if uploaded_jd:
        jd_filename = secure_filename(uploaded_jd.filename)
        if not jd_filename.lower().endswith('.pdf'):
            flash('Only PDF files are allowed.', 'danger')
            return redirect(url_for('user_dashboard'))
        job_desc_path = os.path.join(app.config['UPLOAD_FOLDER'], jd_filename)
        uploaded_jd.save(job_desc_path)
    elif selected_jd:
        job_desc_path = os.path.join(app.config['UPLOAD_FOLDER'], selected_jd)
        if not os.path.exists(job_desc_path):
            flash("Selected job description file doesn't exist.", 'danger')
            return redirect(url_for('user_dashboard'))
    else:
        flash('Please select or upload a job description.', 'danger')
        return redirect(url_for('user_dashboard'))
    # Save the uploaded resume file
    resume_filename = secure_filename(resume_file.filename)
    if not resume_filename.lower().endswith('.pdf'):
        flash('Only PDF files are allowed.', 'danger')
        return redirect(url_for('user_dashboard'))
    resume_path = os.path.join(app.config['UPLOAD_FOLDER'], resume_filename)
    resume_file.save(resume_path)
    # Extract text from resume and job description PDFs
    with open(resume_path, 'rb') as f:
        resume_pdf = PdfReader(f)
        resume_text = " ".join([page.extract_text() or "" for page in resume_pdf.pages])
    with open(job_desc_path, 'rb') as f:
        jd_pdf = PdfReader(f)
        jd_text = " ".join([page.extract_text() or "" for page in jd_pdf.pages])
    # Compute similarity between resume and job description
    vectorizer = TfidfVectorizer(stop_words='english')
    tfidf_matrix = vectorizer.fit_transform([resume_text, jd_text])
    similarity_score = round(float(cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]) * 100, 2)
    # Determine which employer (if any) this job description is associated with
    employer_id = None
    try:
        with open(JOBS_FILE, 'r') as f:
            jobs_list = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        jobs_list = []
    for entry in jobs_list:
        if entry.get('job_description') == os.path.basename(job_desc_path):
            employer_id = entry.get('employer_id')
            break
    # Create match record
    match_data = {
        "candidate_name": user.full_name,
        "candidate_email": user.email,
        "resume": resume_filename,
        "job_description": os.path.basename(job_desc_path),
        "score": similarity_score,
        "date": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
        "employer_id": employer_id
    }
    # Append to user's comparison history in session
    if 'comparison_history' not in session:
        session['comparison_history'] = []
    session['comparison_history'].append(match_data)
    # Save match data to matches.json
    try:
        with open(MATCHES_FILE, 'r') as f:
            matches_list = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        matches_list = []
    matches_list.append(match_data)
    with open(MATCHES_FILE, 'w') as f:
        json.dump(matches_list, f, indent=4)
    # Store similarity_score in session for display on dashboard
    session['similarity_score'] = similarity_score
    flash(f"Resume matched with job description by {similarity_score}%", 'success')
    return redirect(url_for('user_dashboard'))

@app.route('/delete-job/<filename>', methods=['POST'])
def delete_job(filename):
    if 'user_id' not in session or session.get('role') != 'employer':
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('employer_dashboard'))
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(file_path):
        os.remove(file_path)
    # Remove job entry from jobs.json for this employer
    try:
        with open(JOBS_FILE, 'r') as f:
            jobs_list = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        jobs_list = []
    jobs_list = [entry for entry in jobs_list if not (entry.get('job_description') == filename and entry.get('employer_id') == session['user_id'])]
    with open(JOBS_FILE, 'w') as f:
        json.dump(jobs_list, f, indent=4)
    flash(f"Job Description '{filename}' deleted successfully!", 'success')
    return redirect(url_for('employer_dashboard'))

@app.route('/download-job/<filename>')
def download_job(filename):
    """Serve the job description file for download"""
    # Ensure employer is logged in
    if 'user_id' not in session or session.get('role') != 'employer':
        flash('Please log in first.', 'danger')
        return redirect(url_for('employer_login_page'))

    # Verify the requested file belongs to this employer
    try:
        with open(JOBS_FILE, 'r') as f:
            jobs_list = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        jobs_list = []

    job_entry = next(
        (
            job
            for job in jobs_list
            if job.get('job_description') == filename
            and job.get('employer_id') == session['user_id']
        ),
        None,
    )
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not job_entry or not os.path.exists(file_path):
        flash("File not found or you don't have permission to access it.", 'danger')
        return redirect(url_for('employer_dashboard'))

    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)





def extract_text_from_pdf(file):
    pdf_reader = PdfReader(io.BytesIO(file.read()))
    return " ".join([page.extract_text() or "" for page in pdf_reader.pages])

def compute_similarity(text1, text2):
    vectorizer = TfidfVectorizer(stop_words='english')
    tfidf_matrix = vectorizer.fit_transform([text1, text2])
    return cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]

if __name__ == '__main__':
    app.run(debug=True)
