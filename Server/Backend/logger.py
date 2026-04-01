from datetime import datetime

def _ts():
    return datetime.now().strftime("%H:%M:%S")

def info(msg):
    print(f"[{_ts()}][INFO] {msg}")

def event(category, msg):
    print(f"[{_ts()}][{category}] {msg}")

def error(msg):
    print(f"[{_ts()}][ERROR] {msg}")

def warn(msg):
    print(f"[{_ts()}][WARN] {msg}")