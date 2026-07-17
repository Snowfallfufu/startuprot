"""
Shared constants, colors, and fonts used across every module.
pygame.init() lives here so any module can safely create fonts at
import time, regardless of import order.
"""

import pygame

pygame.init()

SCREEN_WIDTH, SCREEN_HEIGHT = 960, 640
FPS = 60

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
BARREL_COLOR = (185, 65, 40)
BARREL_DARK = (95, 25, 15)
BARREL_WARN = (255, 210, 60)
HEALTH_PICKUP = (220, 60, 60)
AMMO_PICKUP = (230, 200, 60)
SNIPER_COLOR = (210, 210, 235)
BG_COLOR = (35, 40, 35)
WALL_COLOR = (95, 92, 88)
WALL_BORDER = (55, 52, 48)
PERK_COLOR = (120, 200, 255)

font_huge = pygame.font.SysFont("arial", 72, bold=True)
font_large = pygame.font.SysFont("arial", 48, bold=True)
font_medium = pygame.font.SysFont("arial", 30, bold=True)
font_small = pygame.font.SysFont("arial", 21)
font_tiny = pygame.font.SysFont("arial", 17)
