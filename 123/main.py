"""
Zombie Shooter - Tactical AI & Player Depth Edition
------------------------------------------------------
A top-down 2D zombie shooter built with Pygame, featuring:
  - Discrete levels (waves) that end once all zombies are cleared
  - A shop screen between levels to upgrade / unlock weapons
  - Multiple weapons: Pistol, Shotgun, Rifle - each with magazine + reload
  - A tough Boss zombie every 5th level, fought in an open arena layout
  - Persistent high scores saved to a local JSON file next to this script
  - Multiple wall/map layouts that rotate between levels
  - Regular zombies that steer around corners/obstacles instead of getting stuck
  - A tactical "Spitter" enemy that checks line-of-sight, leads its shots
    based on your movement, and retreats to real cover after firing
  - A DASH (i-frame escape tool) and GRENADES (AoE crowd control)
  - A PERK system: pick one random permanent bonus after every level

Controls:
    - WASD or Arrow Keys : Move
    - Mouse              : Aim
    - Left Click (hold)  : Shoot
    - SPACE              : Dash (brief invulnerability + burst of speed)
    - G                  : Throw a grenade at your cursor
    - 1 / 2 / 3          : Switch weapon (Pistol / Shotgun / Rifle)
    - R                  : Reload current weapon (during play)
    - In the shop screen : Number keys to buy upgrades / pick a perk,
                           ENTER to start next level
    - R                  : Restart after Game Over
    - ESC                : Quit

Requirements:
    pip install pygame

Run:
    python zombie_shooter.py
"""

import json
import math
import os
import random
import sys
import pygame

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------
pygame.init()

SCREEN_WIDTH, SCREEN_HEIGHT = 960, 640
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Zomsho Project")
clock = pygame.time.Clock()
FPS = 60

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HIGH_SCORE_FILE = os.path.join(SCRIPT_DIR, "zombie_shooter_highscores.json")
MAX_HIGH_SCORES = 5

# Colors
WHITE = (240, 240, 240)
BLACK = (15, 15, 15)
GREEN = (60, 200, 90)
DASH_GREEN = (150, 255, 190)
DARK_GREEN = (30, 120, 55)
RED = (200, 60, 60)
DARK_RED = (120, 25, 25)
YELLOW = (230, 200, 60)
GOLD = (255, 205, 70)
GRAY = (90, 90, 90)
LIGHT_GRAY = (160, 160, 160)
BLUE = (80, 140, 220)
PURPLE = (170, 80, 210)
DARK_PURPLE = (100, 40, 130)
SPITTER_COLOR = (150, 210, 90)
SPITTER_DARK = (85, 130, 45)
SPIT_COLOR = (170, 230, 110)
GRENADE_COLOR = (70, 90, 40)
GRENADE_DARK = (30, 50, 20)
BLAST_COLOR = (255, 140, 40)
BLAST_CORE = (255, 220, 120)
BG_COLOR = (35, 40, 35)
WALL_COLOR = (95, 92, 88)
WALL_BORDER = (55, 52, 48)
PERK_COLOR = (120, 200, 255)

font_huge = pygame.font.SysFont("arial", 72, bold=True)
font_large = pygame.font.SysFont("arial", 48, bold=True)
font_medium = pygame.font.SysFont("arial", 30, bold=True)
font_small = pygame.font.SysFont("arial", 21)
font_tiny = pygame.font.SysFont("arial", 17)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------
def clamp(value, min_value, max_value):
    return max(min_value, min(value, max_value))


def distance(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def move_with_collision(pos, delta, radius, walls):
    new_x = pos.x + delta.x
    rect = pygame.Rect(int(new_x - radius), int(pos.y - radius), int(radius * 2), int(radius * 2))
    if not any(rect.colliderect(w.rect) for w in walls):
        pos.x = new_x

    new_y = pos.y + delta.y
    rect = pygame.Rect(int(pos.x - radius), int(new_y - radius), int(radius * 2), int(radius * 2))
    if not any(rect.colliderect(w.rect) for w in walls):
        pos.y = new_y


STEER_ANGLE_OFFSETS = [0, 25, -25, 50, -50, 75, -75, 100, -100, 130, -130, 160, -160]


def steer_toward(pos, target_pos, speed, radius, walls):
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
        if not any(rect.colliderect(w.rect) for w in walls):
            return step

    return pygame.Vector2(0, 0)


def line_of_sight(a, b, walls, step=10):
    a = pygame.Vector2(a)
    b = pygame.Vector2(b)
    dist = a.distance_to(b)
    if dist == 0:
        return True
    steps = max(1, int(dist // step))
    for i in range(steps + 1):
        t = i / steps
        point = a.lerp(b, t)
        for w in walls:
            if w.rect.collidepoint(point.x, point.y):
                return False
    return True


def compute_cover_points(walls, margin=28):
    points = []
    for w in walls:
        r = w.rect
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


def pick_cover_point(pos, player_pos, cover_points, walls, min_dist_from_player=130):
    best = None
    best_dist = float("inf")
    for cp in cover_points:
        if line_of_sight(cp, player_pos, walls):
            continue
        if distance(cp, player_pos) < min_dist_from_player:
            continue
        d = distance(pos, cp)
        if d < best_dist:
            best_dist = d
            best = cp
    return pygame.Vector2(best) if best else None


# ---------------------------------------------------------------------------
# Map / walls
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# High score persistence
# ---------------------------------------------------------------------------
def load_high_scores():
    if not os.path.exists(HIGH_SCORE_FILE):
        return []
    try:
        with open(HIGH_SCORE_FILE, "r") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return []


def save_high_scores(scores):
    try:
        with open(HIGH_SCORE_FILE, "w") as f:
            json.dump(scores, f, indent=2)
    except OSError:
        pass


def update_high_scores(scores, score, level):
    new_entry = {"score": score, "level": level}
    updated = scores + [new_entry]
    updated.sort(key=lambda e: e["score"], reverse=True)
    updated = updated[:MAX_HIGH_SCORES]
    is_new_record = new_entry in updated and (
        len(scores) < MAX_HIGH_SCORES or score > scores[-1]["score"]
    )
    save_high_scores(updated)
    return updated, is_new_record


# ---------------------------------------------------------------------------
# Perks
# ---------------------------------------------------------------------------
def _perk_adrenaline(p):
    p.speed *= 1.15


def _perk_quick_hands(p):
    p.reload_multiplier *= 0.8


def _perk_sharpshooter(p):
    p.damage_multiplier *= 1.15


def _perk_iron_skin(p):
    p.damage_reduction = 1 - (1 - p.damage_reduction) * 0.9


def _perk_vampiric(p):
    p.lifesteal_per_kill += 2


def _perk_scavenger(p):
    p.money_multiplier *= 1.25


def _perk_grenadier(p):
    p.grenade_cooldown_multiplier *= 0.75


def _perk_dash_master(p):
    p.dash_cooldown_multiplier *= 0.75


PERKS_POOL = [
    ("Adrenaline Rush", "+15% move speed", _perk_adrenaline),
    ("Quick Hands", "-20% reload time", _perk_quick_hands),
    ("Sharpshooter", "+15% weapon damage", _perk_sharpshooter),
    ("Iron Skin", "-10% damage taken", _perk_iron_skin),
    ("Vampiric Bite", "Heal 2 HP per kill", _perk_vampiric),
    ("Scavenger", "+25% money from kills", _perk_scavenger),
    ("Grenadier", "-25% grenade cooldown", _perk_grenadier),
    ("Dash Master", "-25% dash cooldown", _perk_dash_master),
]


# ---------------------------------------------------------------------------
# Weapons
# ---------------------------------------------------------------------------
class Weapon:
    def __init__(self, name, unlocked, unlock_cost, base_damage, damage_per_level,
                 base_cooldown, cooldown_per_level, min_cooldown,
                 bullet_speed, pellets, spread_degrees, color, upgrade_base_cost,
                 magazine_size, reload_frames):
        self.name = name
        self.unlocked = unlocked
        self.unlock_cost = unlock_cost
        self.level = 1 if unlocked else 0
        self.base_damage = base_damage
        self.damage_per_level = damage_per_level
        self.base_cooldown = base_cooldown
        self.cooldown_per_level = cooldown_per_level
        self.min_cooldown = min_cooldown
        self.bullet_speed = bullet_speed
        self.pellets = pellets
        self.spread_degrees = spread_degrees
        self.color = color
        self.upgrade_base_cost = upgrade_base_cost
        self.max_level = 5
        self.magazine_size = magazine_size
        self.reload_frames = reload_frames

    @property
    def damage(self):
        return self.base_damage + self.damage_per_level * (self.level - 1)

    @property
    def cooldown(self):
        cd = self.base_cooldown - self.cooldown_per_level * (self.level - 1)
        return max(self.min_cooldown, cd)

    def upgrade_cost(self):
        if self.level >= self.max_level:
            return None
        return int(self.upgrade_base_cost * (1.6 ** (self.level - 1)))

    def can_upgrade(self):
        return self.unlocked and self.level < self.max_level


def make_default_weapons():
    return {
        "pistol": Weapon(
            name="Pistol", unlocked=True, unlock_cost=0,
            base_damage=25, damage_per_level=8,
            base_cooldown=14, cooldown_per_level=1.5, min_cooldown=7,
            bullet_speed=13, pellets=1, spread_degrees=0,
            color=YELLOW, upgrade_base_cost=40,
            magazine_size=12, reload_frames=55,
        ),
        "shotgun": Weapon(
            name="Shotgun", unlocked=False, unlock_cost=120,
            base_damage=16, damage_per_level=5,
            base_cooldown=42, cooldown_per_level=3, min_cooldown=26,
            bullet_speed=11, pellets=5, spread_degrees=28,
            color=(255, 150, 60), upgrade_base_cost=70,
            magazine_size=6, reload_frames=80,
        ),
        "rifle": Weapon(
            name="Rifle", unlocked=False, unlock_cost=220,
            base_damage=14, damage_per_level=4,
            base_cooldown=6, cooldown_per_level=0.5, min_cooldown=3,
            bullet_speed=17, pellets=1, spread_degrees=3,
            color=(120, 220, 255), upgrade_base_cost=90,
            magazine_size=30, reload_frames=95,
        ),
    }


# ---------------------------------------------------------------------------
# Player
# ---------------------------------------------------------------------------
class Player:
    def __init__(self):
        self.pos = pygame.Vector2(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        self.radius = 18
        self.speed = 4.5
        self.max_health = 100
        self.health = self.max_health
        self.angle = 0
        self.shoot_cooldown = 0
        self.velocity = pygame.Vector2(0, 0)
        self.last_move_dir = pygame.Vector2(1, 0)

        self.weapons = make_default_weapons()
        self.weapon_order = ["pistol", "shotgun", "rifle"]
        self.current_weapon_key = "pistol"

        self.ammo = {key: w.magazine_size if w.unlocked else 0 for key, w in self.weapons.items()}
        self.reloading = False
        self.reload_timer = 0
        self.reload_weapon_key = None

        # Dash
        self.dash_cooldown_max = 90
        self.dash_timer = 0
        self.dashing = False
        self.dash_duration = 10
        self.dash_frames_left = 0
        self.dash_speed_multiplier = 3.2
        self.dash_direction = pygame.Vector2(1, 0)
        self.invulnerable = False

        # Grenades
        self.grenade_cooldown_max = 480
        self.grenade_timer = 0

        # Perk-affected multipliers (permanent for the run)
        self.damage_multiplier = 1.0
        self.damage_reduction = 0.0
        self.lifesteal_per_kill = 0
        self.money_multiplier = 1.0
        self.reload_multiplier = 1.0
        self.dash_cooldown_multiplier = 1.0
        self.grenade_cooldown_multiplier = 1.0
        self.perks_taken = []

    @property
    def current_weapon(self):
        return self.weapons[self.current_weapon_key]

    def ensure_ammo_initialized(self, weapon_key):
        weapon = self.weapons[weapon_key]
        if weapon_key not in self.ammo or self.ammo[weapon_key] == 0:
            self.ammo[weapon_key] = weapon.magazine_size

    def switch_weapon(self, key):
        if key in self.weapons and self.weapons[key].unlocked:
            self.current_weapon_key = key
            self.shoot_cooldown = max(self.shoot_cooldown, 5)

    def start_reload(self):
        weapon = self.current_weapon
        if self.reloading:
            return
        if self.ammo[self.current_weapon_key] >= weapon.magazine_size:
            return
        self.reloading = True
        self.reload_weapon_key = self.current_weapon_key
        self.reload_timer = int(weapon.reload_frames * self.reload_multiplier)

    def start_dash(self):
        if self.dashing or self.dash_timer > 0:
            return
        direction = self.last_move_dir
        if direction.length_squared() == 0:
            direction = pygame.Vector2(math.cos(self.angle), math.sin(self.angle))
        self.dash_direction = direction.normalize()
        self.dashing = True
        self.dash_frames_left = self.dash_duration
        self.dash_timer = int(self.dash_cooldown_max * self.dash_cooldown_multiplier)
        self.invulnerable = True

    def try_throw_grenade(self, target_pos, grenades):
        if self.grenade_timer > 0:
            return
        grenades.append(Grenade(self.pos, target_pos))
        self.grenade_timer = int(self.grenade_cooldown_max * self.grenade_cooldown_multiplier)

    def handle_input(self, keys, walls):
        prev_pos = pygame.Vector2(self.pos)

        move = pygame.Vector2(0, 0)
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            move.y -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            move.y += 1
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            move.x -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            move.x += 1

        if move.length_squared() > 0:
            self.last_move_dir = move.normalize()

        if self.dashing:
            step = self.dash_direction * (self.speed * self.dash_speed_multiplier)
            move_with_collision(self.pos, step, self.radius, walls)
            self.dash_frames_left -= 1
            if self.dash_frames_left <= 0:
                self.dashing = False
                self.invulnerable = False
        elif move.length_squared() > 0:
            scaled = move.normalize() * self.speed
            move_with_collision(self.pos, scaled, self.radius, walls)

        self.pos.x = clamp(self.pos.x, self.radius, SCREEN_WIDTH - self.radius)
        self.pos.y = clamp(self.pos.y, self.radius, SCREEN_HEIGHT - self.radius)

        self.velocity = self.pos - prev_pos

        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= 1
        if self.dash_timer > 0:
            self.dash_timer -= 1
        if self.grenade_timer > 0:
            self.grenade_timer -= 1

        if self.reloading:
            self.reload_timer -= 1
            if self.reload_timer <= 0:
                self.ammo[self.reload_weapon_key] = self.weapons[self.reload_weapon_key].magazine_size
                self.reloading = False
                self.reload_weapon_key = None

    def update_aim(self, mouse_pos):
        dx = mouse_pos[0] - self.pos.x
        dy = mouse_pos[1] - self.pos.y
        self.angle = math.atan2(dy, dx)

    def try_shoot(self, bullets):
        if self.shoot_cooldown > 0 or self.reloading or self.dashing:
            return
        weapon = self.current_weapon
        if self.ammo[self.current_weapon_key] <= 0:
            self.start_reload()
            return

        self.shoot_cooldown = weapon.cooldown
        self.ammo[self.current_weapon_key] -= 1

        pellets = weapon.pellets
        spread = math.radians(weapon.spread_degrees)
        effective_damage = weapon.damage * self.damage_multiplier
        for i in range(pellets):
            if pellets == 1:
                offset = 0
            else:
                offset = -spread / 2 + spread * (i / (pellets - 1))
            angle = self.angle + offset
            direction = pygame.Vector2(math.cos(angle), math.sin(angle))
            barrel_offset = direction * (self.radius + 5)
            bullet_pos = self.pos + barrel_offset
            bullets.append(Bullet(bullet_pos, direction, effective_damage,
                                   weapon.bullet_speed, weapon.color))

    def take_damage(self, amount):
        if self.invulnerable:
            return
        amount = amount * (1 - self.damage_reduction)
        self.health -= amount
        self.health = clamp(self.health, 0, self.max_health)

    def draw(self, surface):
        color = DASH_GREEN if self.dashing else GREEN
        pygame.draw.circle(surface, color, (int(self.pos.x), int(self.pos.y)), self.radius)
        pygame.draw.circle(surface, DARK_GREEN, (int(self.pos.x), int(self.pos.y)), self.radius, 3)
        end_x = self.pos.x + math.cos(self.angle) * (self.radius + 16)
        end_y = self.pos.y + math.sin(self.angle) * (self.radius + 16)
        pygame.draw.line(surface, self.current_weapon.color, self.pos, (end_x, end_y), 4)


# ---------------------------------------------------------------------------
# Bullet, enemy projectile & grenade
# ---------------------------------------------------------------------------
class Bullet:
    def __init__(self, pos, direction, damage, speed, color):
        self.pos = pygame.Vector2(pos)
        self.direction = direction
        self.speed = speed
        self.radius = 4
        self.damage = damage
        self.color = color
        self.alive = True

    def update(self, walls):
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
        if any(rect.colliderect(w.rect) for w in walls):
            self.alive = False

    def draw(self, surface):
        pygame.draw.circle(surface, self.color, (int(self.pos.x), int(self.pos.y)), self.radius)


class Spit:
    def __init__(self, pos, direction, damage, speed):
        self.pos = pygame.Vector2(pos)
        self.direction = direction
        self.speed = speed
        self.radius = 6
        self.damage = damage
        self.alive = True

    def update(self, walls):
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
        if any(rect.colliderect(w.rect) for w in walls):
            self.alive = False

    def draw(self, surface):
        pygame.draw.circle(surface, SPIT_COLOR, (int(self.pos.x), int(self.pos.y)), self.radius)
        pygame.draw.circle(surface, SPITTER_DARK, (int(self.pos.x), int(self.pos.y)), self.radius, 1)


class Grenade:
    """
    A thrown weapon that arcs to the target point (ignoring wall collision
    in flight, like a real throw) and detonates in an AoE radius, either on
    arrival or when its fuse runs out.
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

    def update(self, walls):
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


# ---------------------------------------------------------------------------
# Zombie (Boss and Spitter subclasses)
# ---------------------------------------------------------------------------
class Zombie:
    def __init__(self, pos, speed, health, reward):
        self.pos = pygame.Vector2(pos)
        self.radius = 16
        self.speed = speed
        self.max_health = health
        self.health = health
        self.alive = True
        self.damage = 10
        self.attack_cooldown = 0
        self.reward = reward
        self.is_boss = False
        self.score_value = 10

    def update(self, player_pos, walls):
        step = steer_toward(self.pos, player_pos, self.speed, self.radius, walls)
        if step.length_squared() > 0:
            move_with_collision(self.pos, step, self.radius, walls)
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1

    def take_damage(self, amount):
        self.health -= amount
        if self.health <= 0:
            self.alive = False

    def draw(self, surface):
        pygame.draw.circle(surface, RED, (int(self.pos.x), int(self.pos.y)), self.radius)
        pygame.draw.circle(surface, DARK_RED, (int(self.pos.x), int(self.pos.y)), self.radius, 3)
        bar_width = 32
        health_ratio = clamp(self.health / self.max_health, 0, 1)
        bar_x = self.pos.x - bar_width // 2
        bar_y = self.pos.y - self.radius - 12
        pygame.draw.rect(surface, GRAY, (bar_x, bar_y, bar_width, 5))
        pygame.draw.rect(surface, RED, (bar_x, bar_y, bar_width * health_ratio, 5))


class Boss(Zombie):
    def __init__(self, pos, speed, health, reward):
        super().__init__(pos, speed, health, reward)
        self.radius = 34
        self.damage = 25
        self.is_boss = True
        self.score_value = 25

    def draw(self, surface):
        pygame.draw.circle(surface, PURPLE, (int(self.pos.x), int(self.pos.y)), self.radius)
        pygame.draw.circle(surface, DARK_PURPLE, (int(self.pos.x), int(self.pos.y)), self.radius, 4)

        label = font_small.render("BOSS", True, WHITE)
        surface.blit(label, (self.pos.x - label.get_width() // 2, self.pos.y - self.radius - 32))

        bar_width = 70
        health_ratio = clamp(self.health / self.max_health, 0, 1)
        bar_x = self.pos.x - bar_width // 2
        bar_y = self.pos.y - self.radius - 14
        pygame.draw.rect(surface, GRAY, (bar_x, bar_y, bar_width, 8))
        pygame.draw.rect(surface, PURPLE, (bar_x, bar_y, bar_width * health_ratio, 8))
        pygame.draw.rect(surface, WHITE, (bar_x, bar_y, bar_width, 8), 1)


class Spitter(Zombie):
    def __init__(self, pos, speed, health, reward):
        super().__init__(pos, speed, health, reward)
        self.radius = 15
        self.damage = 8
        self.score_value = 15

        self.attack_range = 260
        self.min_range = 110
        self.aim_time = 22
        self.attack_cooldown_max = 100
        self.retreat_duration = 80
        self.projectile_damage = 12
        self.projectile_speed = 7.5
        self.lead_frames = 16

        self.aiming = False
        self.aim_timer = 0
        self.retreat_timer = 0
        self.cover_target = None

    def update(self, player_pos, player_velocity, walls, cover_points):
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1

        los = line_of_sight(self.pos, player_pos, walls)
        dist_to_player = distance(self.pos, player_pos)
        fired_projectile = None

        if self.aiming:
            if not los:
                self.aiming = False
            else:
                self.aim_timer -= 1
                if self.aim_timer <= 0:
                    lead_point = pygame.Vector2(player_pos) + pygame.Vector2(player_velocity) * self.lead_frames
                    direction = lead_point - self.pos
                    if direction.length_squared() > 0:
                        direction = direction.normalize()
                        spawn_pos = self.pos + direction * (self.radius + 5)
                        fired_projectile = Spit(spawn_pos, direction, self.projectile_damage, self.projectile_speed)
                    self.aiming = False
                    self.attack_cooldown = self.attack_cooldown_max
                    self.retreat_timer = self.retreat_duration
                    self.cover_target = pick_cover_point(self.pos, player_pos, cover_points, walls)
            return fired_projectile

        if self.retreat_timer > 0:
            self.retreat_timer -= 1
            target = self.cover_target
            if target is None:
                self.cover_target = pick_cover_point(self.pos, player_pos, cover_points, walls)
            elif distance(self.pos, target) > 8:
                step = steer_toward(self.pos, target, self.speed, self.radius, walls)
                if step.length_squared() > 0:
                    move_with_collision(self.pos, step, self.radius, walls)
            return fired_projectile

        if dist_to_player < self.min_range:
            away = pygame.Vector2(self.pos) - pygame.Vector2(player_pos)
            if away.length_squared() > 0:
                away = away.normalize()
            target_point = pygame.Vector2(self.pos) + away * 100
            step = steer_toward(self.pos, target_point, self.speed, self.radius, walls)
            if step.length_squared() > 0:
                move_with_collision(self.pos, step, self.radius, walls)
        elif los and self.min_range <= dist_to_player <= self.attack_range and self.attack_cooldown <= 0:
            self.aiming = True
            self.aim_timer = self.aim_time
        else:
            step = steer_toward(self.pos, player_pos, self.speed, self.radius, walls)
            if step.length_squared() > 0:
                move_with_collision(self.pos, step, self.radius, walls)

        return fired_projectile

    def draw(self, surface):
        color = SPITTER_COLOR
        if self.aiming and (self.aim_timer // 4) % 2 == 0:
            color = (255, 230, 120)

        pygame.draw.circle(surface, color, (int(self.pos.x), int(self.pos.y)), self.radius)
        pygame.draw.circle(surface, SPITTER_DARK, (int(self.pos.x), int(self.pos.y)), self.radius, 3)

        if self.aiming:
            pygame.draw.circle(surface, RED, (int(self.pos.x), int(self.pos.y)), self.radius + 6, 2)

        bar_width = 28
        health_ratio = clamp(self.health / self.max_health, 0, 1)
        bar_x = self.pos.x - bar_width // 2
        bar_y = self.pos.y - self.radius - 12
        pygame.draw.rect(surface, GRAY, (bar_x, bar_y, bar_width, 5))
        pygame.draw.rect(surface, SPITTER_COLOR, (bar_x, bar_y, bar_width * health_ratio, 5))


def random_edge_position():
    side = random.choice(["top", "bottom", "left", "right"])
    if side == "top":
        return (random.uniform(0, SCREEN_WIDTH), -30)
    elif side == "bottom":
        return (random.uniform(0, SCREEN_WIDTH), SCREEN_HEIGHT + 30)
    elif side == "left":
        return (-30, random.uniform(0, SCREEN_HEIGHT))
    else:
        return (SCREEN_WIDTH + 30, random.uniform(0, SCREEN_HEIGHT))


def spawn_zombie(level):
    pos = random_edge_position()
    speed = random.uniform(1.2, 1.8) + level * 0.05
    health = 45 + level * 10
    reward = 8 + level
    return Zombie(pos, speed, health, reward)


def spawn_boss(level):
    pos = random_edge_position()
    speed = 0.9 + level * 0.01
    health = 420 + level * 25
    reward = 120 + level * 6
    return Boss(pos, speed, health, reward)


def spawn_spitter(level):
    pos = random_edge_position()
    speed = 1.5 + level * 0.02
    health = 40 + level * 6
    reward = 14 + level
    return Spitter(pos, speed, health, reward)


def is_boss_level(level):
    return level % 5 == 0


# ---------------------------------------------------------------------------
# Upgrade shop option definition
# ---------------------------------------------------------------------------
class ShopOption:
    def __init__(self, key, label_fn, cost_fn, action_fn, enabled_fn):
        self.key = key
        self.label_fn = label_fn
        self.cost_fn = cost_fn
        self.action_fn = action_fn
        self.enabled_fn = enabled_fn


# ---------------------------------------------------------------------------
# Game state
# ---------------------------------------------------------------------------
class Game:
    STATE_PLAYING = "playing"
    STATE_SHOP = "shop"
    STATE_GAME_OVER = "game_over"

    def __init__(self):
        self.high_scores = load_high_scores()
        self.walls = []
        self.cover_points = []
        self.reset()

    def reset(self):
        self.player = Player()
        self.bullets = []
        self.zombies = []
        self.enemy_projectiles = []
        self.grenades = []
        self.score = 0
        self.money = 60
        self.level = 1
        self.spawn_queue = []
        self.spawn_timer = 0
        self.spawn_interval = 55
        self.state = Game.STATE_PLAYING
        self.message_timer = 0
        self.flash_message = ""
        self.is_new_record = False
        self.recorded_this_run = False
        self.perk_choices = []
        self.perk_chosen_this_level = False
        self.begin_level(1)

    # -----------------------------------------------------------------
    # Level flow
    # -----------------------------------------------------------------
    def begin_level(self, level_number):
        self.level = level_number
        self.walls = get_wall_layout(level_number)
        self.cover_points = compute_cover_points(self.walls)

        self.player.pos = pygame.Vector2(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        self.player.velocity = pygame.Vector2(0, 0)

        self.spawn_interval = max(18, 58 - level_number * 2)
        self.spawn_timer = 0
        self.bullets = []
        self.zombies = []
        self.enemy_projectiles = []
        self.grenades = []

        spitter_count = 0
        if level_number >= 3:
            spitter_count = 1 + (level_number - 3) // 3

        if is_boss_level(level_number):
            normal_count = 3 + level_number // 2
            queue = ["normal"] * normal_count + ["spitter"] * spitter_count
            random.shuffle(queue)
            queue.append("boss")
            self.spawn_queue = queue
            self.flash_message = f"LEVEL {level_number} - BOSS INCOMING!"
        else:
            normal_count = 5 + level_number * 2
            queue = ["normal"] * normal_count + ["spitter"] * spitter_count
            random.shuffle(queue)
            self.spawn_queue = queue
            self.flash_message = f"LEVEL {level_number} - GO!"

        self.state = Game.STATE_PLAYING
        self.message_timer = 100

    def enter_shop(self):
        self.state = Game.STATE_SHOP
        self.perk_choices = random.sample(PERKS_POOL, 3)
        self.perk_chosen_this_level = False

    def enter_game_over(self):
        self.state = Game.STATE_GAME_OVER
        if not self.recorded_this_run:
            self.high_scores, self.is_new_record = update_high_scores(
                self.high_scores, self.score, self.level
            )
            self.recorded_this_run = True

    # -----------------------------------------------------------------
    # Update
    # -----------------------------------------------------------------
    def update(self):
        if self.message_timer > 0:
            self.message_timer -= 1

        if self.state != Game.STATE_PLAYING:
            return

        keys = pygame.key.get_pressed()
        mouse_pos = pygame.mouse.get_pos()
        mouse_buttons = pygame.mouse.get_pressed()

        self.player.handle_input(keys, self.walls)
        self.player.update_aim(mouse_pos)

        if mouse_buttons[0]:
            self.player.try_shoot(self.bullets)

        if self.spawn_queue:
            self.spawn_timer += 1
            if self.spawn_timer >= self.spawn_interval:
                self.spawn_timer = 0
                next_type = self.spawn_queue.pop(0)
                if next_type == "boss":
                    self.zombies.append(spawn_boss(self.level))
                elif next_type == "spitter":
                    self.zombies.append(spawn_spitter(self.level))
                else:
                    self.zombies.append(spawn_zombie(self.level))
        elif not self.zombies:
            self.enter_shop()
            return

        for bullet in self.bullets:
            bullet.update(self.walls)
        self.bullets = [b for b in self.bullets if b.alive]

        for zombie in self.zombies:
            if isinstance(zombie, Spitter):
                projectile = zombie.update(self.player.pos, self.player.velocity, self.walls, self.cover_points)
                if projectile is not None:
                    self.enemy_projectiles.append(projectile)
            else:
                zombie.update(self.player.pos, self.walls)

            if distance(zombie.pos, self.player.pos) < zombie.radius + self.player.radius:
                if zombie.attack_cooldown <= 0:
                    self.player.take_damage(zombie.damage)
                    zombie.attack_cooldown = 45

        for projectile in self.enemy_projectiles:
            projectile.update(self.walls)
            if projectile.alive and distance(projectile.pos, self.player.pos) < projectile.radius + self.player.radius:
                self.player.take_damage(projectile.damage)
                projectile.alive = False
        self.enemy_projectiles = [p for p in self.enemy_projectiles if p.alive]

        def award_kill(zombie):
            self.score += zombie.score_value
            self.money += int(zombie.reward * self.player.money_multiplier)
            if self.player.lifesteal_per_kill > 0:
                self.player.health = clamp(
                    self.player.health + self.player.lifesteal_per_kill, 0, self.player.max_health
                )

        for bullet in self.bullets:
            for zombie in self.zombies:
                if zombie.alive and distance(bullet.pos, zombie.pos) < zombie.radius + bullet.radius:
                    zombie.take_damage(bullet.damage)
                    bullet.alive = False
                    if not zombie.alive:
                        award_kill(zombie)
                    break
        self.bullets = [b for b in self.bullets if b.alive]

        for grenade in self.grenades:
            grenade.update(self.walls)
            if grenade.exploded and not grenade.damage_applied:
                for zombie in self.zombies:
                    if zombie.alive and distance(grenade.pos, zombie.pos) <= grenade.radius:
                        zombie.take_damage(grenade.damage)
                        if not zombie.alive:
                            award_kill(zombie)
                grenade.damage_applied = True
        self.grenades = [g for g in self.grenades if g.alive]

        self.zombies = [z for z in self.zombies if z.alive]

        if self.player.health <= 0:
            self.enter_game_over()

    # -----------------------------------------------------------------
    # Shop options
    # -----------------------------------------------------------------
    def build_shop_options(self):
        weapons = self.player.weapons
        options = []

        def make_upgrade_option(key_const, key_name, weapon_key):
            weapon = weapons[weapon_key]

            def label():
                if not weapon.unlocked:
                    return f"[{key_name}] Unlock {weapon.name}"
                if weapon.level >= weapon.max_level:
                    return f"[{key_name}] {weapon.name} (MAX LEVEL)"
                return f"[{key_name}] Upgrade {weapon.name} (Lv {weapon.level} -> {weapon.level + 1})"

            def cost():
                if not weapon.unlocked:
                    return weapon.unlock_cost
                return weapon.upgrade_cost()

            def enabled():
                c = cost()
                return c is not None and self.money >= c

            def action():
                c = cost()
                if c is None or self.money < c:
                    return
                self.money -= c
                if not weapon.unlocked:
                    weapon.unlocked = True
                    weapon.level = 1
                    self.player.ensure_ammo_initialized(weapon_key)
                else:
                    weapon.level += 1

            return ShopOption(key_const, label, cost, action, enabled)

        options.append(make_upgrade_option(pygame.K_1, "1", "pistol"))
        options.append(make_upgrade_option(pygame.K_2, "2", "shotgun"))
        options.append(make_upgrade_option(pygame.K_3, "3", "rifle"))

        def health_label():
            return f"[4] Increase Max Health (+20)  (currently {self.player.max_health})"

        def health_cost():
            return int(35 * (1.4 ** ((self.player.max_health - 100) / 20)))

        def health_enabled():
            return self.money >= health_cost()

        def health_action():
            c = health_cost()
            if self.money < c:
                return
            self.money -= c
            self.player.max_health += 20
            self.player.health = self.player.max_health

        options.append(ShopOption(pygame.K_4, health_label, health_cost, health_action, health_enabled))

        def heal_label():
            return "[5] Full Heal"

        def heal_cost():
            return 25

        def heal_enabled():
            return self.money >= heal_cost() and self.player.health < self.player.max_health

        def heal_action():
            c = heal_cost()
            if self.money < c or self.player.health >= self.player.max_health:
                return
            self.money -= c
            self.player.health = self.player.max_health

        options.append(ShopOption(pygame.K_5, heal_label, heal_cost, heal_action, heal_enabled))

        return options

    def handle_shop_key(self, key):
        if key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self.begin_level(self.level + 1)
            return

        perk_keys = {pygame.K_6: 0, pygame.K_7: 1, pygame.K_8: 2}
        if key in perk_keys and not self.perk_chosen_this_level:
            idx = perk_keys[key]
            if idx < len(self.perk_choices):
                name, desc, apply_fn = self.perk_choices[idx]
                apply_fn(self.player)
                self.player.perks_taken.append(name)
                self.perk_chosen_this_level = True
            return

        for option in self.build_shop_options():
            if option.key == key and option.enabled_fn():
                option.action_fn()
                return

    # -----------------------------------------------------------------
    # Drawing
    # -----------------------------------------------------------------
    def draw(self, surface):
        surface.fill(BG_COLOR)

        for x in range(0, SCREEN_WIDTH, 40):
            pygame.draw.line(surface, (45, 50, 45), (x, 0), (x, SCREEN_HEIGHT))
        for y in range(0, SCREEN_HEIGHT, 40):
            pygame.draw.line(surface, (45, 50, 45), (0, y), (SCREEN_WIDTH, y))

        for wall in self.walls:
            wall.draw(surface)

        for zombie in self.zombies:
            zombie.draw(surface)
        for bullet in self.bullets:
            bullet.draw(surface)
        for projectile in self.enemy_projectiles:
            projectile.draw(surface)
        for grenade in self.grenades:
            grenade.draw(surface)
        self.player.draw(surface)

        self.draw_hud(surface)

        if self.message_timer > 0 and self.state == Game.STATE_PLAYING:
            self.draw_flash_message(surface)

        if self.state == Game.STATE_SHOP:
            self.draw_shop(surface)
        elif self.state == Game.STATE_GAME_OVER:
            self.draw_game_over(surface)

    def draw_flash_message(self, surface):
        text = font_large.render(self.flash_message, True, GOLD)
        alpha = clamp(self.message_timer / 100 * 255, 0, 255)
        text.set_alpha(int(alpha))
        surface.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, 120))

    def draw_hud(self, surface):
        bar_width, bar_height = 220, 22
        x, y = 20, 20
        health_ratio = clamp(self.player.health / self.player.max_health, 0, 1)
        pygame.draw.rect(surface, GRAY, (x, y, bar_width, bar_height), border_radius=4)
        pygame.draw.rect(surface, GREEN, (x, y, bar_width * health_ratio, bar_height), border_radius=4)
        pygame.draw.rect(surface, WHITE, (x, y, bar_width, bar_height), 2, border_radius=4)
        health_text = font_small.render(f"HP: {int(self.player.health)}/{self.player.max_health}", True, WHITE)
        surface.blit(health_text, (x + 8, y + 2))

        money_text = font_medium.render(f"$ {self.money}", True, GOLD)
        surface.blit(money_text, (20, 50))

        score_text = font_medium.render(f"Score: {self.score}", True, WHITE)
        level_text = font_medium.render(f"Level: {self.level}", True, YELLOW)
        surface.blit(score_text, (SCREEN_WIDTH - score_text.get_width() - 20, 15))
        surface.blit(level_text, (SCREEN_WIDTH - level_text.get_width() - 20, 50))

        weapon = self.player.current_weapon
        weapon_text = font_small.render(
            f"Weapon: {weapon.name} (Lv {weapon.level})   [1/2/3 to switch]", True, weapon.color
        )
        surface.blit(weapon_text, (20, SCREEN_HEIGHT - 116))

        ammo = self.player.ammo[self.player.current_weapon_key]
        if self.player.reloading:
            ammo_str = "RELOADING..."
            ammo_color = RED
            progress = 1 - (self.player.reload_timer / max(1, int(weapon.reload_frames * self.player.reload_multiplier)))
            bar_w = 160
            pygame.draw.rect(surface, GRAY, (20, SCREEN_HEIGHT - 92, bar_w, 10))
            pygame.draw.rect(surface, GOLD, (20, SCREEN_HEIGHT - 92, bar_w * clamp(progress, 0, 1), 10))
        else:
            ammo_str = f"Ammo: {ammo}/{weapon.magazine_size}   [R to reload]"
            ammo_color = WHITE if ammo > 0 else RED
        ammo_text = font_small.render(ammo_str, True, ammo_color)
        surface.blit(ammo_text, (20, SCREEN_HEIGHT - 90))

        # Dash indicator
        dash_ready = self.player.dash_timer <= 0 and not self.player.dashing
        dash_color = DASH_GREEN if dash_ready else GRAY
        dash_str = "[SPACE] Dash: READY" if dash_ready else f"[SPACE] Dash: {self.player.dash_timer / FPS:.1f}s"
        dash_text = font_small.render(dash_str, True, dash_color)
        surface.blit(dash_text, (20, SCREEN_HEIGHT - 60))

        # Grenade indicator
        grenade_ready = self.player.grenade_timer <= 0
        grenade_color = GRENADE_COLOR if not grenade_ready else (170, 210, 120)
        grenade_str = "[G] Grenade: READY" if grenade_ready else f"[G] Grenade: {self.player.grenade_timer / FPS:.1f}s"
        grenade_text = font_small.render(grenade_str, True, grenade_color)
        surface.blit(grenade_text, (20, SCREEN_HEIGHT - 32))

        enemies_left = len(self.zombies) + len(self.spawn_queue)
        eleft_text = font_small.render(f"Enemies remaining: {enemies_left}", True, WHITE)
        surface.blit(eleft_text, (SCREEN_WIDTH - 240, SCREEN_HEIGHT - 32))

    def draw_shop(self, surface):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        surface.blit(overlay, (0, 0))

        title = font_huge.render(f"LEVEL {self.level} CLEARED!", True, GOLD)
        surface.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 25))

        money_text = font_medium.render(f"Money: $ {self.money}", True, GOLD)
        surface.blit(money_text, (SCREEN_WIDTH // 2 - money_text.get_width() // 2, 100))

        subtitle = font_small.render("WEAPON SHOP", True, LIGHT_GRAY)
        surface.blit(subtitle, (SCREEN_WIDTH // 2 - 260, 140))

        options = self.build_shop_options()
        start_y = 168
        gap = 34
        for i, option in enumerate(options):
            label = option.label_fn()
            cost = option.cost_fn()
            enabled = option.enabled_fn()

            color = WHITE if enabled else GRAY
            line = label
            if cost is not None:
                line += f"   -  $ {cost}"
            else:
                line += "   -  MAXED"

            text = font_small.render(line, True, color)
            surface.blit(text, (SCREEN_WIDTH // 2 - 260, start_y + i * gap))

        perk_section_y = start_y + len(options) * gap + 24
        perk_subtitle = font_small.render("CHOOSE ONE PERK (free)", True, PERK_COLOR)
        surface.blit(perk_subtitle, (SCREEN_WIDTH // 2 - 260, perk_section_y))

        if self.perk_chosen_this_level:
            chosen_name = self.player.perks_taken[-1] if self.player.perks_taken else "?"
            chosen_text = font_small.render(f"Perk chosen: {chosen_name}", True, GOLD)
            surface.blit(chosen_text, (SCREEN_WIDTH // 2 - 260, perk_section_y + 30))
        else:
            perk_keys_labels = ["6", "7", "8"]
            for i, (name, desc, _fn) in enumerate(self.perk_choices):
                line = f"[{perk_keys_labels[i]}] {name} - {desc}"
                text = font_small.render(line, True, PERK_COLOR)
                surface.blit(text, (SCREEN_WIDTH // 2 - 260, perk_section_y + 28 + i * 30))

        prompt = font_medium.render("Press ENTER to start next level", True, GREEN)
        surface.blit(
            prompt,
            (SCREEN_WIDTH // 2 - prompt.get_width() // 2, perk_section_y + 28 + 3 * 30 + 20),
        )

    def draw_game_over(self, surface):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 190))
        surface.blit(overlay, (0, 0))

        game_over_text = font_huge.render("GAME OVER", True, RED)
        surface.blit(
            game_over_text,
            (SCREEN_WIDTH // 2 - game_over_text.get_width() // 2, 50),
        )

        if self.is_new_record:
            record_text = font_medium.render("NEW HIGH SCORE!", True, GOLD)
            surface.blit(record_text, (SCREEN_WIDTH // 2 - record_text.get_width() // 2, 130))

        score_text = font_medium.render(f"Final Score: {self.score}    Reached Level: {self.level}", True, WHITE)
        surface.blit(score_text, (SCREEN_WIDTH // 2 - score_text.get_width() // 2, 172))

        header = font_small.render("TOP SCORES", True, YELLOW)
        surface.blit(header, (SCREEN_WIDTH // 2 - header.get_width() // 2, 215))

        for i, entry in enumerate(self.high_scores):
            line = f"{i + 1}. Score {entry['score']}  -  Level {entry['level']}"
            color = GOLD if (self.is_new_record and entry["score"] == self.score and entry["level"] == self.level) else WHITE
            text = font_small.render(line, True, color)
            surface.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, 248 + i * 26))

        perks_y = 248 + len(self.high_scores) * 26 + 16
        if self.player.perks_taken:
            perks_header = font_small.render("Perks taken:", True, PERK_COLOR)
            surface.blit(perks_header, (SCREEN_WIDTH // 2 - perks_header.get_width() // 2, perks_y))
            perks_line = ", ".join(self.player.perks_taken)
            perks_text = font_tiny.render(perks_line, True, LIGHT_GRAY)
            surface.blit(perks_text, (SCREEN_WIDTH // 2 - perks_text.get_width() // 2, perks_y + 24))
            perks_y += 48

        restart_text = font_small.render("Press R to Restart or ESC to Quit", True, YELLOW)
        surface.blit(
            restart_text,
            (SCREEN_WIDTH // 2 - restart_text.get_width() // 2, perks_y + 16),
        )


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
def main():
    game = Game()
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_r and game.state == Game.STATE_GAME_OVER:
                    game.reset()
                elif game.state == Game.STATE_SHOP:
                    game.handle_shop_key(event.key)
                elif game.state == Game.STATE_PLAYING:
                    if event.key == pygame.K_1:
                        game.player.switch_weapon("pistol")
                    elif event.key == pygame.K_2:
                        game.player.switch_weapon("shotgun")
                    elif event.key == pygame.K_3:
                        game.player.switch_weapon("rifle")
                    elif event.key == pygame.K_r:
                        game.player.start_reload()
                    elif event.key == pygame.K_SPACE:
                        game.player.start_dash()
                    elif event.key == pygame.K_g:
                        game.player.try_throw_grenade(pygame.mouse.get_pos(), game.grenades)

        game.update()
        game.draw(screen)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
    