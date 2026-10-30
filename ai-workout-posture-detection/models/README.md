# Models folder

This folder must contain the MediaPipe Pose Landmarker model file:

    models/pose_landmarker_lite.task

The file is **not included** in this project (it is a binary file from Google).
Download it with:

    python scripts/download_model.py

Or manually (paste the link into your browser):

    https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task

Then move the downloaded file into this `models/` folder and make sure the name is exactly
`pose_landmarker_lite.task`.

Other official variants exist ("full" and "heavy"). They are more accurate but slower. If you
use one, change `MODEL_PATH` in `config.py`. Official documentation:
https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker
