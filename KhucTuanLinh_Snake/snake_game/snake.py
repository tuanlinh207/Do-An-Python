"""Lớp Snake: quản lý thân rắn, hàng đợi hướng đi, va chạm và vẽ con rắn nội suy mượt."""
from collections import deque

import pygame

from .settings import (
    GRID_COLS, GRID_ROWS, GRID_SIZE, MOVE_INTERVAL, RIGHT, OPPOSITE,
    SNAKE_HEAD, SNAKE_BODY_A, SNAKE_BODY_B, SNAKE_OUTLINE,
    SNAKE_EYE_WHITE, SNAKE_EYE_PUPIL,
)
from .utils import lerp, grid_to_local_px


class Snake:
    def __init__(self, start_gx, start_gy):
        self.body = deque([(start_gx, start_gy), (start_gx - 1, start_gy), (start_gx - 2, start_gy)])
        self.direction = RIGHT
        self.pending_direction = RIGHT
        self.input_queue = deque(maxlen=2)
        self.move_timer = 0.0
        self.move_interval = MOVE_INTERVAL
        self.growth_pending = 0
        self.alive = True

    def queue_direction(self, new_dir):
        check_dir = self.input_queue[-1] if self.input_queue else self.pending_direction
        if new_dir == OPPOSITE.get(check_dir):
            return
        if new_dir == check_dir:
            return
        if len(self.input_queue) < self.input_queue.maxlen:
            self.input_queue.append(new_dir)

    def _next_head(self, direction):
        hx, hy = self.body[0]
        dx, dy = direction
        return (hx + dx, hy + dy)

    def peek_next_direction(self):
        return self.input_queue[0] if self.input_queue else self.pending_direction

    def peek_next_head(self):
        direction = self.peek_next_direction()
        return self._next_head(direction)

    def step(self):
        if self.input_queue:
            self.pending_direction = self.input_queue.popleft()
        self.direction = self.pending_direction

        new_head = self._next_head(self.direction)
        self.body.appendleft(new_head)
        if self.growth_pending > 0:
            self.growth_pending -= 1
        else:
            self.body.pop()

    def grow(self, amount=1):
        self.growth_pending += amount

    def occupied_cells(self, include_head=True):
        cells = set(self.body)
        if not include_head:
            cells.discard(self.body[0])
        return cells

    def head(self):
        return self.body[0]

    def is_wall_collision(self, pos):
        x, y = pos
        return x < 0 or x >= GRID_COLS or y < 0 or y >= GRID_ROWS

    def is_self_collision(self, pos):
        body_list = list(self.body)
        tail_will_move = self.growth_pending <= 0
        check_against = body_list[:-1] if tail_will_move and body_list else body_list
        return pos in check_against

    def draw(self, surface, progress):
        body_list = list(self.body)
        n = len(body_list)
        if n == 0:
            return

        rendered = []
        for i in range(n):
            target = body_list[i]
            source = body_list[i + 1] if i + 1 < n else body_list[i]
            vx = lerp(source[0], target[0], progress)
            vy = lerp(source[1], target[1], progress)
            rendered.append((vx, vy))

        for i in range(n - 1, 0, -1):
            gx, gy = rendered[i]
            px, py = grid_to_local_px(gx, gy)
            cx, cy = px + GRID_SIZE / 2, py + GRID_SIZE / 2
            t = i / max(1, n - 1)
            taper = lerp(1.0, 0.55, t)
            radius = GRID_SIZE * 0.46 * taper
            color = SNAKE_BODY_A if i % 2 == 0 else SNAKE_BODY_B
            pygame.draw.circle(surface, SNAKE_OUTLINE, (cx, cy), radius + 1.5)
            pygame.draw.circle(surface, color, (cx, cy), radius)

        hx, hy = rendered[0]
        hpx, hpy = grid_to_local_px(hx, hy)
        hcx, hcy = hpx + GRID_SIZE / 2, hpy + GRID_SIZE / 2
        head_radius = GRID_SIZE * 0.52

        pygame.draw.circle(surface, SNAKE_OUTLINE, (hcx, hcy), head_radius + 1.5)
        pygame.draw.circle(surface, SNAKE_HEAD, (hcx, hcy), head_radius)

        dx, dy = self.direction
        forward_x, forward_y = dx, dy
        side_x, side_y = -dy, dx

        eye_forward = head_radius * 0.42
        eye_side = head_radius * 0.42
        eye_radius = GRID_SIZE * 0.13
        pupil_radius = eye_radius * 0.55

        for sign in (-1, 1):
            ex = hcx + forward_x * eye_forward + side_x * eye_side * sign
            ey = hcy + forward_y * eye_forward + side_y * eye_side * sign
            pygame.draw.circle(surface, SNAKE_EYE_WHITE, (ex, ey), eye_radius)
            pupil_offset = eye_radius * 0.25
            px_ = ex + forward_x * pupil_offset
            py_ = ey + forward_y * pupil_offset
            pygame.draw.circle(surface, SNAKE_EYE_PUPIL, (px_, py_), pupil_radius)
