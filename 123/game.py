"""
Game: level flow, the weapon/perk shop, the main update loop (spawning,
collisions, AoE/chain reactions), and all HUD/screen drawing.
"""

import random
import pygame

from settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS,
    WHITE, GREEN, RED, YELLOW, GOLD, GRAY, LIGHT_GRAY, PERK_COLOR, GRENADE_COLOR, DASH_GREEN,
    font_huge, font_large, font_medium, font_small, font_tiny,
)
from utils import clamp, distance, compute_cover_points, is_boss_level
from walls import get_wall_layout
from barrels import generate_barrels
from pickups import Pickup, Explosion
from highscores import load_high_scores, update_high_scores
from perks import PERKS_POOL
from player import Player
from enemies import Zombie, Boss, Spitter, spawn_zombie, spawn_boss, spawn_spitter


class ShopOption:
    def __init__(self, key, label_fn, cost_fn, action_fn, enabled_fn):
        self.key = key
        self.label_fn = label_fn
        self.cost_fn = cost_fn
        self.action_fn = action_fn
        self.enabled_fn = enabled_fn


class Game:
    STATE_PLAYING = "playing"
    STATE_SHOP = "shop"
    STATE_GAME_OVER = "game_over"

    def __init__(self):
        self.high_scores = load_high_scores()
        self.walls = []
        self.reset()

    def reset(self):
        self.player = Player()
        self.bullets = []
        self.zombies = []
        self.enemy_projectiles = []
        self.grenades = []
        self.barrels = []
        self.pickups = []
        self.explosions = []
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

        # Every layout keeps the exact center of the screen clear, so
        # recenter the player here to avoid ever spawning inside a wall.
        self.player.pos = pygame.Vector2(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        self.player.velocity = pygame.Vector2(0, 0)

        self.spawn_interval = max(18, 58 - level_number * 2)
        self.spawn_timer = 0
        self.bullets = []
        self.zombies = []
        self.enemy_projectiles = []
        self.grenades = []
        self.pickups = []
        self.explosions = []
        self.barrels = generate_barrels(self.walls, count=min(3 + level_number // 4, 6))

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

        # Obstacles = static walls + any barrels still standing.
        obstacles = self.walls + [b for b in self.barrels if b.alive]
        cover_points = compute_cover_points(obstacles)

        keys = pygame.key.get_pressed()
        mouse_pos = pygame.mouse.get_pos()
        mouse_buttons = pygame.mouse.get_pressed()

        self.player.handle_input(keys, obstacles)
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

        # Bullets only collide with static walls here; barrel hits are
        # handled explicitly below so damage can actually be applied.
        for bullet in self.bullets:
            bullet.update(self.walls)
        self.bullets = [b for b in self.bullets if b.alive]

        newly_spawned_zombies = []
        for zombie in self.zombies:
            if isinstance(zombie, Spitter):
                projectile = zombie.update(self.player.pos, self.player.velocity, obstacles, cover_points)
                if projectile is not None:
                    self.enemy_projectiles.append(projectile)
            else:
                zombie.update(self.player.pos, obstacles)
                if isinstance(zombie, Boss):
                    if zombie.state == "pound_active" and not zombie.pound_hit_applied:
                        if distance(zombie.pos, self.player.pos) <= zombie.pound_radius:
                            self.player.take_damage(zombie.pound_damage)
                        zombie.pound_hit_applied = True
                        self.explosions.append(Explosion(zombie.pos, zombie.pound_radius))
                    if zombie.pending_summon_count > 0:
                        for _ in range(zombie.pending_summon_count):
                            minion = spawn_zombie(self.level)
                            offset = pygame.Vector2(random.uniform(-70, 70), random.uniform(-70, 70))
                            minion.pos = pygame.Vector2(zombie.pos) + offset
                            newly_spawned_zombies.append(minion)
                        zombie.pending_summon_count = 0

            if distance(zombie.pos, self.player.pos) < zombie.radius + self.player.radius:
                if zombie.attack_cooldown <= 0:
                    self.player.take_damage(zombie.damage)
                    zombie.attack_cooldown = 45
        self.zombies.extend(newly_spawned_zombies)

        for projectile in self.enemy_projectiles:
            projectile.update(obstacles)
            if projectile.alive and distance(projectile.pos, self.player.pos) < projectile.radius + self.player.radius:
                self.player.take_damage(projectile.damage)
                projectile.alive = False
        self.enemy_projectiles = [p for p in self.enemy_projectiles if p.alive]

        def award_kill(zombie):
            self.score += zombie.score_value
            self.money += int(zombie.reward * self.player.money_multiplier)
            if self.player.lifesteal_per_kill > 0:
                self.player.heal(self.player.lifesteal_per_kill)
            if random.random() < 0.12:
                kind = random.choice(["health", "ammo"])
                self.pickups.append(Pickup(zombie.pos, kind))

        # Bullets vs barrels (checked first) then bullets vs zombies (with piercing).
        for bullet in self.bullets:
            if not bullet.alive:
                continue
            hit_barrel = False
            for barrel in self.barrels:
                if barrel.alive and distance(bullet.pos, barrel.pos) < barrel.radius + bullet.radius:
                    barrel.take_damage(bullet.damage)
                    bullet.alive = False
                    hit_barrel = True
                    break
            if hit_barrel:
                continue
            for zombie in self.zombies:
                if zombie.alive and distance(bullet.pos, zombie.pos) < zombie.radius + bullet.radius:
                    zombie.take_damage(bullet.damage)
                    if not zombie.alive:
                        award_kill(zombie)
                    if bullet.pierce > 0:
                        bullet.pierce -= 1
                    else:
                        bullet.alive = False
                        break
        self.bullets = [b for b in self.bullets if b.alive]

        # Grenades: AoE damage to zombies and barrels on detonation.
        for grenade in self.grenades:
            grenade.update()
            if grenade.exploded and not grenade.damage_applied:
                for zombie in self.zombies:
                    if zombie.alive and distance(grenade.pos, zombie.pos) <= grenade.radius:
                        zombie.take_damage(grenade.damage)
                        if not zombie.alive:
                            award_kill(zombie)
                for barrel in self.barrels:
                    if barrel.alive and distance(grenade.pos, barrel.pos) <= grenade.radius:
                        barrel.take_damage(grenade.damage)
                grenade.damage_applied = True
        self.grenades = [g for g in self.grenades if g.alive]

        # Barrels: handle newly-triggered explosions (damage + chain reaction).
        for barrel in self.barrels:
            if barrel.exploded and not barrel.explosion_handled:
                barrel.explosion_handled = True
                self.explosions.append(Explosion(barrel.pos, barrel.blast_radius))
                for zombie in self.zombies:
                    if zombie.alive and distance(barrel.pos, zombie.pos) <= barrel.blast_radius:
                        zombie.take_damage(barrel.blast_damage)
                        if not zombie.alive:
                            award_kill(zombie)
                if distance(barrel.pos, self.player.pos) <= barrel.blast_radius:
                    self.player.take_damage(45)
                for other in self.barrels:
                    if other is not barrel and other.alive and distance(barrel.pos, other.pos) <= barrel.blast_radius:
                        other.take_damage(999)
        self.barrels = [b for b in self.barrels if b.alive]

        for explosion in self.explosions:
            explosion.update()
        self.explosions = [e for e in self.explosions if e.alive]

        for pickup in self.pickups:
            pickup.update()
            if pickup.alive and distance(pickup.pos, self.player.pos) < pickup.radius + self.player.radius:
                if pickup.kind == "health":
                    self.player.heal(30)
                else:
                    self.player.refill_all_ammo()
                pickup.alive = False
        self.pickups = [p for p in self.pickups if p.alive]

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
        options.append(make_upgrade_option(pygame.K_4, "4", "sniper"))

        def health_label():
            return f"[5] Increase Max Health (+20)  (currently {self.player.max_health})"

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

        options.append(ShopOption(pygame.K_5, health_label, health_cost, health_action, health_enabled))

        def heal_label():
            return "[6] Full Heal"

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

        options.append(ShopOption(pygame.K_6, heal_label, heal_cost, heal_action, heal_enabled))

        return options

    def handle_shop_key(self, key):
        if key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self.begin_level(self.level + 1)
            return

        perk_keys = {pygame.K_7: 0, pygame.K_8: 1, pygame.K_9: 2}
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
        from settings import BG_COLOR

        surface.fill(BG_COLOR)

        for x in range(0, SCREEN_WIDTH, 40):
            pygame.draw.line(surface, (45, 50, 45), (x, 0), (x, SCREEN_HEIGHT))
        for y in range(0, SCREEN_HEIGHT, 40):
            pygame.draw.line(surface, (45, 50, 45), (0, y), (SCREEN_WIDTH, y))

        for wall in self.walls:
            wall.draw(surface)
        for barrel in self.barrels:
            barrel.draw(surface)
        for pickup in self.pickups:
            pickup.draw(surface)

        for zombie in self.zombies:
            zombie.draw(surface)
        for bullet in self.bullets:
            bullet.draw(surface)
        for projectile in self.enemy_projectiles:
            projectile.draw(surface)
        for grenade in self.grenades:
            grenade.draw(surface)
        self.player.draw(surface)

        for explosion in self.explosions:
            explosion.draw(surface)

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
            f"Weapon: {weapon.name} (Lv {weapon.level})   [1/2/3/4 to switch]", True, weapon.color
        )
        surface.blit(weapon_text, (20, SCREEN_HEIGHT - 116))

        ammo = self.player.ammo[self.player.current_weapon_key]
        effective_mag = self.player.effective_magazine(weapon)
        if self.player.reloading:
            ammo_str = "RELOADING..."
            ammo_color = RED
            reload_total = max(1, int(weapon.reload_frames * self.player.reload_multiplier))
            progress = 1 - (self.player.reload_timer / reload_total)
            bar_w = 160
            pygame.draw.rect(surface, GRAY, (20, SCREEN_HEIGHT - 92, bar_w, 10))
            pygame.draw.rect(surface, GOLD, (20, SCREEN_HEIGHT - 92, bar_w * clamp(progress, 0, 1), 10))
        else:
            ammo_str = f"Ammo: {ammo}/{effective_mag}   [R to reload]"
            ammo_color = WHITE if ammo > 0 else RED
        ammo_text = font_small.render(ammo_str, True, ammo_color)
        surface.blit(ammo_text, (20, SCREEN_HEIGHT - 90))

        dash_ready = self.player.dash_timer <= 0 and not self.player.dashing
        dash_color = DASH_GREEN if dash_ready else GRAY
        dash_str = "[SPACE] Dash: READY" if dash_ready else f"[SPACE] Dash: {self.player.dash_timer / FPS:.1f}s"
        dash_text = font_small.render(dash_str, True, dash_color)
        surface.blit(dash_text, (20, SCREEN_HEIGHT - 60))

        grenade_ready = self.player.grenade_timer <= 0
        grenade_color = (170, 210, 120) if grenade_ready else GRENADE_COLOR
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
        surface.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 20))

        money_text = font_medium.render(f"Money: $ {self.money}", True, GOLD)
        surface.blit(money_text, (SCREEN_WIDTH // 2 - money_text.get_width() // 2, 92))

        subtitle = font_small.render("WEAPON SHOP", True, LIGHT_GRAY)
        surface.blit(subtitle, (SCREEN_WIDTH // 2 - 260, 128))

        options = self.build_shop_options()
        start_y = 154
        gap = 30
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

        perk_section_y = start_y + len(options) * gap + 18
        perk_subtitle = font_small.render("CHOOSE ONE PERK (free)", True, PERK_COLOR)
        surface.blit(perk_subtitle, (SCREEN_WIDTH // 2 - 260, perk_section_y))

        if self.perk_chosen_this_level:
            chosen_name = self.player.perks_taken[-1] if self.player.perks_taken else "?"
            chosen_text = font_small.render(f"Perk chosen: {chosen_name}", True, GOLD)
            surface.blit(chosen_text, (SCREEN_WIDTH // 2 - 260, perk_section_y + 28))
        else:
            perk_keys_labels = ["7", "8", "9"]
            for i, (name, desc, _fn) in enumerate(self.perk_choices):
                line = f"[{perk_keys_labels[i]}] {name} - {desc}"
                text = font_small.render(line, True, PERK_COLOR)
                surface.blit(text, (SCREEN_WIDTH // 2 - 260, perk_section_y + 26 + i * 28))

        prompt = font_medium.render("Press ENTER to start next level", True, GREEN)
        surface.blit(
            prompt,
            (SCREEN_WIDTH // 2 - prompt.get_width() // 2, perk_section_y + 26 + 3 * 28 + 18),
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
