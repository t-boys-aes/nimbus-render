import sys
import json
from datetime import datetime
import os
import argparse

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from pytz import timezone
    def ZoneInfo(name):
        return timezone(name)

STATE_FILE = "last_run_state.json"


def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_state(state: dict) -> None:
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def should_run_now(mode: str) -> bool:
    tz = ZoneInfo("America/New_York")
    now = datetime.now(tz)

    weekday = now.weekday()  # 0 = Monday, 6 = Sunday
    hour = now.hour
    today_str = now.strftime("%Y-%m-%d")

    if mode == "render":
        target_hour = 0
    else:
        # Upload: weekday 19:00 ET, weekend 12:00 ET
        target_hour = 12 if weekday in [5, 6] else 19

    in_target_hour = hour == target_hour

    if not in_target_hour:
        print(
            f"SKIP RUN ({mode}). Current NY local time: "
            f"{now.strftime('%Y-%m-%d %H:%M:%S %Z')}. Target hour: {target_hour}:00."
        )
        return False

    # Sudah di jam target -- sekarang cek dedupe, biar gak run berkali-kali
    # dalam window 1 jam yang sama (karena sekarang dicek tiap 15 menit)
    state = load_state()
    last_run_key = f"last_{mode}_date"
    last_run_date = state.get(last_run_key)

    if last_run_date == today_str:
        print(
            f"SKIP RUN ({mode}). Already executed today ({today_str} NY time). "
            f"Avoiding duplicate run within the same target hour window."
        )
        return False

    print(
        f"TIME MATCH ({mode})! Current NY local time: "
        f"{now.strftime('%Y-%m-%d %H:%M:%S %Z')}. Target hour: {target_hour}:00. "
        f"Marking {today_str} as executed."
    )
    state[last_run_key] = today_str
    save_state(state)
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Check if it is the target hour in New York timezone, with daily dedupe."
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["render", "upload"],
        default="upload",
        help="Mode: check for rendering time (00:00) or posting time (19:00/12:00)",
    )
    args = parser.parse_args()

    is_time = should_run_now(args.mode)

    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        try:
            with open(github_output, "a") as f:
                val = "true" if is_time else "false"
                f.write(f"should_run={val}\n")
            print(f"Logged should_run={val} to GITHUB_OUTPUT.")
        except Exception as e:
            print(f"Failed to write to GITHUB_OUTPUT: {e}")

    sys.exit(0)
