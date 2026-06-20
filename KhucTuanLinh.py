import pygame
import random
import math
import os
import sys
from collections import deque

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False


WINDOW_WIDTH = 760
WINDOW_HEIGHT = 840
GRID_SIZE = 32
GRID_COLS = 20
GRID_ROWS = 20
BOARD_WIDTH = GRID_COLS * GRID_SIZE
BOARD_HEIGHT = GRID_ROWS * GRID_SIZE
BOARD_X = (WINDOW_WIDTH - BOARD_WIDTH) // 2
BOARD_Y = 130

MOVE_INTERVAL = 0.105
GRACE_PERIOD = 0.13
FPS = 60

HIGH_SCORE_FILE = "highscore.txt"

UP = (0, -1)
DOWN = (0, 1)
LEFT = (-1, 0)
RIGHT = (1, 0)
OPPOSITE = {UP: DOWN, DOWN: UP, LEFT: RIGHT, RIGHT: LEFT}

COLOR_BG = (25, 28, 23)
COLOR_GRID_LIGHT = (167, 217, 105)
COLOR_GRID_DARK = (156, 209, 94)
COLOR_PANEL = (38, 43, 35)
COLOR_PANEL_BORDER = (60, 68, 52)
COLOR_TEXT = (240, 245, 235)
COLOR_TEXT_DIM = (170, 182, 160)
COLOR_ACCENT = (255, 196, 60)
COLOR_DANGER = (230, 80, 70)

SNAKE_HEAD = (66, 133, 90)
SNAKE_BODY_A = (78, 156, 105)
SNAKE_BODY_B = (90, 172, 118)
SNAKE_OUTLINE = (40, 90, 58)
SNAKE_EYE_WHITE = (255, 255, 255)
SNAKE_EYE_PUPIL = (25, 25, 25)

APPLE_RED = (217, 60, 56)
APPLE_RED_DARK = (172, 40, 38)
APPLE_HIGHLIGHT = (255, 140, 130)
APPLE_STEM = (110, 75, 45)
APPLE_LEAF = (90, 170, 80)


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


class SoundManager:
    SAMPLE_RATE = 44100

    def __init__(self):
        self.enabled = False
        self.muted = False
        self.sounds = {}

        try:
            pygame.mixer.pre_init(self.SAMPLE_RATE, -16, 1, 256)
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=self.SAMPLE_RATE, size=-16, channels=1)
            self.enabled = True
        except pygame.error as e:
            print(f"[SoundManager] mixer unavailable: {e}")
            self.enabled = False
            return

        if not NUMPY_AVAILABLE:
            print("[SoundManager] numpy missing, sounds disabled")
            self.enabled = False
            return

        try:
            self.sounds["eat"] = self._tone_blip(880, 1320, 0.09, square_mix=0.25)
            self.sounds["turn"] = self._tone_blip(300, 340, 0.03, square_mix=0.0, vol=0.18)
            self.sounds["crash"] = self._crash_sound()
            self.sounds["start"] = self._tone_blip(440, 880, 0.18, square_mix=0.15)
        except Exception as e:
            print(f"[SoundManager] generation failed: {e}")
            self.enabled = False

    def _envelope(self, n, attack=0.05, release=0.6):
        env = np.ones(n, dtype=np.float32)
        a = max(1, int(n * attack))
        r = max(1, int(n * release))
        env[:a] = np.linspace(0, 1, a)
        env[-r:] *= np.linspace(1, 0, r)
        return env

    def _to_sound(self, wave):
        wave = np.clip(wave, -1.0, 1.0)
        int_wave = np.ascontiguousarray((wave * 32767).astype(np.int16))
        return pygame.sndarray.make_sound(int_wave)

    def _tone_blip(self, f_start, f_end, duration, square_mix=0.2, vol=0.5):
        n = int(self.SAMPLE_RATE * duration)
        t = np.linspace(0, duration, n, endpoint=False)
        freq_sweep = np.linspace(f_start, f_end, n)
        phase = 2 * np.pi * np.cumsum(freq_sweep) / self.SAMPLE_RATE
        wave = np.sin(phase) * (1 - square_mix)
        if square_mix > 0:
            wave += square_mix * np.sign(np.sin(phase))
        wave *= self._envelope(n, attack=0.02, release=0.7) * vol
        return self._to_sound(wave.astype(np.float32))

    def _crash_sound(self):
        duration = 0.4
        n = int(self.SAMPLE_RATE * duration)
        t = np.linspace(0, duration, n, endpoint=False)
        thud = np.sin(2 * np.pi * 75 * t) * np.exp(-t * 7)
        noise = (np.random.rand(n).astype(np.float32) * 2 - 1) * np.exp(-t * 10)
        wave = thud * 0.65 + noise * 0.55
        wave *= self._envelope(n, attack=0.005, release=0.85) * 0.8
        return self._to_sound(wave.astype(np.float32))

    def play(self, name):
        if not self.enabled or self.muted:
            return
        s = self.sounds.get(name)
        if s:
            s.play()

    def toggle_mute(self):
        self.muted = not self.muted


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


class Button:
    def __init__(self, rect, text, font):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.font = font
        self.hovered = False

    def update(self, mouse_pos):
        self.hovered = self.rect.collidepoint(mouse_pos)

    def draw(self, surface):
        base_color = COLOR_ACCENT if self.hovered else (210, 170, 60)
        pygame.draw.rect(surface, (30, 35, 28), self.rect.inflate(6, 6), border_radius=14)
        pygame.draw.rect(surface, base_color, self.rect, border_radius=12)
        label = self.font.render(self.text, True, (30, 25, 10))
        label_rect = label.get_rect(center=self.rect.center)
        surface.blit(label, label_rect)

    def clicked(self, event):
        return (
            event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1
            and self.rect.collidepoint(event.pos)
        )


class Game:
    STATE_START_MENU = "start_menu"
    STATE_PLAYING = "playing"
    STATE_GAME_OVER = "game_over"

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Snake")
        self.clock = pygame.time.Clock()
        self.running = True

        self.font_title = pygame.font.SysFont("arial", 56, bold=True)
        self.font_score = pygame.font.SysFont("arial", 34, bold=True)
        self.font_label = pygame.font.SysFont("arial", 18, bold=True)
        self.font_button = pygame.font.SysFont("arial", 24, bold=True)
        self.font_small = pygame.font.SysFont("arial", 15)

        self.sound = SoundManager()
        self.particles = ParticleSystem()
        self.camera = Camera()

        self.high_score = load_high_score()
        self.score = 0

        self.board_surface = pygame.Surface((BOARD_WIDTH, BOARD_HEIGHT))
        self._render_checkerboard()

        self.state = self.STATE_START_MENU
        self.flash_timer = 0.0

        self.play_button = Button(
            (WINDOW_WIDTH // 2 - 110, BOARD_Y + BOARD_HEIGHT // 2 + 40, 220, 56),
            "PLAY", self.font_button
        )
        self.restart_button = Button(
            (WINDOW_WIDTH // 2 - 110, BOARD_Y + BOARD_HEIGHT // 2 + 80, 220, 56),
            "PLAY AGAIN", self.font_button
        )

        self._setup_new_game()

    def _render_checkerboard(self):
        for gy in range(GRID_ROWS):
            for gx in range(GRID_COLS):
                color = COLOR_GRID_LIGHT if (gx + gy) % 2 == 0 else COLOR_GRID_DARK
                rect = pygame.Rect(gx * GRID_SIZE, gy * GRID_SIZE, GRID_SIZE, GRID_SIZE)
                pygame.draw.rect(self.board_surface, color, rect)

    def _setup_new_game(self):
        start_gx, start_gy = GRID_COLS // 3, GRID_ROWS // 2
        self.snake = Snake(start_gx, start_gy)
        self.food = Food()
        self.food.spawn(self.snake.occupied_cells())
        self.score = 0
        self.move_progress = 0.0
        self.grace_timer = 0.0
        self.in_grace = False
        self.particles.clear()

    def start_game(self):
        self._setup_new_game()
        self.state = self.STATE_PLAYING
        self.sound.play("start")

    def end_game(self):
        self.state = self.STATE_GAME_OVER
        self.sound.play("crash")
        self.camera.trigger_shake(magnitude=12, duration=0.4)
        hx, hy = self.snake.head()
        px, py = grid_to_local_px(hx, hy)
        self.particles.burst(
            px + GRID_SIZE / 2,
            py + GRID_SIZE / 2,
            SNAKE_BODY_A, count=26, speed_range=(80, 260), life_range=(0.4, 0.8)
        )
        if self.score > self.high_score:
            self.high_score = self.score
            save_high_score(self.high_score)

    def handle_events(self):
        mouse_pos = pygame.mouse.get_pos()
        self.play_button.update(mouse_pos)
        self.restart_button.update(mouse_pos)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                self._handle_keydown(event.key)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if self.state == self.STATE_START_MENU and self.play_button.clicked(event):
                    self.start_game()
                elif self.state == self.STATE_GAME_OVER and self.restart_button.clicked(event):
                    self.start_game()

    def _handle_keydown(self, key):
        if key == pygame.K_ESCAPE:
            self.running = False
            return
        if key == pygame.K_m:
            self.sound.toggle_mute()
            return

        direction_map = {
            pygame.K_UP: UP, pygame.K_w: UP,
            pygame.K_DOWN: DOWN, pygame.K_s: DOWN,
            pygame.K_LEFT: LEFT, pygame.K_a: LEFT,
            pygame.K_RIGHT: RIGHT, pygame.K_d: RIGHT,
        }

        if self.state == self.STATE_START_MENU:
            if key == pygame.K_SPACE or key in direction_map:
                self.start_game()
                if key in direction_map:
                    self.snake.queue_direction(direction_map[key])
        elif self.state == self.STATE_PLAYING:
            if key in direction_map:
                prev_len = len(self.snake.input_queue)
                self.snake.queue_direction(direction_map[key])
                if len(self.snake.input_queue) > prev_len:
                    self.sound.play("turn")
        elif self.state == self.STATE_GAME_OVER:
            if key == pygame.K_SPACE:
                self.start_game()

    def update(self, dt):
        self.particles.update(dt)
        self.camera.update(dt)
        self.flash_timer += dt
        self.food.update(dt)

        if self.state != self.STATE_PLAYING:
            return

        self.snake.move_timer += dt
        self.move_progress = clamp(self.snake.move_timer / self.snake.move_interval, 0, 1)

        if self.in_grace:
            self.grace_timer -= dt
            if self.grace_timer <= 0:
                self.end_game()
                self.in_grace = False
                return

        if self.snake.move_timer >= self.snake.move_interval:
            self.snake.move_timer -= self.snake.move_interval
            self.move_progress = 0.0
            self._advance_logical_step()

    def _advance_logical_step(self):
        next_head = self.snake.peek_next_head()
        wall_hit = self.snake.is_wall_collision(next_head)
        self_hit = (not wall_hit) and self.snake.is_self_collision(next_head)

        if wall_hit or self_hit:
            if not self.in_grace:
                self.in_grace = True
                self.grace_timer = GRACE_PERIOD
            return

        self.in_grace = False
        self.snake.step()

        head = self.snake.head()
        if self.food.spawned and head == (self.food.gx, self.food.gy):
            self.snake.grow(1)
            self.score += 1
            self.sound.play("eat")
            fx, fy = grid_to_local_px(self.food.gx, self.food.gy)
            self.particles.burst(
                fx + GRID_SIZE / 2, fy + GRID_SIZE / 2,
                APPLE_RED, count=18, speed_range=(60, 200), life_range=(0.3, 0.65)
            )
            self.food.spawn(self.snake.occupied_cells())
            self._ramp_difficulty()

    def _ramp_difficulty(self):
        new_interval = MOVE_INTERVAL - self.score * 0.0025
        self.snake.move_interval = max(0.055, new_interval)

    def draw(self):
        self.screen.fill(COLOR_BG)

        shake_x, shake_y = self.camera.offset
        board_pos = (BOARD_X + shake_x, BOARD_Y + shake_y)

        self._draw_header()

        self.screen.blit(self.board_surface, board_pos)

        game_layer = pygame.Surface((BOARD_WIDTH, BOARD_HEIGHT), pygame.SRCALPHA)
        self.food.draw(game_layer)
        self.snake.draw(game_layer, self.move_progress)
        self.particles.draw(game_layer)
        self.screen.blit(game_layer, board_pos)

        pygame.draw.rect(
            self.screen, COLOR_PANEL_BORDER,
            (board_pos[0] - 3, board_pos[1] - 3, BOARD_WIDTH + 6, BOARD_HEIGHT + 6), 3, border_radius=8
        )

        if self.state == self.STATE_START_MENU:
            self._draw_start_menu()
        elif self.state == self.STATE_GAME_OVER:
            self._draw_game_over()

        self._draw_mute_indicator()

        pygame.display.flip()

    def _draw_header(self):
        panel_rect = pygame.Rect(0, 0, WINDOW_WIDTH, BOARD_Y - 20)
        pygame.draw.rect(self.screen, COLOR_PANEL, panel_rect)
        pygame.draw.line(self.screen, COLOR_PANEL_BORDER, (0, BOARD_Y - 20), (WINDOW_WIDTH, BOARD_Y - 20), 2)

        score_label = self.font_label.render("SCORE", True, COLOR_TEXT_DIM)
        score_value = self.font_score.render(str(self.score), True, COLOR_TEXT)
        self.screen.blit(score_label, (40, 30))
        self.screen.blit(score_value, (40, 52))

        best_label = self.font_label.render("BEST", True, COLOR_TEXT_DIM)
        best_value = self.font_score.render(str(self.high_score), True, COLOR_ACCENT)
        best_w = max(best_label.get_width(), best_value.get_width())
        self.screen.blit(best_label, (WINDOW_WIDTH - 40 - best_w, 30))
        self.screen.blit(best_value, (WINDOW_WIDTH - 40 - best_w, 52))

        title = self.font_title.render("SNAKE", True, COLOR_TEXT)
        title_rect = title.get_rect(center=(WINDOW_WIDTH // 2, 60))
        self.screen.blit(title, title_rect)

    def _draw_mute_indicator(self):
        text = "MUTED (M)" if self.sound.muted else "SOUND ON (M)"
        color = COLOR_DANGER if self.sound.muted else COLOR_TEXT_DIM
        label = self.font_small.render(text, True, color)
        self.screen.blit(label, (WINDOW_WIDTH - label.get_width() - 16, WINDOW_HEIGHT - 28))

    def _draw_overlay_backdrop(self):
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((10, 12, 9, 165))
        self.screen.blit(overlay, (0, 0))

    def _draw_start_menu(self):
        self._draw_overlay_backdrop()

        subtitle = self.font_score.render("Ready?", True, COLOR_TEXT)
        sub_rect = subtitle.get_rect(center=(WINDOW_WIDTH // 2, BOARD_Y + BOARD_HEIGHT // 2 - 50))
        self.screen.blit(subtitle, sub_rect)

        hint = self.font_label.render("Arrow Keys / WASD to move", True, COLOR_TEXT_DIM)
        hint_rect = hint.get_rect(center=(WINDOW_WIDTH // 2, BOARD_Y + BOARD_HEIGHT // 2))
        self.screen.blit(hint, hint_rect)

        self.play_button.draw(self.screen)

        if (self.flash_timer // 0.5) % 2 == 0:
            prompt = self.font_small.render("or press SPACE", True, COLOR_TEXT_DIM)
            prompt_rect = prompt.get_rect(center=(WINDOW_WIDTH // 2, self.play_button.rect.bottom + 28))
            self.screen.blit(prompt, prompt_rect)

    def _draw_game_over(self):
        self._draw_overlay_backdrop()

        title = self.font_title.render("GAME OVER", True, COLOR_DANGER)
        title_rect = title.get_rect(center=(WINDOW_WIDTH // 2, BOARD_Y + BOARD_HEIGHT // 2 - 90))
        self.screen.blit(title, title_rect)

        score_text = self.font_score.render(f"Score: {self.score}", True, COLOR_TEXT)
        score_rect = score_text.get_rect(center=(WINDOW_WIDTH // 2, BOARD_Y + BOARD_HEIGHT // 2 - 40))
        self.screen.blit(score_text, score_rect)

        is_best = self.score >= self.high_score and self.score > 0
        best_color = COLOR_ACCENT if is_best else COLOR_TEXT_DIM
        best_label = "NEW BEST!" if is_best else f"Best: {self.high_score}"
        best_text = self.font_label.render(best_label, True, best_color)
        best_rect = best_text.get_rect(center=(WINDOW_WIDTH // 2, BOARD_Y + BOARD_HEIGHT // 2 - 5))
        self.screen.blit(best_text, best_rect)

        self.restart_button.draw(self.screen)

        if (self.flash_timer // 0.5) % 2 == 0:
            prompt = self.font_small.render("or press SPACE", True, COLOR_TEXT_DIM)
            prompt_rect = prompt.get_rect(center=(WINDOW_WIDTH // 2, self.restart_button.rect.bottom + 28))
            self.screen.blit(prompt, prompt_rect)

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            dt = min(dt, 0.05)
            self.handle_events()
            self.update(dt)
            self.draw()

        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    game = Game()
    game.run()