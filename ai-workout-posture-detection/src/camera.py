"""
camera.py - opens the webcam and gives us frames, with safe error handling.
"""

import sys

import cv2

from config import CAMERA, CameraSettings


class CameraError(RuntimeError):
    """Raised when the webcam cannot be opened or stops working."""


class Camera:
    def __init__(self, settings: CameraSettings = CAMERA):
        self.settings = settings
        self._capture = None
        self._failed_in_a_row = 0

    def open(self):
        """Open the webcam or raise CameraError with a helpful message."""
        # On macOS the AVFoundation backend is the native, most reliable choice.
        if sys.platform == "darwin":
            capture = cv2.VideoCapture(self.settings.index, cv2.CAP_AVFOUNDATION)
        else:
            capture = cv2.VideoCapture(self.settings.index)

        if not capture.isOpened():
            capture.release()
            raise CameraError(
                f"Could not open camera {self.settings.index}.\n"
                "  - Is a webcam connected and not used by another app (Zoom, FaceTime...)?\n"
                "  - On macOS: System Settings > Privacy & Security > Camera, and allow the app\n"
                "    that runs Python (Terminal, iTerm or Visual Studio Code). Then QUIT and\n"
                "    re-open that app and try again.\n"
                "  - Try another camera number:  python main.py --camera 1"
            )

        capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.settings.width)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.settings.height)
        self._capture = capture
        self._failed_in_a_row = 0
        return self

    def read(self):
        """Return the next frame (a NumPy BGR image), or None for one failed frame.

        A single failed frame is normal and is skipped. If too many fail in a row,
        CameraError is raised (camera unplugged, permission revoked, ...).
        """
        if self._capture is None:
            raise CameraError("The camera is not open.")
        ok, frame = self._capture.read()
        if not ok or frame is None:
            self._failed_in_a_row += 1
            if self._failed_in_a_row >= self.settings.max_failed_frames:
                raise CameraError(
                    f"The camera returned {self._failed_in_a_row} failed frames in a row. "
                    "It may have been disconnected or its permission was removed."
                )
            return None
        self._failed_in_a_row = 0
        return frame

    def release(self):
        """Safe to call many times."""
        if self._capture is not None:
            self._capture.release()
            self._capture = None

    def __enter__(self):
        return self.open()

    def __exit__(self, exc_type, exc, traceback):
        self.release()
        return False
