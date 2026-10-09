"""Simple timestamped logging utility."""
import time
import sys


def log(message: str, module: str, level: str = "INFO"):
    """Print a timestamped log message to stdout or stderr."""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    if level == "ERROR":
        print(f"[{timestamp}][{module}][{level}] {message}", file=sys.stderr)
    else:
        print(f"[{timestamp}][{module}][{level}] {message}", file=sys.stdout)
