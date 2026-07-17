"""
Explosive barrels: destructible obstacles that deal AoE damage (and can
chain-detonate each other) when destroyed.
"""

import random
import pygame

from settings import SCREEN_WIDTH, SCREEN_HEIGHT, BARREL_COLOR, BARREL_DARK, BARREL_WARN, GRAY
from utils import clamp, distance


class Barrel:
    def __init__(self, pos):
        self.pos = pygame.Vector2(pos)
        self.radius = 18
        self.rect = pygame.Rect(
            int(self.pos.x - self.radius), int(self.pos.y - self.radius),
            int(self.radius * 2), int(self.radius * 2),
        )
        self.max_health = 40
        self.health = self.max_health
        self.alive = True
        self.exploded = False
        self.explosion_handled = False
        self.blast_radius = 110
        self.blast_damage = 90

    def take_damage(self, amount):
        if not self.alive:
            return
        self.health -= amount
        if self.health <= 0:
            self.alive = False
            self.exploded = True

    def draw(self, surface):
        rect = pygame.Rect(
            int(self.pos.x - self.radius), int(self.pos.y - self.radius),
            int(self.radius * 2), int(self.radius * 2),
        )
        pygame.draw.rect(surface, BARREL_COLOR, rect, border_radius=5)
        pygame.draw.rect(surface, BARREL_DARK, rect, 3, border_radius=5)
        pygame.draw.line(surface, BARREL_DARK, (rect.left + 3, rect.centery), (rect.right - 3, rect.centery), 2)
        pygame.draw.circle(surface, BARREL_WARN, (int(self.pos.x), int(self.pos.y) - 6), 5)

        bar_width = 30
        ratio = clamp(self.health / self.max_health, 0, 1)
        bar_x = self.pos.x - bar_width // 2
        bar_y = self.pos.y - self.radius - 10
        pygame.draw.rect(surface, GRAY, (bar_x, bar_y, bar_width, 5))
        pygame.draw.rect(surface, BARREL_WARN, (bar_x, bar_y, bar_width * ratio, 5))


def generate_barrels(walls, count=4, min_dist_from_center=150):
    barrels = []
    tries = 0
    center = (SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)
    while len(barrels) < count and tries < 300:
        tries += 1
        x = random.uniform(70, SCREEN_WIDTH - 70)
        y = random.uniform(70, SCREEN_HEIGHT - 70)
        if distance((x, y), center) < min_dist_from_center:
            continue
        test_rect = pygame.Rect(x - 20, y - 20, 40, 40)
        if any(test_rect.colliderect(w.rect) for w in walls):
            continue
        if any(test_rect.colliderect(b.rect) for b in barrels):
            continue
        barrels.append(Barrel((x, y)))
    return barrels
