from flask import Flask, render_template, redirect, url_for, request, flash, session, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config
from datetime import datetime
import random, string
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature



app = Flask(__name__)
app.config.from_object(Config)

mail = Mail(app)
s = URLSafeTimedSerializer(app.config['SECRET_KEY'])


db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Fungsi untuk menentukan level berdasarkan skor
def get_level(avg_score):
    if avg_score >= 80:
        return "Ahli"
    elif avg_score >= 60:
        return "Cerdas"
    else:
        return "Pemula"



def only_admin():
    if not current_user.is_authenticated or current_user.role != 'guru':
        abort(403)


# ----- Models -----
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    role = db.Column(db.String(20), default='murid')  # 'murid' or 'guru'
    scores = db.relationship('Score', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Material(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    text = db.Column(db.Text, nullable=False)
    image_filename = db.Column(db.String(200), nullable=True)


class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    qtype = db.Column(db.String(20), default='mcq')  # 'mcq' or 'tf'
    # choices format e.g. "A||Pilihan A;;B||Pilihan B;;C||Pilihan C"
    choices = db.Column(db.Text, nullable=True)
    correct = db.Column(db.String(200), nullable=False)  # e.g. 'A' or 'True'


class Score(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    total = db.Column(db.Integer, nullable=False)
    taken_at = db.Column(db.DateTime, default=datetime.utcnow)


# ----- Login loader -----
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ----- Routes -----
@app.route('/')
def index():
    return render_template('index.html')


# Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        role = request.form.get('role', 'murid')

        if not username or not password:
            flash('Isi username dan password', 'danger')
            return redirect(url_for('register'))
        if User.query.filter_by(username=username).first():
            flash('Username sudah terdaftar', 'warning')
            return redirect(url_for('register'))

        u = User(username=username, role=role)
        u.set_password(password)
        db.session.add(u)
        db.session.commit()
        flash(f'Registrasi {role.capitalize()} berhasil! Silakan login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')


# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash('Login sukses', 'success')
            # redirect to admin dashboard if guru, else normal dashboard
            if user.role == 'guru':
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('dashboard'))
        flash('Username/password salah', 'danger')
    return render_template('login.html')

# ---------- LUPA PASSWORD ----------
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    reset_link = None  # biar bisa dikirim ke template
    if request.method == 'POST':
        username = request.form['email'].strip()
        user = User.query.filter_by(username=username).first()
        if user:
            token = s.dumps(user.username, salt='reset-password')
            link = url_for('reset_password', token=token, _external=True)
            reset_link = link  # kirim ke HTML
            flash('Link reset password telah dibuat!', 'info')
        else:
            flash('Username tidak ditemukan.', 'danger')
    return render_template('forgot_password.html', reset_link=reset_link)





@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        email = s.loads(token, salt='reset-password', max_age=600)  # 10 menit
    except SignatureExpired:
        flash('Link reset password sudah kedaluwarsa.', 'danger')
        return redirect(url_for('forgot_password'))
    except BadSignature:
        flash('Token tidak valid.', 'danger')
        return redirect(url_for('forgot_password'))

    user = User.query.filter_by(username=email).first()
    if request.method == 'POST':
        new_password = request.form['new_password']
        user.set_password(new_password)
        db.session.commit()
        flash('Password berhasil diperbarui. Silakan login.', 'success')
        return redirect(url_for('login'))

    return render_template('reset_password.html', email=email)


# Logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Anda telah logout', 'info')
    return redirect(url_for('index'))


# Dashboard (user)
@app.route('/dashboard')
@login_required
def dashboard():
    # jika guru boleh juga lihat dashboard biasa
    scores = Score.query.filter_by(user_id=current_user.id).order_by(Score.taken_at.asc()).all()
    total_quizzes = Question.query.count()
    last_score = scores[-1] if scores else None

    labels = [s.taken_at.strftime("%d %b %H:%M") for s in scores]
    data_scores = [s.score for s in scores]

    avg_score = int(sum(data_scores) / len(data_scores)) if data_scores else 0
    best_score = max(data_scores) if data_scores else 0

    return render_template(
        'dashboard.html',
        total_quizzes=total_quizzes,
        last_score=last_score,
        scores=scores,
        labels=labels,
        data_scores=data_scores,
        avg_score=avg_score,
        best_score=best_score
    )


# Material (public for logged users)
@app.route('/material')
@login_required
def material():
    mats = Material.query.all()
    return render_template('material.html', materials=mats)


# Start quiz (simple: all questions)
@app.route('/quiz', methods=['GET', 'POST'])
@login_required
def quiz():
    if request.method == 'GET':
        questions = Question.query.all()
        return render_template('quiz.html', questions=questions)
    # POST: grade
    questions = Question.query.all()
    total = len(questions)
    correct_count = 0
    for q in questions:
        key = f'question_{q.id}'
        given = request.form.get(key, '').strip()
        if given != '':
            if q.correct.strip().lower() == given.strip().lower():
                correct_count += 1
    score = int((correct_count / total) * 100) if total > 0 else 0
    s = Score(user_id=current_user.id, score=score, total=total)
    db.session.add(s)
    db.session.commit()
    return render_template('result.html', score=score, total=total, correct=correct_count)


# Leaderboard
@app.route('/leaderboard')
@login_required
def leaderboard():
    subq = db.session.query(Score.user_id, db.func.max(Score.score).label('best_score')).group_by(Score.user_id).subquery()
    results = db.session.query(User.username, subq.c.best_score).join(subq, User.id == subq.c.user_id).order_by(subq.c.best_score.desc()).limit(20).all()
    return render_template('leaderboard.html', results=results)

# ---------- USER PROFILE ----------
@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        new_password = request.form.get('new_password')
        if new_password:
            current_user.set_password(new_password)
            db.session.commit()
            flash('Password berhasil diperbarui!', 'success')
            return redirect(url_for('profile'))

    scores = Score.query.filter_by(user_id=current_user.id).all()
    total_quiz = len(scores)
    avg_score = int(sum([s.score for s in scores]) / total_quiz) if total_quiz > 0 else 0
    best_score = max([s.score for s in scores]) if scores else 0
    level = get_level(avg_score)

    return render_template('profile.html',
                           user=current_user,
                           total_quiz=total_quiz,
                           avg_score=avg_score,
                           best_score=best_score,
                           level=level)


# ---------- LAPORAN GURU ----------
@app.route('/admin/report')
@login_required
def admin_report():
    if current_user.role != 'guru':
        flash('Akses ditolak! Hanya untuk guru.', 'danger')
        return redirect(url_for('dashboard'))

    # Ambil semua murid
    students = User.query.filter_by(role='murid').all()

    # Hitung rata-rata skor setiap murid
    report_data = []
    for student in students:
        scores = Score.query.filter_by(user_id=student.id).all()
        if scores:
            avg_score = int(sum([s.score for s in scores]) / len(scores))
            best_score = max([s.score for s in scores])
        else:
            avg_score = 0
            best_score = 0
        report_data.append({
            'username': student.username,
            'avg_score': avg_score,
            'best_score': best_score
        })

    # Siapkan data untuk chart
    labels = [r['username'] for r in report_data]
    data_scores = [r['avg_score'] for r in report_data]

    return render_template(
        'admin_report.html',
        report_data=report_data,
        labels=labels,
        data_scores=data_scores
    )

import csv
from io import StringIO
from flask import make_response

# ---------- EKSPOR DATA NILAI KE CSV ----------
@app.route('/admin/export_scores')
@login_required
def export_scores():
    if current_user.role != 'guru':
        flash('Akses ditolak! Hanya guru yang dapat mengekspor nilai.', 'danger')
        return redirect(url_for('dashboard'))

    # Ambil semua siswa
    students = User.query.filter_by(role='murid').all()

    # Siapkan data CSV
    csv_data = StringIO()
    writer = csv.writer(csv_data)
    writer.writerow(['Nama Siswa', 'Total Kuis', 'Rata-rata Skor', 'Skor Tertinggi', 'Tanggal Terakhir'])

    for student in students:
        scores = Score.query.filter_by(user_id=student.id).all()
        if scores:
            total_quiz = len(scores)
            avg_score = int(sum([s.score for s in scores]) / total_quiz)
            best_score = max([s.score for s in scores])
            last_date = max([s.taken_at.strftime('%d-%m-%Y') for s in scores])
        else:
            total_quiz = 0
            avg_score = 0
            best_score = 0
            last_date = '-'
        writer.writerow([student.username, total_quiz, avg_score, best_score, last_date])

    # Kirim file CSV ke browser
    response = make_response(csv_data.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=laporan_nilai.csv'
    response.headers['Content-Type'] = 'text/csv'
    return response



# ---------- ADMIN DASHBOARD ----------
@app.route('/admin')
@login_required
def admin_dashboard():
    only_admin()

    # --- Statistik Ringkas ---
    total_users = User.query.count()
    total_murid = User.query.filter_by(role='murid').count()
    total_guru = User.query.filter_by(role='guru').count()
    total_material = Material.query.count()
    total_questions = Question.query.count()

    # Rata-rata keseluruhan
    avg_scores = db.session.query(db.func.avg(Score.score)).scalar() or 0
    avg_scores = round(avg_scores, 2)

    # --- Grafik Bar: Nilai Tertinggi Tiap Murid ---
    subq = db.session.query(
        Score.user_id,
        db.func.max(Score.score).label('best_score')
    ).group_by(Score.user_id).subquery()

    murid_scores = db.session.query(User.username, subq.c.best_score).join(
        subq, User.id == subq.c.user_id
    ).filter(User.role == 'murid').order_by(subq.c.best_score.desc()).all()

    labels = [m[0] for m in murid_scores]
    data_scores = [m[1] for m in murid_scores]

    # --- Grafik Line: Rata-rata Nilai Harian ---
    from sqlalchemy import func
    avg_per_day = (
        db.session.query(
            func.date(Score.taken_at).label("tanggal"),
            func.avg(Score.score).label("rata")
        )
        .group_by(func.date(Score.taken_at))
        .order_by(func.date(Score.taken_at))
        .all()
    )

    line_labels = [str(a[0]) for a in avg_per_day]
    line_data = [round(a[1], 2) for a in avg_per_day]

    return render_template(
        'admin_dashboard.html',
        total_users=total_users,
        total_murid=total_murid,
        total_guru=total_guru,
        total_material=total_material,
        total_questions=total_questions,
        avg_scores=avg_scores,
        labels=labels,
        data_scores=data_scores,
        line_labels=line_labels,
        line_data=line_data
    )




# ---------- CRUD MATERI ----------
@app.route('/admin/material')
@login_required
def admin_material():
    only_admin()
    materials = Material.query.all()
    return render_template('admin_material.html', materials=materials)


@app.route('/admin/material/add', methods=['GET', 'POST'])
@login_required
def admin_material_add():
    only_admin()
    if request.method == 'POST':
        title = request.form['title']
        text = request.form['text']
        image = request.form.get('image', '')
        m = Material(title=title, text=text, image_filename=image)
        db.session.add(m)
        db.session.commit()
        flash('Materi berhasil ditambahkan!', 'success')
        return redirect(url_for('admin_material'))
    return render_template('admin_material_form.html', mode='add')


@app.route('/admin/material/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def admin_material_edit(id):
    only_admin()
    m = Material.query.get_or_404(id)
    if request.method == 'POST':
        m.title = request.form['title']
        m.text = request.form['text']
        m.image_filename = request.form.get('image', '')
        db.session.commit()
        flash('Materi berhasil diperbarui!', 'success')
        return redirect(url_for('admin_material'))
    return render_template('admin_material_form.html', mode='edit', material=m)


@app.route('/admin/material/delete/<int:id>')
@login_required
def admin_material_delete(id):
    only_admin()
    m = Material.query.get_or_404(id)
    db.session.delete(m)
    db.session.commit()
    flash('Materi dihapus!', 'info')
    return redirect(url_for('admin_material'))


# ---------- CRUD SOAL ----------
@app.route('/admin/question')
@login_required
def admin_question():
    only_admin()
    questions = Question.query.all()
    return render_template('admin_question.html', questions=questions)


@app.route('/admin/question/add', methods=['GET', 'POST'])
@login_required
def admin_question_add():
    only_admin()
    if request.method == 'POST':
        text = request.form['text']
        qtype = request.form['qtype']
        choices = request.form.get('choices', '')
        correct = request.form['correct']
        q = Question(text=text, qtype=qtype, choices=choices, correct=correct)
        db.session.add(q)
        db.session.commit()
        flash('Soal baru ditambahkan!', 'success')
        return redirect(url_for('admin_question'))
    return render_template('admin_question_form.html', mode='add')


@app.route('/admin/question/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def admin_question_edit(id):
    only_admin()
    q = Question.query.get_or_404(id)
    if request.method == 'POST':
        q.text = request.form['text']
        q.qtype = request.form['qtype']
        q.choices = request.form.get('choices', '')
        q.correct = request.form['correct']
        db.session.commit()
        flash('Soal diperbarui!', 'success')
        return redirect(url_for('admin_question'))
    return render_template('admin_question_form.html', mode='edit', question=q)


@app.route('/admin/question/delete/<int:id>')
@login_required
def admin_question_delete(id):
    only_admin()
    q = Question.query.get_or_404(id)
    db.session.delete(q)
    db.session.commit()
    flash('Soal dihapus!', 'info')
    return redirect(url_for('admin_question'))


# Simple route to view raw questions (for admin/testing)
@app.route('/admin/questions')
@login_required
def admin_questions():
    only_admin()
    qs = Question.query.all()
    out = []
    for q in qs:
        out.append({'id': q.id, 'text': q.text, 'type': q.qtype, 'choices': q.choices, 'correct': q.correct})
    return {'questions': out}


# Error handlers
@app.errorhandler(403)
def forbidden_error(e):
    return render_template('403.html'), 403


@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404


# Run
if __name__ == '__main__':
    app.run(debug=True)
