import sqlite3

# Connect to database
conn = sqlite3.connect('hw13.db')
cursor = conn.cursor()

# Execute schema file
with open('schema.sql', 'r') as f:
    cursor.executescript(f.read())

# Insert initial test data
# Add John Smith
cursor.execute(
    "INSERT INTO students (first_name, last_name) VALUES (?, ?)",
    ("John", "Smith")
)

# Add Python Basics quiz
cursor.execute(
    "INSERT INTO quizzes (subject, num_questions, quiz_date) VALUES (?, ?, ?)",
    ("Python Basics", 5, "2015-02-05")
)

# Add quiz result for John Smith
cursor.execute(
    "INSERT INTO results (student_id, quiz_id, score) VALUES (?, ?, ?)",
    (1, 1, 85)
)

# Commit changes and close connection
conn.commit()
conn.close()

print("Database initialized successfully.")
