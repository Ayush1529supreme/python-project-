"""
Optional: show a bar chart of squat reps per saved session.

    pip install -r requirements-optional.txt
    python scripts/plot_history.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402
from src.session_storage import SessionStorage  # noqa: E402


def main() -> int:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("Matplotlib is not installed. Run: pip install -r requirements-optional.txt")
        return 1

    if not Path(config.DATABASE_PATH).is_file():
        print("No workout history yet. Finish a session with Q first.")
        return 1

    sessions = list(reversed(SessionStorage(config.DATABASE_PATH).list_sessions(limit=30)))
    if not sessions:
        print("No saved sessions yet.")
        return 1

    labels = [s["started_at"][5:16].replace("T", "\n") for s in sessions]
    reps = [s["squat_reps"] for s in sessions]
    plt.figure(figsize=(9, 4.5))
    plt.bar(range(len(reps)), reps, color="#2e9e5b")
    plt.xticks(range(len(reps)), labels, fontsize=8)
    plt.ylabel("Squat repetitions")
    plt.title("Squat repetitions per session")
    plt.tight_layout()
    plt.show()
    return 0


if __name__ == "__main__":
    sys.exit(main())
