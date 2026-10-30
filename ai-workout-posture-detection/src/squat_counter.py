"""
squat_counter.py - the squat "state machine".

It receives ONE number per video frame (the knee angle) and decides which part
of the squat the person is in. It knows nothing about cameras or drawing, so it
can be tested with made-up angle lists.

States and how they connect:

    WAITING --(stand up)--> STANDING --(knee < descend_start)--> DESCENDING
        ^                       ^                                    |
        |                       | rep counted here           (knee <= bottom_angle
        |                       |                             for a few frames)
        |                  ASCENDING <--(knee > bottom_exit)-- BOTTOM <-+

A repetition is counted ONLY on the step ASCENDING -> STANDING. You can only
get into ASCENDING from BOTTOM, so a half squat can never be counted.
"""

from collections import deque
from enum import Enum
import math

from config import SQUAT, SquatSettings


class SquatState(str, Enum):
    WAITING = "WAITING"        # waiting to see the person standing first
    STANDING = "STANDING"
    DESCENDING = "DESCENDING"
    BOTTOM = "BOTTOM"
    ASCENDING = "ASCENDING"


class SquatCounter:
    def __init__(self, settings: SquatSettings = SQUAT):
        self.settings = settings
        self.rep_count = 0
        self.reset()

    # -- resetting -----------------------------------------------------------
    def reset(self):
        """Full reset: movement state AND repetition count."""
        self.rep_count = 0
        self.last_rep_min_angle = None   # deepest (smallest) knee angle of the last rep
        self.last_rejected_reason = None
        self.soft_reset()

    def soft_reset(self):
        """Forget the current movement but KEEP the repetition count.
        Used when tracking is lost, or when a session starts/resumes."""
        self.state = SquatState.WAITING
        self.smoothed_angle = None
        self.angular_velocity = 0.0      # degrees per second (always >= 0)
        self._recent_angles = deque(maxlen=self.settings.smoothing_window)
        self._lost_frames = 0
        self._frames_at_bottom = 0
        self._rep_start_time = None
        self._min_angle_this_rep = None
        self._previous_smoothed = None
        self._previous_time = None

    # -- main entry point ----------------------------------------------------
    def update(self, knee_angle, timestamp=None):
        """Feed one frame. Returns True only on the frame where a rep is counted.

        knee_angle : degrees, or None when the landmarks were not reliable.
        timestamp  : seconds (any increasing clock). Optional, but needed for
                     speed measurement and the "too fast to be real" check.
        """
        s = self.settings

        # 1) Missing / invalid measurement
        if knee_angle is None or not math.isfinite(knee_angle):
            self._lost_frames += 1
            if self._lost_frames >= s.lost_frames_before_reset:
                self.soft_reset()   # body gone for too long -> start clean
            return False
        self._lost_frames = 0

        # 2) Smooth the angle (average of the last few frames) to ignore jitter
        self._recent_angles.append(float(knee_angle))
        angle = sum(self._recent_angles) / len(self._recent_angles)
        self.smoothed_angle = angle

        # 3) Movement speed (ignored when two frames share a timestamp)
        if timestamp is not None and self._previous_time is not None:
            dt = timestamp - self._previous_time
            if dt > 0 and self._previous_smoothed is not None:
                self.angular_velocity = abs(angle - self._previous_smoothed) / dt
        self._previous_smoothed = angle
        self._previous_time = timestamp

        # 4) State machine
        rep_counted = False
        if self.state == SquatState.WAITING:
            if angle >= s.stand_angle:
                self.state = SquatState.STANDING

        elif self.state == SquatState.STANDING:
            if angle < s.descend_start_angle:
                self.state = SquatState.DESCENDING
                self._rep_start_time = timestamp
                self._frames_at_bottom = 0
                self._min_angle_this_rep = angle

        elif self.state == SquatState.DESCENDING:
            self._min_angle_this_rep = min(self._min_angle_this_rep, angle)
            if angle >= s.stand_angle:
                # Went down a little and came back up: NOT a repetition.
                self.state = SquatState.STANDING
                self._rep_start_time = None
            elif angle <= s.bottom_angle:
                self._frames_at_bottom += 1
                if self._frames_at_bottom >= s.min_frames_at_bottom:
                    self.state = SquatState.BOTTOM
            else:
                self._frames_at_bottom = 0

        elif self.state == SquatState.BOTTOM:
            self._min_angle_this_rep = min(self._min_angle_this_rep, angle)
            if angle > s.bottom_exit_angle:
                self.state = SquatState.ASCENDING

        elif self.state == SquatState.ASCENDING:
            if angle >= s.stand_angle:
                rep_counted = self._finish_repetition(timestamp)
                self.state = SquatState.STANDING
            elif angle <= s.bottom_angle:
                self.state = SquatState.BOTTOM   # bounced back down

        return rep_counted

    # -- helpers -------------------------------------------------------------
    def _finish_repetition(self, timestamp):
        """Count the rep unless it was impossibly fast (probably noise)."""
        too_fast = (
            timestamp is not None
            and self._rep_start_time is not None
            and (timestamp - self._rep_start_time) < self.settings.min_rep_duration_seconds
        )
        self._rep_start_time = None
        if too_fast:
            self.last_rejected_reason = "too fast"
            return False
        self.rep_count += 1
        self.last_rep_min_angle = self._min_angle_this_rep
        self.last_rejected_reason = None
        return True
