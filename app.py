from flask import Flask, render_template, jsonify, request, redirect, url_for, flash, session
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, ValidationError, EqualTo
from database import load_jobs_from_db, load_one_job_from_db, add_application_to_db, add_users_to_db, get_user_from_db, get_user_info_from_db, get_application_info_from_db, had_user_applied, update_user_profile, search_jobs_from_db, update_user_password
from dotenv import load_dotenv
from flask_wtf.csrf import CSRFProtect
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
import bcrypt
import os
import base64
from resume_checker import extract_text_from_file, check_ats_compatibility


load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv('APP_SECRET_KEY')
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 31536000  # 1 year static asset caching
csrf = CSRFProtect(app)


@app.after_request
def add_header(response):
    # Enable aggressive client caching for static files (CSS, JS, images, fonts)
    if request.path.startswith('/static/'):
        response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
    return response


class RegisterForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])

    headline = StringField("Headline")
    linkedin = StringField("Linked in")
    education = StringField("Education")
    experience = StringField("Experience")
    resume = StringField("Resume")
    submit = SubmitField("Register")

    def validate_email(self,field):
        user = get_user_from_db(field.data)
        if user:
            raise ValidationError('Email already taken')


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")


class ForgotPasswordForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    submit = SubmitField("Send Reset Link")


class ResetPasswordForm(FlaskForm):
    password = PasswordField("New Password", validators=[DataRequired()])
    confirm_password = PasswordField(
        "Confirm Password",
        validators=[DataRequired(), EqualTo('password', message="Passwords must match!")]
    )
    submit = SubmitField("Reset Password")


def get_serializer():
    return URLSafeTimedSerializer(app.config['SECRET_KEY'] or 'hire-sense-default-secret-key')


def generate_reset_token(email):
    serializer = get_serializer()
    return serializer.dumps(email, salt='password-reset-salt')


def verify_reset_token(token, expiration=1800):
    serializer = get_serializer()
    try:
        email = serializer.loads(token, salt='password-reset-salt', max_age=expiration)
        return email
    except (SignatureExpired, BadSignature):
        return None


@app.route('/')
def hello_world():
    jobs = load_jobs_from_db()
    return render_template('index.html', jobs=jobs)


@app.route('/register', methods=['GET','POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        name = form.name.data
        email = form.email.data
        password = form.password.data
        headline = form.headline.data
        education = form.education.data
        linkedin = form.linkedin.data
        experience = form.experience.data
        resume = form.resume.data


        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        # form.validate_email(email)

        add_users_to_db(name=name, email=email, password=hashed_password, headline=headline, education=education, 
                        linkedin=linkedin, experience=experience, resume=resume)
        
        user = get_user_from_db(email=email)
        session['user_id'] = user['user_id']
        flash("Registration Successful.")
        return redirect(url_for('hello_world'))


    return render_template("register.html", form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        user = get_user_from_db(email=email)

        if user and bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
            session['user_id'] = user['user_id']
            return redirect(url_for('hello_world'))
        else:
            flash("Login Failed. Please check your email and password!")

    return render_template('login.html', form=form)


@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out successfully")
    return redirect(url_for('login'))


@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        email = form.email.data.strip()
        user = get_user_from_db(email=email)
        if user:
            token = generate_reset_token(email)
            reset_url = url_for('reset_password', token=token, _external=True)

            print("\n" + "=" * 50)
            print(f"[HireSense] Password Reset Requested for: {email}")
            print(f"Reset Link: {reset_url}")
            print("=" * 50 + "\n")

            # Flashed message with category for button rendering
            flash(reset_url, 'reset_link')
            return redirect(url_for('login'))
        else:
            flash("If that email exists in our records, a reset link has been created.")
            return redirect(url_for('login'))

    return render_template('forgot_password.html', form=form)


@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    email = verify_reset_token(token)
    if not email:
        flash("The password reset link is invalid or has expired. Please request a new one.")
        return redirect(url_for('forgot_password'))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        new_password = form.password.data
        hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())

        update_user_password(email, hashed_password)
        flash("Your password has been successfully updated! You can now log in.")
        return redirect(url_for('login'))

    return render_template('reset_password.html', form=form, email=email)


@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' in session:
        user_id = session['user_id']
        user = get_user_info_from_db(user_id=user_id)

        if user :
            data = get_application_info_from_db(user_id)
            return render_template('dashboard.html',user=user,data=data)

    flash("Please Login")
    return redirect(url_for('login'))


@app.route('/jobs/<job_id>')
def show_job(job_id):
    job = load_one_job_from_db(job_id)

    if not job:
        return 'Not Found', 404

    user = None
    has_applied = False
    if "user_id" in session:
        user = get_user_info_from_db(session["user_id"])
        has_applied = had_user_applied(session["user_id"], job_id)

    return render_template('jobpage.html', job=job, user=user, has_applied=has_applied)


@app.route('/jobs/<job_id>/apply', methods=['post'])
def apply_to_job(job_id):
    user_id = session.get("user_id")

    if user_id is None:
        flash("Please log in before applying.")
        return redirect(url_for("login"))

    data = request.form
    add_application_to_db(user_id,job_id,data)
    flash("Application submitted successfully.")
    return redirect(url_for("show_job", job_id=job_id))


@app.route('/edit', methods=["GET","POST"])
def edit():
    user_id = session.get("user_id")

    if user_id is None:
        flash('Please log in')
        return redirect(url_for("login"))

    if request.method == "POST":
        update_user_profile(user_id=user_id, data=request.form)
        flash("Profile Updated Successfully.")
        return redirect(url_for("dashboard"))

    data = get_user_info_from_db(user_id)

    return render_template('edit_profile.html', user=data)


@app.route('/search')
def search():
    query = request.args.get('q', '')
    if query:
        jobs = search_jobs_from_db(query)
    else:
        jobs = load_jobs_from_db()
    return render_template('index.html', jobs=jobs, search_query=query)


@app.route('/resume-checker', methods=['GET', 'POST'])
def resume_checker():
    result = None
    resume_input_text = ""
    job_desc = ""
    resume_file_b64 = None
    resume_file_name = None
    resume_file_type = None
    if request.method == 'GET':
        job_id = request.args.get('job_id')
        if job_id:
            job = load_one_job_from_db(job_id)
            if job:
                parts = []
                if job.get('title'):
                    parts.append(f"Job Title: {job['title']}")
                if job.get('company'):
                    parts.append(f"Company: {job['company']}")
                if job.get('location'):
                    parts.append(f"Location: {job['location']}")
                if job.get('responsibility'):
                    parts.append(f"\nKey Responsibilities:\n{job['responsibility']}")
                if job.get('requirements'):
                    parts.append(f"\nRequirements & Qualifications:\n{job['requirements']}")
                job_desc = "\n".join(parts)
        elif request.args.get('job_description'):
            job_desc = request.args.get('job_description')

    if request.method == 'POST':
        resume_file = request.files.get('resume_file')
        resume_raw_text = request.form.get('resume_text', '').strip()
        job_desc = request.form.get('job_description', '').strip()

        # 1. Process uploaded file (with base64 preview encoding) or pasted text
        if resume_file and resume_file.filename != '':
            filename = resume_file.filename
            resume_file_name = filename
            file_bytes = resume_file.read()
            resume_file_b64 = base64.b64encode(file_bytes).decode('utf-8')

            if filename.lower().endswith('.pdf'):
                resume_file_type = 'pdf'
            elif filename.lower().endswith('.docx'):
                resume_file_type = 'docx'
            else:
                resume_file_type = 'txt'

            resume_file.seek(0)
            resume_input_text = extract_text_from_file(resume_file)
        elif resume_raw_text:
            resume_input_text = resume_raw_text
            resume_file_type = 'text'

        # 2. Check input and calculate ATS keyword compatibility
        if not resume_input_text:
            flash("Please upload a resume file (.pdf, .docx, .txt) or paste your resume text.", "warning")
        elif not job_desc:
            flash("Please enter a job description to compare against.", "warning")
        else:
            try:
                result = check_ats_compatibility(
                    resume_text=resume_input_text,
                    job_description=job_desc
                )
            except Exception as e:
                flash(f"Error checking ATS score: {str(e)}", "danger")

    return render_template(
        'resume_checker.html',
        result=result,
        resume_text=resume_input_text,
        job_description=job_desc,
        resume_file_b64=resume_file_b64,
        resume_file_name=resume_file_name,
        resume_file_type=resume_file_type
    )



@app.route("/api/jobs")
def list_jobs():
    jobs = load_jobs_from_db()
    return jsonify(jobs)



if __name__ == '__main__':
    app.run(debug=True)
