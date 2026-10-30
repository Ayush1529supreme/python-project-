# AI Workout Posture Detection System

> **GitHub description:** A beginner-friendly Python desktop app that uses a webcam, OpenCV and
> MediaPipe Pose Landmarker to detect body landmarks, measure knee angles, count squat
> repetitions with a tested state machine, and show simple real-time feedback. Runs fully
> locally - no cloud, no paid APIs, no video saved.

## Overview

The app opens your webcam, finds 33 body landmarks with a pretrained Google MediaPipe model,
calculates the knee angle (hip - knee - ankle), and counts a squat only after a **complete
movement cycle** (stand -> down -> low position -> up -> stand). Everything is drawn live in an
OpenCV window.

## Features

- Live webcam feed with skeleton overlay and clear error messages (no camera, failed frames).
- Landmark reliability checks (visibility + inside the picture) before any calculation.
- Squat counter based on a state machine with smoothing, hysteresis and a minimum-duration
  check against jitter and duplicate counts.
- Configurable angle thresholds (`config.py`).
- Conservative rule-based feedback messages.
- Session controls: start / pause / resume / reset / quit, with a pause-aware timer.
- Optional local SQLite history (date, duration, reps only) and an optional Matplotlib chart.
- 63 automated unit tests that run without a webcam.

## Technologies

Python - OpenCV (camera, drawing) - MediaPipe Pose Landmarker (pretrained model, Tasks API) -
NumPy / math (angles) - SQLite (optional history) - Matplotlib (optional chart).

## Folder structure

```
ai-workout-posture-detection/
    main.py                  entry point + main loop
    config.py                all thresholds and settings
    requirements.txt         core dependencies
    requirements-optional.txt  matplotlib (chart only)
    requirements-dev.txt     pytest (optional, tests also run with unittest)
    models/                  put pose_landmarker_lite.task here (see "Model setup")
    src/
        camera.py            webcam open/read/release, error handling
        pose_detector.py     MediaPipe wrapper -> landmarks
        pose_metrics.py      reliable landmarks -> knee angle      (added module)
        angle_calculator.py  pure geometry: angle between 3 points
        squat_counter.py     squat state machine + rep counting
        posture_feedback.py  rule-based messages
        workout_session.py   idle/active/paused, timer, statistics
        session_storage.py   optional SQLite storage                (added module)
        visualizer.py        skeleton + interface drawing
    scripts/
        download_model.py    downloads the official model file
        check_setup.py       checks Python, packages, model, (--camera) webcam
        plot_history.py      optional progress chart
    tests/                   unit tests (angles, counter, session, metrics, feedback, storage)
    docs/GUIDE.md            beginner guide: how the code works, test checklists, debugging
    data/                    local database goes here (ignored by git)
```

Two modules were added to the suggested structure: `pose_metrics.py` (keeps "read the body"
separate from both the AI model and the counting logic, so each can be tested alone) and
`session_storage.py` (the optional SQLite part).

## Environment setup (macOS, zsh, VS Code)

**Python version.** Use a 64-bit Python **3.10, 3.11 or 3.12**. Official MediaPipe wheels exist for
arm64 (Apple Silicon) and Intel macOS 11+; if `pip install mediapipe` says
"No matching distribution found", your Python version or architecture is usually the cause
(check with the commands below). The `requirements.txt` uses minimum versions only so `pip`
can pick a compatible set.

```zsh
python3 --version          # want 3.10 - 3.12
python3 -m pip --version
uname -m                   # arm64 = Apple Silicon, x86_64 = Intel
```

If your Python is older/newer, install a suitable one (for example `brew install python@3.12`)
and use `python3.12` in the commands below.

```zsh
cd ai-workout-posture-detection
code .                                  # opens VS Code (or use File > Open Folder)

python3 -m venv .venv                   # create the virtual environment
source .venv/bin/activate               # activate it (prompt shows "(.venv)")
python -m pip install --upgrade pip
pip install -r requirements.txt
```

In VS Code: `Cmd+Shift+P` -> **Python: Select Interpreter** -> choose `./.venv/bin/python`.

**Camera permission (macOS).** The first run asks to allow camera access for the app that runs
Python (Terminal, iTerm or Visual Studio Code). If you clicked "Don't allow": System Settings
-> Privacy & Security -> Camera -> switch it on, then **fully quit and reopen** that app.

## Model setup

The pose model file is not included. Download it once:

```zsh
python scripts/download_model.py
```

It saves `models/pose_landmarker_lite.task`. If the download fails, use the manual link in
`models/README.md`. Official docs:
<https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker>

## Check everything

```zsh
python scripts/check_setup.py            # Python, packages, model file
python scripts/check_setup.py --camera   # also shows the webcam for 5 seconds
```

## Run

```zsh
python main.py
```

Options: `--camera 1` (another camera), `--no-save` (don't store the session),
`--no-mirror`, `--model PATH`.

**Setup tip:** place the camera so your whole body (shoulders to ankles) is inside the picture,
side-on or front-on, with good light and a plain background. Stand 2-3 metres away.

## Keyboard shortcuts

| Key | Action |
|-----|--------|
| **S** | Start the session (or resume if paused) |
| **P** | Pause / resume (the timer stops and nothing is counted while paused) |
| **R** | Reset repetitions, timer and statistics (session state stays) |
| **Q** | Quit safely (camera released, session saved if enabled) |

## How squat counting works

The knee angle is measured at the knee between hip and ankle (about 180 deg = straight leg).
Angles come from pixel coordinates, averaged over the reliable sides, then smoothed over the
last 3 frames. The default thresholds are in `config.py` (`SquatSettings`):

```
WAITING -> STANDING        angle >= 160   (must see you stand first)
STANDING -> DESCENDING     angle < 150
DESCENDING -> BOTTOM       angle <= 100 for at least 2 frames
BOTTOM -> ASCENDING        angle > 110
ASCENDING -> STANDING      angle >= 160   => repetition counted
```

A repetition is counted only on the last step, and you can only reach it through BOTTOM, so
half squats never count. Different gaps between the "down" and "up" thresholds (hysteresis)
and the smoothing stop jitter from creating false reps; repeated frames in one position cannot
add counts; very fast "reps" (< 0.6 s) are rejected as noise; if tracking is lost for 15 frames
the movement state resets (the count is kept). **Thresholds are not right for everyone** -
adjust them if a normal squat of yours is not detected (for example raise `bottom_angle` to
110 for shallower squats).

## Tests

No webcam needed:

```zsh
python -m unittest discover -s tests -t . -v
# or, if you installed pytest (pip install -r requirements-dev.txt):
python -m pytest
```

## Privacy

The app never records or saves video or images. Optional history stores only the start time,
duration, rep count and average depth angle in `data/workouts.db` on your computer.
Disable it with `--no-save` or `StorageSettings(save_sessions=False)` in `config.py`.

## Known limitations

- A single webcam gives a flat 2D view. Angles depend on camera angle, distance, clothing and
  lighting; depth (3D) is only roughly estimated by the model.
- Landmarks can jitter or be wrong when limbs overlap, in poor light, or with loose clothing.
- The feedback only reflects what the camera can reasonably infer (is your body visible, which
  phase of the squat, how fast the knee angle changes). **It is not medical advice, does not
  assess technique, cannot prevent injuries, and does not replace a qualified coach or doctor.**
- Only one person (the first detected) is tracked, and only squats are supported.
- The lite model is chosen for speed; the "full"/"heavy" models are more accurate but slower.

## Future improvements

Desktop GUI dashboard - more exercises (lunges, bicep curls) - history screen and progress
charts - repetition goals - audio feedback - exercise classification with a custom model -
analysis of labelled recordings (with explicit consent).
