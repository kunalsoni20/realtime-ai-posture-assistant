import sqlite3
import os
import time
from datetime import datetime
from typing import List, Dict, Optional, Tuple

DB_PATH = os.path.join(os.path.dirname(__file__), 'gym_coach.db')


def get_db_connection():
    """Returns a SQLite database connection with row factory enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initializes SQLite schema for users and workout sessions."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            goal TEXT DEFAULT 'Muscle Building',
            fitness_level TEXT DEFAULT 'Intermediate',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 2. Workouts table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS workouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            exercise TEXT NOT NULL,
            reps INTEGER NOT NULL,
            target_reps INTEGER DEFAULT 10,
            accuracy_score REAL NOT NULL,
            warnings_count INTEGER DEFAULT 0,
            duration_seconds INTEGER NOT NULL,
            calories_burned REAL DEFAULT 0.0,
            coach_feedback TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # Insert default guest user if no users exist
    cursor.execute('SELECT COUNT(*) FROM users')
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO users (username, goal, fitness_level)
            VALUES (?, ?, ?)
        ''', ('Athlete_Kunal', 'Muscle Building', 'Intermediate'))

    conn.commit()
    conn.close()


def get_or_create_user(username: str, goal: str = "Muscle Building", fitness_level: str = "Intermediate") -> Dict:
    """Retrieves an existing user or creates a new one."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    row = cursor.fetchone()

    if row:
        user = dict(row)
        # Update goal and fitness_level if modified
        if user['goal'] != goal or user['fitness_level'] != fitness_level:
            cursor.execute('''
                UPDATE users SET goal = ?, fitness_level = ? WHERE id = ?
            ''', (goal, fitness_level, user['id']))
            conn.commit()
            user['goal'] = goal
            user['fitness_level'] = fitness_level
    else:
        cursor.execute('''
            INSERT INTO users (username, goal, fitness_level)
            VALUES (?, ?, ?)
        ''', (username, goal, fitness_level))
        conn.commit()
        user_id = cursor.lastrowid
        user = {
            "id": user_id,
            "username": username,
            "goal": goal,
            "fitness_level": fitness_level
        }

    conn.close()
    return user


def get_all_users() -> List[Dict]:
    """Retrieves all registered users."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users ORDER BY created_at DESC')
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def log_workout(user_id: int,
                exercise: str,
                reps: int,
                target_reps: int,
                accuracy_score: float,
                warnings_count: int,
                duration_seconds: int,
                calories_burned: float = 0.0,
                coach_feedback: str = "Good effort!") -> int:
    """Logs a completed workout session into SQLite database."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO workouts (
            user_id, exercise, reps, target_reps, accuracy_score,
            warnings_count, duration_seconds, calories_burned, coach_feedback
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, exercise, reps, target_reps, accuracy_score,
          warnings_count, duration_seconds, calories_burned, coach_feedback))

    conn.commit()
    workout_id = cursor.lastrowid
    conn.close()
    return workout_id


def get_user_workouts(user_id: int, limit: int = 50) -> List[Dict]:
    """Retrieves recent workout history for a specific user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM workouts
        WHERE user_id = ?
        ORDER BY timestamp DESC
        LIMIT ?
    ''', (user_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_user_summary_stats(user_id: int) -> Dict:
    """Computes aggregated lifetime workout stats for a user."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT 
            COUNT(*) as total_sessions,
            COALESCE(SUM(reps), 0) as total_reps,
            COALESCE(AVG(accuracy_score), 100.0) as avg_accuracy,
            COALESCE(SUM(duration_seconds), 0) as total_time_seconds,
            COALESCE(SUM(calories_burned), 0.0) as total_calories
        FROM workouts
        WHERE user_id = ?
    ''', (user_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return {
            "total_sessions": row["total_sessions"],
            "total_reps": row["total_reps"],
            "avg_accuracy": round(row["avg_accuracy"], 1),
            "total_time_mins": round(row["total_time_seconds"] / 60.0, 1),
            "total_calories": round(row["total_calories"], 1)
        }
    return {
        "total_sessions": 0,
        "total_reps": 0,
        "avg_accuracy": 100.0,
        "total_time_mins": 0.0,
        "total_calories": 0.0
    }


# Auto-initialize database on import
init_db()
