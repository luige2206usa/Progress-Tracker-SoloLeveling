import sqlite3

DB_NAME = "tracker.db"
TOTAL_CLASSES = 39


def get_connection():
    """Open a connection to the database file.
    If tracker.db doesn't exist yet, SQLite creates it."""
    return sqlite3.connect(DB_NAME)


def create_tables():
    """Create all tables if they don't already exist."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS athletic_skills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            jump_height REAL,
            deadlift_weight INTEGER,
            upperbody_weight INTEGER,
            body_weight INTEGER
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS golf_rounds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            course TEXT NOT NULL,
            holes INTEGER NOT NULL,
            score INTEGER NOT NULL,
            putts INTEGER
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS climbs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            location TEXT NOT NULL,
            grade TEXT NOT NULL,
            sent INTEGER NOT NULL,
            attempts INTEGER NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS software_development_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            class_name TEXT NOT NULL UNIQUE
        )
    """)

    conn.commit()
    conn.close()

def _insert(sql, values):
    """Run one INSERT command and save it.
    The leading underscore means: only used inside this file."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(sql, values)
    conn.commit()
    conn.close()


def add_athletic_skill(date, jump_height, deadlift_weight, upperbody_weight, body_weight):
    _insert(
        "INSERT INTO athletic_skills (date, jump_height, deadlift_weight, upperbody_weight, body_weight) "
        "VALUES (?, ?, ?, ?, ?)",
        (date, jump_height, deadlift_weight, upperbody_weight, body_weight),
    )


def add_golf_round(date, course, holes, score, putts):
    _insert(
        "INSERT INTO golf_rounds (date, course, holes, score, putts) "
        "VALUES (?, ?, ?, ?, ?)",
        (date, course, holes, score, putts),
    )


def add_climb(date, location, grade, sent, attempts):
    _insert(
        "INSERT INTO climbs (date, location, grade, sent, attempts) "
        "VALUES (?, ?, ?, ?, ?)",
        (date, location, grade, sent, attempts),
    )


def add_completed_class(date, class_name):
    _insert(
        "INSERT INTO software_development_progress (date, class_name) "
        "VALUES (?, ?)",
        (date, class_name),
    )


def get_progress():
    """Return (classes_completed, classes_left)."""
    conn = get_connection()
    count = conn.execute(
        "SELECT COUNT(*) FROM software_development_progress"
    ).fetchone()[0]
    conn.close()
    return count, TOTAL_CLASSES - count