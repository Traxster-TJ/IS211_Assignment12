import os
import sqlite3
from flask import Flask, g, redirect, render_template, request, session, url_for, flash
from datetime import datetime

# Configuration
DATABASE = 'hw13.db'
SECRET_KEY = 'development_key'  # Change this in production

# Create the application
app = Flask(__name__)
app.config.from_object(__name__)

# Database connection helper functions
def connect_db():
    """Connect to the database."""
    rv = sqlite3.connect(app.config['DATABASE'])
    rv.row_factory = sqlite3.Row
    return rv

def get_db():
    """Open a new database connection if there is none yet for the current app context."""
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = connect_db()
    return g.sqlite_db

@app.teardown_appcontext
def close_db(error):
    """Closes the database at the end of the request."""
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()

# Login required decorator
def login_required(f):
    """Decorator to ensure user is logged in."""
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash('Please log in first.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

# Routes
@app.route('/')
def index():
    """Redirect to login page."""
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login."""
    error = None
    if request.method == 'POST':
        if request.form['username'] != 'admin' or request.form['password'] != 'password':
            error = 'Invalid credentials. Please try again.'
        else:
            session['logged_in'] = True
            flash('You were logged in')
            return redirect(url_for('dashboard'))
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    """Handle user logout."""
    session.pop('logged_in', None)
    flash('You were logged out')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Display dashboard with students and quizzes."""
    db = get_db()
    students = db.execute('SELECT id, first_name, last_name FROM students ORDER BY id').fetchall()
    quizzes = db.execute('SELECT id, subject, num_questions, quiz_date FROM quizzes ORDER BY id').fetchall()
    return render_template('dashboard.html', students=students, quizzes=quizzes)

@app.route('/student/add', methods=['GET', 'POST'])
@login_required
def add_student():
    """Add a new student."""
    error = None
    if request.method == 'POST':
        if not request.form['first_name'] or not request.form['last_name']:
            error = 'First name and last name are required.'
        else:
            db = get_db()
            db.execute(
                'INSERT INTO students (first_name, last_name) VALUES (?, ?)',
                [request.form['first_name'], request.form['last_name']]
            )
            db.commit()
            flash('New student added successfully.')
            return redirect(url_for('dashboard'))
    return render_template('add_student.html', error=error)

@app.route('/quiz/add', methods=['GET', 'POST'])
@login_required
def add_quiz():
    """Add a new quiz."""
    error = None
    if request.method == 'POST':
        if not request.form['subject'] or not request.form['num_questions'] or not request.form['quiz_date']:
            error = 'All fields are required.'
        else:
            try:
                num_questions = int(request.form['num_questions'])
                # Parse date from form (expects YYYY-MM-DD format)
                date_str = request.form['quiz_date']
                
                db = get_db()
                db.execute(
                    'INSERT INTO quizzes (subject, num_questions, quiz_date) VALUES (?, ?, ?)',
                    [request.form['subject'], num_questions, date_str]
                )
                db.commit()
                flash('New quiz added successfully.')
                return redirect(url_for('dashboard'))
            except ValueError:
                error = 'Number of questions must be a valid integer.'
    return render_template('add_quiz.html', error=error)

@app.route('/student/<int:student_id>')
@login_required
def view_student_results(student_id):
    """View quiz results for a specific student."""
    db = get_db()
    student = db.execute('SELECT first_name, last_name FROM students WHERE id = ?', [student_id]).fetchone()
    if student is None:
        flash('Student not found.')
        return redirect(url_for('dashboard'))
    
    # Optional part: Using JOIN to get more quiz details
    results = db.execute('''
        SELECT r.quiz_id, r.score, q.subject, q.quiz_date 
        FROM results r
        JOIN quizzes q ON r.quiz_id = q.id
        WHERE r.student_id = ?
        ORDER BY q.quiz_date DESC
    ''', [student_id]).fetchall()
    
    return render_template('student_results.html', student=student, results=results, student_id=student_id)

@app.route('/results/add', methods=['GET', 'POST'])
@login_required
def add_result():
    """Add a quiz result for a student."""
    db = get_db()
    students = db.execute('SELECT id, first_name, last_name FROM students ORDER BY last_name').fetchall()
    quizzes = db.execute('SELECT id, subject, quiz_date FROM quizzes ORDER BY quiz_date DESC').fetchall()
    
    error = None
    if request.method == 'POST':
        try:
            student_id = int(request.form['student_id'])
            quiz_id = int(request.form['quiz_id'])
            score = int(request.form['score'])
            
            if score < 0 or score > 100:
                error = 'Score must be between 0 and 100.'
            else:
                # Check if result already exists
                existing = db.execute(
                    'SELECT 1 FROM results WHERE student_id = ? AND quiz_id = ?',
                    [student_id, quiz_id]
                ).fetchone()
                
                if existing:
                    # Update existing result
                    db.execute(
                        'UPDATE results SET score = ? WHERE student_id = ? AND quiz_id = ?',
                        [score, student_id, quiz_id]
                    )
                    flash('Quiz result updated successfully.')
                else:
                    # Insert new result
                    db.execute(
                        'INSERT INTO results (student_id, quiz_id, score) VALUES (?, ?, ?)',
                        [student_id, quiz_id, score]
                    )
                    flash('Quiz result added successfully.')
                
                db.commit()
                return redirect(url_for('dashboard'))
        except ValueError:
            error = 'Invalid input values.'
    
    return render_template('add_result.html', students=students, quizzes=quizzes, error=error)

# Optional part: View quiz results anonymously
@app.route('/quiz/<int:quiz_id>/results')
def view_quiz_results(quiz_id):
    """View anonymous results for a specific quiz."""
    db = get_db()
    quiz = db.execute('SELECT subject, quiz_date FROM quizzes WHERE id = ?', [quiz_id]).fetchone()
    
    if quiz is None:
        flash('Quiz not found.')
        return redirect(url_for('login'))
    
    # Get results with student IDs only (anonymous view)
    results = db.execute('''
        SELECT r.student_id, r.score
        FROM results r
        WHERE r.quiz_id = ?
        ORDER BY r.score DESC
    ''', [quiz_id]).fetchall()
    
    # If user is logged in, get student names too
    if session.get('logged_in'):
        detailed_results = db.execute('''
            SELECT r.student_id, s.first_name, s.last_name, r.score
            FROM results r
            JOIN students s ON r.student_id = s.id
            WHERE r.quiz_id = ?
            ORDER BY r.score DESC
        ''', [quiz_id]).fetchall()
        return render_template('quiz_results.html', quiz=quiz, results=detailed_results, 
                              quiz_id=quiz_id, anonymous=False)
    
    return render_template('quiz_results.html', quiz=quiz, results=results, 
                          quiz_id=quiz_id, anonymous=True)

if __name__ == '__main__':
    app.run(debug=True)
