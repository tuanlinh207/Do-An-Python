import pygame
import random
import sys
import math
import numpy as np

pygame.init()
pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

CELL = 34
GRID_W = 17
GRID_H = 17
HUD_H  = 50
BORDER = 2

MAP_W  = GRID_W * CELL
MAP_H  = GRID_H * CELL
WIDTH  = MAP_W + BORDER * 2
HEIGHT = MAP_H + BORDER * 2 + HUD_H
MAP_X  = BORDER
MAP_Y  = HUD_H + BORDER

FPS         = 60
SNAKE_SPEED = 8

WHITE      = (255, 255, 255)
BLACK      = (0,   0,   0)
BG_DARK    = (170, 215, 81)
BG_LIGHT   = (162, 209, 73)
BORDER_COL = (74,  117, 44)
HUD_BG     = (74,  117, 44)
GREEN1     = (75,  153, 39)
GREEN2     = (56,  120, 25)
HEAD_COL   = (91,  179, 45)
EYE_W      = (255, 255, 255)
EYE_P      = (0,   0,   0)
RED        = (215, 50,  50)
SHINE      = (255, 180, 180)
GOLD       = (255, 215, 0)
OVERLAY    = (0,   0,   0, 160)


def make_sound(freq=440, duration=0.12, volume=0.18, wave="sine", fade=True):
    sr = 44100
    n  = int(sr * duration)
    t  = np.linspace(0, duration, n, False)
    if wave == "sine":
        data = np.sin(2 * np.pi * freq * t)
    elif wave == "tri":
        data = 2 * np.abs(2 * (t * freq - np.floor(t * freq + 0.5))) - 1
    else:
        data = np.sign(np.sin(2 * np.pi * freq * t))
    if fade:
        env = np.linspace(1, 0, n) ** 2
        data = data * env
    data = (data * volume * 32767).astype(np.int16)
    stereo = np.column_stack([data, data])
    return pygame.sndarray.make_sound(stereo)

try:
    eat_sound   = make_sound(freq=523, duration=0.10, volume=0.15, wave="sine")
    bonus_sound = make_sound(freq=784, duration=0.18, volume=0.15, wave="tri")
    die_sound   = make_sound(freq=180, duration=0.35, volume=0.18, wave="tri")
    SOUND_OK = True
except Exception:
    SOUND_OK = False


def cell_color(col, row):
    return BG_LIGHT if (col + row) % 2 == 0 else BG_DARK


def draw_board(surface):
    pygame.draw.rect(surface, BORDER_COL, (MAP_X - BORDER, MAP_Y - BORDER,
                                           MAP_W + BORDER*2, MAP_H + BORDER*2))
    for row in range(GRID_H):
        for col in range(GRID_W):
            r = pygame.Rect(MAP_X + col * CELL, MAP_Y + row * CELL, CELL, CELL)
            pygame.draw.rect(surface, cell_color(col, row), r)


def draw_snake(surface, snake, direction):
    for i, (gx, gy) in enumerate(snake):
        x = MAP_X + gx * CELL
        y = MAP_Y + gy * CELL
        ratio = i / max(len(snake) - 1, 1)
        r = int(HEAD_COL[0] * (1 - ratio) + GREEN2[0] * ratio)
        g = int(HEAD_COL[1] * (1 - ratio) + GREEN2[1] * ratio)
        b = int(HEAD_COL[2] * (1 - ratio) + GREEN2[2] * ratio)
        color = (r, g, b)
        pad = 2 if i > 0 else 1
        rect = pygame.Rect(x + pad, y + pad, CELL - pad*2, CELL - pad*2)
        radius = 8 if i == 0 else 6
        pygame.draw.rect(surface, color, rect, border_radius=radius)
        if i > 0:
            dark = (max(0, r-25), max(0, g-25), max(0, b-25))
            pygame.draw.rect(surface, dark, rect, width=1, border_radius=radius)
        if i == 0:
            dx, dy = direction
            if   dx ==  1: ex1,ey1,ex2,ey2 = CELL-9, 7, CELL-9, CELL-9
            elif dx == -1: ex1,ey1,ex2,ey2 = 7,      7, 7,       CELL-9
            elif dy ==  1: ex1,ey1,ex2,ey2 = 7, CELL-9, CELL-9,  CELL-9
            else:           ex1,ey1,ex2,ey2 = 7,      7, CELL-9,  7
            pygame.draw.circle(surface, EYE_W, (x+ex1, y+ey1), 4)
            pygame.draw.circle(surface, EYE_W, (x+ex2, y+ey2), 4)
            pygame.draw.circle(surface, EYE_P, (x+ex1, y+ey1), 2)
            pygame.draw.circle(surface, EYE_P, (x+ex2, y+ey2), 2)


def draw_apple(surface, pos, tick):
    x  = MAP_X + pos[0] * CELL
    y  = MAP_Y + pos[1] * CELL
    cx = x + CELL // 2
    cy = y + CELL // 2 + int(math.sin(tick * 0.05) * 1.5)
    rr = CELL // 2 - 4
    pygame.draw.circle(surface, RED,   (cx, cy), rr)
    pygame.draw.circle(surface, SHINE, (cx - rr//3, cy - rr//3), rr//3)
    pygame.draw.line(surface, (80, 40, 10), (cx, cy - rr), (cx+2, cy - rr - 6), 2)
    pygame.draw.polygon(surface, (50, 160, 40),
                        [(cx+2, cy-rr-6), (cx+9, cy-rr-10), (cx+5, cy-rr-2)])


def draw_hud(surface, font, score, high_score):
    pygame.draw.rect(surface, HUD_BG, (0, 0, WIDTH, HUD_H))
    sc = font.render(f"Score: {score}", True, WHITE)
    hi = font.render(f"Best: {high_score}", True, GOLD)
    surface.blit(sc, (12, HUD_H//2 - sc.get_height()//2))
    surface.blit(hi, (WIDTH - hi.get_width() - 12, HUD_H//2 - hi.get_height()//2))


def draw_menu(surface, big_font, font, small_font, high_score, tick):
    surface.fill(HUD_BG)
    draw_board(surface)
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 120))
    surface.blit(overlay, (0, 0))

    for i in range(12):
        bx = MAP_X + 16 + i * (CELL + 2)
        by = HEIGHT // 2 + int(math.sin(tick * 0.04 + i * 0.5) * 18)
        ratio = i / 11
        g = int(120 + ratio * 80)
        pygame.draw.rect(surface, (40, g, 40), (bx, by, CELL-2, CELL-2), border_radius=6)

    title  = big_font.render("SNAKE", True, GREEN1)
    shadow = big_font.render("SNAKE", True, (0, 60, 0))
    surface.blit(shadow, (WIDTH//2 - title.get_width()//2 + 3, 93))
    surface.blit(title,  (WIDTH//2 - title.get_width()//2,     90))

    hi = font.render(f"Best score: {high_score}", True, GOLD)
    surface.blit(hi, (WIDTH//2 - hi.get_width()//2, 170))

    lines = [
        ("Arrow Keys or WASD to move", WHITE),
        ("SPACE to pause", WHITE),
        ("", WHITE),
        ("Press ENTER to start", WHITE),
    ]
    y0 = 230
    for text, color in lines:
        t = small_font.render(text, True, color)
        surface.blit(t, (WIDTH//2 - t.get_width()//2, y0))
        y0 += 32


def draw_gameover(surface, big_font, font, small_font, score, high_score):
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill(OVERLAY)
    surface.blit(overlay, (0, 0))

    over = big_font.render("GAME OVER", True, RED)
    surface.blit(over, (WIDTH//2 - over.get_width()//2, HEIGHT//2 - 110))

    sc  = font.render(f"Your score: {score}", True, WHITE)
    hi  = font.render(f"Best score: {high_score}", True, GOLD)
    msg = small_font.render("ENTER to play again   |   ESC to quit", True, (200, 200, 200))

    surface.blit(sc,  (WIDTH//2 - sc.get_width()//2,  HEIGHT//2 - 20))
    surface.blit(hi,  (WIDTH//2 - hi.get_width()//2,  HEIGHT//2 + 28))
    surface.blit(msg, (WIDTH//2 - msg.get_width()//2, HEIGHT//2 + 90))

    if score > 0 and score >= high_score:
        new = font.render("NEW RECORD!", True, GOLD)
        surface.blit(new, (WIDTH//2 - new.get_width()//2, HEIGHT//2 + 62))


def new_apple(snake):
    while True:
        pos = (random.randint(0, GRID_W - 1), random.randint(0, GRID_H - 1))
        if pos not in snake:
            return pos


def reset_game():
    cx, cy = GRID_W // 2, GRID_H // 2
    snake = [(cx, cy), (cx-1, cy), (cx-2, cy)]
    direction = (1, 0)
    return snake, direction, new_apple(snake), 0


def main():
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Snake")
    clock = pygame.time.Clock()

    big_font   = pygame.font.SysFont("Arial", 54, bold=True)
    font       = pygame.font.SysFont("Arial", 26, bold=True)
    small_font = pygame.font.SysFont("Arial", 20)

    snake, direction, apple, score = reset_game()
    high_score = 0
    STATE = "MENU"
    move_timer = 0
    move_interval = 1.0 / SNAKE_SPEED
    next_dir = direction
    tick = 0

    while True:
        dt = clock.tick(FPS) / 1000.0
        tick += 1

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()

            if event.type == pygame.KEYDOWN:
                if STATE == "MENU" and event.key == pygame.K_RETURN:
                    snake, direction, apple, score = reset_game()
                    next_dir = direction
                    move_timer = 0
                    STATE = "PLAYING"

                elif STATE == "GAMEOVER":
                    if event.key == pygame.K_RETURN:
                        snake, direction, apple, score = reset_game()
                        next_dir = direction
                        move_timer = 0
                        STATE = "PLAYING"
                    elif event.key == pygame.K_ESCAPE:
                        pygame.quit(); sys.exit()

                elif STATE == "PLAYING":
                    dx, dy = direction
                    if event.key in (pygame.K_UP,    pygame.K_w) and dy == 0:
                        next_dir = (0, -1)
                    elif event.key in (pygame.K_DOWN,  pygame.K_s) and dy == 0:
                        next_dir = (0,  1)
                    elif event.key in (pygame.K_LEFT,  pygame.K_a) and dx == 0:
                        next_dir = (-1, 0)
                    elif event.key in (pygame.K_RIGHT, pygame.K_d) and dx == 0:
                        next_dir = (1,  0)
                    elif event.key == pygame.K_SPACE:
                        STATE = "PAUSED"

                elif STATE == "PAUSED" and event.key == pygame.K_SPACE:
                    STATE = "PLAYING"

        if STATE == "PLAYING":
            move_timer += dt
            if move_timer >= move_interval:
                move_timer = 0
                direction = next_dir
                dx, dy = direction
                hx, hy = snake[0]
                new_head = (hx + dx, hy + dy)

                if not (0 <= new_head[0] < GRID_W and 0 <= new_head[1] < GRID_H):
                    if SOUND_OK: die_sound.play()
                    high_score = max(high_score, score)
                    STATE = "GAMEOVER"
                    continue

                if new_head in snake:
                    if SOUND_OK: die_sound.play()
                    high_score = max(high_score, score)
                    STATE = "GAMEOVER"
                    continue

                snake.insert(0, new_head)

                if new_head == apple:
                    score += 10
                    if SOUND_OK:
                        if score % 50 == 0:
                            bonus_sound.play()
                        else:
                            eat_sound.play()
                    apple = new_apple(snake)
                    move_interval = max(0.06, 1.0 / (SNAKE_SPEED + score // 50))
                else:
                    snake.pop()

        if STATE == "MENU":
            draw_menu(screen, big_font, font, small_font, high_score, tick)
        else:
            surface = screen
            surface.fill(HUD_BG)
            draw_board(surface)
            draw_apple(surface, apple, tick)
            draw_snake(surface, snake, direction)
            draw_hud(surface, font, score, high_score)

            if STATE == "PAUSED":
                p = big_font.render("PAUSED", True, WHITE)
                screen.blit(p, (WIDTH//2 - p.get_width()//2, HEIGHT//2 - 28))

            elif STATE == "GAMEOVER":
                draw_gameover(screen, big_font, font, small_font, score, high_score)

        pygame.display.flip()


if __name__ == "__main__":
    main()