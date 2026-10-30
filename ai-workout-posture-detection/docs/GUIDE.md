# Beginner guide

## 1. The big picture (simple English)

Every video frame travels through the same short pipeline:

```
camera.py  ->  pose_detector.py  ->  pose_metrics.py  ->  workout_session.py (+ squat_counter.py)
 (picture)      (33 body points)      (one knee angle)      (count reps)
                                                                  |
                              posture_feedback.py  -> visualizer.py -> window
```

* **Camera**: gives a picture 30 times per second.
* **Pose detector**: a pretrained AI model finds shoulders, hips, knees, ankles... Each point
  has `x`, `y` (0..1) and `visibility` (how sure the model is).
* **Pose metrics**: keeps only trustworthy points, converts them to pixels, and calculates the
  knee angle. If the points are not trustworthy it returns "no angle" instead of guessing.
* **Squat counter**: a state machine. It only sees one number per frame (the angle).
* **Session**: decides whether the counter is allowed to count (only when ACTIVE) and keeps
  time.
* **Feedback + visualizer**: turn the current state into text and drawings.

## 2. The angle maths in one minute

For hip (A), knee (B) and ankle (C), make two arrows starting at the knee: B->A and B->C.
The angle between them is `acos( (BA . BC) / (|BA| * |BC|) )`.
Straight leg = 180 deg, right angle = 90 deg. See `src/angle_calculator.py`.

## 3. Why a state machine?

Looking at one frame cannot tell "going down" from "going up". The machine remembers where you
are in the movement and only allows these steps:

`WAITING -> STANDING -> DESCENDING -> BOTTOM -> ASCENDING -> STANDING (+1 rep)`

You cannot skip BOTTOM, so a half squat never counts. Jitter protection:
average of the last 3 angles, different thresholds for going down (150/100) and coming up
(110/160), at least 2 frames at the bottom, and a minimum rep duration.

## 4. Build phases (how the project was organised)

| Phase | Goal | Files | Quick check |
|------|------|-------|-------------|
| 1 Environment | Python, venv, packages, camera permission | `requirements.txt`, `scripts/check_setup.py` | `python scripts/check_setup.py` shows all `[OK]` |
| 2 Webcam | Live video, safe shutdown | `src/camera.py` | `python scripts/check_setup.py --camera` shows video for 5 s |
| 3 Pose detection | Skeleton on video | `src/pose_detector.py`, `src/visualizer.py` | Green skeleton follows you |
| 4 Angles | Hip-knee-ankle angle | `src/angle_calculator.py`, `src/pose_metrics.py` | Yellow numbers near knees; ~170-180 deg standing |
| 5 Squat counter | State machine | `src/squat_counter.py` | Unit tests pass; one real squat = +1 |
| 6 Feedback | Messages | `src/posture_feedback.py` | Message changes with movement |
| 7 Session | Timer, controls, SQLite | `src/workout_session.py`, `src/session_storage.py` | Pause stops count/timer; data file appears after Q |
| 8 Testing | Automated + manual tests | `tests/` | Command below |
| 9 Docs | README | `README.md` | Another person can set up from it |

## 5. Test checklist (live)

Run `python main.py` and tick each item:

- [ ] Window opens and shows live (mirrored) video; title and shortcuts are visible.
- [ ] Not in frame -> "Tracking: no person found"; message asks you to position yourself.
- [ ] Step back until head-to-feet is visible -> green skeleton, "Tracking: OK", "ready to start".
- [ ] Press **S** -> state ACTIVE, timer runs, message "Begin your squat." after you stand.
- [ ] Do one full squat -> counter becomes 1 (flashes green). Half squat -> no count.
- [ ] Stand still for 10 seconds -> count does not change.
- [ ] Press **P** -> PAUSED, timer stops; squat -> no count. Press **P** again -> resumes.
- [ ] Press **R** -> count and timer go back to 0.
- [ ] Walk out of frame for a few seconds -> "Tracking temporarily unavailable.", no crash.
- [ ] Cover the camera or unplug it -> clear error, program exits cleanly.
- [ ] Press **Q** (or close the window) -> exits; camera light turns off; "Session saved" printed.

## 6. Automated tests

```zsh
python -m unittest discover -s tests -t . -v
```

Covered: angles (valid, missing, invalid, NaN, identical points), full cycle, incomplete
movement, repeated frames, noise and spikes, missing landmarks (short and long), pause,
resume, reset, timer, feedback rules, pixel-vs-normalised angles, SQLite storage.

## 7. Debugging

When something fails, copy the **whole** terminal output (the traceback) plus:

```zsh
python --version
uname -m
pip list | grep -i -E "mediapipe|opencv|numpy"
python scripts/check_setup.py
```

Common causes:

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `No matching distribution found for mediapipe` | Unsupported Python version / 32-bit / wrong architecture | Use 64-bit Python 3.10-3.12 in a fresh venv |
| `Could not open camera 0` or black window | Camera permission, or another app is using it | Allow Terminal/VS Code in Privacy & Security -> Camera, restart that app, close Zoom etc. |
| `Model file not found` | Model not downloaded | `python scripts/download_model.py` |
| Skeleton jumps / reps missed | Poor light, body partly out of frame, thresholds too strict | Better light, step back, tune `SquatSettings` |
| Counter never leaves WAITING | Standing angle never reaches 160 (e.g. camera too low/high) | Re-position camera at about hip height, or lower `stand_angle` slightly |
| `ModuleNotFoundError` | venv not active / wrong interpreter | `source .venv/bin/activate`, select interpreter in VS Code |
