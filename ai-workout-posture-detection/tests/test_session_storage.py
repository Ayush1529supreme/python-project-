import tempfile
import unittest
from pathlib import Path

from src.session_storage import SessionStorage


class SessionStorageTests(unittest.TestCase):
    def test_save_and_list(self):
        with tempfile.TemporaryDirectory() as folder:
            storage = SessionStorage(Path(folder) / "sub" / "test.db")   # folder is created
            first = storage.save_session({"started_at": "2026-01-01T10:00:00",
                                          "duration_seconds": 60.0, "squat_reps": 12,
                                          "avg_depth_angle": 92.5})
            second = storage.save_session({"started_at": "2026-01-02T10:00:00",
                                           "duration_seconds": 30.0, "squat_reps": 5,
                                           "avg_depth_angle": None})
            self.assertNotEqual(first, second)
            rows = storage.list_sessions()
            self.assertEqual([r["squat_reps"] for r in rows], [5, 12])   # newest first
            self.assertIsNone(rows[0]["avg_depth_angle"])

    def test_data_survives_reopening(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "test.db"
            SessionStorage(path).save_session({"started_at": "2026-01-01T10:00:00",
                                               "duration_seconds": 1.0, "squat_reps": 1})
            self.assertEqual(len(SessionStorage(path).list_sessions()), 1)


if __name__ == "__main__":
    unittest.main()
