"""
Projectiles: player bullets (with optional piercing), enemy spit
projectiles, and thrown grenades.
"""

import pygame

from settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, SPIT_COLOR, SPITTER_DARK,
    GRENADE_COLOR, GRENADE_DARK, BLAST_COLOR, BLAST_CORE,
)


class Bullet:
    def __init__(self, pos, direction, damage, speed, color, pierce=0):
        self.pos = pygame.Vector2(pos)
        self.direction = direction
        self.speed = speed
        self.radius = 4
        self.damage = damage
        self.color = color
        self.pierce = pierce
        self.alive = True

    def update(self, obstacles):
        self.pos += self.direction * self.speed
        if (
            self.pos.x < 0 or self.pos.x > SCREEN_WIDTH
            or self.pos.y < 0 or self.pos.y > SCREEN_HEIGHT
        ):
            self.alive = False
            return
        rect = pygame.Rect(
            int(self.pos.x - self.radius), int(self.pos.y - self.radius),
            int(self.radius * 2), int(self.radius * 2),
        )
        if any(rect.colliderect(o.rect) for o in obstacles):
            self.alive = False

    def draw(self, surface):
        if self.pierce > 0:
            tail = self.pos - self.direction * 10
            pygame.draw.line(surface, self.color, tail, self.pos, 3)
        pygame.draw.circle(surface, self.color, (int(self.pos.x), int(self.pos.y)), self.radius)


class Spit:
    """A ranged projectile fired by a Spitter zombie at the player."""

    def __init__(self, pos, direction, damage, speed):
        self.pos = pygame.Vector2(pos)
        self.direction = direction
        self.speed = speed
        self.radius = 6
        self.damage = damage
        self.alive = True

    def update(self, obstacles):
        self.pos += self.direction * self.speed
        if (
            self.pos.x < 0 or self.pos.x > SCREEN_WIDTH
            or self.pos.y < 0 or self.pos.y > SCREEN_HEIGHT
        ):
            self.alive = False
            return
        rect = pygame.Rect(
            int(self.pos.x - self.radius), int(self.pos.y - self.radius),
            int(self.radius * 2), int(self.radius * 2),
        )
        if any(rect.colliderect(o.rect) for o in obstacles):
            self.alive = False

    def draw(self, surface):
        pygame.draw.circle(surface, SPIT_COLOR, (int(self.pos.x), int(self.pos.y)), self.radius)
        pygame.draw.circle(surface, SPITTER_DARK, (int(self.pos.x), int(self.pos.y)), self.radius, 1)


class Grenade:
    """
    A thrown weapon that arcs to the target point (ignoring wall collision
    in flight, like a real throw) and detonates in an AoE radius, either
    on arrival or when its fuse runs out.
    """

    def __init__(self, pos, target, speed=9, damage=85, radius=95, fuse_frames=45):
        self.pos = pygame.Vector2(pos)
        target = pygame.Vector2(target)
        direction = target - self.pos
        self.total_dist = direction.length()
        self.direction = direction.normalize() if direction.length_squared() > 0 else pygame.Vector2(1, 0)
        self.speed = speed
        self.damage = damage
        self.radius = radius
        self.fuse = fuse_frames
        self.traveled = 0
        self.exploded = False
        self.explosion_timer = 0
        self.explosion_duration = 18
        self.damage_applied = False
        self.alive = True

    def update(self):
        if self.exploded:
            self.explosion_timer -= 1
            if self.explosion_timer <= 0:
                self.alive = False
            return
        self.pos += self.direction * self.speed
        self.traveled += self.speed
        self.fuse -= 1
        if self.traveled >= self.total_dist or self.fuse <= 0:
            self.exploded = True
            self.explosion_timer = self.explosion_duration

    def draw(self, surface):
        if self.exploded:
            progress = 1 - (self.explosion_timer / self.explosion_duration)
            r = max(4, int(self.radius * progress))
            pygame.draw.circle(surface, BLAST_COLOR, (int(self.pos.x), int(self.pos.y)), r, 4)
            pygame.draw.circle(surface, BLAST_CORE, (int(self.pos.x), int(self.pos.y)), max(4, int(r * 0.35)))
        else:
            pygame.draw.circle(surface, GRENADE_COLOR, (int(self.pos.x), int(self.pos.y)), 7)
            pygame.draw.circle(surface, GRENADE_DARK, (int(self.pos.x), int(self.pos.y)), 7, 2)
