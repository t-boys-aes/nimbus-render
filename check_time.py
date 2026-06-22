import sys
from datetime import datetime
import os

try:
    from zoneinfo import ZoneInfo
except ImportError:
    # Fallback for older python environments
    from pytz import timezone
    def ZoneInfo(name):
        return timezone(name)

def should_run_now() -> bool:
    # Target New York Timezone
    tz = ZoneInfo("America/New_York")
    now = datetime.now(tz)
    
    weekday = now.weekday()  # 0 = Monday, 6 = Sunday
    hour = now.hour
    
    # Target hours (Eastern Time / ET)
    # Weekdays: 19:00 (7 PM New York Time)
    # Weekends (Saturday=5, Sunday=6): 12:00 (12 PM New York Time)
    if weekday in [5, 6]:
        target_hour = 12
    else:
        target_hour = 19
        
    # Check if current hour matches target hour
    if hour == target_hour:
        print(f"TIME MATCH! Current NY local time: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}. Target hour: {target_hour}:00.")
        return True
    
    print(f"SKIP RUN. Current NY local time: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}. Target hour: {target_hour}:00.")
    return False

if __name__ == "__main__":
    is_time = should_run_now()
    
    # Write output variable for GitHub Actions using GITHUB_OUTPUT environment file
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        try:
            with open(github_output, "a") as f:
                val = "true" if is_time else "false"
                f.write(f"should_run={val}\n")
            print(f"Logged should_run={val} to GITHUB_OUTPUT.")
        except Exception as e:
            print(f"Failed to write to GITHUB_OUTPUT: {e}")
            
    # Exit successfully
    sys.exit(0)
