import unittest

from src.posture_feedback import FeedbackLevel, generate_feedback
from src.pose_metrics import TrackingStatus
from src.squat_counter import SquatState
from src.workout_session import SessionState

OK = TrackingStatus.OK
ACTIVE = SessionState.ACTIVE


class FeedbackTests(unittest.TestCase):
    def test_partial_body_asks_to_reposition(self):
        fb = generate_feedback(SessionState.IDLE, TrackingStatus.PARTIAL_BODY, SquatState.WAITING)
        self.assertIn("fully in the camera frame", fb.message)
        self.assertEqual(fb.level, FeedbackLevel.WARNING)

    def test_no_person_before_start_asks_to_reposition(self):
        fb = generate_feedback(SessionState.IDLE, TrackingStatus.NO_PERSON, SquatState.WAITING)
        self.assertIn("fully in the camera frame", fb.message)

    def test_no_person_during_session_is_tracking_unavailable(self):
        fb = generate_feedback(ACTIVE, TrackingStatus.NO_PERSON, SquatState.STANDING)
        self.assertEqual(fb.message, "Tracking temporarily unavailable.")

    def test_ready_to_start(self):
        fb = generate_feedback(SessionState.IDLE, OK, SquatState.WAITING)
        self.assertIn("ready to start", fb.message)
        self.assertEqual(fb.level, FeedbackLevel.GOOD)

    def test_paused_message(self):
        fb = generate_feedback(SessionState.PAUSED, OK, SquatState.STANDING)
        self.assertIn("paused", fb.message)

    def test_standing_prompts_begin(self):
        self.assertEqual(generate_feedback(ACTIVE, OK, SquatState.STANDING).message,
                         "Begin your squat.")

    def test_moving_normally(self):
        fb = generate_feedback(ACTIVE, OK, SquatState.DESCENDING, angular_velocity=60)
        self.assertEqual(fb.message, "Movement detected.")

    def test_fast_movement_warns(self):
        fb = generate_feedback(ACTIVE, OK, SquatState.DESCENDING, angular_velocity=500)
        self.assertEqual(fb.message, "Keep your movement controlled.")

    def test_bottom_and_ascending_prompt_return(self):
        self.assertEqual(generate_feedback(ACTIVE, OK, SquatState.BOTTOM).message,
                         "Return to standing.")
        self.assertEqual(generate_feedback(ACTIVE, OK, SquatState.ASCENDING, 50).message,
                         "Return to standing.")

    def test_speed_feedback_is_not_given_while_standing(self):
        fb = generate_feedback(ACTIVE, OK, SquatState.STANDING, angular_velocity=999)
        self.assertEqual(fb.message, "Begin your squat.")


if __name__ == "__main__":
    unittest.main()
