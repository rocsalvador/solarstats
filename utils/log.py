"""Simple timestamped logging utility."""
import time
import sys


def log(message: str, module: str, level: str = "INFO", filename: str = None):
    """Print a timestamped log message to stdout, stderr, or a file."""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    if filename:
        with open(filename, "a", encoding="utf-8") as f:
            print(f"[{timestamp}][{module}][{level}] {message}", file=f)
    elif level == "ERROR":
        print(f"[{timestamp}][{module}][{level}] {message}", file=sys.stderr)
    else:
        print(f"[{timestamp}][{module}][{level}] {message}", file=sys.stdout)
