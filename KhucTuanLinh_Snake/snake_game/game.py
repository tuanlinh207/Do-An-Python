"""Lớp Game: quản lý vòng lặp chính, trạng thái (menu/chơi/game over), input và vẽ toàn bộ giao diện."""
import sys

import pygame

from .settings import (
    WINDOW_WIDTH, WINDOW_HEIGHT, GRID_SIZE, GRID_COLS, GRID_ROWS,
    BOARD_WIDTH, BOARD_HEIGHT, BOARD_X, BOARD_Y,
    MOVE_INTERVAL, GRACE_PERIOD, FPS,
    UP, DOWN, LEFT, RIGHT,
    COLOR_BG, COLOR_GRID_LIGHT, COLOR_GRID_DARK, COLOR_PANEL, COLOR_PANEL_BORDER,
    COLOR_TEXT, COLOR_TEXT_DIM, COLOR_ACCENT, COLOR_DANGER,
    SNAKE_BODY_A, APPLE_RED,
)
from .utils import clamp, grid_to_local_px, load_high_score, save_high_score
from .sound_manager import SoundManager
from .particles import ParticleSystem
from .camera import Camera
from .food import Food
from .snake import Snake
from .ui import Button


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
