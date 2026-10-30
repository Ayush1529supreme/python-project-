import random
import unittest

from config import SquatSettings
from src.squat_counter import SquatCounter, SquatState

FPS = 30.0


def ramp(start, end, frames):
    """Straight-line list of angles from start to end (end included)."""
    return [start + (end - start) * (i + 1) / frames for i in range(frames)]


def full_squat(top=175.0, bottom=85.0, down=30, hold=8, up=30):
    """Angles for one complete squat, starting and ending at 'top'."""
    return ramp(top, bottom, down) + [bottom] * hold + ramp(bottom, top, up)


def feed(counter, angles, start_time=0.0):
    """Feed angles at 30 FPS. Returns the number of reps counted by these frames."""
    counted = 0
    for i, angle in enumerate(angles):
        if counter.update(angle, start_time + i / FPS):
            counted += 1
    return counted


class SquatCounterTests(unittest.TestCase):
    def setUp(self):
        self.counter = SquatCounter()
        feed(self.counter, [175.0] * 5)   # stand still first
        self.assertEqual(self.counter.state, SquatState.STANDING)

    def test_complete_cycle_counts_one(self):
        counted = feed(self.counter, full_squat(), start_time=1.0)
        self.assertEqual(counted, 1)
        self.assertEqual(self.counter.rep_count, 1)
        self.assertEqual(self.counter.state, SquatState.STANDING)

    def test_states_are_visited_in_order(self):
        seen = []
        for i, angle in enumerate(full_squat()):
            self.counter.update(angle, 1.0 + i / FPS)
            if not seen or seen[-1] != self.counter.state:
                seen.append(self.counter.state)
        self.assertEqual(seen, [SquatState.STANDING, SquatState.DESCENDING, SquatState.BOTTOM,
                                SquatState.ASCENDING, SquatState.STANDING])

    def test_two_cycles_count_two(self):
        feed(self.counter, full_squat() + [175.0] * 5 + full_squat(), start_time=1.0)
        self.assertEqual(self.counter.rep_count, 2)

    def test_incomplete_movement_is_not_counted(self):
        half = ramp(175, 125, 20) + [125] * 6 + ramp(125, 175, 20)   # never reaches 100
        feed(self.counter, half, start_time=1.0)
        self.assertEqual(self.counter.rep_count, 0)
        self.assertEqual(self.counter.state, SquatState.STANDING)

    def test_going_down_and_staying_down_is_not_counted(self):
        feed(self.counter, ramp(175, 85, 30) + [85] * 60, start_time=1.0)
        self.assertEqual(self.counter.rep_count, 0)
        self.assertEqual(self.counter.state, SquatState.BOTTOM)

    def test_repeated_frames_in_same_position_never_add_counts(self):
        feed(self.counter, full_squat(), start_time=1.0)
        feed(self.counter, [175.0] * 200, start_time=10.0)   # standing for a long time
        self.assertEqual(self.counter.rep_count, 1)
        feed(self.counter, [85.0] * 5, start_time=20.0)
        self.assertEqual(self.counter.rep_count, 1)

    def test_identical_timestamps_do_not_crash_or_double_count(self):
        for angle in full_squat():
            self.counter.update(angle, 5.0)    # same timestamp every frame
        self.assertEqual(self.counter.rep_count, 0)   # also too "fast" -> rejected
        self.assertGreaterEqual(self.counter.angular_velocity, 0.0)

    def test_single_frame_spike_is_ignored(self):
        feed(self.counter, [175, 175, 80, 175, 175, 175], start_time=1.0)
        self.assertEqual(self.counter.rep_count, 0)

    def test_jitter_around_standing_threshold_is_ignored(self):
        jitter = [152.0, 168.0] * 30
        feed(self.counter, jitter, start_time=1.0)
        self.assertEqual(self.counter.rep_count, 0)

    def test_noisy_full_squat_still_counts_exactly_once(self):
        rng = random.Random(42)
        noisy = [a + rng.uniform(-4, 4) for a in full_squat(down=40, up=40)]
        feed(self.counter, noisy, start_time=1.0)
        self.assertEqual(self.counter.rep_count, 1)

    def test_must_see_standing_before_counting(self):
        counter = SquatCounter()
        feed(counter, [90.0] * 10)              # starts already squatting
        self.assertEqual(counter.state, SquatState.WAITING)
        feed(counter, ramp(90, 175, 30))        # stands up: not a repetition
        self.assertEqual(counter.rep_count, 0)
        self.assertEqual(counter.state, SquatState.STANDING)

    def test_too_fast_cycle_is_rejected_as_noise(self):
        fast = [175, 120, 80, 80, 120, 175, 175]
        feed(self.counter, fast, start_time=1.0)   # whole thing takes ~0.2 s
        self.assertEqual(self.counter.rep_count, 0)

    def test_short_missing_landmarks_keep_the_movement(self):
        angles = full_squat()
        half = len(angles) // 2
        feed(self.counter, angles[:half], start_time=1.0)
        for _ in range(5):                          # a few lost frames
            self.assertFalse(self.counter.update(None, 2.0))
        feed(self.counter, angles[half:], start_time=3.0)
        self.assertEqual(self.counter.rep_count, 1)

    def test_long_missing_landmarks_reset_the_state_but_keep_the_count(self):
        feed(self.counter, full_squat(), start_time=1.0)
        self.assertEqual(self.counter.rep_count, 1)
        feed(self.counter, ramp(175, 120, 15), start_time=5.0)   # mid-movement
        for _ in range(self.counter.settings.lost_frames_before_reset):
            self.counter.update(None, 6.0)
        self.assertEqual(self.counter.state, SquatState.WAITING)
        self.assertEqual(self.counter.rep_count, 1)
        # After returning, the leftover half-movement cannot complete a rep.
        feed(self.counter, ramp(120, 175, 15), start_time=8.0)
        self.assertEqual(self.counter.rep_count, 1)

    def test_nan_angle_is_treated_as_missing(self):
        self.assertFalse(self.counter.update(float("nan"), 1.0))
        self.assertEqual(self.counter.state, SquatState.STANDING)

    def test_reset_clears_count_and_state(self):
        feed(self.counter, full_squat(), start_time=1.0)
        self.counter.reset()
        self.assertEqual(self.counter.rep_count, 0)
        self.assertEqual(self.counter.state, SquatState.WAITING)
        self.assertIsNone(self.counter.smoothed_angle)

    def test_last_rep_depth_is_recorded(self):
        feed(self.counter, full_squat(bottom=88.0), start_time=1.0)
        self.assertAlmostEqual(self.counter.last_rep_min_angle, 88.0, delta=2.0)

    def test_speed_is_measured(self):
        feed(self.counter, ramp(175, 85, 30), start_time=1.0)   # 90 deg in 1 s
        self.assertGreater(self.counter.angular_velocity, 50)

    def test_custom_thresholds_are_respected(self):
        easy = SquatSettings(stand_angle=150, descend_start_angle=140,
                             bottom_angle=120, bottom_exit_angle=125)
        counter = SquatCounter(easy)
        feed(counter, [165.0] * 5)
        feed(counter, ramp(165, 110, 30) + [110] * 5 + ramp(110, 165, 30), start_time=1.0)
        self.assertEqual(counter.rep_count, 1)

    def test_invalid_settings_are_rejected(self):
        with self.assertRaises(ValueError):
            SquatSettings(stand_angle=100, bottom_angle=120)
        with self.assertRaises(ValueError):
            SquatSettings(smoothing_window=0)


if __name__ == "__main__":
    unittest.main()
