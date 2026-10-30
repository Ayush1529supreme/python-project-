import math
import unittest

from src.angle_calculator import calculate_angle


class CalculateAngleTests(unittest.TestCase):
    def test_right_angle(self):
        self.assertAlmostEqual(calculate_angle((0, 1), (0, 0), (1, 0)), 90.0, places=6)

    def test_straight_line_is_180(self):
        self.assertAlmostEqual(calculate_angle((0, 0), (1, 0), (2, 0)), 180.0, places=6)

    def test_fully_folded_is_0(self):
        self.assertAlmostEqual(calculate_angle((1, 0), (0, 0), (2, 0)), 0.0, places=4)

    def test_45_degrees(self):
        self.assertAlmostEqual(calculate_angle((1, 1), (0, 0), (1, 0)), 45.0, places=6)

    def test_squat_example_hip_knee_ankle(self):
        # Hip above the knee, ankle below and slightly behind: a clearly bent leg.
        angle = calculate_angle((0.0, 0.0), (0.0, 1.0), (-1.0, 1.0))
        self.assertAlmostEqual(angle, 90.0, places=6)

    def test_three_dimensional_points(self):
        self.assertAlmostEqual(calculate_angle((1, 0, 0), (0, 0, 0), (0, 1, 0)), 90.0, places=6)

    def test_result_does_not_depend_on_scale(self):
        small = calculate_angle((0, 1), (0, 0), (1, 1))
        large = calculate_angle((0, 100), (0, 0), (100, 100))
        self.assertAlmostEqual(small, large, places=6)

    def test_order_of_end_points_does_not_matter(self):
        a, b, c = (3, 4), (0, 0), (5, -2)
        self.assertAlmostEqual(calculate_angle(a, b, c), calculate_angle(c, b, a), places=9)

    def test_missing_point_returns_none(self):
        self.assertIsNone(calculate_angle(None, (0, 0), (1, 0)))
        self.assertIsNone(calculate_angle((0, 1), None, (1, 0)))
        self.assertIsNone(calculate_angle((0, 1), (0, 0), None))

    def test_invalid_inputs_return_none(self):
        self.assertIsNone(calculate_angle((0, 1), (0, 0), (1,)))            # wrong length
        self.assertIsNone(calculate_angle((0, 1), (0, 0), (1, 0, 0)))       # mixed 2D / 3D
        self.assertIsNone(calculate_angle("abc", (0, 0), (1, 0)))           # not numbers
        self.assertIsNone(calculate_angle((0, 1, 2, 3), (0, 0, 0, 0), (1, 0, 0, 0)))
        self.assertIsNone(calculate_angle([[0, 1]], (0, 0), (1, 0)))        # 2-D array

    def test_nan_and_infinite_return_none(self):
        self.assertIsNone(calculate_angle((math.nan, 1), (0, 0), (1, 0)))
        self.assertIsNone(calculate_angle((0, 1), (0, 0), (math.inf, 0)))

    def test_identical_points_return_none(self):
        self.assertIsNone(calculate_angle((0, 0), (0, 0), (1, 0)))
        self.assertIsNone(calculate_angle((1, 1), (1, 1), (1, 1)))

    def test_result_always_between_0_and_180(self):
        for a, b, c in [((5, 5), (1, 2), (-3, 7)), ((0, -4), (2, 2), (9, 1))]:
            angle = calculate_angle(a, b, c)
            self.assertGreaterEqual(angle, 0.0)
            self.assertLessEqual(angle, 180.0)


if __name__ == "__main__":
    unittest.main()
