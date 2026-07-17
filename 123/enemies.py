"""
Enemy types:
  - Zombie: base melee chaser that steers around obstacles.
  - Boss: adds ground-pound AoE, a charge attack, enrage, and summons.
  - Spitter: ranged unit that uses line-of-sight, leads shots based on
    player velocity, and retreats to real cover after firing.
"""

import math
import random
import pygame

from settings import (
    RED, DARK_RED, GRAY, WHITE, PURPLE, DARK_PURPLE,
    SPITTER_COLOR, SPITTER_DARK, font_small,
)
from utils import clamp, distance, steer_toward, move_with_collision, line_of_sight, pick_cover_point, is_boss_level
from projectiles import Spit


# ---------------------------------------------------------------------------
# Base Zombie
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

    def update(self, player_pos, obstacles):
        step = steer_toward(self.pos, player_pos, self.speed, self.radius, obstacles)
        if step.length_squared() > 0:
            move_with_collision(self.pos, step, self.radius, obstacles)
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


# ---------------------------------------------------------------------------
# Boss
# ---------------------------------------------------------------------------
class Boss(Zombie):
    """
    A boss with three mechanics layered on top of normal chasing:
      - Ground Pound: telegraphs, then deals AoE damage in a radius -
        punishes staying in melee range.
      - Charge: telegraphs, then dashes at high speed toward where the
        player was standing, dealing bonus contact damage.
      - Enrage: below 30% health, moves faster and acts more often.
      - Reinforcements: summons zombies at 75% / 50% / 25% health.
    """

    def __init__(self, pos, speed, health, reward):
        super().__init__(pos, speed, health, reward)
        self.radius = 34
        self.base_contact_damage = 25
        self.damage = self.base_contact_damage
        self.is_boss = True
        self.score_value = 25

        self.ability_cooldown = 240
        self.ability_timer = self.ability_cooldown
        self.state = "chase"  # chase, telegraph_pound, pound_active, telegraph_charge, charging
        self.telegraph_timer = 0
        self.action_duration = 0

        self.pound_radius = 150
        self.pound_damage = 28
        self.pound_hit_applied = False

        self.charge_damage = 38
        self.charge_speed = speed * 4.5
        self.charge_dir = pygame.Vector2(1, 0)
        self.charge_target = None

        self.summon_thresholds = [0.75, 0.5, 0.25]
        self.summoned_flags = set()
        self.pending_summon_count = 0

        self.enraged = False

    def update(self, player_pos, obstacles):
        ratio = self.health / self.max_health

        if not self.enraged and ratio <= 0.3:
            self.enraged = True
            self.speed *= 1.3
            self.ability_cooldown = max(90, int(self.ability_cooldown * 0.65))

        for t in self.summon_thresholds:
            if ratio <= t and t not in self.summoned_flags:
                self.summoned_flags.add(t)
                self.pending_summon_count += 2

        if self.state == "chase":
            step = steer_toward(self.pos, player_pos, self.speed, self.radius, obstacles)
            if step.length_squared() > 0:
                move_with_collision(self.pos, step, self.radius, obstacles)
            self.ability_timer -= 1
            if self.ability_timer <= 0:
                ability = random.choice(["pound", "charge"])
                if ability == "pound":
                    self.state = "telegraph_pound"
                    self.telegraph_timer = 45
                else:
                    self.state = "telegraph_charge"
                    self.telegraph_timer = 35
                    self.charge_target = pygame.Vector2(player_pos)
        elif self.state == "telegraph_pound":
            self.telegraph_timer -= 1
            if self.telegraph_timer <= 0:
                self.state = "pound_active"
                self.action_duration = 8
                self.pound_hit_applied = False
        elif self.state == "pound_active":
            self.action_duration -= 1
            if self.action_duration <= 0:
                self.state = "chase"
                self.ability_timer = self.ability_cooldown
        elif self.state == "telegraph_charge":
            self.telegraph_timer -= 1
            if self.telegraph_timer <= 0:
                self.state = "charging"
                self.action_duration = 16
                direction = self.charge_target - self.pos
                self.charge_dir = direction.normalize() if direction.length_squared() > 0 else pygame.Vector2(1, 0)
                self.damage = self.charge_damage
        elif self.state == "charging":
            move_with_collision(self.pos, self.charge_dir * self.charge_speed, self.radius, obstacles)
            self.action_duration -= 1
            if self.action_duration <= 0:
                self.state = "chase"
                self.ability_timer = self.ability_cooldown
                self.damage = self.base_contact_damage

        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1

    def draw(self, surface):
        color = (225, 70, 170) if self.enraged else PURPLE
        pygame.draw.circle(surface, color, (int(self.pos.x), int(self.pos.y)), self.radius)
        pygame.draw.circle(surface, DARK_PURPLE, (int(self.pos.x), int(self.pos.y)), self.radius, 4)

        if self.state == "telegraph_pound":
            progress = 1 - (self.telegraph_timer / 45)
            r = max(4, int(self.pound_radius * progress))
            pygame.draw.circle(surface, RED, (int(self.pos.x), int(self.pos.y)), r, 3)
        elif self.state == "telegraph_charge" and (self.telegraph_timer // 4) % 2 == 0:
            pygame.draw.circle(surface, RED, (int(self.pos.x), int(self.pos.y)), self.radius + 8, 3)
        elif self.state == "charging":
            tail = self.pos - self.charge_dir * 40
            pygame.draw.line(surface, (255, 230, 255), tail, self.pos, 6)

        label_str = "BOSS (ENRAGED)" if self.enraged else "BOSS"
        label = font_small.render(label_str, True, WHITE)
        surface.blit(label, (self.pos.x - label.get_width() // 2, self.pos.y - self.radius - 32))

        bar_width = 70
        health_ratio = clamp(self.health / self.max_health, 0, 1)
        bar_x = self.pos.x - bar_width // 2
        bar_y = self.pos.y - self.radius - 14
        pygame.draw.rect(surface, GRAY, (bar_x, bar_y, bar_width, 8))
        pygame.draw.rect(surface, PURPLE, (bar_x, bar_y, bar_width * health_ratio, 8))
        pygame.draw.rect(surface, WHITE, (bar_x, bar_y, bar_width, 8), 1)


# ---------------------------------------------------------------------------
# Spitter (tactical ranged enemy)
# ---------------------------------------------------------------------------
class Spitter(Zombie):
    def __init__(self, pos, speed, health, reward):
        super().__init__(pos, speed, health, reward)
        self.radius = 15
        self.damage = 8  # weak fallback melee if the player closes to point-blank
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

    def update(self, player_pos, player_velocity, obstacles, cover_points):
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1

        los = line_of_sight(self.pos, player_pos, obstacles)
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
                    self.cover_target = pick_cover_point(self.pos, player_pos, cover_points, obstacles)
            return fired_projectile

        if self.retreat_timer > 0:
            self.retreat_timer -= 1
            target = self.cover_target
            if target is None:
                self.cover_target = pick_cover_point(self.pos, player_pos, cover_points, obstacles)
            elif distance(self.pos, target) > 8:
                step = steer_toward(self.pos, target, self.speed, self.radius, obstacles)
                if step.length_squared() > 0:
                    move_with_collision(self.pos, step, self.radius, obstacles)
            return fired_projectile

        if dist_to_player < self.min_range:
            away = pygame.Vector2(self.pos) - pygame.Vector2(player_pos)
            if away.length_squared() > 0:
                away = away.normalize()
            target_point = pygame.Vector2(self.pos) + away * 100
            step = steer_toward(self.pos, target_point, self.speed, self.radius, obstacles)
            if step.length_squared() > 0:
                move_with_collision(self.pos, step, self.radius, obstacles)
        elif los and self.min_range <= dist_to_player <= self.attack_range and self.attack_cooldown <= 0:
            self.aiming = True
            self.aim_timer = self.aim_time
        else:
            step = steer_toward(self.pos, player_pos, self.speed, self.radius, obstacles)
            if step.length_squared() > 0:
                move_with_collision(self.pos, step, self.radius, obstacles)

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


# ---------------------------------------------------------------------------
# Spawning
# ---------------------------------------------------------------------------
def random_edge_position():
    from settings import SCREEN_WIDTH, SCREEN_HEIGHT
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
