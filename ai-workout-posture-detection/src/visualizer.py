"""
visualizer.py - everything that is DRAWN on the video: skeleton, counter,
status text, feedback bar and keyboard hints. No logic about squats here.
"""

from dataclasses import dataclass
from typing import Optional

import cv2

from config import POSE, PoseSettings, WINDOW_NAME
from src.pose_detector import LANDMARK_INDEX, PoseResult
from src.posture_feedback import Feedback, FeedbackLevel
from src.pose_metrics import SquatMetrics, TrackingStatus
from src.workout_session import SessionState

# Colours are BGR (OpenCV order), not RGB.
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (80, 220, 100)
YELLOW = (0, 215, 255)
ORANGE = (0, 140, 255)
RED = (60, 60, 230)
GREY = (170, 170, 170)
DARK_PANEL = (30, 30, 30)
FONT = cv2.FONT_HERSHEY_SIMPLEX

# Pairs of landmark indexes that are joined by a line (arms, torso, legs, feet).
SKELETON_CONNECTIONS = [
    (11, 12), (11, 13), (13, 15), (12, 14), (14, 16),   # shoulders and arms
    (11, 23), (12, 24), (23, 24),                       # torso
    (23, 25), (25, 27), (24, 26), (26, 28),             # legs
    (27, 29), (29, 31), (27, 31), (28, 30), (30, 32), (28, 32),  # feet
]
SQUAT_LANDMARKS = set(LANDMARK_INDEX.values())

SESSION_COLOURS = {
    SessionState.IDLE: GREY,
    SessionState.ACTIVE: GREEN,
    SessionState.PAUSED: YELLOW,
}
FEEDBACK_COLOURS = {
    FeedbackLevel.INFO: WHITE,
    FeedbackLevel.GOOD: GREEN,
    FeedbackLevel.WARNING: ORANGE,
}


@dataclass
class HudData:
    """Everything the on-screen display needs for one frame."""
    session_state: SessionState
    rep_count: int
    squat_state: str
    knee_angle: Optional[float]
    elapsed_seconds: float
    average_depth_angle: Optional[float]
    tracking_status: TrackingStatus
    feedback: Feedback
    fps: float = 0.0
    rep_flash: bool = False   # True for a short moment after a rep is counted


def _text(frame, text, origin, scale, colour, thickness=1):
    """Text with a dark outline so it stays readable on any background."""
    cv2.putText(frame, text, origin, FONT, scale, BLACK, thickness + 3, cv2.LINE_AA)
    cv2.putText(frame, text, origin, FONT, scale, colour, thickness, cv2.LINE_AA)


def _panel(frame, top_left, bottom_right, alpha=0.55):
    """Semi-transparent dark rectangle behind text."""
    x1, y1 = top_left
    x2, y2 = bottom_right
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(frame.shape[1], x2), min(frame.shape[0], y2)
    if x2 <= x1 or y2 <= y1:
        return
    region = frame[y1:y2, x1:x2]
    overlay = region.copy()
    overlay[:] = DARK_PANEL
    cv2.addWeighted(overlay, alpha, region, 1 - alpha, 0, dst=region)


def draw_skeleton(frame, pose: PoseResult, metrics: SquatMetrics,
                  settings: PoseSettings = POSE):
    """Draw lines and dots for reliable landmarks only."""
    if not pose.person_detected:
        return
    h, w = frame.shape[:2]
    min_vis = settings.min_landmark_visibility

    def point(index):
        lm = pose.landmarks[index]
        return int(lm.x * w), int(lm.y * h), lm.visibility >= min_vis

    for a, b in SKELETON_CONNECTIONS:
        xa, ya, ok_a = point(a)
        xb, yb, ok_b = point(b)
        if ok_a and ok_b:
            cv2.line(frame, (xa, ya), (xb, yb), GREEN, 3, cv2.LINE_AA)

    for index in range(len(pose.landmarks)):
        if index < 11:      # skip face points to keep the picture clean
            continue
        x, y, ok = point(index)
        if not ok:
            continue
        radius = 7 if index in SQUAT_LANDMARKS else 4
        colour = YELLOW if index in SQUAT_LANDMARKS else WHITE
        cv2.circle(frame, (x, y), radius, colour, -1, cv2.LINE_AA)

    # Knee angle next to each measured knee
    for side, angle in (("left", metrics.left_knee_angle), ("right", metrics.right_knee_angle)):
        if angle is not None:
            x, y = pose.pixel_point(f"{side}_knee")
            _text(frame, f"{angle:.0f}", (int(x) + 12, int(y) - 12), 0.7, YELLOW, 2)


def draw_hud(frame, hud: HudData):
    """Draw the whole interface on top of the video frame."""
    h, w = frame.shape[:2]
    s = h / 720.0                      # scale text with the picture size

    # ---- Top bar: title, session state, timer ----
    _panel(frame, (0, 0), (w, int(52 * s)), alpha=0.65)
    _text(frame, "AI Workout Posture Detection", (int(16 * s), int(35 * s)), 0.9 * s, WHITE, 2)
    state_colour = SESSION_COLOURS[hud.session_state]
    minutes, seconds = divmod(int(hud.elapsed_seconds), 60)
    top_right = f"{hud.session_state.value}   {minutes:02d}:{seconds:02d}"
    size = cv2.getTextSize(top_right, FONT, 0.9 * s, 2)[0]
    _text(frame, top_right, (w - size[0] - int(16 * s), int(35 * s)), 0.9 * s, state_colour, 2)

    # ---- Left panel: big repetition counter and details ----
    panel_w, panel_h = int(300 * s), int(262 * s)
    top = int(70 * s)
    _panel(frame, (int(12 * s), top), (int(12 * s) + panel_w, top + panel_h))
    _text(frame, "SQUAT REPS", (int(28 * s), top + int(32 * s)), 0.8 * s, GREY, 2)
    counter_colour = GREEN if hud.rep_flash else WHITE
    _text(frame, str(hud.rep_count), (int(28 * s), top + int(150 * s)), 4.0 * s, counter_colour, 8)
    _text(frame, f"State: {hud.squat_state}", (int(28 * s), top + int(188 * s)), 0.7 * s, WHITE, 2)
    angle_text = f"{hud.knee_angle:.0f} deg" if hud.knee_angle is not None else "--"
    _text(frame, f"Knee angle: {angle_text}", (int(28 * s), top + int(218 * s)), 0.7 * s, WHITE, 2)
    depth_text = (f"{hud.average_depth_angle:.0f} deg"
                  if hud.average_depth_angle is not None else "--")
    _text(frame, f"Avg depth: {depth_text}", (int(28 * s), top + int(246 * s)), 0.7 * s, WHITE, 2)

    # ---- Tracking indicator (top right, under the bar) ----
    tracking_colours = {
        TrackingStatus.OK: (GREEN, "Tracking: OK"),
        TrackingStatus.PARTIAL_BODY: (ORANGE, "Tracking: body not fully visible"),
        TrackingStatus.NO_PERSON: (RED, "Tracking: no person found"),
    }
    colour, label = tracking_colours[hud.tracking_status]
    size = cv2.getTextSize(label, FONT, 0.7 * s, 2)[0]
    _panel(frame, (w - size[0] - int(52 * s), int(64 * s)), (w - int(8 * s), int(100 * s)))
    cv2.circle(frame, (w - size[0] - int(34 * s), int(82 * s)), int(8 * s), colour, -1, cv2.LINE_AA)
    _text(frame, label, (w - size[0] - int(18 * s), int(89 * s)), 0.7 * s, colour, 2)
    _text(frame, f"{hud.fps:.0f} FPS", (w - int(95 * s), int(124 * s)), 0.6 * s, GREY, 1)

    # ---- Bottom: feedback bar and keyboard shortcuts ----
    _panel(frame, (0, h - int(110 * s)), (w, h - int(40 * s)), alpha=0.65)
    _text(frame, hud.feedback.message, (int(20 * s), h - int(62 * s)), 1.0 * s,
          FEEDBACK_COLOURS[hud.feedback.level], 2)
    _panel(frame, (0, h - int(40 * s)), (w, h), alpha=0.75)
    _text(frame, "[S] Start/Resume   [P] Pause   [R] Reset   [Q] Quit",
          (int(20 * s), h - int(14 * s)), 0.7 * s, WHITE, 1)
