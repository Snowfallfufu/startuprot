"""
Wall obstacle class and the rotating set of level layouts.
"""

import pygame

from settings import WALL_COLOR, WALL_BORDER
from utils import is_boss_level


class Wall:
    def __init__(self, x, y, w, h):
        self.rect = pygame.Rect(x, y, w, h)

    def draw(self, surface):
        pygame.draw.rect(surface, WALL_COLOR, self.rect)
        pygame.draw.rect(surface, WALL_BORDER, self.rect, 3)
        brick_h = 16
        y = self.rect.top
        row = 0
        while y < self.rect.bottom:
            offset = 0 if row % 2 == 0 else 20
            x = self.rect.left + offset
            while x < self.rect.right:
                pygame.draw.line(surface, WALL_BORDER, (x, y), (x, min(y + brick_h, self.rect.bottom)), 1)
                x += 40
            pygame.draw.line(surface, WALL_BORDER, (self.rect.left, y), (self.rect.right, y), 1)
            y += brick_h
            row += 1


LAYOUT_CORNERS = [
    (140, 90, 220, 28), (140, 90, 28, 160),
    (600, 90, 220, 28), (792, 90, 28, 160),
    (140, 522, 220, 28), (140, 362, 28, 160),
    (600, 522, 220, 28), (792, 362, 28, 160),
    (466, 150, 28, 90), (466, 400, 28, 90),
]

LAYOUT_CORRIDORS = [
    (80, 140, 200, 30), (340, 140, 280, 30), (680, 140, 200, 30),
    (80, 470, 200, 30), (340, 470, 280, 30), (680, 470, 200, 30),
    (150, 220, 30, 200), (780, 220, 30, 200),
]

LAYOUT_PILLARS = [
    (200, 150, 50, 50), (700, 150, 50, 50),
    (200, 440, 50, 50), (700, 440, 50, 50),
    (350, 300, 50, 50), (600, 300, 50, 50),
    (455, 170, 50, 50), (455, 420, 50, 50),
]

NORMAL_LAYOUTS = [LAYOUT_CORNERS, LAYOUT_CORRIDORS, LAYOUT_PILLARS]

BOSS_LAYOUT = [
    (60, 60, 40, 40), (860, 60, 40, 40),
    (60, 540, 40, 40), (860, 540, 40, 40),
]


def build_walls_from_data(data):
    return [Wall(*rect) for rect in data]


def get_wall_layout(level):
    if is_boss_level(level):
        return build_walls_from_data(BOSS_LAYOUT)
    idx = (level - 1) % len(NORMAL_LAYOUTS)
    return build_walls_from_data(NORMAL_LAYOUTS[idx])
