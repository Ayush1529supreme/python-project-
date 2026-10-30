"""
pose_metrics.py - turns raw landmarks into the numbers the squat logic needs.

(This file is an addition to the suggested structure. It keeps "reading the
body" separate from both the AI model and the squat state machine.)

Rules (conservative on purpose):
  * A landmark is "reliable" only if its visibility is high enough AND it lies
    inside the picture.
  * A side (left or right) is usable only if its shoulder, hip, knee AND ankle
    are all reliable. Only usable sides are measured.
  * If neither side is usable we do NOT calculate anything.
  * With two usable sides, the knee angle is the average of both.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from config import POSE, PoseSettings
from src.angle_calculator import calculate_angle
from src.pose_detector import PoseResult


class TrackingStatus(str, Enum):
    NO_PERSON = "NO_PERSON"          # model found nobody
    PARTIAL_BODY = "PARTIAL_BODY"    # someone found, but not enough reliable points
    OK = "OK"                        # at least one full side is reliable


@dataclass
class SquatMetrics:
    status: TrackingStatus
    knee_angle: Optional[float] = None
    left_knee_angle: Optional[float] = None
    right_knee_angle: Optional[float] = None
    full_body_visible: bool = False  # all 8 landmarks reliable (both sides)

    @property
    def tracking_ok(self) -> bool:
        return self.status == TrackingStatus.OK and self.knee_angle is not None


def _is_reliable(landmark, settings: PoseSettings) -> bool:
    if landmark is None:
        return False
    tolerance = settings.frame_edge_tolerance
    inside = (-tolerance <= landmark.x <= 1 + tolerance
              and -tolerance <= landmark.y <= 1 + tolerance)
    return inside and landmark.visibility >= settings.min_landmark_visibility


def _side_knee_angle(pose: PoseResult, side: str, settings: PoseSettings):
    """Knee angle for one side, or None if that side isn't fully reliable."""
    names = [f"{side}_{part}" for part in ("shoulder", "hip", "knee", "ankle")]
    if not all(_is_reliable(pose.get(name), settings) for name in names):
        return None
    return calculate_angle(
        pose.pixel_point(f"{side}_hip"),
        pose.pixel_point(f"{side}_knee"),
        pose.pixel_point(f"{side}_ankle"),
    )


def compute_squat_metrics(pose: PoseResult, settings: PoseSettings = POSE) -> SquatMetrics:
    if not pose.person_detected:
        return SquatMetrics(status=TrackingStatus.NO_PERSON)

    left = _side_knee_angle(pose, "left", settings)
    right = _side_knee_angle(pose, "right", settings)
    usable = [angle for angle in (left, right) if angle is not None]

    all_names = [f"{side}_{part}" for side in ("left", "right")
                 for part in ("shoulder", "hip", "knee", "ankle")]
    full_body = all(_is_reliable(pose.get(name), settings) for name in all_names)

    if not usable:
        return SquatMetrics(status=TrackingStatus.PARTIAL_BODY, full_body_visible=full_body)

    return SquatMetrics(
        status=TrackingStatus.OK,
        knee_angle=sum(usable) / len(usable),
        left_knee_angle=left,
        right_knee_angle=right,
        full_body_visible=full_body,
    )
