import unittest

from src.squat_counter import SquatState
from src.workout_session import SessionState, WorkoutSession
from tests.test_squat_counter import FPS, full_squat


class FakeClock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


def play(session, clock, angles):
    """Feed angles to the session at 30 FPS using the fake clock."""
    counted = 0
    for angle in angles:
        clock.advance(1 / FPS)
        if session.process_frame(angle):
            counted += 1
    return counted


class WorkoutSessionTests(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.session = WorkoutSession(clock=self.clock)

    def test_nothing_is_counted_before_start(self):
        counted = play(self.session, self.clock, [175.0] * 5 + full_squat())
        self.assertEqual(counted, 0)
        self.assertEqual(self.session.rep_count, 0)
        self.assertEqual(self.session.state, SessionState.IDLE)

    def test_start_then_count(self):
        self.session.start()
        counted = play(self.session, self.clock, [175.0] * 5 + full_squat())
        self.assertEqual(counted, 1)
        self.assertEqual(self.session.rep_count, 1)

    def test_paused_session_does_not_count(self):
        self.session.start()
        play(self.session, self.clock, [175.0] * 5)
        self.session.toggle_pause()
        self.assertEqual(self.session.state, SessionState.PAUSED)
        counted = play(self.session, self.clock, full_squat())
        self.assertEqual(counted, 0)
        self.assertEqual(self.session.rep_count, 0)

    def test_resume_after_pause_counts_again_but_forgets_old_movement(self):
        self.session.start()
        play(self.session, self.clock, [175.0] * 5 + full_squat()[:20])  # mid-squat...
        self.session.toggle_pause()
        play(self.session, self.clock, full_squat())                     # ignored
        self.session.toggle_pause()                                      # resume
        self.assertEqual(self.session.counter.state, SquatState.WAITING)
        play(self.session, self.clock, [175.0] * 5 + full_squat())
        self.assertEqual(self.session.rep_count, 1)

    def test_s_key_resumes_a_paused_session(self):
        self.session.start()
        self.session.toggle_pause()
        self.assertTrue(self.session.start())
        self.assertEqual(self.session.state, SessionState.ACTIVE)

    def test_pause_before_start_does_nothing(self):
        self.assertFalse(self.session.toggle_pause())
        self.assertEqual(self.session.state, SessionState.IDLE)

    def test_timer_excludes_paused_time(self):
        self.session.start()
        self.clock.advance(10)
        self.session.toggle_pause()
        self.clock.advance(50)               # paused for 50 s
        self.assertAlmostEqual(self.session.elapsed_seconds, 10.0, places=6)
        self.session.toggle_pause()
        self.clock.advance(5)
        self.assertAlmostEqual(self.session.elapsed_seconds, 15.0, places=6)

    def test_reset_clears_reps_and_timer_but_keeps_session_state(self):
        self.session.start()
        play(self.session, self.clock, [175.0] * 5 + full_squat())
        self.assertEqual(self.session.rep_count, 1)
        self.session.reset()
        self.assertEqual(self.session.rep_count, 0)
        self.assertLess(self.session.elapsed_seconds, 0.01)
        self.assertIsNone(self.session.average_depth_angle)
        self.assertEqual(self.session.state, SessionState.ACTIVE)

    def test_statistics_and_summary(self):
        self.session.start()
        play(self.session, self.clock, [175.0] * 5 + full_squat(bottom=90.0))
        self.assertIsNotNone(self.session.average_recent_angle)
        self.assertAlmostEqual(self.session.average_depth_angle, 90.0, delta=3.0)
        summary = self.session.summary()
        self.assertEqual(summary["squat_reps"], 1)
        self.assertGreater(summary["duration_seconds"], 0)

    def test_missing_landmarks_in_active_session_are_safe(self):
        self.session.start()
        for _ in range(40):
            self.clock.advance(1 / FPS)
            self.assertFalse(self.session.process_frame(None))
        self.assertEqual(self.session.counter.state, SquatState.WAITING)


if __name__ == "__main__":
    unittest.main()
