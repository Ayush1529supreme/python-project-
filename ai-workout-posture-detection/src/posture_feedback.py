"""
posture_feedback.py - simple, rule-based messages.

Important: these messages only describe what the camera can reasonably infer
(is the body visible? which phase of the squat? is the knee angle changing
very fast?). They are NOT a judgement of exercise technique, and they are not
medical advice.
"""

from dataclasses import dataclass
from enum import Enum

from config import FEEDBACK, FeedbackSettings
from src.pose_metrics import TrackingStatus
from src.squat_counter import SquatState
from src.workout_session import SessionState


class FeedbackLevel(str, Enum):
    INFO = "INFO"
    GOOD = "GOOD"
    WARNING = "WARNING"


@dataclass(frozen=True)
class Feedback:
    message: str
    level: FeedbackLevel = FeedbackLevel.INFO


def generate_feedback(
    session_state: SessionState,
    tracking_status: TrackingStatus,
    squat_state: SquatState,
    angular_velocity: float = 0.0,
    settings: FeedbackSettings = FEEDBACK,
) -> Feedback:
    # Tracking problems come first: nothing else can be trusted without landmarks.
    if tracking_status == TrackingStatus.PARTIAL_BODY:
        return Feedback("Position yourself fully in the camera frame.", FeedbackLevel.WARNING)
    if tracking_status == TrackingStatus.NO_PERSON:
        if session_state == SessionState.ACTIVE:
            return Feedback("Tracking temporarily unavailable.", FeedbackLevel.WARNING)
        return Feedback("Position yourself fully in the camera frame.", FeedbackLevel.WARNING)

    # Body is tracked from here on.
    if session_state == SessionState.IDLE:
        return Feedback("Body detected - ready to start. Press S.", FeedbackLevel.GOOD)
    if session_state == SessionState.PAUSED:
        return Feedback("Session paused. Press P or S to resume.", FeedbackLevel.INFO)

    # Session is ACTIVE
    if squat_state == SquatState.WAITING:
        return Feedback("Stand up straight to begin.", FeedbackLevel.INFO)
    if squat_state == SquatState.STANDING:
        return Feedback("Begin your squat.", FeedbackLevel.INFO)

    moving = squat_state in (SquatState.DESCENDING, SquatState.ASCENDING)
    if (moving and settings.enable_speed_feedback
            and angular_velocity > settings.fast_movement_deg_per_sec):
        return Feedback("Keep your movement controlled.", FeedbackLevel.WARNING)

    if squat_state == SquatState.DESCENDING:
        return Feedback("Movement detected.", FeedbackLevel.INFO)
    return Feedback("Return to standing.", FeedbackLevel.INFO)  # BOTTOM or ASCENDING
