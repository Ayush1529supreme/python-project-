"""
Check your environment, step by step.

    python scripts/check_setup.py            # checks Python, packages, model file
    python scripts/check_setup.py --camera   # also opens the webcam for 5 seconds
                                             # (a window should show live video)
"""

import platform
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def check(label, ok, detail=""):
    print(f"[{'OK' if ok else 'FAIL'}] {label} {detail}")
    return ok


def main() -> int:
    import config

    all_ok = True
    print(f"Python  : {sys.version.split()[0]} ({platform.machine()}, {platform.system()})")
    all_ok &= check("Python 3.10-3.12 recommended", (3, 10) <= sys.version_info[:2] <= (3, 12),
                    "(other versions may still work, but MediaPipe wheels might be missing)")

    for module in ("numpy", "cv2", "mediapipe"):
        try:
            imported = __import__(module)
            check(f"import {module}", True, getattr(imported, "__version__", ""))
        except Exception as error:  # noqa: BLE001
            all_ok = False
            check(f"import {module}", False, f"-> {error}")

    model_ok = Path(config.MODEL_PATH).is_file()
    all_ok &= check("model file", model_ok, str(config.MODEL_PATH)
                    if model_ok else "missing - run: python scripts/download_model.py")

    if "--camera" in sys.argv:
        from src.camera import Camera, CameraError
        import cv2
        try:
            with Camera() as camera:
                end = time.time() + 5
                frames = 0
                while time.time() < end:
                    frame = camera.read()
                    if frame is None:
                        continue
                    frames += 1
                    cv2.imshow("Camera test (closes itself after 5 s)", frame)
                    cv2.waitKey(1)
                cv2.destroyAllWindows()
                cv2.waitKey(1)
            all_ok &= check("camera", frames > 0, f"({frames} frames in 5 s)")
        except CameraError as error:
            all_ok = False
            check("camera", False)
            print(error)

    print("\nEverything looks fine." if all_ok else "\nFix the FAIL lines above, then run again.")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
