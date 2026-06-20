"""Các hàm tiện ích dùng chung: nội suy, kẹp giá trị, đổi tọa độ, đọc/ghi điểm cao."""
import os

from .settings import GRID_SIZE, HIGH_SCORE_FILE


def lerp(a, b, t):
    return a + (b - a) * t


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def grid_to_local_px(gx, gy):
    return (gx * GRID_SIZE, gy * GRID_SIZE)


def load_high_score():
    try:
        if os.path.exists(HIGH_SCORE_FILE):
            with open(HIGH_SCORE_FILE, "r") as f:
                content = f.read().strip()
                return int(content) if content.isdigit() else 0
    except (IOError, ValueError) as e:
        print(f"[HighScore] read failed: {e}")
    return 0


def save_high_score(score):
    try:
        with open(HIGH_SCORE_FILE, "w") as f:
            f.write(str(score))
    except IOError as e:
        print(f"[HighScore] write failed: {e}")
