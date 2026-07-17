"""
Shared helper functions: math utilities, collision resolution, obstacle
steering, line-of-sight checks, and cover-point selection. Used by the
player, enemies, and projectiles.
"""

import math
import pygame

from settings import SCREEN_WIDTH, SCREEN_HEIGHT


def clamp(value, min_value, max_value):
    return max(min_value, min(value, max_value))


def distance(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def is_boss_level(level):
    return level % 5 == 0


def move_with_collision(pos, delta, radius, obstacles):
    """
    Move `pos` (a pygame.Vector2) by `delta`, resolving collisions against
    `obstacles` (anything with a `.rect`) one axis at a time so entities
    slide along surfaces instead of getting stuck.
    """
    new_x = pos.x + delta.x
    rect = pygame.Rect(int(new_x - radius), int(pos.y - radius), int(radius * 2), int(radius * 2))
    if not any(rect.colliderect(o.rect) for o in obstacles):
        pos.x = new_x

    new_y = pos.y + delta.y
    rect = pygame.Rect(int(pos.x - radius), int(new_y - radius), int(radius * 2), int(radius * 2))
    if not any(rect.colliderect(o.rect) for o in obstacles):
        pos.y = new_y


STEER_ANGLE_OFFSETS = [0, 25, -25, 50, -50, 75, -75, 100, -100, 130, -130, 160, -160]


def steer_toward(pos, target_pos, speed, radius, obstacles):
    """
    Return a movement vector that heads toward `target_pos` but fans out to
    either side to find a direction that isn't immediately blocked, so
    entities route around corners instead of getting stuck.
    """
    base_dir = pygame.Vector2(target_pos) - pos
    if base_dir.length_squared() == 0:
        return pygame.Vector2(0, 0)
    base_dir = base_dir.normalize()
    base_angle = math.atan2(base_dir.y, base_dir.x)

    for offset_deg in STEER_ANGLE_OFFSETS:
        test_angle = base_angle + math.radians(offset_deg)
        test_dir = pygame.Vector2(math.cos(test_angle), math.sin(test_angle))
        step = test_dir * speed
        prospective = pos + step
        rect = pygame.Rect(
            int(prospective.x - radius), int(prospective.y - radius),
            int(radius * 2), int(radius * 2),
        )
        if not any(rect.colliderect(o.rect) for o in obstacles):
            return step

    return pygame.Vector2(0, 0)


def line_of_sight(a, b, obstacles, step=10):
    """Sample points along segment a->b; blocked if any point is inside an obstacle."""
    a = pygame.Vector2(a)
    b = pygame.Vector2(b)
    dist = a.distance_to(b)
    if dist == 0:
        return True
    steps = max(1, int(dist // step))
    for i in range(steps + 1):
        t = i / steps
        point = a.lerp(b, t)
        for o in obstacles:
            if o.rect.collidepoint(point.x, point.y):
                return False
    return True


def compute_cover_points(obstacles, margin=28):
    """Candidate 'hiding spots' just outside each obstacle's corners/edges."""
    points = []
    for o in obstacles:
        r = o.rect
        candidates = [
            (r.left - margin, r.top - margin), (r.right + margin, r.top - margin),
            (r.left - margin, r.bottom + margin), (r.right + margin, r.bottom + margin),
            (r.centerx, r.top - margin), (r.centerx, r.bottom + margin),
            (r.left - margin, r.centery), (r.right + margin, r.centery),
        ]
        for cx, cy in candidates:
            cx = clamp(cx, 15, SCREEN_WIDTH - 15)
            cy = clamp(cy, 15, SCREEN_HEIGHT - 15)
            points.append((cx, cy))
    return points


def pick_cover_point(pos, player_pos, cover_points, obstacles, min_dist_from_player=130):
    """Nearest cover point that currently breaks line-of-sight to the player."""
    best = None
    best_dist = float("inf")
    for cp in cover_points:
        if line_of_sight(cp, player_pos, obstacles):
            continue
        if distance(cp, player_pos) < min_dist_from_player:
            continue
        d = distance(pos, cp)
        if d < best_dist:
            best_dist = d
            best = cp
    return pygame.Vector2(best) if best else None
