"""
Download the official MediaPipe Pose Landmarker (lite) model into models/.

Run from the project folder:   python scripts/download_model.py
Needs an internet connection (one time only). Uses only the standard library.
"""

import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

MIN_EXPECTED_BYTES = 1_000_000  # the real file is several MB; tiny = an error page


def main() -> int:
    target = Path(config.MODEL_PATH)
    if target.is_file() and target.stat().st_size > MIN_EXPECTED_BYTES:
        print(f"Model already present: {target} ({target.stat().st_size / 1e6:.1f} MB)")
        return 0

    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".task.part")
    print(f"Downloading:\n  {config.MODEL_URL}\n-> {target}")
    try:
        urllib.request.urlretrieve(config.MODEL_URL, temporary)
        if temporary.stat().st_size < MIN_EXPECTED_BYTES:
            raise ValueError("Downloaded file is too small - probably not the model.")
        temporary.replace(target)
    except (urllib.error.URLError, OSError, ValueError) as error:
        temporary.unlink(missing_ok=True)
        print(f"\nDownload failed: {error}")
        print("Download it manually in your browser from the link above and place it in models/.")
        print("See models/README.md")
        return 1

    print(f"Done ({target.stat().st_size / 1e6:.1f} MB).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
