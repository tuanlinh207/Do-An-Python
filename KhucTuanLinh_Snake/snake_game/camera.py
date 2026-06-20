"""Lớp Camera: tạo hiệu ứng rung màn hình (screen shake) khi va chạm."""
import random


class Camera:
    def __init__(self):
        self.shake_time = 0.0
        self.shake_duration = 0.0
        self.shake_magnitude = 0.0
        self.offset = (0, 0)

    def trigger_shake(self, magnitude=10, duration=0.35):
        self.shake_magnitude = magnitude
        self.shake_duration = duration
        self.shake_time = duration

    def update(self, dt):
        if self.shake_time > 0:
            self.shake_time = max(0, self.shake_time - dt)
            t = self.shake_time / self.shake_duration if self.shake_duration > 0 else 0
            mag = self.shake_magnitude * t
            self.offset = (random.uniform(-mag, mag), random.uniform(-mag, mag))
        else:
            self.offset = (0, 0)
