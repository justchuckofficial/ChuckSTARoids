import pygame
import math
import random
import sys
import time
from typing import List, Tuple

# Initialize Pygame
pygame.init()

# Constants
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800
FPS = 60

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
YELLOW = (255, 255, 0)
CYAN = (0, 255, 255)
BLUE = (0, 100, 255)
PURPLE = (147, 20, 255)
HOT_PINK = (255, 20, 147)

class Vector2D:
    def __init__(self, x=0, y=0):
        self.x = x
        self.y = y
    
    def __add__(self, other):
        return Vector2D(self.x + other.x, self.y + other.y)
    
    def __sub__(self, other):
        return Vector2D(self.x - other.x, self.y - other.y)
    
    def __mul__(self, scalar):
        return Vector2D(self.x * scalar, self.y * scalar)
    
    def magnitude(self):
        return math.sqrt(self.x**2 + self.y**2)
    
    def normalize(self):
        mag = self.magnitude()
        if mag > 0:
            return Vector2D(self.x / mag, self.y / mag)
        return Vector2D(0, 0)
    
    def rotate(self, angle):
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        return Vector2D(
            self.x * cos_a - self.y * sin_a,
            self.x * sin_a + self.y * cos_a
        )

class GlowDemoShip:
    def __init__(self, x, y, effect_type="normal"):
        self.position = Vector2D(x, y)
        self.angle = 0
        self.radius = 15
        self.active = True
        
        # Effect type determines what visual effects to show
        self.effect_type = effect_type
        
        # Shield properties (3 shields)
        self.shield_hits = 3
        self.max_shield_hits = 3
        self.shield_radius = self.radius + 15
        
        # Shield effect timers
        self.shield_damage_timer = 0.0
        self.shield_damage_duration = 0.5
        self.shield_recharge_pulse_timer = 0.0
        self.shield_recharge_pulse_duration = 1.0
        self.shield_full_flash_timer = 0.0
        self.shield_full_flash_duration = 0.5
        self.shield_full_hold_timer = 0.0
        self.shield_full_hold_duration = 0.333
        self.shield_full_fade_timer = 0.0
        self.shield_full_fade_duration = 1.0
        self.shield_pulse_timer = 0.0
        
        # Ability properties (2 ability rings)
        self.ability_charges = 2
        self.max_ability_charges = 2
        self.ability_radius_base = self.radius + 10
        
        # Ability effect timers
        self.ability_recharge_pulse_timer = 0.0
        self.ability_recharge_pulse_duration = 0.5
        self.ability_hold_timer = 0.0
        self.ability_hold_duration = 1.0
        self.ability_fade_timer = 0.0
        self.ability_fade_duration = 0.5
        self.ability_fully_charged_pulse_timer = 0.0
        self.ability_flash_count = 4
        
        # Ship effect timers
        self.invulnerable = False
        self.invulnerable_time = 0.0
        self.red_flash_timer = 0.0
        self.red_flash_duration = 0.1
        self.thrusting = False
        
        # Ring pulse timers
        self.ring_pulse_timer = 0.0
        
        # Demo control
        self.demo_timer = 0.0
        self.demo_phase = 0
        self.demo_phases = [
            "normal", "invulnerable", "damaged", "shield_damage", "shield_recharge", 
            "shield_full_flash", "shield_hold", "shield_fade", "ability_flash", 
            "ability_hold", "ability_fade", "ability_pulse", "thrusting"
        ]
        
        # Load ship image
        try:
            self.image = pygame.image.load("xwing.gif")
            self.image = self.image.convert_alpha()
            image_size = int(self.radius * 2)
            self.image = pygame.transform.smoothscale(self.image, (image_size, image_size))
        except:
            self.image = None
    
    def update(self, dt):
        self.demo_timer += dt
        
        # Cycle through demo phases every 3 seconds
        phase_duration = 3.0
        self.demo_phase = int(self.demo_timer / phase_duration) % len(self.demo_phases)
        current_phase = self.demo_phases[self.demo_phase]
        
        # Update effect timers based on current phase
        self.update_effect_timers(dt, current_phase)
        
        # Update ring pulse timers
        self.ring_pulse_timer += dt
        if self.shield_pulse_timer > 0:
            self.shield_pulse_timer -= dt
        
        # Update ability fully charged pulse timer
        if self.ability_charges == self.max_ability_charges and self.ability_fade_timer <= 0:
            self.ability_fully_charged_pulse_timer += dt
    
    def update_effect_timers(self, dt, phase):
        """Update effect timers based on current demo phase"""
        if phase == "invulnerable":
            self.invulnerable = True
            self.invulnerable_time = 2.0
        elif phase == "damaged":
            self.red_flash_timer = self.red_flash_duration
        elif phase == "shield_damage":
            self.shield_damage_timer = self.shield_damage_duration
        elif phase == "shield_recharge":
            self.shield_recharge_pulse_timer = self.shield_recharge_pulse_duration
            self.shield_pulse_timer = 1.0
        elif phase == "shield_full_flash":
            self.shield_full_flash_timer = self.shield_full_flash_duration
        elif phase == "shield_hold":
            self.shield_full_hold_timer = self.shield_full_hold_duration
        elif phase == "shield_fade":
            self.shield_full_fade_timer = self.shield_full_fade_duration
        elif phase == "ability_flash":
            self.ability_recharge_pulse_timer = self.ability_recharge_pulse_duration
        elif phase == "ability_hold":
            self.ability_hold_timer = self.ability_hold_duration
        elif phase == "ability_fade":
            self.ability_fade_timer = self.ability_fade_duration
        elif phase == "thrusting":
            self.thrusting = True
        
        # Update timers
        if self.invulnerable_time > 0:
            self.invulnerable_time -= dt
            if self.invulnerable_time <= 0:
                self.invulnerable = False
        
        if self.red_flash_timer > 0:
            self.red_flash_timer -= dt
        
        if self.shield_damage_timer > 0:
            self.shield_damage_timer -= dt
        
        if self.shield_recharge_pulse_timer > 0:
            self.shield_recharge_pulse_timer -= dt
        
        if self.shield_full_flash_timer > 0:
            self.shield_full_flash_timer -= dt
            if self.shield_full_flash_timer <= 0:
                self.shield_full_hold_timer = self.shield_full_hold_duration
        
        if self.shield_full_hold_timer > 0:
            self.shield_full_hold_timer -= dt
            if self.shield_full_hold_timer <= 0:
                self.shield_full_fade_timer = self.shield_full_fade_duration
        
        if self.shield_full_fade_timer > 0:
            self.shield_full_fade_timer -= dt
        
        if self.ability_recharge_pulse_timer > 0:
            self.ability_recharge_pulse_timer -= dt
        
        if self.ability_hold_timer > 0:
            self.ability_hold_timer -= dt
            if self.ability_hold_timer <= 0:
                self.ability_fade_timer = self.ability_fade_duration
        
        if self.ability_fade_timer > 0:
            self.ability_fade_timer -= dt
            if self.ability_fade_timer <= 0:
                self.ability_fully_charged_pulse_timer = 0.0
    
    def draw(self, screen):
        if not self.active:
            return
        
        # Draw ship
        self.draw_ship(screen)
        
        # Draw shields
        self.draw_shields(screen)
        
        # Draw ability rings
        self.draw_ability_rings(screen)
        
        # Draw thrust
        if self.thrusting:
            self.draw_thrust(screen)
    
    def draw_ship(self, screen):
        """Draw the ship with various glow effects"""
        if self.image:
            # Rotate the ship image
            rotated_ship = pygame.transform.rotate(self.image, -math.degrees(self.angle) - 90)
            ship_rect = rotated_ship.get_rect(center=(int(self.position.x), int(self.position.y)))
            
            # Apply visual effects with bloom
            if self.invulnerable and int(self.invulnerable_time * 40) % 2:
                # Cyan flash effect when invulnerable with bloom
                self.draw_bloom_circle(screen, self.position.x, self.position.y, self.radius + 5, 
                                     (0, 255, 255), 0.8, 3, 3)
                cyan_ship = self.image.copy()
                cyan_ship.fill((0, 255, 255, 128), special_flags=pygame.BLEND_MULT)
                cyan_ship = pygame.transform.rotate(cyan_ship, -math.degrees(self.angle) - 90)
                screen.blit(cyan_ship, ship_rect)
            elif self.red_flash_timer > 0:
                # Red flash effect when taking damage with bloom
                self.draw_bloom_circle(screen, self.position.x, self.position.y, self.radius + 5, 
                                     (255, 0, 0), 0.8, 3, 3)
                red_ship = self.image.copy()
                red_ship.fill((255, 0, 0, 128), special_flags=pygame.BLEND_MULT)
                red_ship = pygame.transform.rotate(red_ship, -math.degrees(self.angle) - 90)
                screen.blit(red_ship, ship_rect)
            else:
                screen.blit(rotated_ship, ship_rect)
        else:
            # Fallback triangle with bloom
            points = []
            for i in range(3):
                angle = self.angle + i * (2 * math.pi / 3)
                x = self.position.x + math.cos(angle) * self.radius
                y = self.position.y + math.sin(angle) * self.radius
                points.append((x, y))
            
            color = WHITE
            if self.invulnerable and int(self.invulnerable_time * 40) % 2:
                color = CYAN
                # Add bloom for invulnerable triangle
                self.draw_bloom_circle(screen, self.position.x, self.position.y, self.radius + 5, 
                                     (0, 255, 255), 0.8, 3, 3)
            elif self.red_flash_timer > 0:
                color = RED
                # Add bloom for damage triangle
                self.draw_bloom_circle(screen, self.position.x, self.position.y, self.radius + 5, 
                                     (255, 0, 0), 0.8, 3, 3)
            
            pygame.draw.polygon(screen, color, points)
    
    def draw_shields(self, screen):
        """Draw 3 shield rings with various glow effects"""
        if self.shield_hits <= 0:
            return
        
        pulse_intensity = 0.0
        fade_progress = 0.0
        
        # Determine shield effect based on timers
        if self.shield_damage_timer > 0:
            # Shield damage - pulse 10%-100% (4 cycles in 0.5s)
            pulse = (self.shield_damage_duration - self.shield_damage_timer) / self.shield_damage_duration
            pulse_intensity = 0.1 + 0.9 * math.sin(pulse * math.pi * 8)
        elif self.shield_recharge_pulse_timer > 0:
            # Shield recharge - pulse 0%-100% (4 cycles in 1.0s)
            pulse = (self.shield_recharge_pulse_duration - self.shield_recharge_pulse_timer) / self.shield_recharge_pulse_duration
            pulse_intensity = 0.5 + 0.5 * math.sin(pulse * math.pi * 8)
        elif self.shield_full_flash_timer > 0:
            # Shield full flash - flash 0%-100% (4 times in 0.5s)
            pulse = (self.shield_full_flash_duration - self.shield_full_flash_timer) / self.shield_full_flash_duration
            pulse_intensity = 0.5 + 0.5 * math.sin(pulse * math.pi * 8)
        elif self.shield_full_hold_timer > 0:
            # Shield full hold - 100% opacity
            pulse_intensity = 1.0
        elif self.shield_full_fade_timer > 0:
            # Shield full fade - fade from 100% to 0%
            fade_progress = self.shield_full_fade_timer / self.shield_full_fade_duration
            pulse_intensity = fade_progress * fade_progress  # Quadratic ease-out
        
        # Draw shield rings with bloom/glow effects
        if pulse_intensity > 0:
            for i in range(self.shield_hits):
                # Add pulsing effect with offset between rings
                shield_phase = (self.shield_pulse_timer * 2) + (i * 0.10 * math.pi)
                shield_pulse = 0.5 + 0.5 * math.sin(shield_phase)
                
                # Calculate ring intensity
                ring_intensity = pulse_intensity * shield_pulse
                
                # Apply fade effect for individual rings
                if self.shield_full_fade_timer > 0:
                    ring_delay = i * 0.1  # 10% delay per ring
                    ring_fade_progress = max(0, min(1, (fade_progress - ring_delay) / (1 - ring_delay)))
                    ring_intensity = ring_fade_progress * ring_fade_progress
                
                circle_radius = self.shield_radius + i * 5
                width = max(1, int(4 * ring_intensity * shield_pulse))
                
                # Create bloom effect with multiple layers
                self.draw_bloom_circle(screen, self.position.x, self.position.y, circle_radius, 
                                     (0, 100, 255), ring_intensity * 0.8, width, 3)
    
    def draw_ability_rings(self, screen):
        """Draw 2 ability rings with various glow effects"""
        if self.ability_charges <= 0:
            return
        
        pulse_intensity = 0.0
        
        # Determine ability effect based on timers
        if self.ability_recharge_pulse_timer > 0:
            # Ability recharge flash - flash 0% to 100%
            pulse = (self.ability_recharge_pulse_duration - self.ability_recharge_pulse_timer) / self.ability_recharge_pulse_duration
            flash_frequency = self.ability_flash_count * 2
            pulse_intensity = 0.5 + 0.5 * math.sin(pulse * math.pi * flash_frequency)
        elif self.ability_hold_timer > 0:
            # Ability hold - 100% opacity
            pulse_intensity = 1.0
        elif self.ability_fade_timer > 0:
            # Ability fade - fade from 100% to 33%
            fade_progress = self.ability_fade_timer / self.ability_fade_duration
            smooth_fade = fade_progress * fade_progress
            pulse_intensity = 0.33 + 0.67 * smooth_fade
        elif self.ability_charges == self.max_ability_charges:
            # Fully charged - pulse between 25% and 100%
            pulse_intensity = 1.0
        
        # Draw ability rings with bloom effects
        if pulse_intensity > 0:
            for charge in range(self.max_ability_charges):
                ability_radius = self.ability_radius_base + (charge * 3)
                
                # Calculate ring intensity with offset
                if self.ability_charges == self.max_ability_charges and self.ability_fade_timer <= 0:
                    # Pulsing effect with 33% offset per ring
                    pulse_cycle = (self.ability_fully_charged_pulse_timer * 1) % 1.0
                    ring_offset = charge * 0.33
                    pulse_progress = (pulse_cycle + ring_offset) % 1.0
                    ring_intensity = 0.25 + 0.75 * (0.5 + 0.5 * math.sin(pulse_progress * 2 * math.pi))
                else:
                    ring_intensity = pulse_intensity
                
                # Determine color based on charge count
                if self.ability_charges == 1:
                    color = (147, 20, 255)  # Purple
                else:
                    color = (255, 20, 147)  # Hot pink
                
                # Draw ability ring with bloom
                thickness = 1 + int(2 * ring_intensity)
                width = max(1, thickness)
                
                # Create bloom effect with multiple layers
                self.draw_bloom_circle(screen, self.position.x, self.position.y, ability_radius, 
                                     color, ring_intensity * 0.8, width, 3)
    
    def draw_thrust(self, screen):
        """Draw thrust flame with glow effect"""
        # Calculate thrust position behind ship
        flame_angle = self.angle + math.pi
        flame_x = self.position.x + math.cos(flame_angle) * 40
        flame_y = self.position.y + math.sin(flame_angle) * 40
        
        # Draw bloom effect for thrust
        self.draw_bloom_circle(screen, flame_x, flame_y, 15, 
                             (255, 150, 0), 1.0, 8, 4)
        
        # Draw main flame
        flame_points = []
        flame_radius = 10
        for i in range(3):
            angle = self.angle + math.pi + i * (2 * math.pi / 3)
            x = self.position.x + math.cos(angle) * flame_radius
            y = self.position.y + math.sin(angle) * flame_radius
            flame_points.append((x, y))
        pygame.draw.polygon(screen, YELLOW, flame_points)
    
    def draw_bloom_circle(self, screen, x, y, radius, color, intensity, width, layers):
        """Draw a circle with bloom/glow effect using multiple layers and proper blending"""
        # Draw multiple glow layers with different colors and sizes for visible glow
        for i in range(layers + 2):  # Fewer layers to avoid solid circles
            layer_radius = radius + i * 4
            # More dramatic fade for better glow effect
            layer_alpha = int(255 * intensity * (1.0 - i * 0.15))  # Faster fade
            layer_alpha = max(0, min(255, layer_alpha))
            
            # Create layer color with alpha - make it brighter for glow
            if i == 0:
                # Main ring - use original color
                layer_color = (*color, layer_alpha)
                pygame.draw.circle(screen, layer_color, 
                                (int(x), int(y)), 
                                layer_radius, width)
            else:
                # Glow layers - use brighter colors but draw as rings, not filled circles
                bright_color = (
                    min(255, color[0] + 20 + i * 5), 
                    min(255, color[1] + 20 + i * 5), 
                    min(255, color[2] + 20 + i * 5), 
                    layer_alpha
                )
                # Draw as ring, not filled circle
                glow_width = max(1, width + i)
                pygame.draw.circle(screen, bright_color, 
                                (int(x), int(y)), 
                                layer_radius, glow_width)
        
        # Add extra bright outer glow as rings
        for i in range(1):
            glow_radius = radius + (layers + 2 + i) * 4
            glow_alpha = int(255 * intensity * 0.3 * (1.0 - i * 0.5))
            glow_alpha = max(0, min(255, glow_alpha))
            
            # Create very bright glow color
            bright_color = (
                min(255, color[0] + 40), 
                min(255, color[1] + 40), 
                min(255, color[2] + 40), 
                glow_alpha
            )
            
            # Draw as ring, not filled circle
            pygame.draw.circle(screen, bright_color, 
                            (int(x), int(y)), 
                            glow_radius, 2)

class GlowDemo:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Glow Demo - All Visual Effects")
        self.clock = pygame.time.Clock()
        self.running = True
        
        # Create demo ships
        self.ships = []
        ship_positions = [
            (200, 200), (400, 200), (600, 200), (800, 200), (1000, 200),
            (200, 400), (400, 400), (600, 400), (800, 400), (1000, 400),
            (200, 600), (400, 600), (600, 600), (800, 600), (1000, 600)
        ]
        
        for i, pos in enumerate(ship_positions):
            ship = GlowDemoShip(pos[0], pos[1])
            self.ships.append(ship)
        
        # Font for UI
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)
    
    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            
            self.handle_events()
            self.update(dt)
            self.draw()
        
        pygame.quit()
        sys.exit()
    
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
    
    def update(self, dt):
        for ship in self.ships:
            ship.update(dt)
    
    def draw(self):
        self.screen.fill(BLACK)
        
        # Draw ships
        for ship in self.ships:
            ship.draw(self.screen)
        
        # Draw UI
        self.draw_ui()
        
        pygame.display.flip()
    
    def draw_ui(self):
        # Draw title
        title_text = self.font.render("Glow Demo - All Visual Effects", True, WHITE)
        self.screen.blit(title_text, (10, 10))
        
        # Draw current phase info
        if self.ships:
            current_phase = self.ships[0].demo_phases[self.ships[0].demo_phase]
            phase_text = self.small_font.render(f"Current Phase: {current_phase}", True, WHITE)
            self.screen.blit(phase_text, (10, 50))
        
        # Draw effect descriptions
        descriptions = [
            "Normal - Basic ship appearance",
            "Invulnerable - Cyan flashing",
            "Damaged - Red flash",
            "Shield Damage - Shield pulsing",
            "Shield Recharge - Shield celebration",
            "Shield Full Flash - Victory flash",
            "Shield Hold - Full opacity hold",
            "Shield Fade - Gradual fade out",
            "Ability Flash - Ability celebration",
            "Ability Hold - Full opacity hold",
            "Ability Fade - Gradual fade out",
            "Ability Pulse - Rhythmic pulsing",
            "Thrusting - Flame glow effect"
        ]
        
        y_offset = 80
        for i, desc in enumerate(descriptions):
            color = YELLOW if i == (self.ships[0].demo_phase if self.ships else 0) else WHITE
            desc_text = self.small_font.render(desc, True, color)
            self.screen.blit(desc_text, (10, y_offset + i * 20))
        
        # Draw instructions
        instructions = [
            "ESC - Exit",
            "Each phase lasts 3 seconds",
            "All ships show the same effect simultaneously"
        ]
        
        y_offset = 400
        for i, instruction in enumerate(instructions):
            inst_text = self.small_font.render(instruction, True, CYAN)
            self.screen.blit(inst_text, (10, y_offset + i * 20))

if __name__ == "__main__":
    demo = GlowDemo()
    demo.run()
