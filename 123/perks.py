"""
Perks: permanent per-run bonuses the player picks one of after every level.
Each apply_fn takes the Player instance and mutates it directly.
"""


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


def _perk_piercing_rounds(p):
    p.bonus_pierce += 1


def _perk_steady_aim(p):
    p.bullet_speed_multiplier *= 1.1


def _perk_bulk_ammo(p):
    p.magazine_bonus += 3


# Each entry: (display name, description, apply_fn)
PERKS_POOL = [
    ("Adrenaline Rush", "+15% move speed", _perk_adrenaline),
    ("Quick Hands", "-20% reload time", _perk_quick_hands),
    ("Sharpshooter", "+15% weapon damage", _perk_sharpshooter),
    ("Iron Skin", "-10% damage taken", _perk_iron_skin),
    ("Vampiric Bite", "Heal 2 HP per kill", _perk_vampiric),
    ("Scavenger", "+25% money from kills", _perk_scavenger),
    ("Grenadier", "-25% grenade cooldown", _perk_grenadier),
    ("Dash Master", "-25% dash cooldown", _perk_dash_master),
    ("Piercing Rounds", "+1 bullet pierce, all weapons", _perk_piercing_rounds),
    ("Steady Aim", "+10% bullet speed", _perk_steady_aim),
    ("Bulk Ammo", "+3 magazine capacity, all weapons", _perk_bulk_ammo),
]
