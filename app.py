import os
import sqlite3
from flask import Flask, request, session, g, redirect, url_for, abort, \
     render_template, flash

# Create the Flask app
app = Flask(__name__)

# Load default config
app.config.update(dict(
    DATABASE=os.path.join(app.root_path, 'hw13.db'),
    SECRET_KEY='development key',
    USERNAME='admin',
    PASSWORD='password'
))

# Database functions
def connect_db():
    """Connects to the specified database."""
    rv = sqlite3.connect(app.config['DATABASE'])
    rv.row_factory = sqlite3.Row
    return rv

def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = connect_db()
    return g.sqlite_db

@app.teardown_appcontext
def close_db(error):
    """Closes the database again at the end of the request."""
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()

def init_db():
    """Initializes the database."""
    db = get_db()
    with app.open_resource('schema.sql', mode='r') as f:
        db.cursor().executescript(f.read())
    db.commit()

@app.cli.command('initdb')
def initdb_command():
    """Creates the database tables."""
    init_db()
    print('Initialized the database.')

# Authentication decorator
def login_required(f):
    """Decorator that ensures user is logged in before accessing a route."""
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash('Please log in first', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

# Routes
@app.route('/')
def index():
    """Main index page, redirects to login if not authenticated."""
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return redirect(url_for('dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login route for teacher authentication."""
    error = None
    if request.method == 'POST':
        if request.form['username'] != app.config['USERNAME']:
            error = 'Invalid username'
        elif request.form['password'] != app.config['PASSWORD']:
            error = 'Invalid password'
        else:
            session['logged_in'] = True
            flash('You were logged in', 'success')
            return redirect(url_for('dashboard'))
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    """Logout route to end session."""
    session.pop('logged_in', None)
    flash('You were logged out', 'success')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Dashboard page showing students and quizzes."""
    db = get_db()
    students = db.execute('SELECT id, first_name, last_name FROM students ORDER BY id').fetchall()
    quizzes = db.execute('SELECT id, subject, num_questions, quiz_date FROM quizzes ORDER BY id').fetchall()
    return render_template('dashboard.html', students=students, quizzes=quizzes)

@app.route('/student/add', methods=['GET', 'POST'])
@login_required
def add_student():
    """Add a new student to the class."""
    error = None
    if request.method == 'POST':
        if not request.form['first_name']:
            error = 'First name is required'
        elif not request.form['last_name']:
            error = 'Last name is required'
        else:
            db = get_db()
            db.execute('INSERT INTO students (first_name, last_name) VALUES (?, ?)',
                     [request.form['first_name'], request.form['last_name']])
            db.commit()
            flash('New student was successfully added', 'success')
            return redirect(url_for('dashboard'))
    return render_template('add_student.html', error=error)

@app.route('/quiz/add', methods=['GET', 'POST'])
@login_required
def add_quiz():
    """Add a new quiz to the class."""
    error = None
    if request.method == 'POST':
        if not request.form['subject']:
            error = 'Subject is required'
        elif not request.form['num_questions'] or not request.form['num_questions'].isdigit():
            error = 'Number of questions must be a valid number'
        elif not request.form['quiz_date']:
            error = 'Quiz date is required'
        else:
            db = get_db()
            db.execute('INSERT INTO quizzes (subject, num_questions, quiz_date) VALUES (?, ?, ?)',
                     [request.form['subject'], request.form['num_questions'], request.form['quiz_date']])
            db.commit()
            flash('New quiz was successfully added', 'success')
            return redirect(url_for('dashboard'))
    return render_template('add_quiz.html', error=error)

@app.route('/student/<int:student_id>')
@login_required
def student_results(student_id):
    """View results for a specific student."""
    db = get_db()
    # Get student information
    student = db.execute('SELECT id, first_name, last_name FROM students WHERE id = ?',
                        [student_id]).fetchone()
    
    if student is None:
        abort(404)
    
    # Get quiz results for this student
    # Using JOIN to get more quiz information (optional part)
    results = db.execute('''
        SELECT r.id, r.quiz_id, r.score, q.subject, q.quiz_date
        FROM results r
        JOIN quizzes q ON r.quiz_id = q.id
        WHERE r.student_id = ?
    ''', [student_id]).fetchall()
    
    return render_template('student_results.html', student=student, results=results)

@app.route('/results/add', methods=['GET', 'POST'])
@login_required
def add_result():
    """Add a quiz result for a student."""
    db = get_db()
    students = db.execute('SELECT id, first_name, last_name FROM students ORDER BY last_name').fetchall()
    quizzes = db.execute('SELECT id, subject, quiz_date FROM quizzes ORDER BY quiz_date DESC').fetchall()
    
    error = None
    if request.method == 'POST':
        if not request.form['student_id']:
            error = 'Student selection is required'
        elif not request.form['quiz_id']:
            error = 'Quiz selection is required'
        elif not request.form['score'] or not request.form['score'].isdigit():
            error = 'Score must be a valid number'
        elif int(request.form['score']) < 0 or int(request.form['score']) > 100:
            error = 'Score must be between 0 and 100'
        else:
            # Check if this result already exists
            existing = db.execute(
                'SELECT id FROM results WHERE student_id = ? AND quiz_id = ?',
                [request.form['student_id'], request.form['quiz_id']]
            ).fetchone()
            
            if existing:
                error = 'A result for this student and quiz already exists'
            else:
                db.execute(
                    'INSERT INTO results (student_id, quiz_id, score) VALUES (?, ?, ?)',
                    [request.form['student_id'], request.form['quiz_id'], request.form['score']]
                )
                db.commit()
                flash('Quiz result was successfully added', 'success')
                return redirect(url_for('dashboard'))
    
    return render_template('add_result.html', students=students, quizzes=quizzes, error=error)

# Optional part - Anonymous view of quiz results
@app.route('/quiz/<int:quiz_id>/results/')
def quiz_results(quiz_id):
    """Anonymous view of results for a specific quiz."""
    db = get_db()
    # Get quiz information
    quiz = db.execute('SELECT id, subject, num_questions, quiz_date FROM quizzes WHERE id = ?',
                     [quiz_id]).fetchone()
    
    if quiz is None:
        abort(404)
    
    # If user is logged in, show full details, otherwise show anonymized results
    if session.get('logged_in'):
        results = db.execute('''
            SELECT r.id, r.student_id, r.score, s.first_name, s.last_name
            FROM results r
            JOIN students s ON r.student_id = s.id
            WHERE r.quiz_id = ?
            ORDER BY r.score DESC
        ''', [quiz_id]).fetchall()
    else:
        results = db.execute('''
            SELECT r.id, r.student_id, r.score
            FROM results r
            WHERE r.quiz_id = ?
            ORDER BY r.score DESC
        ''', [quiz_id]).fetchall()
    
    return render_template('quiz_results.html', quiz=quiz, results=results, 
                          is_teacher=session.get('logged_in', False))

# For command-line initialization of the database
if __name__ == '__main__':
    app.run(debug=True)
