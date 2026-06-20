"""Hệ thống hạt hiệu ứng (particle) dùng cho hiệu ứng nổ khi ăn táo hoặc va chạm."""
import math
import random

import pygame

from .utils import clamp


class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "radius", "color")

    def __init__(self, x, y, vx, vy, life, radius, color):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.life = life
        self.max_life = life
        self.radius = radius
        self.color = color

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vx *= 0.92
        self.vy *= 0.92
        self.vy += 80 * dt
        self.life -= dt
        return self.life > 0

    def draw(self, surface):
        t = clamp(self.life / self.max_life, 0, 1)
        alpha = int(255 * t)
        r = max(1, int(self.radius * t))
        s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        color = (*self.color, alpha)
        pygame.draw.circle(s, color, (r, r), r)
        surface.blit(s, (self.x - r, self.y - r))


class ParticleSystem:
    def __init__(self):
        self.particles = []

    def burst(self, x, y, color, count=16, speed_range=(60, 220), life_range=(0.35, 0.7)):
        for _ in range(count):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(*speed_range)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            life = random.uniform(*life_range)
            radius = random.uniform(2, 5)
            shade = tuple(clamp(c + random.randint(-20, 20), 0, 255) for c in color)
            self.particles.append(Particle(x, y, vx, vy, life, radius, shade))

    def update(self, dt):
        self.particles = [p for p in self.particles if p.update(dt)]

    def draw(self, surface):
        for p in self.particles:
            p.draw(surface)

    def clear(self):
        self.particles.clear()
