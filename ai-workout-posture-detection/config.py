"""
config.py - every setting you may want to change lives here.

Beginner tip: if the app counts too easily or too hard, change the numbers in
SquatSettings (angles are in degrees). Nobody's squat is identical, and a
webcam only sees a flat 2D picture, so these numbers are starting points,
not "correct" values.
"""

from dataclasses import dataclass
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths (always built from the project folder, never from a fixed absolute path)
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent
MODEL_PATH = PROJECT_ROOT / "models" / "pose_landmarker_lite.task"
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
    "pose_landmarker_lite/float16/latest/pose_landmarker_lite.task"
)
DATABASE_PATH = PROJECT_ROOT / "data" / "workouts.db"

# ---------------------------------------------------------------------------
# Application window
# ---------------------------------------------------------------------------
WINDOW_NAME = "AI Workout Posture Detection System"
MIRROR_VIEW = True  # flip the picture like a mirror (feels natural when exercising)


@dataclass(frozen=True)
class CameraSettings:
    index: int = 0                  # 0 = default webcam
    width: int = 1280               # requested size (the camera may choose another)
    height: int = 720
    max_failed_frames: int = 30     # stop if this many frames in a row fail


@dataclass(frozen=True)
class PoseSettings:
    min_detection_confidence: float = 0.5
    min_presence_confidence: float = 0.5
    min_tracking_confidence: float = 0.5
    # A landmark is only used if MediaPipe is at least this sure it is visible.
    min_landmark_visibility: float = 0.5
    # A landmark must also lie inside the picture (0..1) with this small tolerance.
    frame_edge_tolerance: float = 0.01


@dataclass(frozen=True)
class SquatSettings:
    """Knee angle = angle at the knee between the hip and the ankle.
    About 180 = leg straight, smaller = more bent."""

    stand_angle: float = 160.0          # at/above this = standing
    descend_start_angle: float = 150.0  # below this (from standing) = going down
    bottom_angle: float = 100.0         # at/below this = low squat position
    bottom_exit_angle: float = 110.0    # above this (from bottom) = going up
    min_frames_at_bottom: int = 2       # frames needed at the bottom (anti-jitter)
    smoothing_window: int = 3           # average the last N angles (anti-jitter)
    lost_frames_before_reset: int = 15  # frames without tracking before state resets
    min_rep_duration_seconds: float = 0.6  # faster "reps" are treated as noise

    def __post_init__(self):
        if not (self.bottom_angle < self.bottom_exit_angle
                < self.descend_start_angle < self.stand_angle):
            raise ValueError(
                "Angles must satisfy: bottom_angle < bottom_exit_angle < "
                "descend_start_angle < stand_angle"
            )
        if self.smoothing_window < 1 or self.min_frames_at_bottom < 1:
            raise ValueError("smoothing_window and min_frames_at_bottom must be >= 1")
        if self.lost_frames_before_reset < 1:
            raise ValueError("lost_frames_before_reset must be >= 1")


@dataclass(frozen=True)
class FeedbackSettings:
    enable_speed_feedback: bool = True
    # Knee angle changing faster than this (degrees per second) = "not controlled".
    fast_movement_deg_per_sec: float = 220.0


@dataclass(frozen=True)
class StorageSettings:
    save_sessions: bool = True  # saves ONLY date, duration and rep count (never video)


# Ready-to-use default instances
CAMERA = CameraSettings()
POSE = PoseSettings()
SQUAT = SquatSettings()
FEEDBACK = FeedbackSettings()
STORAGE = StorageSettings()
