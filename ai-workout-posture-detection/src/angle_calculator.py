"""
angle_calculator.py - pure geometry, no camera and no AI here.

The angle at point B formed by points A, B, C:

    A
     \\
      \\
       B ------ C

We turn A->B and C->B into two arrows (vectors) that start at B.
The "dot product" of two arrows tells us how much they point the same way:

    cos(angle) = (BA . BC) / (|BA| * |BC|)     ->     angle = acos(...)

Example for a squat: A = hip, B = knee, C = ankle.
Straight leg  -> about 180 degrees.   Deeply bent knee -> small angle.
"""

import math

import numpy as np


def calculate_angle(point_a, point_b, point_c):
    """Return the angle (in degrees, 0..180) at point_b, or None if it can't be computed.

    Each point is a sequence of 2 numbers (x, y) or 3 numbers (x, y, z).
    None is returned (instead of crashing) for: missing points (None), wrong
    shapes, NaN/infinite values, or two points on the same spot.
    """
    try:
        a = np.asarray(point_a, dtype=float)
        b = np.asarray(point_b, dtype=float)
        c = np.asarray(point_c, dtype=float)
    except (TypeError, ValueError):
        return None

    # All three must be 1-D with the same length, and that length must be 2 or 3.
    if not (a.ndim == b.ndim == c.ndim == 1):
        return None
    if not (a.shape == b.shape == c.shape) or a.size not in (2, 3):
        return None
    if not (np.all(np.isfinite(a)) and np.all(np.isfinite(b)) and np.all(np.isfinite(c))):
        return None

    ba = a - b  # arrow from the middle point to the first point
    bc = c - b  # arrow from the middle point to the last point
    length_ba = float(np.linalg.norm(ba))
    length_bc = float(np.linalg.norm(bc))
    if length_ba < 1e-9 or length_bc < 1e-9:
        return None  # an arrow of length zero has no direction

    cosine = float(np.dot(ba, bc)) / (length_ba * length_bc)
    cosine = max(-1.0, min(1.0, cosine))  # protect acos from tiny rounding errors
    return math.degrees(math.acos(cosine))
