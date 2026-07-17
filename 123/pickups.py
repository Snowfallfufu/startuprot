"""
Ground pickups (health / ammo) that occasionally drop from kills, and the
shared Explosion visual effect used by grenades and barrels.
"""

import math
import random
import pygame

from settings import WHITE, HEALTH_PICKUP, AMMO_PICKUP, BLAST_COLOR, BLAST_CORE
from utils import clamp


class Pickup:
    def __init__(self, pos, kind):
        self.pos = pygame.Vector2(pos)
        self.kind = kind  # "health" or "ammo"
        self.radius = 13
        self.lifetime = 600  # 10 seconds
        self.alive = True
        self.bob_timer = random.randint(0, 100)

    def update(self):
        self.lifetime -= 1
        self.bob_timer += 1
        if self.lifetime <= 0:
            self.alive = False

    def draw(self, surface):
        bob = math.sin(self.bob_timer * 0.1) * 3
        cx = int(self.pos.x)
        cy = int(self.pos.y + bob)

        if self.kind == "health":
            pygame.draw.circle(surface, HEALTH_PICKUP, (cx, cy), self.radius)
            pygame.draw.circle(surface, WHITE, (cx, cy), self.radius, 2)
            pygame.draw.line(surface, WHITE, (cx - 6, cy), (cx + 6, cy), 3)
            pygame.draw.line(surface, WHITE, (cx, cy - 6), (cx, cy + 6), 3)
        else:
            pygame.draw.circle(surface, AMMO_PICKUP, (cx, cy), self.radius)
            pygame.draw.circle(surface, (120, 100, 20), (cx, cy), self.radius, 2)
            pygame.draw.rect(surface, (80, 60, 10), (cx - 3, cy - 7, 6, 14))

        if self.lifetime < 120 and (self.lifetime // 8) % 2 == 0:
            pygame.draw.circle(surface, WHITE, (cx, cy), self.radius + 3, 1)


class Explosion:
    def __init__(self, pos, radius):
        self.pos = pygame.Vector2(pos)
        self.radius = radius
        self.duration = 18
        self.timer = self.duration
        self.alive = True

    def update(self):
        self.timer -= 1
        if self.timer <= 0:
            self.alive = False

    def draw(self, surface):
        progress = 1 - (self.timer / self.duration)
        r = max(4, int(self.radius * progress))
        pygame.draw.circle(surface, BLAST_COLOR, (int(self.pos.x), int(self.pos.y)), r, 4)
        pygame.draw.circle(surface, BLAST_CORE, (int(self.pos.x), int(self.pos.y)), max(4, int(r * 0.35)))
