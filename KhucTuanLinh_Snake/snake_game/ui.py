"""Lớp Button: nút bấm giao diện dùng cho menu bắt đầu và màn hình game over."""
import pygame

from .settings import COLOR_ACCENT


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
