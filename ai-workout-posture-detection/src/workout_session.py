"""
workout_session.py - session state (idle / active / paused), timer, statistics.

The session owns the SquatCounter. While the session is not ACTIVE it simply
does not pass any angles to the counter, so nothing can be counted.
"""

from collections import deque
from datetime import datetime
from enum import Enum
import time

from src.squat_counter import SquatCounter


class SessionState(str, Enum):
    IDLE = "IDLE"        # not started yet
    ACTIVE = "ACTIVE"    # counting
    PAUSED = "PAUSED"    # timer stopped, counting off


class WorkoutSession:
    def __init__(self, counter=None, clock=time.monotonic):
        self.counter = counter if counter is not None else SquatCounter()
        self._clock = clock               # injectable so tests can fake time
        self.state = SessionState.IDLE
        self.started_at = None            # wall-clock datetime of the first start
        self._reset_statistics()

    # -- controls ------------------------------------------------------------
    def start(self) -> bool:
        """'S' key: start (from IDLE) or resume (from PAUSED). Returns True if changed."""
        if self.state == SessionState.ACTIVE:
            return False
        if self.started_at is None:
            self.started_at = datetime.now()
        self.state = SessionState.ACTIVE
        self._active_since = self._clock()
        self.counter.soft_reset()  # forget stale movement from before the pause
        return True

    def toggle_pause(self) -> bool:
        """'P' key: ACTIVE <-> PAUSED. Does nothing before the session started."""
        if self.state == SessionState.ACTIVE:
            self._accumulated += self._clock() - self._active_since
            self._active_since = None
            self.state = SessionState.PAUSED
            return True
        if self.state == SessionState.PAUSED:
            return self.start()
        return False

    def reset(self):
        """'R' key: zero the repetitions, timer and statistics. The session state
        (idle / active / paused) stays as it is."""
        self.counter.reset()
        self._reset_statistics()
        if self.state == SessionState.ACTIVE:
            self._active_since = self._clock()

    # -- per-frame update ----------------------------------------------------
    def process_frame(self, knee_angle, timestamp=None) -> bool:
        """Give this frame's knee angle (or None). Returns True if a rep was counted."""
        if self.state != SessionState.ACTIVE:
            return False  # paused or not started: never count
        if timestamp is None:
            timestamp = self._clock()

        rep_counted = self.counter.update(knee_angle, timestamp)

        if self.counter.smoothed_angle is not None and knee_angle is not None:
            self._recent_angles.append(self.counter.smoothed_angle)
        if rep_counted and self.counter.last_rep_min_angle is not None:
            self._rep_depths.append(self.counter.last_rep_min_angle)
        return rep_counted

    # -- statistics ----------------------------------------------------------
    @property
    def rep_count(self) -> int:
        return self.counter.rep_count

    @property
    def elapsed_seconds(self) -> float:
        total = self._accumulated
        if self.state == SessionState.ACTIVE and self._active_since is not None:
            total += self._clock() - self._active_since
        return total

    @property
    def average_recent_angle(self):
        """Average of the last ~30 knee angles, or None if there are none yet."""
        if not self._recent_angles:
            return None
        return sum(self._recent_angles) / len(self._recent_angles)

    @property
    def average_depth_angle(self):
        """Average deepest knee angle over all counted reps (smaller = deeper)."""
        if not self._rep_depths:
            return None
        return sum(self._rep_depths) / len(self._rep_depths)

    @property
    def was_started(self) -> bool:
        return self.started_at is not None

    def summary(self) -> dict:
        return {
            "started_at": (self.started_at or datetime.now()).isoformat(timespec="seconds"),
            "duration_seconds": round(self.elapsed_seconds, 1),
            "squat_reps": self.rep_count,
            "avg_depth_angle": (round(self.average_depth_angle, 1)
                                if self.average_depth_angle is not None else None),
        }

    def _reset_statistics(self):
        self._accumulated = 0.0
        self._active_since = None
        self._recent_angles = deque(maxlen=30)
        self._rep_depths = []
