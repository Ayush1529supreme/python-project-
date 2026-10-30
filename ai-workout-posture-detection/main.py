"""
main.py - starts the app and runs the main loop.

Each loop turn (one video frame):
  1. read a camera frame
  2. find body landmarks (AI)
  3. calculate the knee angle from reliable landmarks
  4. update the session / squat counter
  5. choose a feedback message
  6. draw everything and handle key presses
"""

import argparse
import sys
import time
import traceback
from dataclasses import replace

import cv2

import config
from src.camera import Camera, CameraError
from src.pose_detector import PoseDetector, PoseDetectorError
from src.pose_metrics import compute_squat_metrics
from src.posture_feedback import generate_feedback
from src.session_storage import SessionStorage
from src.visualizer import HudData, draw_hud, draw_skeleton
from src.workout_session import SessionState, WorkoutSession

REP_FLASH_SECONDS = 0.6


def parse_arguments():
    parser = argparse.ArgumentParser(description="AI Workout Posture Detection System")
    parser.add_argument("--camera", type=int, default=config.CAMERA.index,
                        help="camera number (default 0)")
    parser.add_argument("--model", default=str(config.MODEL_PATH),
                        help="path to pose_landmarker_*.task")
    parser.add_argument("--no-save", action="store_true",
                        help="do not save the session to the local database")
    parser.add_argument("--no-mirror", action="store_true", help="do not flip the picture")
    return parser.parse_args()


def save_session_if_wanted(session, enabled):
    """Store only date, duration and rep count - never video."""
    if not enabled or not session.was_started:
        return
    try:
        storage = SessionStorage(config.DATABASE_PATH)
        storage.save_session(session.summary())
        print(f"Session saved: {session.rep_count} reps, "
              f"{session.elapsed_seconds:.0f} s  ->  {config.DATABASE_PATH}")
    except Exception as error:  # saving must never crash the shutdown
        print(f"Warning: could not save the session ({error}).")


def run(args) -> int:
    mirror = config.MIRROR_VIEW and not args.no_mirror
    save_enabled = config.STORAGE.save_sessions and not args.no_save

    # --- Start the AI model first (fails fast with a clear message) ---
    try:
        detector = PoseDetector(args.model)
    except PoseDetectorError as error:
        print(f"\nERROR: {error}\n")
        return 1

    camera = Camera(replace(config.CAMERA, index=args.camera))
    session = WorkoutSession()
    window_shown = False

    try:
        try:
            camera.open()
        except CameraError as error:
            print(f"\nERROR: {error}\n")
            return 1

        print("Camera started. Controls: S start/resume, P pause, R reset, Q quit.")
        start_time = time.monotonic()
        fps = 0.0
        last_frame_time = start_time
        last_rep_time = -10.0

        while True:
            frame = camera.read()          # may raise CameraError
            if frame is None:              # one bad frame: skip it
                if cv2.waitKey(1) & 0xFF in (ord("q"), ord("Q")):
                    break
                continue

            if mirror:
                frame = cv2.flip(frame, 1)

            now = time.monotonic()
            timestamp_ms = int((now - start_time) * 1000)

            # 2-3) AI landmarks -> measurements
            pose = detector.detect(frame, timestamp_ms)
            metrics = compute_squat_metrics(pose)

            # 4) Session + counter (nothing is counted unless ACTIVE)
            angle = metrics.knee_angle if metrics.tracking_ok else None
            if session.process_frame(angle, now):
                last_rep_time = now

            # 5) Feedback message
            feedback = generate_feedback(
                session.state, metrics.status, session.counter.state,
                session.counter.angular_velocity,
            )

            # 6) Draw
            frame_time = max(now - last_frame_time, 1e-6)
            fps = 0.9 * fps + 0.1 * (1.0 / frame_time) if fps else 1.0 / frame_time
            last_frame_time = now

            draw_skeleton(frame, pose, metrics)
            draw_hud(frame, HudData(
                session_state=session.state,
                rep_count=session.rep_count,
                squat_state=session.counter.state.value,
                knee_angle=angle,
                elapsed_seconds=session.elapsed_seconds,
                average_depth_angle=session.average_depth_angle,
                tracking_status=metrics.status,
                feedback=feedback,
                fps=fps,
                rep_flash=(now - last_rep_time) < REP_FLASH_SECONDS,
            ))
            cv2.imshow(config.WINDOW_NAME, frame)
            window_shown = True

            # Keys
            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), ord("Q")):
                break
            elif key in (ord("s"), ord("S")):
                session.start()
            elif key in (ord("p"), ord("P")):
                session.toggle_pause()
            elif key in (ord("r"), ord("R")):
                session.reset()

            # Window closed with the mouse
            if cv2.getWindowProperty(config.WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1:
                break

    except CameraError as error:
        print(f"\nCAMERA ERROR: {error}\n")
        return 1
    except KeyboardInterrupt:
        print("\nStopped with Ctrl+C.")
    except Exception:
        print("\nUNEXPECTED ERROR - please copy this whole message when asking for help:\n")
        traceback.print_exc()
        return 1
    finally:
        # Always runs: free the camera, the model and the window.
        camera.release()
        detector.close()
        cv2.destroyAllWindows()
        if window_shown:
            cv2.waitKey(1)   # lets macOS actually close the window
        save_session_if_wanted(session, save_enabled)
    return 0


if __name__ == "__main__":
    sys.exit(run(parse_arguments()))
