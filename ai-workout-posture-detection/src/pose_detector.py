"""
pose_detector.py - wraps MediaPipe Pose Landmarker (the pretrained AI model).

What it does:  camera picture in  ->  33 body landmarks out.
Each landmark has x, y (0..1 across the picture), z (depth, rough) and a
"visibility" score (how sure the model is that the point can be seen).

The heavy `mediapipe` import happens INSIDE PoseDetector.__init__, so the rest
of the project (and the unit tests) work even without MediaPipe installed.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import cv2

from config import POSE, PoseSettings

# Index numbers of the landmarks we need (from the MediaPipe pose landmark map).
LANDMARK_INDEX = {
    "left_shoulder": 11, "right_shoulder": 12,
    "left_hip": 23, "right_hip": 24,
    "left_knee": 25, "right_knee": 26,
    "left_ankle": 27, "right_ankle": 28,
}
NUM_LANDMARKS = 33


class PoseDetectorError(RuntimeError):
    """Raised for any problem starting or running the pose model."""


@dataclass
class Landmark:
    x: float            # 0..1 from left to right of the picture
    y: float            # 0..1 from top to bottom of the picture
    z: float = 0.0
    visibility: float = 0.0


@dataclass
class PoseResult:
    landmarks: List[Landmark] = field(default_factory=list)  # empty = nobody found
    frame_width: int = 1
    frame_height: int = 1

    @property
    def person_detected(self) -> bool:
        return len(self.landmarks) == NUM_LANDMARKS

    def get(self, name: str) -> Optional[Landmark]:
        """Landmark by name (e.g. 'left_knee'), or None if there is no person."""
        if not self.person_detected:
            return None
        return self.landmarks[LANDMARK_INDEX[name]]

    def pixel_point(self, name: str):
        """(x, y) in PIXELS. We measure angles in pixels because the picture is
        wider than it is tall; using 0..1 values would distort the angles."""
        landmark = self.get(name)
        if landmark is None:
            return None
        return (landmark.x * self.frame_width, landmark.y * self.frame_height)


class PoseDetector:
    def __init__(self, model_path, settings: PoseSettings = POSE):
        model_path = Path(model_path)
        if not model_path.is_file():
            raise PoseDetectorError(
                f"Model file not found: {model_path}\n"
                "Download it first with:  python scripts/download_model.py\n"
                "(see models/README.md for the manual download link)"
            )
        try:
            import mediapipe as mp
        except ImportError as error:
            raise PoseDetectorError(
                "The 'mediapipe' package is not installed in this Python environment.\n"
                "Activate your virtual environment and run:  pip install -r requirements.txt"
            ) from error

        self._mp = mp
        self._last_timestamp_ms = -1
        try:
            options = mp.tasks.vision.PoseLandmarkerOptions(
                base_options=mp.tasks.BaseOptions(model_asset_path=str(model_path)),
                running_mode=mp.tasks.vision.RunningMode.VIDEO,  # video = tracks between frames
                num_poses=1,
                min_pose_detection_confidence=settings.min_detection_confidence,
                min_pose_presence_confidence=settings.min_presence_confidence,
                min_tracking_confidence=settings.min_tracking_confidence,
            )
            self._landmarker = mp.tasks.vision.PoseLandmarker.create_from_options(options)
        except Exception as error:  # MediaPipe raises several different error types
            raise PoseDetectorError(
                f"Could not start the pose model ({error}).\n"
                "The model file may be damaged - delete it and download it again."
            ) from error

    def detect(self, frame_bgr, timestamp_ms: int) -> PoseResult:
        """Find the body in one OpenCV (BGR) frame."""
        height, width = frame_bgr.shape[:2]

        # MediaPipe wants RGB; OpenCV gives BGR.
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=rgb)

        # In VIDEO mode timestamps must strictly increase.
        timestamp_ms = max(int(timestamp_ms), self._last_timestamp_ms + 1)
        self._last_timestamp_ms = timestamp_ms

        result = self._landmarker.detect_for_video(mp_image, timestamp_ms)
        if not result.pose_landmarks:
            return PoseResult(frame_width=width, frame_height=height)

        landmarks = [
            Landmark(x=p.x, y=p.y, z=p.z, visibility=(p.visibility or 0.0))
            for p in result.pose_landmarks[0]
        ]
        return PoseResult(landmarks=landmarks, frame_width=width, frame_height=height)

    def close(self):
        landmarker = getattr(self, "_landmarker", None)
        if landmarker is not None:
            landmarker.close()
            self._landmarker = None
