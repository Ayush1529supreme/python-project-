import unittest

from src.pose_detector import LANDMARK_INDEX, NUM_LANDMARKS, Landmark, PoseResult
from src.pose_metrics import TrackingStatus, compute_squat_metrics


def make_pose(width=1000, height=1000, standing=True, **overrides):
    """A fake pose: a person standing straight, facing the camera.
    overrides: landmark_name=Landmark(...) or None (None = very low visibility)."""
    landmarks = [Landmark(0.5, 0.5, 0.0, 0.99) for _ in range(NUM_LANDMARKS)]
    layout = {   # (x, y) for each side, x differs for left/right
        "shoulder": 0.2, "hip": 0.45, "knee": 0.65, "ankle": 0.9,
    }
    for side, x in (("left", 0.45), ("right", 0.55)):
        for part, y in layout.items():
            landmarks[LANDMARK_INDEX[f"{side}_{part}"]] = Landmark(x, y, 0.0, 0.99)
    for name, value in overrides.items():
        landmarks[LANDMARK_INDEX[name]] = value if value is not None else Landmark(0.5, 0.5, 0, 0.0)
    return PoseResult(landmarks=landmarks, frame_width=width, frame_height=height)


class PoseMetricsTests(unittest.TestCase):
    def test_no_person(self):
        metrics = compute_squat_metrics(PoseResult())
        self.assertEqual(metrics.status, TrackingStatus.NO_PERSON)
        self.assertIsNone(metrics.knee_angle)
        self.assertFalse(metrics.tracking_ok)

    def test_standing_person_has_straight_legs(self):
        metrics = compute_squat_metrics(make_pose())
        self.assertEqual(metrics.status, TrackingStatus.OK)
        self.assertAlmostEqual(metrics.knee_angle, 180.0, places=3)
        self.assertTrue(metrics.full_body_visible)
        self.assertTrue(metrics.tracking_ok)

    def test_one_hidden_side_still_works_using_the_other(self):
        pose = make_pose(left_knee=None)
        metrics = compute_squat_metrics(pose)
        self.assertEqual(metrics.status, TrackingStatus.OK)
        self.assertIsNone(metrics.left_knee_angle)
        self.assertIsNotNone(metrics.right_knee_angle)
        self.assertFalse(metrics.full_body_visible)

    def test_low_visibility_on_both_sides_is_partial_body(self):
        pose = make_pose(left_knee=None, right_ankle=None)
        metrics = compute_squat_metrics(pose)
        self.assertEqual(metrics.status, TrackingStatus.PARTIAL_BODY)
        self.assertIsNone(metrics.knee_angle)

    def test_ankles_outside_the_picture_are_not_reliable(self):
        pose = make_pose(
            left_ankle=Landmark(0.45, 1.3, 0, 0.99),
            right_ankle=Landmark(0.55, 1.3, 0, 0.99),
        )
        metrics = compute_squat_metrics(pose)
        self.assertEqual(metrics.status, TrackingStatus.PARTIAL_BODY)

    def test_missing_shoulder_makes_that_side_unusable(self):
        pose = make_pose(left_shoulder=None, right_shoulder=None)
        self.assertEqual(compute_squat_metrics(pose).status, TrackingStatus.PARTIAL_BODY)

    def test_angles_are_measured_in_pixels_not_normalised_units(self):
        # Wide, short picture. In 0..1 units this angle would come out ~153 degrees;
        # in real pixels the answer is 135 degrees.
        pose = make_pose(
            width=200, height=100,
            left_hip=Landmark(0.5, 0.0, 0, 0.99),
            left_knee=Landmark(0.5, 0.5, 0, 0.99),
            left_ankle=Landmark(0.75, 1.0, 0, 0.99),
            right_hip=None,
        )
        metrics = compute_squat_metrics(pose)
        self.assertAlmostEqual(metrics.left_knee_angle, 135.0, places=3)
        self.assertAlmostEqual(metrics.knee_angle, 135.0, places=3)

    def test_bent_knee_gives_smaller_angle(self):
        pose = make_pose(
            left_hip=Landmark(0.45, 0.45, 0, 0.99),
            left_knee=Landmark(0.65, 0.55, 0, 0.99),
            left_ankle=Landmark(0.45, 0.75, 0, 0.99),
            right_hip=None,
        )
        self.assertLess(compute_squat_metrics(pose).knee_angle, 120.0)


if __name__ == "__main__":
    unittest.main()
