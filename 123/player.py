"""
Player: movement/collision, aiming, shooting, ammo & reload, dash,
grenade throwing, and all perk-affected stat multipliers.
"""

import math
import pygame

from settings import SCREEN_WIDTH, SCREEN_HEIGHT, GREEN, DASH_GREEN, DARK_GREEN
from utils import clamp, move_with_collision
from weapons import make_default_weapons
from projectiles import Bullet, Grenade


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
        self.weapon_order = ["pistol", "shotgun", "rifle", "sniper"]
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
        self.bonus_pierce = 0
        self.bullet_speed_multiplier = 1.0
        self.magazine_bonus = 0
        self.perks_taken = []

    @property
    def current_weapon(self):
        return self.weapons[self.current_weapon_key]

    def effective_magazine(self, weapon):
        return weapon.magazine_size + self.magazine_bonus

    def ensure_ammo_initialized(self, weapon_key):
        weapon = self.weapons[weapon_key]
        if weapon_key not in self.ammo or self.ammo[weapon_key] == 0:
            self.ammo[weapon_key] = self.effective_magazine(weapon)

    def switch_weapon(self, key):
        if key in self.weapons and self.weapons[key].unlocked:
            self.current_weapon_key = key
            self.shoot_cooldown = max(self.shoot_cooldown, 5)

    def start_reload(self):
        weapon = self.current_weapon
        if self.reloading:
            return
        if self.ammo[self.current_weapon_key] >= self.effective_magazine(weapon):
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

    def handle_input(self, keys, obstacles):
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
            move_with_collision(self.pos, step, self.radius, obstacles)
            self.dash_frames_left -= 1
            if self.dash_frames_left <= 0:
                self.dashing = False
                self.invulnerable = False
        elif move.length_squared() > 0:
            scaled = move.normalize() * self.speed
            move_with_collision(self.pos, scaled, self.radius, obstacles)

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
                self.ammo[self.reload_weapon_key] = self.effective_magazine(self.weapons[self.reload_weapon_key])
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
        effective_speed = weapon.bullet_speed * self.bullet_speed_multiplier
        effective_pierce = weapon.pierce + self.bonus_pierce
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
                                   effective_speed, weapon.color, pierce=effective_pierce))

    def take_damage(self, amount):
        if self.invulnerable:
            return
        amount = amount * (1 - self.damage_reduction)
        self.health -= amount
        self.health = clamp(self.health, 0, self.max_health)

    def heal(self, amount):
        self.health = clamp(self.health + amount, 0, self.max_health)

    def refill_all_ammo(self):
        for key, weapon in self.weapons.items():
            if weapon.unlocked:
                self.ammo[key] = self.effective_magazine(weapon)
        if self.reloading:
            self.reloading = False
            self.reload_timer = 0

    def draw(self, surface):
        color = DASH_GREEN if self.dashing else GREEN
        pygame.draw.circle(surface, color, (int(self.pos.x), int(self.pos.y)), self.radius)
        pygame.draw.circle(surface, DARK_GREEN, (int(self.pos.x), int(self.pos.y)), self.radius, 3)
        end_x = self.pos.x + math.cos(self.angle) * (self.radius + 16)
        end_y = self.pos.y + math.sin(self.angle) * (self.radius + 16)
        pygame.draw.line(surface, self.current_weapon.color, self.pos, (end_x, end_y), 4)
