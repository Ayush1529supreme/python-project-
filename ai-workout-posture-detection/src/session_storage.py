"""
session_storage.py - optional SQLite storage of finished sessions.

Only these things are stored: start date/time, duration, rep count and the
average depth angle. No video, no images, no landmarks.
"""

import sqlite3
from contextlib import closing
from pathlib import Path


class SessionStorage:
    def __init__(self, db_path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS workout_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    started_at TEXT NOT NULL,
                    duration_seconds REAL NOT NULL,
                    squat_reps INTEGER NOT NULL,
                    avg_depth_angle REAL
                )
                """
            )

    def _connect(self):
        return sqlite3.connect(str(self.db_path))

    def save_session(self, summary: dict) -> int:
        """Save one session summary (see WorkoutSession.summary). Returns the new row id."""
        with closing(self._connect()) as connection, connection:
            cursor = connection.execute(
                "INSERT INTO workout_sessions "
                "(started_at, duration_seconds, squat_reps, avg_depth_angle) "
                "VALUES (?, ?, ?, ?)",
                (
                    summary["started_at"],
                    summary["duration_seconds"],
                    summary["squat_reps"],
                    summary.get("avg_depth_angle"),
                ),
            )
            return cursor.lastrowid

    def list_sessions(self, limit=50):
        """Newest sessions first, as a list of dictionaries."""
        with closing(self._connect()) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                "SELECT * FROM workout_sessions ORDER BY started_at DESC, id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]
