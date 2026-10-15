import os
import time
from datetime import datetime
import pandas as pd


CSV_FILE_PATH = os.path.join(os.path.dirname(__file__), "workout_logs.csv")
COLUMNS = [
    "session_id",
    "timestamp",
    "exercise",
    "reps_completed",
    "accuracy_score",
    "posture_warnings",
    "avg_fps",
    "duration_seconds"
]


def init_logger():
    """Initializes the CSV logging file if it doesn't exist with initial seed data."""
    if not os.path.exists(CSV_FILE_PATH) or os.path.getsize(CSV_FILE_PATH) == 0:
        sample_data = [
            {
                "session_id": "SES-1001",
                "timestamp": "2026-10-14 09:15:22",
                "exercise": "Bicep Curls",
                "reps_completed": 15,
                "accuracy_score": 93.4,
                "posture_warnings": 2,
                "avg_fps": 28.6,
                "duration_seconds": 78
            },
            {
                "session_id": "SES-1002",
                "timestamp": "2026-10-14 17:42:05",
                "exercise": "Squats",
                "reps_completed": 20,
                "accuracy_score": 88.5,
                "posture_warnings": 4,
                "avg_fps": 27.9,
                "duration_seconds": 115
            },
            {
                "session_id": "SES-1003",
                "timestamp": "2026-10-15 11:20:18",
                "exercise": "Push-ups",
                "reps_completed": 18,
                "accuracy_score": 95.0,
                "posture_warnings": 1,
                "avg_fps": 29.1,
                "duration_seconds": 92
            },
            {
                "session_id": "SES-1004",
                "timestamp": "2026-10-15 18:35:44",
                "exercise": "Bicep Curls",
                "reps_completed": 12,
                "accuracy_score": 91.0,
                "posture_warnings": 3,
                "avg_fps": 28.2,
                "duration_seconds": 65
            }
        ]
        df = pd.DataFrame(sample_data, columns=COLUMNS)
        df.to_csv(CSV_FILE_PATH, index=False)


def log_workout_session(exercise: str,
                        reps_completed: int,
                        accuracy_score: float,
                        posture_warnings: int,
                        avg_fps: float,
                        duration_seconds: int) -> dict:
    """
    Logs a completed workout session into the Pandas CSV database.
    """
    init_logger()

    session_id = f"SES-{int(time.time() % 100000):05d}"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    new_record = {
        "session_id": session_id,
        "timestamp": timestamp,
        "exercise": exercise,
        "reps_completed": int(reps_completed),
        "accuracy_score": round(float(accuracy_score), 1),
        "posture_warnings": int(posture_warnings),
        "avg_fps": round(float(avg_fps), 1),
        "duration_seconds": int(duration_seconds)
    }

    df_new = pd.DataFrame([new_record], columns=COLUMNS)
    df_new.to_csv(CSV_FILE_PATH, mode='a', header=False, index=False)

    return new_record


def get_all_logs() -> pd.DataFrame:
    """Reads all session records as a Pandas DataFrame."""
    init_logger()
    try:
        df = pd.read_csv(CSV_FILE_PATH)
        return df
    except Exception:
        return pd.DataFrame(columns=COLUMNS)


def get_recent_sessions(limit: int = 20) -> list:
    """Returns the most recent workout sessions sorted by timestamp descending."""
    df = get_all_logs()
    if df.empty:
        return []
    df_sorted = df.tail(limit).iloc[::-1]
    return df_sorted.to_dict(orient="records")


def get_summary_metrics() -> dict:
    """
    Aggregates overall workout analytics using Pandas vector methods.
    """
    df = get_all_logs()
    if df.empty:
        return {
            "total_workouts": 0,
            "total_reps": 0,
            "avg_accuracy": 0.0,
            "avg_fps": 0.0,
            "total_duration_minutes": 0.0,
            "exercise_breakdown": {}
        }

    total_workouts = len(df)
    total_reps = int(df["reps_completed"].sum())
    avg_accuracy = round(float(df["accuracy_score"].mean()), 1)
    avg_fps = round(float(df["avg_fps"].mean()), 1)
    total_duration_min = round(float(df["duration_seconds"].sum()) / 60.0, 1)

    # Exercise count breakdown
    breakdown_df = df.groupby("exercise")["reps_completed"].sum()
    breakdown = breakdown_df.to_dict()

    return {
        "total_workouts": total_workouts,
        "total_reps": total_reps,
        "avg_accuracy": avg_accuracy,
        "avg_fps": avg_fps,
        "total_duration_minutes": total_duration_min,
        "exercise_breakdown": breakdown
    }


def clear_workout_logs():
    """Resets the workout log CSV file with an empty schema."""
    df = pd.DataFrame(columns=COLUMNS)
    df.to_csv(CSV_FILE_PATH, index=False)
