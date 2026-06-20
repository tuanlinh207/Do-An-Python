"""Lớp Food: sinh và vẽ quả táo trên lưới, có hiệu ứng nảy khi xuất hiện."""
import math
import random

import pygame

from .settings import GRID_COLS, GRID_ROWS, GRID_SIZE
from .settings import APPLE_RED, APPLE_RED_DARK, APPLE_HIGHLIGHT, APPLE_STEM, APPLE_LEAF
from .utils import clamp, grid_to_local_px


class Food:
    def __init__(self):
        self.gx = 0
        self.gy = 0
        self.spawn_timer = 0.0
        self.spawn_duration = 0.22
        self.spawned = False

    def spawn(self, occupied):
        free_cells = [
            (x, y) for x in range(GRID_COLS) for y in range(GRID_ROWS)
            if (x, y) not in occupied
        ]
        if not free_cells:
            self.spawned = False
            return
        self.gx, self.gy = random.choice(free_cells)
        self.spawn_timer = 0.0
        self.spawned = True

    def update(self, dt):
        if self.spawn_timer < self.spawn_duration:
            self.spawn_timer = min(self.spawn_duration, self.spawn_timer + dt)

    @property
    def scale(self):
        t = self.spawn_timer / self.spawn_duration
        if t >= 1.0:
            return 1.0
        overshoot = math.sin(t * math.pi) * 0.18
        return clamp(t + overshoot, 0, 1.18)

    def draw(self, surface):
        if not self.spawned:
            return
        cx, cy = grid_to_local_px(self.gx, self.gy)
        cx += GRID_SIZE / 2
        cy += GRID_SIZE / 2
        scale = self.scale
        base_r = GRID_SIZE * 0.36 * scale

        bob = math.sin(pygame.time.get_ticks() * 0.004 + self.gx) * 1.5

        leaf_pts = [
            (cx + 2, cy - base_r - 4 + bob),
            (cx + 14, cy - base_r - 10 + bob),
            (cx + 6, cy - base_r - 2 + bob),
        ]
        if scale > 0.05:
            pygame.draw.polygon(surface, APPLE_LEAF, leaf_pts)

        stem_rect = pygame.Rect(0, 0, max(1, int(3 * scale)), max(1, int(8 * scale)))
        stem_rect.midbottom = (cx, cy - base_r + 2 + bob)
        pygame.draw.rect(surface, APPLE_STEM, stem_rect, border_radius=2)

        body_center = (cx, cy + bob)
        pygame.draw.circle(surface, APPLE_RED_DARK, body_center, base_r)
        pygame.draw.circle(surface, APPLE_RED, (cx - base_r * 0.05, cy + bob - base_r * 0.05), base_r * 0.94)
        highlight_r = base_r * 0.32
        pygame.draw.circle(
            surface, APPLE_HIGHLIGHT,
            (cx - base_r * 0.32, cy + bob - base_r * 0.32), highlight_r
        )
