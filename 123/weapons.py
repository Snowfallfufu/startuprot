"""
Weapon definitions: stats scale with upgrade level; magazine/reload data
feeds the ammo system in player.py.
"""

from settings import YELLOW, SNIPER_COLOR


class Weapon:
    def __init__(self, name, unlocked, unlock_cost, base_damage, damage_per_level,
                 base_cooldown, cooldown_per_level, min_cooldown,
                 bullet_speed, pellets, spread_degrees, color, upgrade_base_cost,
                 magazine_size, reload_frames, pierce=0):
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
        self.pierce = pierce

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
        "sniper": Weapon(
            name="Sniper", unlocked=False, unlock_cost=300,
            base_damage=90, damage_per_level=25,
            base_cooldown=55, cooldown_per_level=4, min_cooldown=35,
            bullet_speed=22, pellets=1, spread_degrees=0,
            color=SNIPER_COLOR, upgrade_base_cost=110,
            magazine_size=5, reload_frames=110,
            pierce=2,
        ),
    }
