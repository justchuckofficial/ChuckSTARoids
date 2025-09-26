import pygame
import math
import random
import sys
import logging
import traceback
from datetime import datetime
import time
import threading
import numpy as np
from typing import List, Tuple

# Setup logging for ability and particle generation
def setup_logging():
    """Setup logging to gamelog.txt for debugging"""
    # Only configure if not already configured
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('gamelog.txt'),
                logging.StreamHandler(sys.stdout)
            ]
        )
    return logging.getLogger(__name__)

# Initialize logger (lazy initialization)
logger = None

def get_logger():
    """Get logger, initializing if needed"""
    global logger
    if logger is None:
        logger = setup_logging()
    return logger

# Initialize Pygame
pygame.init()

# Constants
SCREEN_WIDTH = 1000  # 25% bigger (800 * 1.25)
SCREEN_HEIGHT = 750  # 25% bigger (600 * 1.25)
FPS = 60

# Window resizing
RESIZABLE = True
MIN_WIDTH = 400
MIN_HEIGHT = 300

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
YELLOW = (255, 255, 0)
CYAN = (0, 255, 255)

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

class GameObject:
    def __init__(self, x, y, vx=0, vy=0):
        self.position = Vector2D(x, y)
        self.velocity = Vector2D(vx, vy)
        self.angle = 0
        self.active = True
    
    def update(self, dt, screen_width=None, screen_height=None):
        if self.active:
            self.position.x += self.velocity.x * dt
            self.position.y += self.velocity.y * dt
            
            # Use current screen dimensions or fallback to constants
            width = screen_width if screen_width is not None else SCREEN_WIDTH
            height = screen_height if screen_height is not None else SCREEN_HEIGHT
            
            # Classic Asteroids Deluxe screen wrapping
            if self.position.x < 0:
                self.position.x = width
            elif self.position.x > width:
                self.position.x = 0
            if self.position.y < 0:
                self.position.y = height
            elif self.position.y > height:
                self.position.y = 0

class Ship(GameObject):
    def __init__(self, x, y):
        super().__init__(x, y)
        self.radius = 15  # 50% increase from 10
        self.thrust_power = 281.25  # 2x increase from 140.625
        self.rotation_speed = 5
        self.max_speed = 1000000000  # 10x increase from 100M to 1B speed
        self.invulnerable = False
        self.invulnerable_time = 0
        self.thrusting = False
        self.shoot_timer = 0
        self.shoot_interval = 0.1  # seconds between shots (50% slower than 0.05)
        
        # Shield system
        self.shield_hits = 3  # Can take 3 hits
        self.max_shield_hits = 3
        self.shield_recharge_time = 0
        self.shield_recharge_duration = 3.0  # 3 seconds per hit
        self.shield_damage_timer = 0  # Timer for shield damage visual
        self.shield_damage_duration = 1.0  # Show shield for 1 second after damage
        
        # Speed decay
        self.speed_decay_rate = 0.275  # 50% increase in deceleration (was 0.55, now 0.275 = 72.5% decay per second)
        
        # Rotation tracking for "spinning trick" achievement
        self.total_rotations = 0.0
        self.last_angle = 0.0
        self.spinning_trick_shown = False
        self.is_spinning = False  # Track if currently spinning
        
        # Speed tracking for "interstellar" achievement
        self.interstellar_timer = 0.0
        self.interstellar_threshold = 11.38  # seconds at 100% speed
        self.interstellar_shown = False
        self.is_at_max_speed = False  # Track if currently at 100% speed
        
        # Deceleration tracking for time dilation
        self.last_velocity = Vector2D(0, 0)  # Previous frame velocity
        self.deceleration_rate = 0.0  # Current deceleration rate
        
        # Shield recharge pulse effect
        self.shield_recharge_pulse_timer = 0.0  # Timer for shield recharge pulse effect
        self.shield_recharge_pulse_duration = 1.0  # Duration of pulse effect
        
        # Dual ability system
        self.ability_charges = 0  # Start with 0 charges (both empty)
        self.max_ability_charges = 2
        self.ability_timer = 0.0
        self.ability_duration = 10.0  # 10 seconds to charge one ability
        self.first_charge_duration = 5.0  # 5 seconds for first charge on new game
        self.ability_ready = False  # Start with no abilities ready
        self.ability_used = False
        self.is_first_game = True  # Track if this is the first game
        
        # Ring pulsing timers
        self.ring_pulse_timer = 0.0
        self.shield_pulse_timer = 0.0
        
        # Level transition system
        self.level_transition_delay = 0.0
        self.level_flash_timer = 0.0
        self.level_flash_duration = 0.4
        self.level_flash_count = 0
        self.pending_level = None
        
        # Load ship image
        try:
            self.image = pygame.image.load("xwing.gif")
            self.image = self.image.convert_alpha()
            self.image = pygame.transform.smoothscale(self.image, (40, 40))
        except:
            self.image = None
        
    def rotate_left(self, dt):
        self.angle -= self.rotation_speed * dt
    
    def rotate_right(self, dt):
        self.angle += self.rotation_speed * dt
    
    def thrust(self, dt):
        self.thrusting = True
        # Rotate thrust vector 90 degrees clockwise so up arrow moves ship to the right
        thrust_vector = Vector2D(self.thrust_power, 0).rotate(self.angle)
        self.velocity.x += thrust_vector.x * dt
        self.velocity.y += thrust_vector.y * dt
        
        # Limit max speed
        speed = self.velocity.magnitude()
        if speed > self.max_speed:
            self.velocity.x = (self.velocity.x / speed) * self.max_speed
            self.velocity.y = (self.velocity.y / speed) * self.max_speed
    
    def reverse_thrust(self, dt):
        self.thrusting = True
        # Reverse thrust vector (opposite direction)
        thrust_vector = Vector2D(-self.thrust_power, 0).rotate(self.angle)
        self.velocity.x += thrust_vector.x * dt
        self.velocity.y += thrust_vector.y * dt
        
        # Limit max speed
        speed = self.velocity.magnitude()
        if speed > self.max_speed:
            self.velocity.x = (self.velocity.x / speed) * self.max_speed
            self.velocity.y = (self.velocity.y / speed) * self.max_speed
    
    def stop_thrust(self):
        self.thrusting = False
    
    def strafe_left(self, dt):
        """Strafe left (perpendicular to ship's facing direction)"""
        self.thrusting = True
        # Strafe vector is 90 degrees counterclockwise from thrust direction
        strafe_vector = Vector2D(0, -self.thrust_power).rotate(self.angle)
        self.velocity.x += strafe_vector.x * dt
        self.velocity.y += strafe_vector.y * dt
        
        # Limit max speed
        speed = self.velocity.magnitude()
        if speed > self.max_speed:
            self.velocity.x = (self.velocity.x / speed) * self.max_speed
            self.velocity.y = (self.velocity.y / speed) * self.max_speed
    
    def strafe_right(self, dt):
        """Strafe right (perpendicular to ship's facing direction)"""
        self.thrusting = True
        # Strafe vector is 90 degrees clockwise from thrust direction
        strafe_vector = Vector2D(0, self.thrust_power).rotate(self.angle)
        self.velocity.x += strafe_vector.x * dt
        self.velocity.y += strafe_vector.y * dt
        
        # Limit max speed
        speed = self.velocity.magnitude()
        if speed > self.max_speed:
            self.velocity.x = (self.velocity.x / speed) * self.max_speed
            self.velocity.y = (self.velocity.y / speed) * self.max_speed
    
    def update(self, dt, screen_width=None, screen_height=None, time_dilation_factor=1.0):
        # Calculate deceleration rate before updating position
        current_speed = self.velocity.magnitude()
        last_speed = self.last_velocity.magnitude()
        
        # Calculate deceleration rate (negative when slowing down)
        if dt > 0:
            self.deceleration_rate = (current_speed - last_speed) / dt
        else:
            self.deceleration_rate = 0.0
        
        # Store current velocity for next frame
        self.last_velocity = Vector2D(self.velocity.x, self.velocity.y)
        
        super().update(dt, screen_width, screen_height)
        if self.invulnerable:
            self.invulnerable_time -= dt
            if self.invulnerable_time <= 0:
                self.invulnerable = False
        
        # Update shoot timer (affected by time dilation)
        if self.shoot_timer > 0:
            self.shoot_timer -= dt
        
        
        # Update shield recharge (subject to time dilation)
        if self.shield_hits < self.max_shield_hits:
            self.shield_recharge_time += dt
            if self.shield_recharge_time >= self.shield_recharge_duration:
                # Check if going from 2 to 3 shields (full recharge)
                if self.shield_hits == 2:
                    self.shield_recharge_pulse_timer = self.shield_recharge_pulse_duration
                    # Trigger ring pulse when shield charges
                    self.shield_pulse_timer = 1.0  # 1 second pulse
                self.shield_hits += 1
                self.shield_recharge_time = 0
        
        # Update shield damage visual timer (affected by time dilation)
        if self.shield_damage_timer > 0:
            self.shield_damage_timer -= dt
        
        # Update shield recharge pulse timer (affected by time dilation)
        if self.shield_recharge_pulse_timer > 0:
            self.shield_recharge_pulse_timer -= dt
        
        # Update ability timer (affected by time dilation)
        if self.ability_charges < self.max_ability_charges and not self.ability_used:
            self.ability_timer += dt
            # Use first charge duration for first charge on first game, otherwise normal duration
            charge_duration = self.first_charge_duration if (self.is_first_game and self.ability_charges == 0) else self.ability_duration
            if self.ability_timer >= charge_duration:
                self.ability_charges += 1
                self.ability_timer = 0.0
                self.ability_ready = True  # Any charge makes ability ready
                # Mark that we're no longer in first game after first charge
                if self.is_first_game and self.ability_charges == 1:
                    self.is_first_game = False
        elif self.ability_used:
            # Reset ability after use
            self.ability_used = False
            self.ability_ready = self.ability_charges > 0
            if self.ability_charges > 0:
                self.ability_timer = 0.0
        
        # Update ring pulse timers
        self.ring_pulse_timer += dt
        if self.shield_pulse_timer > 0:
            self.shield_pulse_timer -= dt
        
        # Apply speed decay
        if not self.thrusting:
            # Only decay when not thrusting
            current_speed = self.velocity.magnitude()
            speed_percent = current_speed / 1000.0 * 100  # Convert to percentage
            
            # Use much faster decay when speed is below 10%
            if speed_percent < 10.0:
                # Much faster decay to quickly reach 0%
                decay_rate = self.speed_decay_rate ** 4  # 4th power for very fast decay
            else:
                decay_rate = self.speed_decay_rate
            
            self.velocity.x *= decay_rate ** dt
            self.velocity.y *= decay_rate ** dt
        
        # Track rotations for "spinning trick" achievement (only while actively spinning)
        if not self.spinning_trick_shown and self.is_spinning:
            # Calculate angle difference, handling wraparound
            angle_diff = self.angle - self.last_angle
            # Normalize angle difference to [-π, π]
            while angle_diff > math.pi:
                angle_diff -= 2 * math.pi
            while angle_diff < -math.pi:
                angle_diff += 2 * math.pi
            
            # Add to total rotations (convert to full rotations)
            self.total_rotations += abs(angle_diff) / (2 * math.pi)
            self.last_angle = self.angle
            
            # Check if we've reached 11.38 rotations
            if self.total_rotations >= 11.38:
                self.spinning_trick_shown = True
        elif not self.is_spinning:
            # Reset tracking when not spinning
            self.total_rotations = 0.0
            self.last_angle = self.angle
        
        # Track speed for "interstellar" achievement (only while at 100% speed)
        current_speed = self.velocity.magnitude()
        max_speed = 1000.0  # 100% speed threshold
        self.is_at_max_speed = current_speed >= max_speed
        
        if not self.interstellar_shown and self.is_at_max_speed:
            # Add time spent at max speed
            self.interstellar_timer += dt
            
            # Check if we've reached 11.38 seconds at max speed
            if self.interstellar_timer >= self.interstellar_threshold:
                self.interstellar_shown = True
        elif not self.is_at_max_speed:
            # Reset tracking when not at max speed
            self.interstellar_timer = 0.0
    
    def draw(self, screen):
        if not self.active:
            return
            
        # Draw ship using image or fallback to triangle
        if self.image:
            # Rotate the ship image 90 degrees clockwise from default orientation
            rotated_ship = pygame.transform.rotate(self.image, -math.degrees(self.angle) - 90)
            ship_rect = rotated_ship.get_rect(center=(int(self.position.x), int(self.position.y)))
            
            # Draw ship
            if self.invulnerable and int(self.invulnerable_time * 20) % 2:
                # Flash effect when invulnerable - create a blue tinted version
                blue_ship = self.image.copy()
                blue_ship.fill((0, 0, 255, 128), special_flags=pygame.BLEND_MULT)
                blue_ship = pygame.transform.rotate(blue_ship, -math.degrees(self.angle) - 90)
                screen.blit(blue_ship, ship_rect)
            else:
                screen.blit(rotated_ship, ship_rect)
        else:
            # Fallback to triangle shape
            points = []
            for i in range(3):
                angle = self.angle + i * (2 * math.pi / 3)
                x = self.position.x + math.cos(angle) * self.radius
                y = self.position.y + math.sin(angle) * self.radius
                points.append((x, y))
            
            # Draw ship
            color = WHITE
            if self.invulnerable and int(self.invulnerable_time * 20) % 2:
                color = (0, 0, 255)  # Flash blue when invulnerable
            pygame.draw.polygon(screen, color, points)
        
        
        # Draw thrust flame
        if self.thrusting:
            # Calculate thrust width based on player speed (0-60 width from 0-100% speed)
            player_speed = self.velocity.magnitude()
            player_speed_percent = min(player_speed / 1000.0 * 100, 100)  # Cap at 100%
            # Scale from 0 width at 0% speed to 60 width at 100% speed
            thrust_width = int((player_speed_percent / 100.0) * 60)
            
            if thrust_width > 0:  # Only draw if there's thrust
                # Position flame behind the rocket (opposite direction of movement)
                flame_angle = self.angle + math.pi
                flame_x = self.position.x + math.cos(flame_angle) * 40
                flame_y = self.position.y + math.sin(flame_angle) * 40
                
                try:
                    # Try fire.gif image with rotation
                    flame_image = pygame.image.load("fire.gif")
                    # Scale thrust width based on player speed
                    thrust_height = max(5, thrust_width // 2)  # Height is half the width
                    flame_image = pygame.transform.scale(flame_image, (thrust_width, thrust_height))
                    # Rotate the flame 180 degrees and match ship rotation
                    rotated_flame = pygame.transform.rotate(flame_image, -math.degrees(self.angle) - 90 + 90 + 180)
                    flame_rect = rotated_flame.get_rect(center=(int(flame_x), int(flame_y)))
                    screen.blit(rotated_flame, flame_rect)
                except:
                    # Fallback to triangle flame - scale based on thrust width
                    flame_points = []
                    flame_radius = max(5, thrust_width // 4)  # Scale triangle size with thrust
                    for i in range(3):
                        angle = self.angle + math.pi + i * (2 * math.pi / 3)
                        x = self.position.x + math.cos(angle) * flame_radius
                        y = self.position.y + math.sin(angle) * flame_radius
                        flame_points.append((x, y))
                    pygame.draw.polygon(screen, YELLOW, flame_points)
        
        # Draw shield (only when taking damage or during recharge pulse)
        # Only show shield rings when pulsing during recharge (2→3) or when damaged
        if self.shield_hits > 0:
            shield_radius = self.radius + 15
            pulse_intensity = 0.0  # Start invisible
            
            # Add pulsing effect if recently damaged
            if self.shield_damage_timer > 0:
                pulse = (self.shield_damage_duration - self.shield_damage_timer) / self.shield_damage_duration
                pulse_intensity = 0.5 + 0.5 * math.sin(pulse * math.pi * 8)  # Fast pulse
            # Add pulsing effect if shield just recharged to full (2 to 3)
            elif self.shield_recharge_pulse_timer > 0:
                pulse = (self.shield_recharge_pulse_duration - self.shield_recharge_pulse_timer) / self.shield_recharge_pulse_duration
                pulse_intensity = 0.8 + 0.2 * math.sin(pulse * math.pi * 12)  # Bright, fast pulse
            # Add pulsing effect during recharge (1-2 shields)
            elif self.shield_hits < self.max_shield_hits:
                recharge_progress = self.shield_recharge_time / self.shield_recharge_duration
                pulse_intensity = 0.3 + 0.7 * recharge_progress  # Fade from 30% to 100%
                # Add pulsing effect during recharge
                pulse = recharge_progress * math.pi * 4  # 4 pulses during recharge
                pulse_intensity = pulse_intensity * (0.5 + 0.5 * math.sin(pulse))
            # At full shields (3/3) - invisible (no continuous pulse)
            
            # Only draw circles if they should be visible
            if pulse_intensity > 0:
                # Draw circles for each shield hit (outline only, no fill)
                for i in range(self.shield_hits):
                    # Add 7% offset between shield rings for pulsing effect
                    shield_phase = (self.shield_pulse_timer * 5) + (i * 0.07 * math.pi)  # 7% offset
                    shield_pulse = 0.5 + 0.5 * math.sin(shield_phase)  # 0.5 to 1.0 multiplier
                    
                    alpha = int(255 * pulse_intensity * shield_pulse)
                    color = (0, 100, 255, alpha)
                    # Draw outline circle (width parameter makes it outline only)
                    # Ensure minimum width of 1 to avoid filled circles
                    width = max(1, int(3 * pulse_intensity * shield_pulse))
                    pygame.draw.circle(screen, (0, 100, 255), 
                                    (int(self.position.x), int(self.position.y)), 
                                    shield_radius + i * 5, width)
        
        # Draw shield recharge progress indicator (clockwise from 12 o'clock)
        if self.shield_hits < self.max_shield_hits:
            recharge_progress = self.shield_recharge_time / self.shield_recharge_duration
            if recharge_progress > 0:
                # Calculate arc angles for clockwise progress from 12 o'clock
                # 0% = 12 o'clock (3π/2), 50% = 6 o'clock (π/2), 100% = 12 o'clock (3π/2)
                start_angle = 3 * math.pi / 2  # 12 o'clock (270 degrees)
                end_angle = start_angle + (2 * math.pi * recharge_progress)  # Clockwise progress
                
                # Draw the recharge progress arc
                shield_radius = self.radius + 15
                arc_rect = pygame.Rect(
                    int(self.position.x - shield_radius), 
                    int(self.position.y - shield_radius), 
                    shield_radius * 2, 
                    shield_radius * 2
                )
                
                # Calculate color intensity based on recharge progress
                color_intensity = 0.3 + 0.7 * recharge_progress
                alpha = int(255 * color_intensity)
                color = (0, 150, 255)  # Slightly brighter blue for recharge indicator
                
                # Draw the arc with a thick line to make it visible (50% thinner)
                width = max(2, int(2.5 * recharge_progress))
                pygame.draw.arc(screen, color, arc_rect, start_angle, end_angle, width)
        
        # Draw dual ability timer rings (purple, inside smallest shield circle)
        self.draw_ability_rings(screen)
    
    def draw_ability_rings(self, screen):
        """Draw dual ability rings with offset pulsing"""
        base_radius = self.radius + 10  # Inside the smallest shield
        
        # Calculate pulsing effects
        ring_pulse = 0.1 + 0.9 * math.sin(self.ring_pulse_timer * 6)  # 10% to 100% opacity, 2x faster
        shield_pulse = 1.0
        if self.shield_pulse_timer > 0:
            # 25% offset from inside to outside when shield charges (50% slower)
            shield_pulse = 1.0 + 0.5 * math.sin(self.shield_pulse_timer * 5)
        
        # Draw rings for each charge
        for charge in range(self.max_ability_charges):
            # Calculate radius for this ring (slightly different for each)
            ability_radius = base_radius + (charge * 3)  # 3 pixel separation
            
            # Calculate pulsing with 10% offset between rings (only when ready)
            ring_phase = (self.ring_pulse_timer * 6) + (charge * math.pi * 0.2)  # 10% offset, 2x faster
            pulse = 0.1 + 0.9 * math.sin(ring_phase)  # 10% to 100% opacity
            
            # Apply shield pulse if active
            if self.shield_pulse_timer > 0:
                shield_phase = (self.shield_pulse_timer * 5) + (charge * 0.25 * math.pi)  # 25% offset, 50% slower
                pulse *= (1.0 + 0.5 * math.sin(shield_phase))
            
            # Clamp pulse to valid range (0.0 to 1.0)
            pulse = max(0.0, min(1.0, pulse))
            
            # Determine if this charge is ready
            is_ready = charge < self.ability_charges
            
            if is_ready:
                # Ready phase: full circle with pulsing
                arc_rect = pygame.Rect(
                    int(self.position.x - ability_radius), 
                    int(self.position.y - ability_radius), 
                    ability_radius * 2, 
                    ability_radius * 2
                )
                
                # Create surface with alpha
                arc_surface = pygame.Surface((arc_rect.width, arc_rect.height), pygame.SRCALPHA)
                
                # Color based on number of charges
                if self.ability_charges == 1:  # 1 charge = purple
                    red = 128
                    green = 0
                    blue = 255
                else:  # 2 charges = hot pink
                    red = 255
                    green = 20
                    blue = 147
                
                opacity = max(0, min(255, int(255 * pulse)))
                color = (red, green, blue, opacity)
                
                # Thickness pulsing (1x to 2x)
                thickness_pulse = 1.0 + 1.0 * math.sin(ring_phase)
                width = max(1, int(thickness_pulse))
                
                # Draw full circle
                pygame.draw.arc(arc_surface, color, pygame.Rect(0, 0, arc_rect.width, arc_rect.height), 0, 2 * math.pi, width)
                screen.blit(arc_surface, arc_rect)
                
            else:
                # Charging phase: arc based on progress
                if self.ability_charges < self.max_ability_charges:  # Show progress if not fully charged
                    # Calculate progress for this specific ring
                    if charge == 0:
                        # First ring: use first charge duration for first game, otherwise normal
                        charge_duration = self.first_charge_duration if self.is_first_game else self.ability_duration
                        ability_progress = self.ability_timer / charge_duration
                    else:
                        # Second ring: only show progress if first ring is charged
                        if self.ability_charges > 0:
                            ability_progress = self.ability_timer / self.ability_duration
                        else:
                            ability_progress = 0
                    
                    if ability_progress > 0:
                        # Calculate arc angles for clockwise progress from 12 o'clock
                        start_angle = 3 * math.pi / 2  # 12 o'clock
                        end_angle = start_angle + (2 * math.pi * ability_progress)
                        
                        arc_rect = pygame.Rect(
                            int(self.position.x - ability_radius), 
                            int(self.position.y - ability_radius), 
                            ability_radius * 2, 
                            ability_radius * 2
                        )
                        
                        # Create surface with alpha
                        arc_surface = pygame.Surface((arc_rect.width, arc_rect.height), pygame.SRCALPHA)
                        
                        # Purple color with opacity fade (no pulsing during charging)
                        opacity = max(0, min(255, int(255 * 0.75 * ability_progress)))
                        color = (128, 0, 255, opacity)  # Bright purple
                        
                        # Draw arc
                        width = 1
                        pygame.draw.arc(arc_surface, color, pygame.Rect(0, 0, arc_rect.width, arc_rect.height), start_angle, end_angle, width)
                        screen.blit(arc_surface, arc_rect)

class Bullet(GameObject):
    def __init__(self, x, y, vx, vy, is_ufo_bullet=False, angle=None):
        super().__init__(x, y, vx, vy)
        self.lifetime = 2.0  # seconds
        self.age = 0
        self.is_ufo_bullet = is_ufo_bullet
        # Use provided angle or calculate from velocity for rotation
        if angle is not None:
            self.angle = angle
        else:
            self.angle = math.atan2(vy, vx)
        
        # Calculate velocity-based scaling (0.5x to 2x based on speed)
        velocity_magnitude = math.sqrt(vx*vx + vy*vy)
        # Scale from 0.5x at low speed to 2x at high speed
        # Assuming max bullet speed around 1000, scale from 0.5x to 2x
        max_bullet_speed = 1000.0
        speed_ratio = min(velocity_magnitude / max_bullet_speed, 1.0)
        self.velocity_scale = 0.5 + (speed_ratio * 1.5)  # 0.5 to 2.0
        
        # Base dimensions
        self.base_width = 16
        self.base_height = 8
        
        # Calculate scaled dimensions
        self.scaled_width = int(self.base_width * self.velocity_scale)
        self.scaled_height = int(self.base_height * self.velocity_scale)
        
        # Dynamic hitbox radius based on actual bullet dimensions
        self.radius = max(2, min(self.scaled_width, self.scaled_height) // 2)
        
        # Load bullet image
        try:
            if is_ufo_bullet:
                self.image = pygame.image.load("tieshot.gif")
            else:
                self.image = pygame.image.load("shot.gif")
            # Scale bullet based on velocity
            self.image = pygame.transform.scale(self.image, (self.scaled_width, self.scaled_height))
        except Exception as e:
            print(f"Bullet image error: {e}")
            self.image = None
    
    def update(self, dt, screen_width=None, screen_height=None):
        super().update(dt, screen_width, screen_height)
        self.age += dt
        if self.age >= self.lifetime:
            self.active = False
    
    def draw(self, screen):
        if self.active:
            if self.image:
                # Draw bullet using image with rotation (aligned with velocity direction)
                rotated_image = pygame.transform.rotate(self.image, -math.degrees(self.angle))
                bullet_rect = rotated_image.get_rect(center=(int(self.position.x), int(self.position.y)))
                screen.blit(rotated_image, bullet_rect)
            else:
                # Fallback to ellipse - match actual bullet dimensions
                color = RED if self.is_ufo_bullet else WHITE
                # Draw ellipse to match bullet shape and size
                ellipse_rect = pygame.Rect(
                    int(self.position.x - self.scaled_width // 2),
                    int(self.position.y - self.scaled_height // 2),
                    self.scaled_width,
                    self.scaled_height
                )
                pygame.draw.ellipse(screen, color, ellipse_rect)
            
            

class Asteroid(GameObject):
    def __init__(self, x, y, size=3):
        super().__init__(x, y)
        self.size = size  # 9=XXXL, 8=XXL, 7=XL, 6=L, 5=M, 4=S, 3=XS, 2=XXS, 1=XXS
        # Match hitbox to visual size better (custom sizes)
        base_radius = 50  # Base radius for 100% scale
        scale_factors = {9: 7.5, 8: 6.0, 7: 4.5, 6: 3.0, 5: 1.5, 4: 1.0, 3: 0.75, 2: 0.5, 1: 0.25}
        self.radius = int(base_radius * scale_factors.get(size, 1.0) * 0.925)  # 7.5% smaller hitboxes
        # Size-based rotation scaling (larger = slower rotation)
        base_rotation = random.uniform(-2, 2)
        rotation_multipliers = {9: 0.1, 8: 0.2, 7: 0.3, 6: 0.4, 5: 0.5, 4: 0.6, 3: 0.7, 2: 0.8, 1: 0.9, 0: 1.0}
        self.rotation_speed = base_rotation * rotation_multipliers.get(size, 1.0)
        self.rotation_angle = 0
        
        # Size-based speed scaling system (25% slower)
        base_speed = random.uniform(50, 150) * 0.75  # Base speed range, 25% slower
        speed_multipliers = {9: 1/10, 8: 3/10, 7: 5/10, 6: 7/10, 5: 9/10, 4: 1.0, 3: 1.5, 2: 2.0, 1: 2.5, 0: 3.0}
        speed = base_speed * speed_multipliers.get(size, 1.0)
        angle = random.uniform(0, 2 * math.pi)
        self.velocity = Vector2D(
            math.cos(angle) * speed,
            math.sin(angle) * speed
        )
        
        # Load asteroid image
        try:
            self.image = pygame.image.load("roid.gif")
            self.image = self.image.convert_alpha()
            # New size hierarchy scaling (custom sizes)
            base_size = 100  # Base size for 100% scale
            scale_factors = {9: 7.5, 8: 6.0, 7: 4.5, 6: 3.0, 5: 1.5, 4: 1.0, 3: 0.75, 2: 0.5, 1: 0.25}
            scale = int(base_size * scale_factors.get(size, 1.0))
            self.image = pygame.transform.smoothscale(self.image, (scale, scale))
        except:
            self.image = None
        
        # Create classic irregular shape (fallback)
        self.points = self.create_shape()
    
    def create_shape(self):
        # Classic Asteroids Deluxe irregular polygon generation
        points = []
        num_points = 8 + self.size * 2  # More points for larger asteroids
        for i in range(num_points):
            angle = (i / num_points) * 2 * math.pi
            # Classic irregularity - more pronounced than modern versions
            radius_variation = random.uniform(0.6, 1.4)
            radius = self.radius * radius_variation
            x = math.cos(angle) * radius
            y = math.sin(angle) * radius
            points.append((x, y))
        return points
    
    def update(self, dt, screen_width=None, screen_height=None, player_speed=0, time_dilation_factor=1.0):
        # dt is already dilated time, so use it directly
        super().update(dt, screen_width, screen_height)
        # Apply time dilation to rotation speed (rotation should also be affected by time dilation)
        self.rotation_angle += self.rotation_speed * dt
    
    def draw(self, screen, screen_width=None, screen_height=None):
        if not self.active:
            return
        
        # Get screen dimensions (use current screen size or fallback to constants)
        width = screen_width if screen_width is not None else SCREEN_WIDTH
        height = screen_height if screen_height is not None else SCREEN_HEIGHT
        
        # Calculate wrapped positions for screen wrapping
        positions = []
        
        # Main position
        positions.append((self.position.x, self.position.y))
        
        # Check if asteroid is crossing screen edges and add wrapped positions
        asteroid_radius = self.radius
        
        # Horizontal wrapping
        if self.position.x < asteroid_radius:
            positions.append((self.position.x + width, self.position.y))
        elif self.position.x > width - asteroid_radius:
            positions.append((self.position.x - width, self.position.y))
        
        # Vertical wrapping
        if self.position.y < asteroid_radius:
            positions.append((self.position.x, self.position.y + height))
        elif self.position.y > height - asteroid_radius:
            positions.append((self.position.x, self.position.y - height))
        
        # Corner wrapping (when asteroid is in corner)
        if (self.position.x < asteroid_radius and self.position.y < asteroid_radius):
            positions.append((self.position.x + width, self.position.y + height))
        elif (self.position.x > width - asteroid_radius and self.position.y < asteroid_radius):
            positions.append((self.position.x - width, self.position.y + height))
        elif (self.position.x < asteroid_radius and self.position.y > height - asteroid_radius):
            positions.append((self.position.x + width, self.position.y - height))
        elif (self.position.x > width - asteroid_radius and self.position.y > height - asteroid_radius):
            positions.append((self.position.x - width, self.position.y - height))
        
        # Draw asteroid at all calculated positions
        for pos_x, pos_y in positions:
            if self.image:
                # Draw asteroid using image
                rotated_asteroid = pygame.transform.rotate(self.image, -math.degrees(self.rotation_angle))
                asteroid_rect = rotated_asteroid.get_rect(center=(int(pos_x), int(pos_y)))
                screen.blit(rotated_asteroid, asteroid_rect)
            else:
                # Classic polygon shape drawing
                rotated_points = []
                for point in self.points:
                    x, y = point
                    # Rotate
                    cos_a = math.cos(self.rotation_angle)
                    sin_a = math.sin(self.rotation_angle)
                    rx = x * cos_a - y * sin_a
                    ry = x * sin_a + y * cos_a
                    # Translate to wrapped position
                    rotated_points.append((rx + pos_x, ry + pos_y))
                
                pygame.draw.polygon(screen, WHITE, rotated_points, 2)
        
        
    
    def split(self, projectile_velocity=None):
        # Special XXS splitting behavior
        if self.size == 2:  # XXS asteroid
            if random.random() < 0.25:  # 25% chance to split into 2 XXXS
                new_asteroids = []
                for i in range(2):
                    new_asteroid = Asteroid(self.position.x, self.position.y, 1)  # XXXS
                    
                    # Inherit parent velocity with random offset
                    base_speed = self.velocity.magnitude() * 1.3
                    angle_offset = random.uniform(-math.pi/3, math.pi/3)
                    angle = math.atan2(self.velocity.y, self.velocity.x) + angle_offset
                    
                    speed_variation = random.uniform(0.7, 1.3)
                    final_speed = base_speed * speed_variation
                    
                    # Add projectile velocity if provided (5% of projectile velocity)
                    if projectile_velocity:
                        new_asteroid.velocity = Vector2D(
                            math.cos(angle) * final_speed + projectile_velocity.x * 0.05,
                            math.sin(angle) * final_speed + projectile_velocity.y * 0.05
                        )
                    else:
                        new_asteroid.velocity = Vector2D(
                            math.cos(angle) * final_speed,
                            math.sin(angle) * final_speed
                        )
                    
                    # Size-based rotation
                    base_rotation = random.uniform(-2, 2)
                    rotation_multipliers = {9: 0.1, 8: 0.2, 7: 0.3, 6: 0.4, 5: 0.5, 4: 0.6, 3: 0.7, 2: 0.8, 1: 0.9, 0: 1.0}
                    new_asteroid.rotation_speed = base_rotation * rotation_multipliers.get(new_asteroid.size, 1.0)
                    new_asteroid.rotation_angle = random.uniform(0, 2 * math.pi)
                    new_asteroids.append(new_asteroid)
                return new_asteroids
            else:
                # 75% chance to just be destroyed
                return []
        
        # Normal splitting for other sizes
        elif self.size > 1:
            new_asteroids = []
            for i in range(2):
                new_asteroid = Asteroid(self.position.x, self.position.y, self.size - 1)
                
                # Classic splitting: inherit parent velocity with random offset
                base_speed = self.velocity.magnitude() * 1.3  # Classic speed multiplier
                angle_offset = random.uniform(-math.pi/3, math.pi/3)  # ±60 degrees from parent
                angle = math.atan2(self.velocity.y, self.velocity.x) + angle_offset
                
                # Classic speed variation
                speed_variation = random.uniform(0.7, 1.3)
                final_speed = base_speed * speed_variation
                
                # Add projectile velocity if provided (5% of projectile velocity)
                if projectile_velocity:
                    new_asteroid.velocity = Vector2D(
                        math.cos(angle) * final_speed + projectile_velocity.x * 0.05,
                        math.sin(angle) * final_speed + projectile_velocity.y * 0.05
                    )
                else:
                    new_asteroid.velocity = Vector2D(
                        math.cos(angle) * final_speed,
                        math.sin(angle) * final_speed
                    )
                
                # Size-based rotation
                base_rotation = random.uniform(-2, 2)
                rotation_multipliers = {9: 0.1, 8: 0.2, 7: 0.3, 6: 0.4, 5: 0.5, 4: 0.6, 3: 0.7, 2: 0.8, 1: 0.9, 0: 1.0}
                new_asteroid.rotation_speed = base_rotation * rotation_multipliers.get(new_asteroid.size, 1.0)
                new_asteroid.rotation_angle = random.uniform(0, 2 * math.pi)
                new_asteroids.append(new_asteroid)
            return new_asteroids
        return []

class AdvancedUFO(GameObject):
    def __init__(self, x, y, ai_personality="aggressive"):
        super().__init__(x, y)
        
        # Basic properties
        self.radius = 26  # Half as big (52 * 0.5 = 26)
        self.speed = 100
        self.max_speed = 150
        self.acceleration = 50
        
        # AI Personality Types
        self.personality = ai_personality  # "aggressive", "defensive", "tactical", "swarm", "deadly"
        
        # State Machine
        self.current_state = "patrol"
        self.state_timer = 0.0
        self.state_duration = 0.0
        
        # Behavior Layers
        self.behavior_weights = {
            "seek": 0.0,      # Move toward player
            "flee": 0.0,      # Move away from player
            "flank": 0.0,     # Move to flanking position
            "swarm": 0.0,     # Coordinate with other UFOs
            "patrol": 0.0,    # Random patrol movement
            "intercept": 0.0, # Predict and intercept player
            "evade": 0.0,     # Avoid player bullets
            "avoid_asteroids": 0.0  # Avoid asteroids
        }
        
        # Environmental Awareness
        self.player_position = Vector2D(0, 0)
        self.player_velocity = Vector2D(0, 0)
        self.player_bullets = []
        self.other_ufos = []
        self.asteroids = []
        
        # Tactical Variables
        self.last_known_player_pos = Vector2D(0, 0)
        self.pursuit_timer = 0.0
        self.retreat_timer = 0.0
        self.flanking_target = Vector2D(0, 0)
        self.optimal_distance = 200
        self.danger_zone = 100
        
        # Swarm Coordination
        self.swarm_center = Vector2D(0, 0)
        self.swarm_radius = 300
        self.formation_position = Vector2D(0, 0)
        
        # Combat Variables
        self.shoot_timer = 0.0
        self.shoot_interval = 1.0
        self.accuracy_modifier = 1.0
        self.aggression_level = 1.0
        
        # Deadly AI enhancements
        if ai_personality == "deadly":
            self.speed = 120  # 20% faster
            self.max_speed = 180  # 20% faster max speed
            self.shoot_interval = 0.7  # 30% faster shooting
            self.accuracy_modifier = 1.5  # 50% more accurate
            self.aggression_level = 2.0  # Double aggression
        
        # Asteroid avoidance
        self.asteroid_avoidance_distance = 80
        self.avoidance_force = Vector2D(0, 0)
        
        # Initial movement
        self.direction = 1 if random.random() < 0.5 else -1
        self.velocity = Vector2D(self.direction * self.speed, 0)
        self.oscillation = 0
        self.oscillation_speed = 2
        self.angle = math.atan2(self.velocity.y, self.velocity.x)
        
        # Load UFO image
        try:
            self.image = pygame.image.load("tie.gif")
            self.image = self.image.convert_alpha()
            image_size = int(self.radius * 2)
            self.image = pygame.transform.smoothscale(self.image, (image_size, image_size))
        except Exception as e:
            print(f"Failed to load UFO image: {e}")
            self.image = None
    
    def update(self, dt, ship_pos, screen_width=None, screen_height=None, time_dilation_factor=1.0):
        super().update(dt, screen_width, screen_height)
        
        # Update environmental awareness
        self.update_environmental_awareness(ship_pos)
        
        # Calculate threat and opportunity levels
        threat_level = self.calculate_threat_level()
        opportunity_level = self.calculate_opportunity_level()
        
        # Update AI state based on personality
        self.update_ai_state(dt, threat_level, opportunity_level)
        
        # Update behavior weights
        self.update_behavior_weights()
        
        # Calculate movement vector
        self.calculate_movement_vector(dt)
        
        # Update shooting behavior
        should_shoot = self.update_shooting_behavior(dt)
        
        return should_shoot
    
    def draw(self, screen, debug_mode=False):
        if not self.active:
            return
            
        if self.image:
            # Draw UFO using image with rotation (90 degrees clockwise offset)
            rotated_ufo = pygame.transform.rotate(self.image, -math.degrees(self.angle) - 90)
            ufo_rect = rotated_ufo.get_rect(center=(int(self.position.x), int(self.position.y)))
            screen.blit(rotated_ufo, ufo_rect)
        else:
            # Fallback to original UFO shape (no rotation for fallback)
            pygame.draw.ellipse(screen, WHITE, 
                              (self.position.x - self.radius, self.position.y - self.radius/2,
                               self.radius * 2, self.radius))
            pygame.draw.rect(screen, WHITE,
                            (self.position.x - self.radius/2, self.position.y - self.radius/4,
                             self.radius, self.radius/2))
        
        # Debug text: Show UFO state and personality (only in debug mode)
        if debug_mode:
            font = pygame.font.Font(None, 24)
            debug_text = f"{self.personality.upper()}: {self.current_state.upper()}"
            
            # Add swarm info if applicable
            if self.current_state.startswith("swarm"):
                debug_text += " (SWARMING)"
            
            text_surface = font.render(debug_text, True, (255, 255, 0))  # Yellow text
            text_rect = text_surface.get_rect(center=(int(self.position.x), int(self.position.y) + 40))
            screen.blit(text_surface, text_rect)
    
    def update_environmental_awareness(self, ship_pos):
        """Update awareness of game world"""
        if ship_pos:
            self.player_position = Vector2D(ship_pos.x, ship_pos.y)
            # Track player movement patterns
            if hasattr(self, 'last_player_pos'):
                self.player_velocity = ship_pos - self.last_player_pos
            self.last_player_pos = Vector2D(ship_pos.x, ship_pos.y)
    
    def calculate_threat_level(self):
        """Calculate current threat level (0.0 to 1.0)"""
        threat = 0.0
        
        # Distance to player (closer = more threat)
        distance_to_player = (self.position - self.player_position).magnitude()
        if distance_to_player < self.danger_zone:
            threat += 0.4
        elif distance_to_player < self.optimal_distance:
            threat += 0.2
        
        # Player bullets nearby
        for bullet in self.player_bullets:
            if bullet.active:
                bullet_distance = (self.position - bullet.position).magnitude()
                if bullet_distance < 50:
                    threat += 0.3
                elif bullet_distance < 100:
                    threat += 0.1
        
        # Player speed (faster = more dangerous)
        player_speed = self.player_velocity.magnitude()
        if player_speed > 800:
            threat += 0.3
        elif player_speed > 400:
            threat += 0.1
        
        return min(threat, 1.0)
    
    def calculate_opportunity_level(self):
        """Calculate current opportunity level (0.0 to 1.0)"""
        opportunity = 0.0
        
        # Player is slow or stationary
        player_speed = self.player_velocity.magnitude()
        if player_speed < 200:
            opportunity += 0.4
        elif player_speed < 400:
            opportunity += 0.2
        
        # Player is busy with asteroids
        nearby_asteroids = sum(1 for asteroid in self.asteroids 
                              if asteroid.active and (asteroid.position - self.player_position).magnitude() < 200)
        if nearby_asteroids > 2:
            opportunity += 0.3
        
        return min(opportunity, 1.0)
    
    def update_ai_state(self, dt, threat_level, opportunity_level):
        """Update AI state based on personality and situation"""
        self.state_timer += dt
        
        # State transitions based on personality
        if self.personality == "aggressive":
            self.update_aggressive_ai(dt, threat_level, opportunity_level)
        elif self.personality == "defensive":
            self.update_defensive_ai(dt, threat_level, opportunity_level)
        elif self.personality == "tactical":
            self.update_tactical_ai(dt, threat_level, opportunity_level)
        elif self.personality == "swarm":
            self.update_swarm_ai(dt, threat_level, opportunity_level)
        elif self.personality == "deadly":
            self.update_deadly_ai(dt, threat_level, opportunity_level)
        else:
            # Default to aggressive behavior
            self.update_aggressive_ai(dt, threat_level, opportunity_level)
    
    def update_aggressive_ai(self, dt, threat_level, opportunity_level):
        """Aggressive UFOs prioritize direct engagement"""
        if threat_level < 0.3:  # Low threat
            if opportunity_level > 0.7:  # High opportunity
                self.current_state = "pursue"
                self.state_duration = 4.0
            else:
                self.current_state = "patrol"
                self.state_duration = 3.0
        elif threat_level < 0.7:  # Medium threat
            if opportunity_level > 0.5:
                self.current_state = "flank"
                self.state_duration = 3.0
            else:
                self.current_state = "intercept"
                self.state_duration = 2.0
        else:  # High threat
            if opportunity_level > 0.8:
                self.current_state = "pursue"  # Still aggressive even under threat
                self.state_duration = 2.0
            else:
                self.current_state = "evade"
                self.state_duration = 1.5
    
    def update_defensive_ai(self, dt, threat_level, opportunity_level):
        """Defensive UFOs prioritize survival and positioning"""
        if threat_level > 0.6:
            self.current_state = "flee"
            self.state_duration = 2.0
        elif threat_level > 0.3:
            self.current_state = "evade"
            self.state_duration = 1.5
        elif opportunity_level > 0.6:
            self.current_state = "intercept"
            self.state_duration = 2.5
        else:
            self.current_state = "patrol"
            self.state_duration = 4.0
    
    def update_tactical_ai(self, dt, threat_level, opportunity_level):
        """Tactical UFOs use complex strategies"""
        player_speed = self.player_velocity.magnitude()
        
        if player_speed > 500:  # Player is moving fast
            self.current_state = "intercept"
            self.state_duration = 2.0
        elif threat_level > 0.5:
            self.current_state = "evade"
            self.state_duration = 1.0
        elif opportunity_level > 0.6:
            self.current_state = "flank"
            self.state_duration = 3.0
        else:
            self.current_state = "seek"
            self.state_duration = 2.5
    
    def update_swarm_ai(self, dt, threat_level, opportunity_level):
        """Swarm UFOs coordinate with each other"""
        if len(self.other_ufos) > 0:
            if opportunity_level > 0.6:
                self.current_state = "swarm_attack"
                self.state_duration = 3.0
            else:
                self.current_state = "swarm_patrol"
                self.state_duration = 2.0
        else:
            self.current_state = "patrol"
            self.state_duration = 2.0
    
    def update_deadly_ai(self, dt, threat_level, opportunity_level):
        """Deadly UFOs use the most aggressive and intelligent tactics"""
        # Deadly AI is always aggressive and never retreats
        if opportunity_level > 0.3:  # Any opportunity
            if threat_level < 0.4:  # Low threat
                self.current_state = "pursue"
                self.state_duration = 5.0  # Longer pursuit
            elif threat_level < 0.7:  # Medium threat
                self.current_state = "flank"
                self.state_duration = 4.0  # Longer flanking
            else:  # High threat
                self.current_state = "intercept"  # Still intercept even under high threat
                self.state_duration = 3.0
        else:  # Low opportunity
            if threat_level < 0.6:  # Low-medium threat
                self.current_state = "intercept"  # Always try to intercept
                self.state_duration = 3.0
            else:  # High threat
                self.current_state = "evade"  # Only evade when very threatened
                self.state_duration = 1.0  # Short evade, then back to attack
    
    def update_behavior_weights(self):
        """Dynamically adjust behavior weights based on current state"""
        # Reset all weights
        for behavior in self.behavior_weights:
            self.behavior_weights[behavior] = 0.0
        
        # Base weights from current state
        if self.current_state == "pursue":
            self.behavior_weights["seek"] = 0.8
            self.behavior_weights["intercept"] = 0.2
        elif self.current_state == "flank":
            self.behavior_weights["flank"] = 0.6
            self.behavior_weights["seek"] = 0.4
        elif self.current_state == "flee":
            self.behavior_weights["flee"] = 0.9
            self.behavior_weights["evade"] = 0.1
        elif self.current_state == "evade":
            self.behavior_weights["evade"] = 0.7
            self.behavior_weights["flee"] = 0.3
        elif self.current_state == "patrol":
            self.behavior_weights["patrol"] = 0.8
            self.behavior_weights["seek"] = 0.2
        elif self.current_state == "intercept":
            self.behavior_weights["intercept"] = 0.9
            self.behavior_weights["seek"] = 0.1
        elif self.current_state == "swarm_attack":
            self.behavior_weights["swarm"] = 0.6
            self.behavior_weights["seek"] = 0.4
        elif self.current_state == "swarm_patrol":
            self.behavior_weights["swarm"] = 0.8
            self.behavior_weights["patrol"] = 0.2
        elif self.current_state == "seek":
            self.behavior_weights["seek"] = 1.0
        
        # Always add asteroid avoidance
        self.behavior_weights["avoid_asteroids"] = 0.3
    
    def calculate_movement_vector(self, dt):
        """Calculate final movement vector combining all behaviors"""
        final_velocity = Vector2D(0, 0)
        
        # Apply each behavior with its weight
        if self.behavior_weights["seek"] > 0:
            seek_vector = self.calculate_seek_vector()
            final_velocity += seek_vector * self.behavior_weights["seek"]
        
        if self.behavior_weights["flee"] > 0:
            flee_vector = self.calculate_flee_vector()
            final_velocity += flee_vector * self.behavior_weights["flee"]
        
        if self.behavior_weights["flank"] > 0:
            flank_vector = self.calculate_flank_vector()
            final_velocity += flank_vector * self.behavior_weights["flank"]
        
        if self.behavior_weights["swarm"] > 0:
            swarm_vector = self.calculate_swarm_vector()
            final_velocity += swarm_vector * self.behavior_weights["swarm"]
        
        if self.behavior_weights["patrol"] > 0:
            patrol_vector = self.calculate_patrol_vector(dt)
            final_velocity += patrol_vector * self.behavior_weights["patrol"]
        
        if self.behavior_weights["intercept"] > 0:
            intercept_vector = self.calculate_intercept_vector()
            final_velocity += intercept_vector * self.behavior_weights["intercept"]
        
        if self.behavior_weights["evade"] > 0:
            evade_vector = self.calculate_evade_vector()
            final_velocity += evade_vector * self.behavior_weights["evade"]
        
        if self.behavior_weights["avoid_asteroids"] > 0:
            avoid_vector = self.calculate_asteroid_avoidance_vector()
            final_velocity += avoid_vector * self.behavior_weights["avoid_asteroids"]
        
        # Normalize and apply speed limits
        if final_velocity.magnitude() > 0:
            final_velocity = final_velocity.normalize() * min(final_velocity.magnitude(), self.max_speed)
            self.velocity = final_velocity
        
        # Always update angle for smooth visual rotation
        # Use time dilation factor to smooth the rotation during slow motion
        if final_velocity.magnitude() > 0:
            target_angle = math.atan2(self.velocity.y, self.velocity.x)
            
            # Smooth rotation based on time dilation
            if hasattr(self, 'time_dilation_factor'):
                # Faster rotation when time is dilated (slow motion) - 50% of original speed
                rotation_speed = 2.5 * (1.0 / max(self.time_dilation_factor, 0.1))
                
                # Calculate angle difference
                angle_diff = target_angle - self.angle
                
                # Normalize angle difference to [-π, π]
                while angle_diff > math.pi:
                    angle_diff -= 2 * math.pi
                while angle_diff < -math.pi:
                    angle_diff += 2 * math.pi
                
                # Smooth interpolation towards target angle
                self.angle += angle_diff * rotation_speed * dt
            else:
                # Fallback to direct angle update
                self.angle = target_angle
    
    def calculate_seek_vector(self):
        """Calculate vector to move toward player"""
        direction = self.player_position - self.position
        if direction.magnitude() > 0:
            return direction.normalize() * self.speed
        return Vector2D(0, 0)
    
    def calculate_flee_vector(self):
        """Calculate vector to move away from player"""
        direction = self.position - self.player_position
        if direction.magnitude() > 0:
            return direction.normalize() * self.speed
        return Vector2D(0, 0)
    
    def calculate_flank_vector(self):
        """Calculate vector to flanking position"""
        # Calculate perpendicular positions to flank the player
        player_angle = math.atan2(self.player_velocity.y, self.player_velocity.x)
        flank_angle = player_angle + math.pi/2  # 90 degrees perpendicular
        
        # Choose the closer flanking position
        flank_x = self.player_position.x + math.cos(flank_angle) * 150
        flank_y = self.player_position.y + math.sin(flank_angle) * 150
        
        direction = Vector2D(flank_x, flank_y) - self.position
        if direction.magnitude() > 0:
            return direction.normalize() * self.speed
        return Vector2D(0, 0)
    
    def calculate_swarm_vector(self):
        """Calculate vector for swarm coordination"""
        if len(self.other_ufos) == 0:
            return Vector2D(0, 0)
        
        # Calculate swarm center
        swarm_center = Vector2D(0, 0)
        for ufo in self.other_ufos:
            if ufo.active:
                swarm_center += ufo.position
        swarm_center = swarm_center * (1.0 / len(self.other_ufos))
        
        # Move toward swarm center but maintain some distance
        direction = swarm_center - self.position
        if direction.magnitude() > 0:
            return direction.normalize() * self.speed * 0.5
        return Vector2D(0, 0)
    
    def calculate_patrol_vector(self, dt):
        """Calculate random patrol movement"""
        # Simple oscillating movement
        self.oscillation += self.oscillation_speed * dt
        return Vector2D(self.direction * self.speed, math.sin(self.oscillation) * 50)
    
    def calculate_intercept_vector(self):
        """Calculate vector to intercept player"""
        # Predict where player will be in 1 second
        future_pos = self.player_position + self.player_velocity * 1.0
        direction = future_pos - self.position
        if direction.magnitude() > 0:
            return direction.normalize() * self.speed
        return Vector2D(0, 0)
    
    def calculate_evade_vector(self):
        """Calculate vector to evade player bullets"""
        evade_force = Vector2D(0, 0)
        for bullet in self.player_bullets:
            if bullet.active:
                bullet_distance = (self.position - bullet.position).magnitude()
                if bullet_distance < 100:
                    direction = self.position - bullet.position
                    if direction.magnitude() > 0:
                        evade_strength = (100 - bullet_distance) / 100
                        evade_force += direction.normalize() * evade_strength
        return evade_force.normalize() * self.speed if evade_force.magnitude() > 0 else Vector2D(0, 0)
    
    def calculate_asteroid_avoidance_vector(self):
        """Calculate vector to avoid asteroids"""
        avoid_force = Vector2D(0, 0)
        for asteroid in self.asteroids:
            if asteroid.active:
                asteroid_distance = (self.position - asteroid.position).magnitude()
                if asteroid_distance < self.asteroid_avoidance_distance:
                    # Calculate avoidance direction
                    direction = self.position - asteroid.position
                    if direction.magnitude() > 0:
                        # Stronger avoidance for closer asteroids
                        avoidance_strength = (self.asteroid_avoidance_distance - asteroid_distance) / self.asteroid_avoidance_distance
                        avoid_force += direction.normalize() * avoidance_strength * 2.0
        
        return avoid_force.normalize() * self.speed if avoid_force.magnitude() > 0 else Vector2D(0, 0)
    
    def update_shooting_behavior(self, dt):
        """Update shooting behavior and return whether to shoot"""
        self.shoot_timer += dt
        if self.shoot_timer >= self.shoot_interval:
            self.shoot_timer = 0
            return True
        return False
    

class Particle:
    def __init__(self, x, y, vx, vy, color, lifetime=1.0, size=2.0):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.lifetime = lifetime
        self.max_lifetime = lifetime
        self.size = size
        self.active = True
    
    def update(self, dt):
        if not self.active:
            return
            
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.lifetime -= dt
        
        # Fade out over time
        self.lifetime = max(0, self.lifetime)
        
        if self.lifetime <= 0:
            self.active = False
    
    def draw(self, screen):
        if not self.active:
            return
            
        # Calculate alpha based on remaining lifetime
        alpha = int(255 * (self.lifetime / self.max_lifetime))
        alpha = max(0, min(255, alpha))
        
        # Create color with alpha
        color_with_alpha = (*self.color, alpha)
        
        # Draw particle (ensure minimum size of 1 pixel)
        radius = max(1, int(self.size))
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), radius)

class ExplosionSystem:
    def __init__(self):
        self.particles = []
    
    def add_explosion(self, x, y, num_particles=50, color=(255, 255, 0), asteroid_size=None, is_ufo=False):
        for _ in range(num_particles):
            # Random spawn position within diameter based on asteroid size
            if asteroid_size is not None:
                if asteroid_size <= 7:
                    # Size 7 and smaller: spawn from one point
                    spawn_x = x
                    spawn_y = y
                else:
                    # Size 8 and 9: spawn within diameter
                    spawn_radius = asteroid_size * 2  # Diameter increases with asteroid size
                    spawn_angle = random.uniform(0, 2 * math.pi)
                    spawn_distance = random.uniform(0, spawn_radius)
                    spawn_x = x + math.cos(spawn_angle) * spawn_distance
                    spawn_y = y + math.sin(spawn_angle) * spawn_distance
            else:
                spawn_x = x
                spawn_y = y
            
            # Random velocity in all directions
            angle = random.uniform(0, 2 * math.pi)
            
            if asteroid_size is not None:
                # New asteroid particle speed formula
                if asteroid_size == 1:
                    base_speed = 50
                elif asteroid_size == 5:
                    base_speed = 100
                elif asteroid_size == 9:
                    base_speed = 150
                else:
                    # Interpolate for other sizes
                    if asteroid_size < 5:
                        base_speed = 50 + ((asteroid_size - 1) / 4) * 50  # 50 to 100
                    else:
                        base_speed = 100 + ((asteroid_size - 5) / 4) * 50  # 100 to 150
                
                speed_multiplier = random.uniform(0.5, 1.5)  # ±50% variation (100% additional randomization)
                speed = base_speed * speed_multiplier
            elif is_ufo:
                # UFO explosion particles - 200% velocity increase
                speed = random.uniform(50, 300) * random.uniform(0.5, 1.5)  # 200% increase from base
            else:
                # Default speed for non-asteroid explosions (with 100% additional randomization)
                speed = random.uniform(25, 100) * random.uniform(0.5, 1.5)  # ±50% variation
            
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            
            # Random particle properties
            particle_color = (
                random.randint(max(0, color[0] - 50), min(255, color[0] + 50)),
                random.randint(max(0, color[1] - 50), min(255, color[1] + 50)),
                random.randint(max(0, color[2] - 50), min(255, color[2] + 50))
            )
            
            if asteroid_size is not None:
                # New asteroid particle lifetime formula
                base_lifetime = asteroid_size * 0.2  # asteroid size x 0.2 seconds
                lifetime_multiplier = random.uniform(0.75, 1.00)
                lifetime = base_lifetime * lifetime_multiplier
                
                # New asteroid particle size formula
                if asteroid_size == 1:
                    size_base = 1.0
                elif asteroid_size == 5:
                    size_base = 2.0
                elif asteroid_size == 9:
                    size_base = 4.0
                else:
                    # Interpolate for other sizes
                    if asteroid_size < 5:
                        size_base = 1.0 + ((asteroid_size - 1) / 4) * 1.0  # 1 to 2
                    else:
                        size_base = 2.0 + ((asteroid_size - 5) / 4) * 2.0  # 2 to 4
                
                size_random = random.uniform(0.75, 1.0)  # 0.75-1.0 multiplier
                size = size_base * size_random
            else:
                # Default properties for non-asteroid explosions
                base_lifetime = random.uniform(0.5, 1.5)
                lifetime = base_lifetime * random.uniform(0.8, 1.2)  # ±20% variation
                size = random.uniform(1.0, 1.5)  # UFO explosion size
            
            particle = Particle(spawn_x, spawn_y, vx, vy, particle_color, lifetime, size)
            self.particles.append(particle)
    
    def add_rainbow_explosion(self, x, y, num_particles=200):
        """Add rainbow color cycling particles for player death"""
        for _ in range(num_particles):
            # Random velocity in all directions
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(50, 600)  # Increased range for 100% additional randomization
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            
            # Rainbow color cycling
            hue = random.uniform(0, 360)  # Random hue
            # Convert HSV to RGB for rainbow effect
            import colorsys
            rgb = colorsys.hsv_to_rgb(hue / 360.0, 1.0, 1.0)
            particle_color = (int(rgb[0] * 255), int(rgb[1] * 255), int(rgb[2] * 255))
            
            # Longer lifetime for dramatic effect
            lifetime = random.uniform(2.0, 4.0)
            size = random.uniform(1.5, 2.0)  # Player death size range
            
            particle = Particle(x, y, vx, vy, particle_color, lifetime, size)
            self.particles.append(particle)
    
    def add_ship_explosion(self, x, y, num_particles=150):
        """Add a ship explosion with 80% bright yellow and 20% white with various brightnesses"""
        for _ in range(num_particles):
            # Random velocity in all directions
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(75, 300)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            
            # 80% bright yellow, 20% white with various brightnesses
            if random.random() < 0.8:  # 80% chance for yellow
                # Bright yellow with various brightnesses
                brightness = random.uniform(0.7, 1.0)  # 70% to 100% brightness
                color = (
                    int(255 * brightness),  # Red component
                    int(255 * brightness),  # Green component
                    int(50 * brightness)    # Blue component (slight blue for yellow)
                )
            else:  # 20% chance for white
                # White with various brightnesses
                brightness = random.uniform(0.6, 1.0)  # 60% to 100% brightness
                color = (
                    int(255 * brightness),  # Red component
                    int(255 * brightness),  # Green component
                    int(255 * brightness)   # Blue component
                )
            
            # Random particle properties
            lifetime = random.uniform(1.2, 2.5)
            size = random.uniform(1.25, 3.5)  # Half as big as before
            
            particle = Particle(x, y, vx, vy, color, lifetime, size)
            self.particles.append(particle)
    
    def update(self, dt):
        for particle in self.particles[:]:
            particle.update(dt)
            if not particle.active:
                self.particles.remove(particle)
    
    def draw(self, screen):
        for particle in self.particles:
            particle.draw(screen)

class EnhancedMusicPlayer:
    """An enhanced music player with dual channels, reverb, and speed control."""
    
    def __init__(self, sample_rate: int = 44100):
        """Initialize the enhanced music player."""
        pygame.mixer.pre_init(frequency=sample_rate, size=-16, channels=2, buffer=1024)
        pygame.mixer.init()
        self.sample_rate = sample_rate
        self.is_playing = False
        self.current_thread = None
        
    def apply_reverb(self, wave: np.ndarray, reverb_amount: float = 0.3, delay_samples: int = 2205) -> np.ndarray:
        """Apply enhanced reverb effect with multiple delays and feedback."""
        if reverb_amount <= 0:
            return wave
        
        result = wave.copy()
        
        # Multiple reverb delays for richer effect
        delays = [delay_samples, delay_samples * 2, delay_samples * 3, delay_samples * 4]
        feedbacks = [reverb_amount, reverb_amount * 0.7, reverb_amount * 0.5, reverb_amount * 0.3]
        
        for delay, feedback in zip(delays, feedbacks):
            if len(wave) > delay:
                delayed = np.zeros_like(wave)
                delayed[delay:] = wave[:-delay] * feedback
                result += delayed
        
        # Add some high-frequency rolloff for more realistic reverb
        # Simple low-pass filter effect
        if len(result) > 1:
            for i in range(1, len(result)):
                result[i] = result[i] * 0.9 + result[i-1] * 0.1
        
        return result
    
    def generate_tone(self, frequency: float, duration: float, volume: float = 0.5, 
                     wave_type: str = "sine", harmonics: List[float] = None, 
                     reverb_amount: float = 0.0) -> pygame.mixer.Sound:
        """Generate a tone with different wave types, harmonics, and reverb."""
        # Extend duration to allow reverb to fully decay
        extended_duration = duration + (reverb_amount * 0.2)  # Add reverb tail time
        frames = int(extended_duration * self.sample_rate)
        
        # Create time array
        t = np.linspace(0, extended_duration, frames, False)
        
        # Generate base wave
        if wave_type == "sine":
            wave = np.sin(2 * np.pi * frequency * t)
        elif wave_type == "square":
            wave = np.sign(np.sin(2 * np.pi * frequency * t))
        elif wave_type == "sawtooth":
            wave = 2 * (frequency * t - np.floor(frequency * t + 0.5))
        elif wave_type == "triangle":
            wave = 2 * np.abs(2 * (frequency * t - np.floor(frequency * t + 0.5))) - 1
        else:
            wave = np.sin(2 * np.pi * frequency * t)
        
        # Add harmonics if specified
        if harmonics:
            for i, harmonic_amp in enumerate(harmonics, 1):
                if wave_type == "sine":
                    wave += harmonic_amp * np.sin(2 * np.pi * frequency * i * t)
                elif wave_type == "triangle":
                    wave += harmonic_amp * (2 * np.abs(2 * (frequency * i * t - np.floor(frequency * i * t + 0.5))) - 1)
        
        # Apply envelope to avoid clicks
        envelope = np.ones(frames)
        # Fade in
        fade_frames = int(0.01 * self.sample_rate)  # 10ms fade in
        if fade_frames > 0:
            envelope[:fade_frames] = np.linspace(0, 1, fade_frames)
        
        # Main note envelope - ends at original duration
        main_note_frames = int(duration * self.sample_rate)
        if main_note_frames < frames:
            # Fade out the main note
            fade_out_frames = int(0.05 * self.sample_rate)  # 50ms fade out
            if fade_out_frames > 0 and main_note_frames > fade_out_frames:
                envelope[main_note_frames - fade_out_frames:main_note_frames] = np.linspace(1, 0, fade_out_frames)
                envelope[main_note_frames:] = 0  # Silence after main note
            else:
                envelope[main_note_frames:] = 0
        else:
            # Fade out at the end
            if fade_frames > 0:
                envelope[-fade_frames:] = np.linspace(1, 0, fade_frames)
        
        wave *= envelope
        
        # Apply reverb
        if reverb_amount > 0:
            wave = self.apply_reverb(wave, reverb_amount)
        
        # Normalize and apply volume
        max_amplitude = np.max(np.abs(wave))
        if max_amplitude > 0:
            wave = wave / max_amplitude * volume
        else:
            wave = wave * volume
        
        # Convert to 16-bit stereo
        wave_16bit = (wave * 32767).astype(np.int16)
        stereo_wave = np.column_stack((wave_16bit, wave_16bit))
        
        return pygame.sndarray.make_sound(stereo_wave)
    
    def play_dual_channel_sequence(self, left_sequence: List[Tuple], right_sequence: List[Tuple], 
                                 tempo: float = 120.0):
        """Play two sequences simultaneously on left and right channels."""
        self.is_playing = True
        
        def play_thread():
            beat_duration = 60.0 / tempo
            
            # Create combined sequence with both channels
            max_length = max(len(left_sequence), len(right_sequence))
            
            for i in range(max_length):
                if not self.is_playing:
                    break
                
                # Get events from both channels (or silence if one is shorter)
                left_event = left_sequence[i] if i < len(left_sequence) else (0, 0.1, 0.0)
                right_event = right_sequence[i] if i < len(right_sequence) else (0, 0.1, 0.0)
                
                # Process left channel
                if len(left_event) >= 3:
                    freq_l, dur_l, vol_l = left_event[:3]
                    wave_type_l = left_event[3] if len(left_event) > 3 else "sine"
                    harmonics_l = left_event[4] if len(left_event) > 4 else None
                    reverb_l = left_event[5] if len(left_event) > 5 else 0.0
                else:
                    freq_l, dur_l, vol_l = left_event[0], left_event[1], 0.0
                    wave_type_l, harmonics_l, reverb_l = "sine", None, 0.0
                
                # Process right channel
                if len(right_event) >= 3:
                    freq_r, dur_r, vol_r = right_event[:3]
                    wave_type_r = right_event[3] if len(right_event) > 3 else "sine"
                    harmonics_r = right_event[4] if len(right_event) > 4 else None
                    reverb_r = right_event[5] if len(right_event) > 5 else 0.0
                else:
                    freq_r, dur_r, vol_r = right_event[0], right_event[1], 0.0
                    wave_type_r, harmonics_r, reverb_r = "sine", None, 0.0
                
                # Use the longer duration
                note_duration = max(dur_l, dur_r) * beat_duration
                
                # Calculate extended duration for reverb
                max_reverb = max(reverb_l, reverb_r)
                extended_duration = note_duration + (max_reverb * 0.2)
                
                # Generate sounds for both channels
                if freq_l > 0:
                    sound_l = self.generate_tone(freq_l, note_duration, vol_l, wave_type_l, harmonics_l, reverb_l)
                    sound_l.play()
                
                if freq_r > 0:
                    sound_r = self.generate_tone(freq_r, note_duration, vol_r, wave_type_r, harmonics_r, reverb_r)
                    sound_r.play()
                
                time.sleep(extended_duration)
            
            self.is_playing = False
        
        self.current_thread = threading.Thread(target=play_thread)
        self.current_thread.start()
    
    def stop(self):
        """Stop the current playback."""
        self.is_playing = False
        pygame.mixer.stop()
        if self.current_thread:
            self.current_thread.join()
    
    def close(self):
        """Close the player and cleanup resources."""
        self.stop()
        try:
            pygame.mixer.quit()
        except:
            pass  # Ignore if mixer already quit
    
    def __del__(self):
        """Cleanup when the object is destroyed."""
        try:
            self.close()
        except:
            pass  # Ignore cleanup errors


class EnhancedAAGACAStyles:
    """Enhanced AAGACA styles with dual channels and effects."""
    
    # Musical note frequencies (Hz)
    NOTES = {
        'A': 440.00,  # A4
        'B': 493.88,  # B4
        'C': 523.25,  # C5
        'D': 587.33,  # D5
        'E': 659.25,  # E5
        'F': 698.46,  # F5
        'G': 391.99,  # G4 (down one octave)
    }
    
    @classmethod
    def get_note_frequency(cls, note_name: str) -> float:
        """Get frequency for a note name."""
        return cls.NOTES.get(note_name.upper(), 440.00)
    
    @classmethod
    def get_base_sequence(cls) -> List[Tuple]:
        """Get the base AAGACA sequence timing."""
        return [
            # A - full beat
            (cls.get_note_frequency('A'), 1.0, 0.1),
            # Quarter beat rest
            (0, 0.25, 0.0),
            # A - full beat
            (cls.get_note_frequency('A'), 1.0, 0.1),
            # Quarter beat rest
            (0, 0.25, 0.0),
            # G - half beat
            (cls.get_note_frequency('G'), 0.5, 0.1),
            # Quarter beat rest
            (0, 0.25, 0.0),
            # A - half beat
            (cls.get_note_frequency('A'), 0.5, 0.1),
            # Quarter beat rest
            (0, 0.25, 0.0),
            # Quarter beat rest (before C)
            (0, 0.25, 0.0),
            # C - 2 beats
            (cls.get_note_frequency('C'), 2.0, 0.1),
            # A - 1.5 beats
            (cls.get_note_frequency('A'), 1.5, 0.1),
        ]
    
    @classmethod
    def get_crystal_style(cls) -> List[Tuple]:
        """Crystal style - triangle waves with crystal-like harmonics and moderate reverb."""
        sequence = cls.get_base_sequence()
        return [(freq, dur, vol * 0.6, "triangle", [0.2, 0.15, 0.1, 0.05, 0.03], 0.3) if freq > 0 else (freq, dur, vol) 
                for freq, dur, vol in sequence]
    
    @classmethod
    def get_ambient_style(cls) -> List[Tuple]:
        """Ambient style - very soft, pure sine waves with moderate reverb."""
        sequence = cls.get_base_sequence()
        return [(freq, dur, vol * 0.6, "sine", None, 0.4) if freq > 0 else (freq, dur, vol) 
                for freq, dur, vol in sequence]
    
    @classmethod
    def get_dual_crystal_ambient(cls) -> Tuple[List[Tuple], List[Tuple]]:
        """Get Crystal and Ambient styles for dual-channel playback."""
        crystal = cls.get_crystal_style()
        ambient = cls.get_ambient_style()
        return crystal, ambient


class StarField:
    def __init__(self, num_stars=200):
        self.stars = []
        self.num_stars = num_stars
        self.last_speed_factor = 0.0  # For smoothing
        self.explosion_mode = False
        self.explosion_timer = 0.0
        self.explosion_duration = 2.0
        self.screen_center_x = 0
        self.screen_center_y = 0
        # Don't generate stars here - will be generated when screen size is known
    
    def generate_stars(self, screen_width, screen_height):
        self.stars = []
        self.screen_center_x = screen_width // 2
        self.screen_center_y = screen_height // 2
        for _ in range(self.num_stars):
            star = {
                'x': random.uniform(0, screen_width),
                'y': random.uniform(0, screen_height),
                'speed': random.uniform(0.5, 3.0),
                'brightness': random.uniform(0.3, 1.0),
                'size': random.uniform(0.5, 2.0),
                'stationary_brightness': random.randint(20, 150),  # Pre-calculated stationary brightness
                'explosion_speed': random.uniform(400, 1000)  # Speed for explosion effect (doubled)
            }
            self.stars.append(star)
    
    def start_explosion(self, screen_width, screen_height):
        """Start the star explosion effect"""
        self.explosion_mode = True
        self.explosion_timer = 0.0
        self.screen_center_x = screen_width // 2
        self.screen_center_y = screen_height // 2
    
    def update(self, ship_velocity, screen_width, screen_height, dt=0.016):
        if self.explosion_mode:
            # Update explosion timer
            self.explosion_timer += dt
            
            # Move stars outward from center during explosion
            for star in self.stars:
                # Calculate direction from center to star
                dx = star['x'] - self.screen_center_x
                dy = star['y'] - self.screen_center_y
                distance = math.sqrt(dx*dx + dy*dy)
                
                if distance > 0:  # Avoid division by zero
                    # Normalize direction vector
                    dx /= distance
                    dy /= distance
                    
                    # Move star outward with increasing speed
                    explosion_speed = star['explosion_speed'] * (1.0 + self.explosion_timer * 4.0)  # Accelerating (doubled)
                    star['x'] += dx * explosion_speed * dt
                    star['y'] += dy * explosion_speed * dt
        else:
            # Normal star movement
            speed_factor = min(ship_velocity.magnitude() / 100.0, 10.0)  # Cap at 10x speed for trails
            
            for star in self.stars:
                # Move stars opposite to ship movement
                star['x'] -= ship_velocity.x * star['speed'] * 0.01 * speed_factor
                star['y'] -= ship_velocity.y * star['speed'] * 0.01 * speed_factor
                
                # Wrap around screen
                if star['x'] < 0:
                    star['x'] = screen_width
                elif star['x'] > screen_width:
                    star['x'] = 0
                if star['y'] < 0:
                    star['y'] = screen_height
                elif star['y'] > screen_height:
                    star['y'] = 0
    
    def draw(self, screen, ship_velocity):
        # Handle case where ship_velocity might be None
        if ship_velocity is None:
            ship_velocity = Vector2D(0, 0)
            
        for star in self.stars:
            if self.explosion_mode:
                # During explosion: bright stars with no trails
                brightness = int(255 * star['brightness'] * 1.5)  # Brighter during explosion
                brightness = max(0, min(255, brightness))
                color = (brightness, brightness, brightness)
            else:
                # Normal star behavior
                # Calculate brightness based on speed with smoothing
                raw_speed_factor = min(ship_velocity.magnitude() / 100.0, 10.0)  # Match update method cap
                # Smooth the speed factor to reduce flickering
                speed_factor = self.last_speed_factor * 0.8 + raw_speed_factor * 0.2
                self.last_speed_factor = speed_factor
                
                # Base brightness calculation with minimum visibility
                if speed_factor > 0.1:  # Threshold to switch between stationary and moving
                    # When moving: brightness scales with speed
                    brightness = int(255 * star['brightness'] * min(speed_factor, 2.0))
                else:
                    # When stationary or very slow: use pre-calculated stable brightness
                    brightness = star['stationary_brightness']
                
                # Clamp brightness to valid range
                brightness = max(0, min(255, brightness))
                color = (brightness, brightness, brightness)
                
                # Draw star with trail effect (only when going 42% of max speed and not in explosion mode)
                if speed_factor >= 4.2:  # 42% of Player Speed % (420 units/second)
                    # Draw trail - starts at 42% Player Speed, max length at 100% Player Speed
                    # Scale from 0 to 30 pixels as speed goes from 4.2 to 10.0 speed_factor
                    trail_progress = min((speed_factor - 4.2) / 5.8, 1.0)  # 0 to 1 as speed goes from 4.2 to 10.0
                    trail_length = trail_progress * 30  # 0 to 30 pixels
                    trail_x = star['x'] + ship_velocity.x * star['speed'] * 0.01 * trail_length
                    trail_y = star['y'] + ship_velocity.y * star['speed'] * 0.01 * trail_length
                    trail_brightness = max(0, min(255, brightness//3))
                    # Electric blue hyperspace trail (Star Wars style)
                    trail_color = (trail_brightness//4, trail_brightness//2, trail_brightness)
                    pygame.draw.line(screen, trail_color, 
                                   (star['x'], star['y']), (trail_x, trail_y), 1)
            
            # Draw star
            pygame.draw.circle(screen, color, (int(star['x']), int(star['y'])), max(1, int(star['size'])))

class Game:
    def __init__(self):
        if RESIZABLE:
            self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)
        else:
            self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("C H U C K S T A R O I D S")
        self.clock = pygame.time.Clock()
        self.running = False
        self.score = 0
        self.lives = 3
        self.level = 1
        self.game_state = "waiting"  # waiting, playing, game_over, paused
        
        # Debug mode
        self.debug_mode = False
        
        # Ability break system
        self.ability_breaking = False
        self.ability_break_count = 0
        self.ability_break_timer = 0.0
        self.ability_break_delay = 0.0
        
        # Level transition system
        self.level_transition_delay = 0.0
        self.level_pause_timer = 0.0
        self.level_pause_duration = 2.0  # Changed to 2 seconds
        self.level_flash_timer = 0.0
        self.level_flash_duration = 2.0  # Match pause duration
        self.level_flash_count = 0
        self.pending_level = None
        
        # Screen shake system
        self.screen_shake_x = 0.0
        self.screen_shake_y = 0.0
        self.screen_shake_timer = 0.0
        self.screen_shake_intensity = 0.0
        
        # Time advance system for ability blasts
        self.time_advance_timer = 0.0
        
        # Window resizing
        self.current_width = SCREEN_WIDTH
        self.current_height = SCREEN_HEIGHT
        
        # Star explosion effect
        self.star_explosion_active = False
        self.star_explosion_timer = 0.0
        self.star_explosion_duration = 2.0  # 2 seconds
        
        # Game objects
        self.ship = None
        self.bullets = []
        self.asteroids = []
        self.ufos = []
        self.ufo_bullets = []
        
        # Star field
        self.star_field = StarField(200)
        self.star_field.generate_stars(self.current_width, self.current_height)
        
        # Explosion system
        self.explosions = ExplosionSystem()
        
        # Input handling
        self.keys_pressed = set()
        
        # Spawn timer
        self.ufo_spawn_timer = 0
        self.ufo_spawn_interval = 1.0  # 1 second between UFO spawns
        self.initial_ufo_timer = 5.0  # 5 seconds before first UFOs spawn
        self.ufos_to_spawn = 0  # Number of UFOs to spawn this wave
        self.ufo_spawn_delay = 0  # Delay between individual UFO spawns
        self.ufo_spawn_types = None  # Specific types for level 1, None for others
        self.ufo_spawn_corner = None  # Random corner for this level
        self.ufo_mass_spawn = False  # 10% chance for mass spawn from all corners
        
        # Spinning trick message
        self.spinning_trick_timer = 0.0
        self.show_spinning_trick = False
        
        # Interstellar message
        self.interstellar_timer = 0.0
        self.show_interstellar = False
        
        # Screen shake variables
        self.screen_shake_intensity = 0
        self.screen_shake_duration = 0
        self.screen_shake_timer = 0
        self.game_over_timer = 0  # Timer for game over state
        
        # Time dilation system (Superhot-style)
        self.time_dilation_factor = 1.0  # 1.0 = normal time, 0.01 = 100x slower
        
        # Music system
        self.music_player = None
        self.music_playing = False
        self.title_music_played = False
        
    def trigger_screen_shake(self, intensity, duration, time_dilation_factor=1.0):
        """Trigger screen shake effect"""
        # Don't trigger screen shake during game over state (except for player death)
        if self.game_state == "game_over" and self.game_over_timer > 0.1:
            return
        self.screen_shake_intensity = intensity
        self.screen_shake_duration = duration
        # Apply time dilation to duration (longer shake when time is slowed)
        self.screen_shake_timer = duration / max(time_dilation_factor, 0.01)
    
    def calculate_time_dilation(self, dt):
        """Calculate time dilation factor based on ship movement and shooting"""
        if not self.ship:
            self.time_dilation_factor = 1.0
            return
        
        # Get player speed magnitude
        player_speed = self.ship.velocity.magnitude()
        
        # Check for shooting action
        is_shooting = self.ship.shoot_timer > 0 or pygame.K_SPACE in self.keys_pressed
        
        # Calculate shooting-based forward movement
        shooting_forward_movement = 0.0
        if is_shooting:
            # Shooting provides forward movement equivalent to moving at 500 speed units
            shooting_forward_movement = 500.0
        
        # Total effective movement = actual movement + shooting forward movement
        total_movement = player_speed + shooting_forward_movement
        
        # Calculate time dilation based on total movement
        # Map movement to time dilation (0.01x to 1.0x)
        # 0 movement = 0.01x (nearly frozen)
        # 1000+ movement = 1.0x (normal speed)
        max_speed = 1000.0
        speed_ratio = min(total_movement / max_speed, 1.0)
        target_dilation = 0.01 + (1.0 - 0.01) * speed_ratio
        
        # Smooth transition to target dilation
        if target_dilation > self.time_dilation_factor:
            # Accelerating: smooth interpolation
            dilation_diff = target_dilation - self.time_dilation_factor
            self.time_dilation_factor += dilation_diff * 2.0 * dt  # Fast acceleration
        else:
            # Decaying: use ship's decay rate for consistency
            current_speed = self.ship.velocity.magnitude()
            speed_percent = current_speed / 1000.0 * 100  # Convert to percentage
            
            # Use much faster decay when speed is below 10%
            if speed_percent < 10.0:
                # Much faster decay to quickly reach 0%
                decay_rate = self.ship.speed_decay_rate ** 4  # 4th power for very fast decay
            else:
                decay_rate = self.ship.speed_decay_rate
            
            self.time_dilation_factor *= decay_rate ** dt
        
        # Clamp to valid range (0.01x to 1.0x)
        self.time_dilation_factor = max(0.01, min(1.0, self.time_dilation_factor))
    
    def apply_shake_offset(self, x, y, shake_x, shake_y):
        """Apply screen shake offset to coordinates"""
        return x + shake_x, y + shake_y
    
    def init_music_player(self):
        """Initialize the music player if not already initialized"""
        if self.music_player is None:
            try:
                self.music_player = EnhancedMusicPlayer()
            except Exception as e:
                get_logger().warning(f"Failed to initialize music player: {e}")
                self.music_player = None
    
    def play_title_music(self):
        """Play music on the title screen"""
        if not self.title_music_played and self.game_state == "waiting":
            self.init_music_player()
            if self.music_player and not self.music_playing:
                try:
                    crystal_seq, ambient_seq = EnhancedAAGACAStyles.get_dual_crystal_ambient()
                    self.music_player.play_dual_channel_sequence(crystal_seq, ambient_seq, tempo=180)
                    self.music_playing = True
                    self.title_music_played = True
                except Exception as e:
                    get_logger().warning(f"Failed to play title music: {e}")
    
    def play_level_music(self):
        """Play music on level change with 10% chance"""
        if random.random() < 0.1:  # 10% chance
            self.init_music_player()
            if self.music_player and not self.music_playing:
                try:
                    crystal_seq, ambient_seq = EnhancedAAGACAStyles.get_dual_crystal_ambient()
                    self.music_player.play_dual_channel_sequence(crystal_seq, ambient_seq, tempo=180)
                    self.music_playing = True
                except Exception as e:
                    get_logger().warning(f"Failed to play level music: {e}")
    
    def stop_music(self):
        """Stop any currently playing music"""
        if self.music_player and self.music_playing:
            try:
                self.music_player.stop()
                self.music_playing = False
            except Exception as e:
                get_logger().warning(f"Failed to stop music: {e}")
    
    def init_ship(self):
        self.ship = Ship(self.current_width // 2, self.current_height // 2)
        self.ship.invulnerable = True
        self.ship.invulnerable_time = 3.0
    
    def spawn_asteroids(self, count=None):
        # Updated asteroid spawning system
        large_sizes = [9, 8, 7]  # XXXL, XXL, XL
        medium_sizes = [1, 2, 3, 4, 5, 6, 7]  # Sizes 1-7 for random medium asteroid
        all_sizes = [1, 2, 3, 4, 5, 6, 7, 8, 9]  # All sizes for additional asteroids
        
        # Spawn 1 random large asteroid (XXXL, XXL, or XL) on edge
        random_large = random.choice(large_sizes)
        x, y = self.get_edge_position()
        self.asteroids.append(Asteroid(x, y, random_large))
        
        # Spawn 1 random medium asteroid (sizes 1-7) on edge
        random_medium = random.choice(medium_sizes)
        x, y = self.get_edge_position()
        self.asteroids.append(Asteroid(x, y, random_medium))
        
        # Spawn additional asteroids based on level
        if self.level >= 2:
            # Calculate additional asteroids: ((level - 0.5, rounded down) - 1)
            additional_count = max(0, int(self.level - 0.5) - 1)
            for _ in range(additional_count):
                random_size = random.choice(all_sizes)
                x, y = self.get_edge_position()
                self.asteroids.append(Asteroid(x, y, random_size))
    
    def get_edge_position(self):
        # Spawn on edge of screen
        side = random.randint(0, 3)
        if side == 0:  # Top
            x = random.uniform(0, self.current_width)
            y = 0
        elif side == 1:  # Right
            x = self.current_width
            y = random.uniform(0, self.current_height)
        elif side == 2:  # Bottom
            x = random.uniform(0, self.current_width)
            y = self.current_height
        else:  # Left
            x = 0
            y = random.uniform(0, self.current_height)
        return x, y
    
    def spawn_ufo(self):
        side = random.randint(0, 1)
        if side == 0:  # Left
            x = 0
            y = random.uniform(0, self.current_height)
        else:  # Right
            x = self.current_width
            y = random.uniform(0, self.current_height)
        
        # Level-based personality selection with 50% deadly chance
        if random.random() < 0.5:
            personality = "deadly"
        else:
            if self.level == 1:
                # Level 1: 1 of each type (defensive for this spawn)
                personality = "defensive"
            elif self.level == 2:
                # Level 2: defensive only
                personality = "defensive"
            elif self.level == 3:
                # Level 3: random between aggressive and defensive
                personality = random.choice(["aggressive", "defensive"])
            elif self.level == 4:
                # Level 4: aggressive only
                personality = "aggressive"
            elif self.level == 5:
                # Level 5: random between all 4 types
                personality = random.choice(["aggressive", "defensive", "tactical", "swarm"])
            else:
                # Level 6+: random between all 4 types
                personality = random.choice(["aggressive", "defensive", "tactical", "swarm"])
        
        self.ufos.append(AdvancedUFO(x, y, personality))
    
    def spawn_ufo_from_corner(self):
        # Pick a random corner
        corners = [
            (0, 0),  # Top-left
            (self.current_width, 0),  # Top-right
            (0, self.current_height),  # Bottom-left
            (self.current_width, self.current_height)  # Bottom-right
        ]
        x, y = random.choice(corners)
        
        # Level-based personality selection with 50% deadly chance
        if random.random() < 0.5:
            personality = "deadly"
        else:
            if self.level == 1:
                # Level 1: 1 of each type (defensive for this spawn)
                personality = "defensive"
            elif self.level == 2:
                # Level 2: defensive only
                personality = "defensive"
            elif self.level == 3:
                # Level 3: random between aggressive and defensive
                personality = random.choice(["aggressive", "defensive"])
            elif self.level == 4:
                # Level 4: aggressive only
                personality = "aggressive"
            elif self.level == 5:
                # Level 5: random between all 4 types
                personality = random.choice(["aggressive", "defensive", "tactical", "swarm"])
            else:
                # Level 6+: random between all 4 types
                personality = random.choice(["aggressive", "defensive", "tactical", "swarm"])
        
        self.ufos.append(AdvancedUFO(x, y, personality))
    
    def spawn_ufo_with_personality(self, personality):
        """Spawn a UFO with a specific personality from a random corner"""
        # Pick a random corner
        corners = [
            (0, 0),  # Top-left
            (self.current_width, 0),  # Top-right
            (0, self.current_height),  # Bottom-left
            (self.current_width, self.current_height)  # Bottom-right
        ]
        x, y = random.choice(corners)
        self.ufos.append(AdvancedUFO(x, y, personality))
    
    def spawn_ufo_with_personality_at_corner(self, personality, corner):
        """Spawn a UFO with a specific personality at a specific corner"""
        x, y = corner
        self.ufos.append(AdvancedUFO(x, y, personality))
    
    def spawn_ufo_from_selected_corner(self):
        """Spawn a UFO with random personality from the selected corner for this level"""
        x, y = self.ufo_spawn_corner
        
        # Level-based personality selection with 50% deadly chance
        if random.random() < 0.5:
            personality = "deadly"
        else:
            if self.level == 2:
                # Level 2: defensive only
                personality = "defensive"
            elif self.level == 3:
                # Level 3: random between aggressive and defensive
                personality = random.choice(["aggressive", "defensive"])
            elif self.level == 4:
                # Level 4: aggressive only
                personality = "aggressive"
            elif self.level == 5:
                # Level 5: random between all 4 types
                personality = random.choice(["aggressive", "defensive", "tactical", "swarm"])
            else:
                # Level 6+: random between all 4 types
                personality = random.choice(["aggressive", "defensive", "tactical", "swarm"])
        
        self.ufos.append(AdvancedUFO(x, y, personality))
    
    def spawn_all_ufos_mass(self):
        """Spawn all remaining UFOs at once from all corners"""
        corners = [
            (0, 0),  # Top-left
            (self.current_width, 0),  # Top-right
            (0, self.current_height),  # Bottom-left
            (self.current_width, self.current_height)  # Bottom-right
        ]
        
        for i in range(self.ufos_to_spawn):
            # Pick a random corner for each UFO
            x, y = random.choice(corners)
            
            # Level-based personality selection with 50% deadly chance
            if random.random() < 0.5:
                personality = "deadly"
            else:
                if self.level == 1:
                    # Level 1: Use specific types in order if available
                    if self.ufo_spawn_types and len(self.ufo_spawn_types) > 0:
                        personality = self.ufo_spawn_types.pop(0)
                    else:
                        personality = random.choice(["aggressive", "defensive", "tactical", "swarm"])
                elif self.level == 2:
                    # Level 2: defensive only
                    personality = "defensive"
                elif self.level == 3:
                    # Level 3: random between aggressive and defensive
                    personality = random.choice(["aggressive", "defensive"])
                elif self.level == 4:
                    # Level 4: aggressive only
                    personality = "aggressive"
                elif self.level == 5:
                    # Level 5: random between all 4 types
                    personality = random.choice(["aggressive", "defensive", "tactical", "swarm"])
                else:
                    # Level 6+: random between all 4 types
                    personality = random.choice(["aggressive", "defensive", "tactical", "swarm"])
            
            self.ufos.append(AdvancedUFO(x, y, personality))
    
    def handle_input(self, dt):
        # R key restart works at any time
        if pygame.K_r in self.keys_pressed:
            self.restart_game()
            return
            
        if self.game_state != "playing":
            return
            
        # Input handling uses normal time (not dilated) for responsive controls
        # Support both arrow keys and WASD
        left_rotate_pressed = pygame.K_LEFT in self.keys_pressed
        right_rotate_pressed = pygame.K_RIGHT in self.keys_pressed
        left_strafe_pressed = pygame.K_a in self.keys_pressed
        right_strafe_pressed = pygame.K_d in self.keys_pressed
        up_pressed = pygame.K_UP in self.keys_pressed or pygame.K_w in self.keys_pressed
        down_pressed = pygame.K_DOWN in self.keys_pressed or pygame.K_s in self.keys_pressed
        
        # Rotation (arrow keys only)
        if left_rotate_pressed:
            self.ship.rotate_left(dt)
            self.ship.is_spinning = True
        elif right_rotate_pressed:
            self.ship.rotate_right(dt)
            self.ship.is_spinning = True
        else:
            self.ship.is_spinning = False
            
        # Strafe (A and D keys)
        if left_strafe_pressed:
            self.ship.strafe_left(dt)
        elif right_strafe_pressed:
            self.ship.strafe_right(dt)
            
        # Thrust (W and S keys, or arrow keys)
        if up_pressed:
            self.ship.thrust(dt)
        elif down_pressed:
            self.ship.reverse_thrust(dt)
        else:
            self.ship.stop_thrust()
            
        if pygame.K_SPACE in self.keys_pressed:
            self.shoot_continuous()
        
        # Ability activation (Q, E, or B keys)
        if (pygame.K_q in self.keys_pressed or pygame.K_e in self.keys_pressed or pygame.K_b in self.keys_pressed):
            self.activate_ability()
        
        # Debug mode toggle (F1 key)
        if pygame.K_F1 in self.keys_pressed:
            self.debug_mode = not self.debug_mode
    
    def shoot(self):
        if len(self.bullets) < 20:  # Limit bullets (5x increase from 4)
            bullet_speed = 400
            angle = self.ship.angle
            # Add player velocity to bullet velocity
            vx = math.cos(angle) * bullet_speed + self.ship.velocity.x
            vy = math.sin(angle) * bullet_speed + self.ship.velocity.y
            # Spawn bullet slightly in front of the rocket
            bullet_x = self.ship.position.x + math.cos(angle) * 25
            bullet_y = self.ship.position.y + math.sin(angle) * 25
            bullet = Bullet(bullet_x, bullet_y, vx, vy, is_ufo_bullet=False, angle=angle)
            self.bullets.append(bullet)
    
    def shoot_continuous(self):
        # Check if enough time has passed since last shot
        if self.ship.shoot_timer <= 0 and len(self.bullets) < 40:  # 5x increased bullet limit
            bullet_speed = 400
            angle = self.ship.angle
            # Add player velocity to bullet velocity
            vx = math.cos(angle) * bullet_speed + self.ship.velocity.x
            vy = math.sin(angle) * bullet_speed + self.ship.velocity.y
            # Spawn bullet slightly in front of the rocket
            bullet_x = self.ship.position.x + math.cos(angle) * 25
            bullet_y = self.ship.position.y + math.sin(angle) * 25
            bullet = Bullet(bullet_x, bullet_y, vx, vy, is_ufo_bullet=False, angle=angle)
            self.bullets.append(bullet)
            self.ship.shoot_timer = self.ship.shoot_interval  # Reset timer
    
    def add_screen_shake(self, intensity, duration):
        """Add screen shake with random intensity (1-5/10) and specified duration"""
        self.screen_shake_intensity = intensity
        self.screen_shake_timer = duration
    
    def update_screen_shake(self, dt):
        """Update screen shake effect"""
        if self.screen_shake_timer > 0:
            self.screen_shake_timer -= dt
            # Random shake offset
            self.screen_shake_x = random.uniform(-self.screen_shake_intensity, self.screen_shake_intensity)
            self.screen_shake_y = random.uniform(-self.screen_shake_intensity, self.screen_shake_intensity)
        else:
            self.screen_shake_x = 0.0
            self.screen_shake_y = 0.0
    
    def perform_ability_break(self):
        """Perform one break in the ability sequence"""
        # Add screen shake with random intensity (1-5/10) and duration matching blast delay
        shake_intensity = random.uniform(1.0, 5.0)
        shake_duration = self.ability_break_delay  # Match the blast delay duration
        self.add_screen_shake(shake_intensity, shake_duration)
        
        # Simulate 2x player shots for time dilation effect
        # Player shots add 500 speed units, so 2x shots = 1000 speed units
        ability_shot_movement = 1000.0  # Equivalent to 2x player shots
        
        # Calculate time dilation based on current movement + ability shot movement
        if self.ship:
            player_speed = self.ship.velocity.magnitude()
            total_movement = player_speed + ability_shot_movement
            
            # Calculate time dilation (same as in calculate_time_dilation)
            max_speed = 1000.0
            speed_ratio = min(total_movement / max_speed, 1.0)
            target_dilation = 0.01 + (1.0 - 0.01) * speed_ratio
            
            # Apply the calculated time dilation
            self.time_dilation_factor = target_dilation
            
            # Set timer to restore normal time dilation after ability effect
            self.time_advance_timer = 0.1  # 0.1 seconds of ability time effect
        
        # Break all asteroids by 1 level using normal splitting logic
        for asteroid in self.asteroids[:]:
            if asteroid.active:
                if asteroid.size > 1:  # Can still break down
                    # Use normal asteroid splitting logic
                    new_asteroids = asteroid.split()
                    if new_asteroids:
                        # Add the new asteroids to the game
                        for new_asteroid in new_asteroids:
                            self.asteroids.append(new_asteroid)
                    
                    # Generate explosion particles (like normal asteroid hit)
                    self.explosions.add_explosion(asteroid.position.x, asteroid.position.y, 
                                                num_particles=20 + asteroid.size * 5, 
                                                color=(255, 255, 0), 
                                                asteroid_size=asteroid.size, is_ufo=False)
                    
                    # Add score (like normal asteroid hit)
                    self.score += asteroid.size * 50
                    
                    # Remove the original asteroid
                    asteroid.active = False
                    self.asteroids.remove(asteroid)
                else:
                    # Asteroid is destroyed - generate explosion and add score
                    self.explosions.add_explosion(asteroid.position.x, asteroid.position.y, 
                                                num_particles=20 + asteroid.size * 5, 
                                                color=(255, 255, 0), 
                                                asteroid_size=asteroid.size, is_ufo=False)
                    self.score += asteroid.size * 50
                    asteroid.active = False
                    self.asteroids.remove(asteroid)
        
        # Clear 30% of UFOs on each break (3 breaks = 90% total)
        if len(self.ufos) > 0:
            ufos_to_remove = max(1, math.ceil(len(self.ufos) * 0.3))
            ufos_removed = 0
            for ufo in self.ufos[:]:
                if ufos_removed >= ufos_to_remove:
                    break
                if ufo.active:
                    ufo.active = False
                    self.ufos.remove(ufo)
                    ufos_removed += 1

    def activate_ability(self):
        """Activate the asteroid breaking ability if ready"""
        if self.ship.ability_charges > 0 and not self.ship.ability_used and not self.ability_breaking:
            # Use one charge
            self.ship.ability_charges -= 1
            self.ship.ability_ready = self.ship.ability_charges > 0
            
            # Determine blast count based on charges used
            # 1 charge = 2 blasts, 2 charges = 4 blasts
            if self.ship.ability_charges == 0:  # Used 1 charge (had 1)
                self.ability_blast_count = 2
            else:  # Used 1 charge (had 2)
                self.ability_blast_count = 4
            
            # Start the break sequence
            self.ability_breaking = True
            self.ability_break_count = 0
            self.ability_break_timer = 0.0
            self.ability_break_delay = random.uniform(0.2, 0.42)
            
            # Generate particles for all objects on first break
            total_asteroids = sum(1 for asteroid in self.asteroids if asteroid.active)
            total_ufos = sum(1 for ufo in self.ufos if ufo.active)
            total_objects = total_asteroids + total_ufos
            
            if total_objects > 0:
                particles_per_object = 20  # Fixed 20 particles per blast
                
                # Generate particles for all asteroids
                for asteroid in self.asteroids[:]:
                    if asteroid.active:
                        self.explosions.add_explosion(asteroid.position.x, asteroid.position.y, 
                                                    num_particles=particles_per_object, color=(255, 255, 0), 
                                                    asteroid_size=asteroid.size, is_ufo=False)
                
                # Generate particles for all UFOs
                for ufo in self.ufos[:]:
                    if ufo.active:
                        self.explosions.add_explosion(ufo.position.x, ufo.position.y, 
                                                    num_particles=particles_per_object, color=(255, 100, 100), 
                                                    asteroid_size=None, is_ufo=True)
            
            # Generate 200 purple and pink particles from player
            for _ in range(200):
                angle = random.uniform(0, 2 * math.pi)
                speed = random.uniform(100, 400)
                vx = math.cos(angle) * speed
                vy = math.sin(angle) * speed
                
                # Randomly choose between purple and pink hues
                if random.random() < 0.5:
                    # Purple hue
                    color = (random.randint(100, 200), 0, random.randint(200, 255))
                else:
                    # Pink hue
                    color = (random.randint(200, 255), random.randint(20, 100), random.randint(100, 200))
                
                lifetime = random.uniform(1.0, 2.0)
                size = 1.5
                particle = Particle(self.ship.position.x, self.ship.position.y, vx, vy, color, lifetime, size)
                self.explosions.particles.append(particle)
            
    
    def check_collisions(self):
        # Bullet vs Asteroid (with screen wrapping)
        for bullet in self.bullets[:]:
            if not bullet.active:
                continue
            for asteroid in self.asteroids[:]:
                if not asteroid.active:
                    continue
                # Check collision with screen wrapping
                if self.check_wrapped_collision(bullet.position, asteroid.position, bullet.radius, asteroid.radius):
                    # Hit!
                    bullet.active = False
                    asteroid.active = False
                    
                    # Add screen shake for asteroid sizes 5+ only
                    if asteroid.size == 9:
                        self.trigger_screen_shake(12, 0.75)  # Large shake for size 9
                    elif asteroid.size == 8:
                        self.trigger_screen_shake(10, 0.5)  # Base shake for size 8
                    elif asteroid.size == 7:
                        self.trigger_screen_shake(8, 0.4)  # Medium shake for size 7
                    elif asteroid.size == 6:
                        self.trigger_screen_shake(6, 0.30)  # Medium shake for size 6
                    elif asteroid.size == 5:
                        self.trigger_screen_shake(5, 0.20)  # Small shake for size 5
                    # Sizes 1-4: No screen shake
                    
                    # Add explosion particles (new scaling formula)
                    total_particles = int((20 + ((2 * asteroid.size) * 20)) * 0.5)  # 50% fewer particles
                    
                    # 40% red particles
                    self.explosions.add_explosion(asteroid.position.x, asteroid.position.y, 
                                                num_particles=int(total_particles * 0.40), 
                                                color=(255, 50, 50), asteroid_size=asteroid.size)  # Red
                    # 35% orange particles
                    self.explosions.add_explosion(asteroid.position.x, asteroid.position.y, 
                                                num_particles=int(total_particles * 0.35), 
                                                color=(255, 150, 0), asteroid_size=asteroid.size)  # Orange
                    # 25% yellow particles
                    self.explosions.add_explosion(asteroid.position.x, asteroid.position.y, 
                                                num_particles=int(total_particles * 0.25), 
                                                color=(255, 255, 100), asteroid_size=asteroid.size)  # Yellow
                    
                    # Add score (size 4 = 400 points, size 3 = 300, etc.)
                    self.score += asteroid.size * 100
                    
                    # Split asteroid with projectile velocity
                    new_asteroids = asteroid.split(bullet.velocity)
                    self.asteroids.extend(new_asteroids)
                    break
        
        # Bullet vs UFO (with screen wrapping)
        for bullet in self.bullets[:]:
            if not bullet.active:
                continue
            for ufo in self.ufos[:]:
                if not ufo.active:
                    continue
                if self.check_wrapped_collision(bullet.position, ufo.position, bullet.radius, ufo.radius):
                    # Hit!
                    bullet.active = False
                    ufo.active = False
                    
                    # Add screen shake for UFO destruction
                    self.trigger_screen_shake(8, 0.5)  # UFO shake
                    
                    # Add explosion particles (90% electric blue, 10% bright white)
                    total_particles = int(40 * 1.5 * 1.5)  # 50% more particles (60 * 1.5 = 90)
                    
                    # 90% electric blue particles
                    self.explosions.add_explosion(ufo.position.x, ufo.position.y, 
                                                num_particles=int(total_particles * 0.90), 
                                                color=(0, 150, 255), is_ufo=True)  # Electric blue
                    # 10% bright white particles
                    self.explosions.add_explosion(ufo.position.x, ufo.position.y, 
                                                num_particles=int(total_particles * 0.10), 
                                                color=(255, 255, 255), is_ufo=True)  # Bright white
                    
                    self.score += 200
                    break
        
        # Ship vs Asteroid (with screen wrapping)
        if self.ship.active and not self.ship.invulnerable:
            for asteroid in self.asteroids:
                if not asteroid.active:
                    continue
                if self.check_wrapped_collision(self.ship.position, asteroid.position, self.ship.radius, asteroid.radius):
                    # Collision!
                    if self.ship.shield_hits > 0:
                        # Shield absorbs hit
                        self.ship.shield_hits -= 1
                        self.ship.shield_recharge_time = 0  # Reset recharge timer
                        self.ship.shield_damage_timer = self.ship.shield_damage_duration  # Show shield visual
                        
                        # Add camera shake based on remaining shields (subject to time dilation)
                        if self.ship.shield_hits == 2:  # Lost first shield (3/3 -> 2/3)
                            self.trigger_screen_shake(1, 0.2, self.time_dilation_factor)  # Light shake
                        elif self.ship.shield_hits == 1:  # Lost second shield (2/3 -> 1/3)
                            self.trigger_screen_shake(3, 0.4, self.time_dilation_factor)  # Medium shake
                        elif self.ship.shield_hits == 0:  # Lost last shield (1/3 -> 0/3)
                            self.trigger_screen_shake(5, 0.6, self.time_dilation_factor)  # Strong shake
                        
                        asteroid.active = False  # Destroy asteroid
                        
                        # Add explosion particles (with randomized lifetimes)
                        self.explosions.add_explosion(asteroid.position.x, asteroid.position.y, 
                                                    num_particles=20 + asteroid.size * 5, 
                                                    color=(0, 100, 255))  # Blue explosion
                        
                        # Add score for destroying asteroid with shield
                        self.score += asteroid.size * 50
                    else:
                        # No shield, ship destroyed
                        # Add rainbow explosion for dramatic death effect
                        self.explosions.add_ship_explosion(self.ship.position.x, self.ship.position.y, 150)
                        self.ship.active = False
                        asteroid.active = False
                        self.lives -= 1
                        if self.lives <= 0:
                            # Game over - no screen shake
                            self.game_state = "game_over"
                            self.game_over_timer = 0  # Start game over timer
                            # Stop music on game over
                            self.stop_music()
                            # Start star explosion effect
                            self.star_explosion_active = True
                            self.star_field.start_explosion(self.current_width, self.current_height)
                        else:
                            # Still alive - trigger screen shake
                            self.trigger_screen_shake(7, 0.6)  # Level 7 shake for player death
                            self.init_ship()
                    break
        
        # UFO vs Asteroid (with screen wrapping) - UFOs break asteroids on collision
        for ufo in self.ufos[:]:
            if not ufo.active:
                continue
            for asteroid in self.asteroids[:]:
                if not asteroid.active:
                    continue
                if self.check_wrapped_collision(ufo.position, asteroid.position, ufo.radius, asteroid.radius):
                    # UFO hits asteroid - break the asteroid
                    asteroid.active = False
                    
                    # Add screen shake for asteroid sizes 5+ only
                    if asteroid.size == 9:
                        self.trigger_screen_shake(12, 0.75)  # Large shake for size 9
                    elif asteroid.size == 8:
                        self.trigger_screen_shake(10, 0.5)  # Base shake for size 8
                    elif asteroid.size == 7:
                        self.trigger_screen_shake(8, 0.4)  # Medium shake for size 7
                    elif asteroid.size == 6:
                        self.trigger_screen_shake(6, 0.30)  # Medium shake for size 6
                    elif asteroid.size == 5:
                        self.trigger_screen_shake(5, 0.20)  # Small shake for size 5
                    # Sizes 1-4: No screen shake
                    
                    # Add explosion particles
                    total_particles = int((20 + ((2 * asteroid.size) * 20)) * 0.5)  # 50% fewer particles
                    
                    # 40% red particles
                    self.explosions.add_explosion(asteroid.position.x, asteroid.position.y, 
                                                num_particles=int(total_particles * 0.40), 
                                                color=(255, 50, 50), asteroid_size=asteroid.size)  # Red
                    # 35% orange particles
                    self.explosions.add_explosion(asteroid.position.x, asteroid.position.y, 
                                                num_particles=int(total_particles * 0.35), 
                                                color=(255, 150, 0), asteroid_size=asteroid.size)  # Orange
                    # 25% yellow particles
                    self.explosions.add_explosion(asteroid.position.x, asteroid.position.y, 
                                                num_particles=int(total_particles * 0.25), 
                                                color=(255, 255, 100), asteroid_size=asteroid.size)  # Yellow
                    
                    # Add score (size 4 = 400 points, size 3 = 300, etc.)
                    self.score += asteroid.size * 100
                    
                    # Split asteroid with UFO velocity
                    new_asteroids = asteroid.split(ufo.velocity)
                    self.asteroids.extend(new_asteroids)
                    break
        
        # Ship vs UFO (with screen wrapping)
        if self.ship.active and not self.ship.invulnerable:
            for ufo in self.ufos:
                if not ufo.active:
                    continue
                if self.check_wrapped_collision(self.ship.position, ufo.position, self.ship.radius, ufo.radius):
                    # Collision!
                    if self.ship.shield_hits > 0:
                        # Shield absorbs hit
                        self.ship.shield_hits -= 1
                        self.ship.shield_recharge_time = 0  # Reset recharge timer
                        self.ship.shield_damage_timer = self.ship.shield_damage_duration  # Show shield visual
                        
                        # Add camera shake based on remaining shields (subject to time dilation)
                        if self.ship.shield_hits == 2:  # Lost first shield (3/3 -> 2/3)
                            self.trigger_screen_shake(1, 0.2, self.time_dilation_factor)  # Light shake
                        elif self.ship.shield_hits == 1:  # Lost second shield (2/3 -> 1/3)
                            self.trigger_screen_shake(3, 0.4, self.time_dilation_factor)  # Medium shake
                        elif self.ship.shield_hits == 0:  # Lost last shield (1/3 -> 0/3)
                            self.trigger_screen_shake(5, 0.6, self.time_dilation_factor)  # Strong shake
                        
                        ufo.active = False  # Destroy UFO
                        
                        # Add explosion particles
                        self.explosions.add_explosion(ufo.position.x, ufo.position.y, 
                                                    num_particles=45,  # 50% more particles (30 * 1.5 = 45)
                                                    color=(0, 100, 255), is_ufo=True)  # Blue explosion
                        
                        # Add score for destroying UFO with shield
                        self.score += 100
                    else:
                        # No shield, ship destroyed
                        # Add rainbow explosion for dramatic death effect
                        self.explosions.add_ship_explosion(self.ship.position.x, self.ship.position.y, 150)
                        self.ship.active = False
                        ufo.active = False
                        self.lives -= 1
                        if self.lives <= 0:
                            # Game over - no screen shake
                            self.game_state = "game_over"
                            self.game_over_timer = 0  # Start game over timer
                            # Stop music on game over
                            self.stop_music()
                            # Start star explosion effect
                            self.star_explosion_active = True
                            self.star_field.start_explosion(self.current_width, self.current_height)
                        else:
                            # Still alive - trigger screen shake
                            self.trigger_screen_shake(7, 0.6)  # Level 7 shake for player death
                            self.init_ship()
                    break
        
        # Ship vs UFO bullets
        if self.ship.active and not self.ship.invulnerable:
            for bullet in self.ufo_bullets[:]:
                if not bullet.active:
                    continue
                if self.check_wrapped_collision(self.ship.position, bullet.position, self.ship.radius, bullet.radius):
                    # Hit!
                    bullet.active = False
                    if self.ship.shield_hits > 0:
                        # Shield absorbs hit
                        self.ship.shield_hits -= 1
                        self.ship.shield_recharge_time = 0  # Reset recharge timer
                        self.ship.shield_damage_timer = self.ship.shield_damage_duration  # Show shield visual
                        
                        # Add camera shake based on remaining shields (subject to time dilation)
                        if self.ship.shield_hits == 2:  # Lost first shield (3/3 -> 2/3)
                            self.trigger_screen_shake(1, 0.2, self.time_dilation_factor)  # Light shake
                        elif self.ship.shield_hits == 1:  # Lost second shield (2/3 -> 1/3)
                            self.trigger_screen_shake(3, 0.4, self.time_dilation_factor)  # Medium shake
                        elif self.ship.shield_hits == 0:  # Lost last shield (1/3 -> 0/3)
                            self.trigger_screen_shake(5, 0.6, self.time_dilation_factor)  # Strong shake
                        
                        # Add shield hit particles
                        self.explosions.add_explosion(self.ship.position.x, self.ship.position.y, 
                                                    num_particles=25, 
                                                    color=(0, 100, 255))  # Blue shield hit explosion
                    else:
                        # No shield, ship destroyed
                        # Add rainbow explosion for dramatic death effect
                        self.explosions.add_ship_explosion(self.ship.position.x, self.ship.position.y, 150)
                        self.ship.active = False
                        self.lives -= 1
                        if self.lives <= 0:
                            # Game over - no screen shake
                            self.game_state = "game_over"
                            self.game_over_timer = 0  # Start game over timer
                            # Stop music on game over
                            self.stop_music()
                            # Start star explosion effect
                            self.star_explosion_active = True
                            self.star_field.start_explosion(self.current_width, self.current_height)
                        else:
                            # Still alive - trigger screen shake
                            self.trigger_screen_shake(7, 0.6)  # Level 7 shake for player death
                            self.init_ship()
                    break
        
        # UFO bullets vs Asteroids (100% blockable, 10% chance to break)
        for bullet in self.ufo_bullets[:]:
            if not bullet.active:
                continue
            for asteroid in self.asteroids[:]:
                if not asteroid.active:
                    continue
                if self.check_wrapped_collision(bullet.position, asteroid.position, bullet.radius, asteroid.radius):
                    # UFO bullet hits asteroid - always blocked
                    bullet.active = False
                    
                    # 10% chance to break the asteroid
                    if random.random() < 0.1:  # 10% chance
                        asteroid.active = False
                        
                        # Add screen shake for asteroid sizes 5+ only
                        if asteroid.size == 9:
                            self.trigger_screen_shake(12, 0.75)  # Large shake for size 9
                        elif asteroid.size == 8:
                            self.trigger_screen_shake(10, 0.5)  # Base shake for size 8
                        elif asteroid.size == 7:
                            self.trigger_screen_shake(8, 0.4)  # Medium shake for size 7
                        elif asteroid.size == 6:
                            self.trigger_screen_shake(6, 0.30)  # Medium shake for size 6
                        elif asteroid.size == 5:
                            self.trigger_screen_shake(5, 0.20)  # Small shake for size 5
                        # Sizes 1-4: No screen shake
                        
                        # Add explosion particles
                        total_particles = int((20 + ((2 * asteroid.size) * 20)) * 0.5)  # 50% fewer particles
                        
                        # 40% red particles
                        self.explosions.add_explosion(asteroid.position.x, asteroid.position.y, 
                                                    num_particles=int(total_particles * 0.40), 
                                                    color=(255, 50, 50), asteroid_size=asteroid.size)  # Red
                        # 35% orange particles
                        self.explosions.add_explosion(asteroid.position.x, asteroid.position.y, 
                                                    num_particles=int(total_particles * 0.35), 
                                                    color=(255, 150, 0), asteroid_size=asteroid.size)  # Orange
                        # 25% yellow particles
                        self.explosions.add_explosion(asteroid.position.x, asteroid.position.y, 
                                                    num_particles=int(total_particles * 0.25), 
                                                    color=(255, 255, 100), asteroid_size=asteroid.size)  # Yellow
                        
                        # Add score (size 4 = 400 points, size 3 = 300, etc.)
                        self.score += asteroid.size * 100
                        
                        # Split asteroid with UFO bullet velocity
                        new_asteroids = asteroid.split(bullet.velocity)
                        self.asteroids.extend(new_asteroids)
                    break
    
    def update(self, dt):
        # Play title music when in waiting state
        if self.game_state == "waiting":
            self.play_title_music()
            return
        
        if self.game_state not in ["playing", "paused"]:
            return
        
        # Calculate time dilation based on player movement (Superhot-style)
        self.calculate_time_dilation(dt)
        
        # Update screen shake
        self.update_screen_shake(dt)
        
        # Update time advance for ability blasts
        if self.time_advance_timer > 0:
            self.time_advance_timer -= dt
            if self.time_advance_timer <= 0:
                # Restore normal time dilation
                self.calculate_time_dilation(dt)
        
        # Calculate dilated time for non-player objects
        dilated_dt = dt * self.time_dilation_factor
        
        # Handle ability breaking sequence (only if not transitioning to new level)
        if self.ability_breaking and self.pending_level is None:
            self.ability_break_timer += dt
            if self.ability_break_timer >= self.ability_break_delay:
                # Perform one break
                self.perform_ability_break()
                self.ability_break_count += 1
                self.ability_break_timer = 0.0
                
                if self.ability_break_count >= self.ability_blast_count:
                    # All breaks complete for this charge
                    self.ability_breaking = False
                    self.ability_break_count = 0
                    self.ship.ability_used = True
                    self.ship.ability_ready = self.ship.ability_charges > 0
                    if self.ship.ability_charges > 0:
                        self.ship.ability_timer = 0.0
                    
                    # Check if level should advance
                    if len(self.asteroids) == 0:
                        # Add 2-second pause before level transition
                        if not hasattr(self, 'level_clear_pause_timer') or self.level_clear_pause_timer <= 0:
                            # Start the 2-second pause and star explosion
                            self.level_clear_pause_timer = 2.0
                            self.star_explosion_active = True
                            self.star_field.start_explosion(self.current_width, self.current_height)
                        else:
                            # Count down the pause timer
                            self.level_clear_pause_timer -= dt
                            if self.level_clear_pause_timer <= 0:
                                # Pause complete, advance level
                                self.advance_level()
                else:
                    # Set delay for next break
                    self.ability_break_delay = random.uniform(0.2, 0.42)
        elif self.ability_breaking and self.pending_level is not None:
            # Cancel ability breaking when transitioning to new level
            self.ability_breaking = False
            self.ability_break_count = 0
            self.ship.ability_used = True
            self.ship.ability_ready = self.ship.ability_charges > 0
            if self.ship.ability_charges > 0:
                self.ship.ability_timer = 0.0
            
        # Update ship (affected by time dilation like everything else)
        if self.ship:
            self.ship.update(dilated_dt, self.current_width, self.current_height, 1.0)
            # Update star field with ship velocity (affected by time dilation)
            self.star_field.update(self.ship.velocity, self.current_width, self.current_height, dilated_dt)
        elif self.star_explosion_active:
            # Update star field during explosion even when ship is not active
            self.star_field.update(None, self.current_width, self.current_height, dilated_dt)
        
        # Update star explosion effect
        if self.star_explosion_active:
            self.star_explosion_timer += dt  # Use normal time, not dilated
            if self.star_explosion_timer >= self.star_explosion_duration:
                # Explosion finished, reset
                self.star_explosion_active = False
                self.star_explosion_timer = 0.0
                self.star_field.explosion_mode = False
            
            # Check for spinning trick achievement
            if self.ship.spinning_trick_shown and not self.show_spinning_trick:
                self.show_spinning_trick = True
                self.spinning_trick_timer = 10.0  # Show for 10 seconds
            
            # Check for interstellar achievement
            if self.ship.interstellar_shown and not self.show_interstellar:
                self.show_interstellar = True
                self.interstellar_timer = 10.0  # Show for 10 seconds
        
        # Update explosion particles (affected by time dilation)
        self.explosions.update(dilated_dt)
        
        # Update screen shake (NOT affected by time dilation - always normal speed)
        if self.screen_shake_timer > 0:
            self.screen_shake_timer -= dt
            if self.screen_shake_timer <= 0:
                self.screen_shake_intensity = 0
        
        # Add speed-based camera shake (50-100% speed = 0-10 intensity)
        if self.ship and self.game_state == "playing":
            player_speed = self.ship.velocity.magnitude()
            player_speed_percent = min(player_speed / 1000.0 * 100, 100)  # Cap at 100%
            
            if player_speed_percent >= 50.0:  # Only shake at 50%+ speed
                # Use a curve that's less intense at lower speeds, more intense at higher speeds
                # Normalize speed from 50-100% to 0-1 range
                normalized_speed = (player_speed_percent - 50.0) / 50.0
                
                # Apply exponential curve: x^2 for more dramatic effect at high speeds
                # This makes low speeds (50-75%) have much less shake
                # and high speeds (75-100%) have much more shake
                curved_intensity = normalized_speed ** 2
                
                # Scale to 0-7 intensity range
                speed_shake_intensity = curved_intensity * 7.0
                
                # Add continuous shake while moving fast
                self.add_screen_shake(speed_shake_intensity, 0.1)  # Very short duration for continuous effect
        
        # Update game over timer and stop screen shake after 1 second (NOT affected by time dilation)
        if self.game_state == "game_over":
            self.game_over_timer += dt  # Use normal time, not dilated time
            if self.game_over_timer >= 1.0:  # After 1 second
                # Force stop all screen shake for game over
                self.screen_shake_intensity = 0
                self.screen_shake_timer = 0
                self.screen_shake_duration = 0
        
        # Update bullets (affected by time dilation)
        for bullet in self.bullets[:]:
            bullet.update(dilated_dt, self.current_width, self.current_height)
            if not bullet.active:
                self.bullets.remove(bullet)
        
        # Update asteroids (affected by time dilation)
        for asteroid in self.asteroids[:]:
            player_speed = self.ship.velocity.magnitude() if self.ship else 0
            # Pass dilated time directly to asteroids
            asteroid.update(dilated_dt, self.current_width, self.current_height, player_speed, 1.0)
            if not asteroid.active:
                self.asteroids.remove(asteroid)
        
        # Update UFOs (affected by time dilation)
        for ufo in self.ufos[:]:
            # Provide environmental context to UFO
            ufo.player_position = self.ship.position if self.ship else Vector2D(0, 0)
            ufo.player_velocity = self.ship.velocity if self.ship else Vector2D(0, 0)
            ufo.player_bullets = self.bullets
            ufo.other_ufos = [u for u in self.ufos if u != ufo]
            ufo.asteroids = self.asteroids
            ufo.screen_width = self.current_width
            ufo.screen_height = self.current_height
            ufo.time_dilation_factor = self.time_dilation_factor
            
            should_shoot = ufo.update(dilated_dt, self.ship.position if self.ship else Vector2D(0, 0), self.current_width, self.current_height, self.time_dilation_factor)
            if should_shoot and self.ship:
                # UFO shoots at ship
                angle = math.atan2(self.ship.position.y - ufo.position.y,
                                 self.ship.position.x - ufo.position.x)
                bullet_speed = 200
                vx = math.cos(angle) * bullet_speed
                vy = math.sin(angle) * bullet_speed
                ufo_bullet = Bullet(ufo.position.x, ufo.position.y, vx, vy, is_ufo_bullet=True)
                self.ufo_bullets.append(ufo_bullet)
            
            if not ufo.active:
                self.ufos.remove(ufo)
        
        # Update UFO bullets (affected by time dilation)
        for bullet in self.ufo_bullets[:]:
            bullet.update(dilated_dt, self.current_width, self.current_height)
            if not bullet.active:
                self.ufo_bullets.remove(bullet)
        
        # Spawn UFOs with 5-second delay, then from random corner (affected by time dilation)
        if self.initial_ufo_timer > 0:
            self.initial_ufo_timer -= dilated_dt
            if self.initial_ufo_timer <= 0:
                # Determine how many UFOs to spawn based on level
                if self.level == 1:
                    self.ufos_to_spawn = 5  # 1 of each type (aggressive, defensive, tactical, swarm, deadly)
                    self.ufo_spawn_types = ["aggressive", "defensive", "tactical", "swarm", "deadly"]  # Specific order for level 1
                elif self.level == 2:
                    self.ufos_to_spawn = random.randint(2, 6)  # 2-6 defensive only
                    self.ufo_spawn_types = None  # Use normal random selection
                elif self.level == 3:
                    self.ufos_to_spawn = random.randint(3, 9)  # 3-9 aggressive/defensive
                    self.ufo_spawn_types = None  # Use normal random selection
                elif self.level == 4:
                    self.ufos_to_spawn = random.randint(4, 12)  # 4-12 aggressive only
                    self.ufo_spawn_types = None  # Use normal random selection
                elif self.level == 5:
                    self.ufos_to_spawn = random.randint(5, 15)  # 5-15 all types
                    self.ufo_spawn_types = None  # Use normal random selection
                else:
                    # Level 6+: random.randint(1, 3) × current level
                    self.ufos_to_spawn = random.randint(1, 3) * self.level
                    self.ufo_spawn_types = None  # Use normal random selection
                
                # Pick a random corner for this level
                corners = [
                    (0, 0),  # Top-left
                    (self.current_width, 0),  # Top-right
                    (0, self.current_height),  # Bottom-left
                    (self.current_width, self.current_height)  # Bottom-right
                ]
                self.ufo_spawn_corner = random.choice(corners)
                
                # 10% chance for mass spawn from all corners
                self.ufo_mass_spawn = random.random() < 0.1
                
                self.ufo_spawn_delay = 0  # Start spawning immediately
        elif self.ufos_to_spawn > 0:
            if self.ufo_mass_spawn:
                # Mass spawn: Spawn all remaining UFOs at once from all corners
                self.spawn_all_ufos_mass()
                self.ufos_to_spawn = 0
            else:
                # Normal spawn: One UFO per second from selected corner
                self.ufo_spawn_delay += dilated_dt
                if self.ufo_spawn_delay >= 1.0:  # 1 second between spawns
                    self.ufo_spawn_delay = 0
                    if self.ufo_spawn_types and len(self.ufo_spawn_types) > 0:
                        # Level 1: Use specific types in order
                        personality = self.ufo_spawn_types.pop(0)  # Get next type and remove it
                        self.spawn_ufo_with_personality_at_corner(personality, self.ufo_spawn_corner)
                    else:
                        # Other levels: Use normal random selection from selected corner
                        self.spawn_ufo_from_selected_corner()
                    self.ufos_to_spawn -= 1
        
        # Check for level complete
        if len(self.asteroids) == 0:
            # Check if ability is breaking - delay level transition
            if self.ability_breaking:
                # Set pending level and wait for ability to finish
                self.pending_level = self.level + 1
                self.level_transition_delay = 0.3  # 0.3 second delay after ability finishes
            else:
                # No ability breaking, add 2-second pause before level transition
                if not hasattr(self, 'level_clear_pause_timer') or self.level_clear_pause_timer <= 0:
                    # Start the 2-second pause and star explosion
                    self.level_clear_pause_timer = 2.0
                    self.star_explosion_active = True
                    self.star_field.start_explosion(self.current_width, self.current_height)
                else:
                    # Count down the pause timer
                    self.level_clear_pause_timer -= dt
                    if self.level_clear_pause_timer <= 0:
                        # Pause complete, advance level
                        self.advance_level()
        
        # Check collisions (affected by time dilation)
        self.check_collisions()
        
        # Update spinning trick message timer (affected by time dilation)
        if self.show_spinning_trick and self.spinning_trick_timer > 0:
            self.spinning_trick_timer -= dilated_dt
            if self.spinning_trick_timer <= 0:
                self.show_spinning_trick = False
        
        # Update interstellar message timer (affected by time dilation)
        if self.show_interstellar and self.interstellar_timer > 0:
            self.interstellar_timer -= dilated_dt
            if self.interstellar_timer <= 0:
                self.show_interstellar = False
        
        # Update level transition delay
        if self.level_transition_delay > 0:
            self.level_transition_delay -= dt  # Use normal time, not dilated
            if self.level_transition_delay <= 0:
                # Delay finished, advance level
                self.advance_level()
        
        # Update level pause timer
        if self.level_pause_timer > 0:
            self.level_pause_timer -= dt  # Use normal time, not dilated
            if self.level_pause_timer <= 0:
                # Pause finished, start level flash
                self.level_flash_timer = self.level_flash_duration
                self.level_flash_count = 0
        
        # Update level flash timer
        if self.level_flash_timer > 0:
            self.level_flash_timer -= dt  # Use normal time, not dilated
    
    def advance_level(self):
        """Advance to the next level with flash effect"""
        self.level += 1
        self.spawn_asteroids()
        
        # Play level music with 10% chance
        self.play_level_music()
        
        # Spawn UFOs for new level (1-3 randomly chosen x current level) after 5 second delay
        self.initial_ufo_timer = 5.0  # 5 second delay for new level
        self.ufos_to_spawn = 0  # Will be set when timer expires
        
        # Reset level clear pause timer
        self.level_clear_pause_timer = 0.0
        
        # Clear all player shots and UFOs
        self.bullets.clear()
        self.ufo_bullets.clear()
        self.ufos.clear()
        
        # Reset player to center of screen with 0% speed
        if self.ship:
            self.ship.position.x = self.current_width // 2
            self.ship.position.y = self.current_height // 2
            self.ship.velocity.x = 0.0
            self.ship.velocity.y = 0.0
            self.ship.angle = 0.0
            
            # Refresh shields to maximum and trigger pulse
            self.ship.shield_hits = self.ship.max_shield_hits
            self.ship.shield_recharge_pulse_timer = self.ship.shield_recharge_pulse_duration
            self.ship.shield_pulse_timer = 1.0  # 1 second pulse
            
            # Add invulnerability for 1 second
            self.ship.invulnerable = True
            self.ship.invulnerable_time = 1.0
        
        # Add 1 life on new level (maximum 3 lives)
        if self.lives < 3:
            self.lives += 1
        
        # Start with pause before showing level text
        self.level_pause_timer = self.level_pause_duration
        self.level_flash_timer = 0.0  # Will start after pause
        
        # Clear pending level
        self.pending_level = None
        
        # Ability persists across levels - no reset needed
    
    def draw_level_flash(self, surface):
        """Draw the LEVEL # flash effect with bottom-to-top animation and pulsing opacity"""
        # Calculate flash progress (0.0 to 1.0)
        flash_progress = 1.0 - (self.level_flash_timer / self.level_flash_duration)
        
        # Pulse opacity 1 time per level (25% to 100%)
        pulse_cycle = (flash_progress * self.level) % 1.0
        opacity = 0.25 + 0.75 * (0.5 + 0.5 * math.sin(pulse_cycle * 2 * math.pi))  # 25% to 100%
        
        # Create large, bold font for level flash
        flash_font = pygame.font.Font(None, 72)
        flash_text = f"LEVEL {self.level}"
        flash_surface = flash_font.render(flash_text, True, WHITE)
        
        # Animate from bottom to top during the 2 second pause
        start_y = self.current_height - 50
        end_y = self.current_height // 2
        current_y = start_y - (start_y - end_y) * flash_progress
        
        # Center the text
        flash_rect = flash_surface.get_rect(center=(self.current_width//2, current_y))
        
        # Apply opacity
        flash_surface.set_alpha(int(255 * opacity))
        
        # Draw background rectangle with opacity
        bg_rect = flash_rect.inflate(20, 10)
        bg_surface = pygame.Surface(bg_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(bg_surface, (0, 0, 0, int(255 * opacity)), bg_surface.get_rect())
        pygame.draw.rect(bg_surface, (255, 255, 255, int(255 * opacity)), bg_surface.get_rect(), 2)
        surface.blit(bg_surface, bg_rect)
        
        surface.blit(flash_surface, flash_rect)
    
    def draw(self):
        # Apply screen shake offset
        shake_x = int(self.screen_shake_x)
        shake_y = int(self.screen_shake_y)
        
        # Clear screen
        self.screen.fill(BLACK)
        draw_surface = self.screen
        
        # Draw star field background
        if self.ship:
            self.star_field.draw(draw_surface, self.ship.velocity)
        
        # Draw ship (player always visible, including during waiting state for invulnerability flash)
        if self.ship:
            # Apply screen shake offset to ship position
            original_x = self.ship.position.x
            original_y = self.ship.position.y
            self.ship.position.x += shake_x
            self.ship.position.y += shake_y
            self.ship.draw(draw_surface)
            # Restore original position
            self.ship.position.x = original_x
            self.ship.position.y = original_y
        
        if self.game_state == "playing":
            # Draw asteroids (background layer)
            for asteroid in self.asteroids:
                # Apply screen shake offset to asteroid position
                original_x = asteroid.position.x
                original_y = asteroid.position.y
                asteroid.position.x += shake_x
                asteroid.position.y += shake_y
                asteroid.draw(draw_surface, self.current_width, self.current_height)
                # Restore original position
                asteroid.position.x = original_x
                asteroid.position.y = original_y
            
            # Draw UFOs (middle layer)
            for ufo in self.ufos:
                # Apply screen shake offset to UFO position
                original_x = ufo.position.x
                original_y = ufo.position.y
                ufo.position.x += shake_x
                ufo.position.y += shake_y
                ufo.draw(draw_surface, self.debug_mode)
                # Restore original position
                ufo.position.x = original_x
                ufo.position.y = original_y
            
            # Draw all bullets on top (player bullets + UFO bullets)
            for bullet in self.bullets:
                # Apply screen shake offset to bullet position
                original_x = bullet.position.x
                original_y = bullet.position.y
                bullet.position.x += shake_x
                bullet.position.y += shake_y
                bullet.draw(draw_surface)
                # Restore original position
                bullet.position.x = original_x
                bullet.position.y = original_y
            for bullet in self.ufo_bullets:
                # Apply screen shake offset to UFO bullet position
                original_x = bullet.position.x
                original_y = bullet.position.y
                bullet.position.x += shake_x
                bullet.position.y += shake_y
                bullet.draw(draw_surface)
                # Restore original position
                bullet.position.x = original_x
                bullet.position.y = original_y
            
            # Draw debug hitboxes if debug mode is enabled
            if self.debug_mode:
                self.draw_debug_hitboxes(draw_surface)
        
        # Create font for UI elements
        font = pygame.font.Font(None, 36)
        
        # Draw UI (only during gameplay)
        if self.game_state == "playing":
            # Create combined UI text in one line at top center
            if self.ship:
                # Add shield recharge countdown if shields are recharging
                if self.ship.shield_hits < self.ship.max_shield_hits:
                    remaining_time = self.ship.shield_recharge_duration - self.ship.shield_recharge_time
                    ui_text = f"Score: {self.score} | Lives: {self.lives} | Level: {self.level} | Shield: {self.ship.shield_hits}/{self.ship.max_shield_hits} ({remaining_time:.1f}s)"
                else:
                    ui_text = f"Score: {self.score} | Lives: {self.lives} | Level: {self.level} | Shield: {self.ship.shield_hits}/{self.ship.max_shield_hits}"
            else:
                ui_text = f"Score: {self.score} | Lives: {self.lives} | Level: {self.level} | Shield: 0/0"
            
            ui_surface = font.render(ui_text, True, WHITE)
            ui_rect = ui_surface.get_rect(center=(self.current_width//2, 30))
            draw_surface.blit(ui_surface, ui_rect)
            
            # Draw level flash effect
            if self.level_flash_timer > 0:
                self.draw_level_flash(draw_surface)
            
            # Add speed information on second line
            if self.ship:
                player_speed = self.ship.velocity.magnitude()
                player_speed_percent = min(player_speed / 1000.0 * 100, 100)  # Cap at 100%
                world_speed_percent = self.time_dilation_factor * 100
                speed_text = f"Player Speed: {player_speed_percent:.1f}% | World Speed: {world_speed_percent:.1f}%"
            else:
                speed_text = f"Player Speed: 0.0% | World Speed: {self.time_dilation_factor * 100:.1f}%"
            
            speed_surface = font.render(speed_text, True, WHITE)
            speed_rect = speed_surface.get_rect(center=(self.current_width//2, 60))
            draw_surface.blit(speed_surface, speed_rect)
            
            # Draw debug mode status
            if self.debug_mode:
                debug_text = "DEBUG MODE - F1 to toggle | Hitboxes: Red=Ship, Green=Asteroids, Yellow=UFOs, Blue=Bullets, Magenta=UFO Bullets"
                debug_surface = font.render(debug_text, True, (255, 255, 0))
                debug_rect = debug_surface.get_rect(center=(self.current_width//2, 90))
                draw_surface.blit(debug_surface, debug_rect)
        
        # Draw spinning trick message
        if self.show_spinning_trick:
            spinning_font = pygame.font.Font(None, 48)
            spinning_text = spinning_font.render("I'll try spinning, that's a good trick!", True, YELLOW)
            text_rect = spinning_text.get_rect(center=(self.current_width//2, 50))
            draw_surface.blit(spinning_text, text_rect)
        
        # Draw interstellar message
        if self.show_interstellar:
            interstellar_font = pygame.font.Font(None, 48)
            interstellar_text = interstellar_font.render("Interstellar!", True, YELLOW)
            text_rect = interstellar_text.get_rect(center=(self.current_width//2, 50))
            draw_surface.blit(interstellar_text, text_rect)
            
        
        
        if self.game_state == "waiting":
            # Title - yellow, bold, larger (48pt instead of 44pt)
            title_font = pygame.font.Font(None, 48)
            title_font.set_bold(True)
            title_text = title_font.render("C H U C K S T A R O I D S", True, YELLOW)
            title_rect = title_text.get_rect(center=(self.current_width//2, self.current_height//2 - 100))
            draw_surface.blit(title_text, title_rect)
            
            # Add two lines underneath the title
            subtitle_font = pygame.font.Font(None, 32)
            subtitle_font.set_bold(True)
            
            # First subtitle line
            subtitle1_text = subtitle_font.render("A SPACE ADVENTURE", True, WHITE)
            subtitle1_rect = subtitle1_text.get_rect(center=(self.current_width//2, self.current_height//2 - 50))
            draw_surface.blit(subtitle1_text, subtitle1_rect)
            
            # Second subtitle line
            subtitle2_text = subtitle_font.render("PRESS SPACE TO START", True, WHITE)
            subtitle2_rect = subtitle2_text.get_rect(center=(self.current_width//2, self.current_height//2 - 10))
            draw_surface.blit(subtitle2_text, subtitle2_rect)
            
            # Controls - centered, smaller font (18pt instead of 36pt)
            controls_font = pygame.font.Font(None, 18)
            controls_text = controls_font.render("Arrow Keys: Move | Space: Shoot | P: Pause | ESC: Quit", True, (200, 200, 200))
            controls_rect = controls_text.get_rect(center=(self.current_width//2, self.current_height//2 + 20))
            draw_surface.blit(controls_text, controls_rect)
        elif self.game_state == "game_over":
            # Only show game over text after star explosion has finished
            if not self.star_explosion_active:
                game_over_text = font.render("GAME OVER", True, RED)
                restart_text = font.render("Press R to restart", True, WHITE)
                draw_surface.blit(game_over_text, (self.current_width//2 - 100, self.current_height//2 - 50))
                draw_surface.blit(restart_text, (self.current_width//2 - 120, self.current_height//2))
        elif self.game_state == "paused":
            pause_text = font.render("PAUSED", True, YELLOW)
            resume_text = font.render("Press P to resume", True, WHITE)
            draw_surface.blit(pause_text, (self.current_width//2 - 60, self.current_height//2 - 50))
            draw_surface.blit(resume_text, (self.current_width//2 - 120, self.current_height//2))
        
        # Draw explosion particles on top of everything
        self.explosions.draw(draw_surface)
        
        # Apply screen shake by blitting with offset
        if self.screen_shake_intensity > 0:
            self.screen.blit(draw_surface, (shake_x, shake_y))
        else:
            self.screen.blit(draw_surface, (0, 0))
        
        pygame.display.flip()
    
    def restart_game(self):
        self.score = 0
        self.lives = 3
        self.level = 1
        self.game_state = "playing"
        self.bullets.clear()
        self.asteroids.clear()
        self.ufos.clear()
        self.ufo_bullets.clear()
        self.init_ship()
        self.spawn_asteroids()
        # Reset spinning trick tracking
        self.show_spinning_trick = False
        self.spinning_trick_timer = 0.0
        
        # Reset interstellar tracking
        self.show_interstellar = False
        self.interstellar_timer = 0.0
        # Reset UFO spawn timer for new game
        self.initial_ufo_timer = 5.0  # 5 second delay before first UFOs
        self.game_over_timer = 0  # Reset game over timer
        # Reset time dilation
        self.time_dilation_factor = 1.0
        # Reset first game flag for ability charging
        if self.ship:
            self.ship.is_first_game = True
        # Reset music state
        self.title_music_played = False
        self.stop_music()
    
    def draw_debug_hitboxes(self, surface):
        """Draw debug hitboxes for all game objects with screen wrapping"""
        # Draw ship hitbox
        if self.ship and self.ship.active:
            pygame.draw.circle(surface, (255, 0, 0), 
                             (int(self.ship.position.x), int(self.ship.position.y)), 
                             int(self.ship.radius), 2)
        
        # Draw asteroid hitboxes with wrapping and size info
        for asteroid in self.asteroids:
            if asteroid.active:
                self.draw_wrapped_hitbox(surface, asteroid.position, asteroid.radius, (0, 255, 0))
                # Draw asteroid size text
                font = pygame.font.Font(None, 20)
                size_text = f"Size {asteroid.size}"
                text_surface = font.render(size_text, True, (0, 255, 0))
                text_rect = text_surface.get_rect(center=(int(asteroid.position.x), int(asteroid.position.y) - asteroid.radius - 15))
                surface.blit(text_surface, text_rect)
        
        # Draw UFO hitboxes with wrapping
        for ufo in self.ufos:
            if ufo.active:
                self.draw_wrapped_hitbox(surface, ufo.position, ufo.radius, (255, 255, 0))
        
        # Draw bullet hitboxes with wrapping
        for bullet in self.bullets:
            if bullet.active:
                self.draw_wrapped_hitbox(surface, bullet.position, bullet.radius, (0, 0, 255))
        
        for bullet in self.ufo_bullets:
            if bullet.active:
                self.draw_wrapped_hitbox(surface, bullet.position, bullet.radius, (255, 0, 255))
    
    def check_wrapped_collision(self, pos1, pos2, radius1, radius2):
        """Check collision between two objects with screen wrapping support"""
        width = self.current_width
        height = self.current_height
        
        # Check all possible wrapped positions
        positions1 = self.get_wrapped_positions(pos1, radius1, width, height)
        positions2 = self.get_wrapped_positions(pos2, radius2, width, height)
        
        for p1 in positions1:
            for p2 in positions2:
                distance = math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)
                if distance < radius1 + radius2:
                    return True
        return False
    
    def get_wrapped_positions(self, position, radius, width, height):
        """Get all possible wrapped positions for an object"""
        positions = [(position.x, position.y)]
        
        # Horizontal wrapping
        if position.x < radius:
            positions.append((position.x + width, position.y))
        elif position.x > width - radius:
            positions.append((position.x - width, position.y))
        
        # Vertical wrapping
        if position.y < radius:
            positions.append((position.x, position.y + height))
        elif position.y > height - radius:
            positions.append((position.x, position.y - height))
        
        # Corner wrapping
        if (position.x < radius and position.y < radius):
            positions.append((position.x + width, position.y + height))
        elif (position.x > width - radius and position.y < radius):
            positions.append((position.x - width, position.y + height))
        elif (position.x < radius and position.y > height - radius):
            positions.append((position.x + width, position.y - height))
        elif (position.x > width - radius and position.y > height - radius):
            positions.append((position.x - width, position.y - height))
        
        return positions
    
    def draw_wrapped_hitbox(self, surface, position, radius, color):
        """Draw a hitbox with screen wrapping support"""
        width = self.current_width
        height = self.current_height
        
        # Main position
        pygame.draw.circle(surface, color, 
                         (int(position.x), int(position.y)), 
                         int(radius), 2)
        
        # Check if object is crossing screen edges and add wrapped positions
        # Horizontal wrapping
        if position.x < radius:
            pygame.draw.circle(surface, color, 
                             (int(position.x + width), int(position.y)), 
                             int(radius), 2)
        elif position.x > width - radius:
            pygame.draw.circle(surface, color, 
                             (int(position.x - width), int(position.y)), 
                             int(radius), 2)
        
        # Vertical wrapping
        if position.y < radius:
            pygame.draw.circle(surface, color, 
                             (int(position.x), int(position.y + height)), 
                             int(radius), 2)
        elif position.y > height - radius:
            pygame.draw.circle(surface, color, 
                             (int(position.x), int(position.y - height)), 
                             int(radius), 2)
        
        # Corner wrapping (when object is near both edges)
        if position.x < radius and position.y < radius:
            pygame.draw.circle(surface, color, 
                             (int(position.x + width), int(position.y + height)), 
                             int(radius), 2)
        elif position.x > width - radius and position.y < radius:
            pygame.draw.circle(surface, color, 
                             (int(position.x - width), int(position.y + height)), 
                             int(radius), 2)
        elif position.x < radius and position.y > height - radius:
            pygame.draw.circle(surface, color, 
                             (int(position.x + width), int(position.y - height)), 
                             int(radius), 2)
        elif position.x > width - radius and position.y > height - radius:
            pygame.draw.circle(surface, color, 
                             (int(position.x - width), int(position.y - height)), 
                             int(radius), 2)
    
    def run(self):
        self.running = True
        get_logger().info("Game started")
        
        try:
            while self.running:
                dt = self.clock.tick(FPS) / 1000.0  # Convert to seconds
                
                # Handle events
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.running = False
                    elif event.type == pygame.VIDEORESIZE:
                        # Handle window resizing
                        if event.w >= MIN_WIDTH and event.h >= MIN_HEIGHT:
                            self.current_width = event.w
                            self.current_height = event.h
                            self.screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
                            # Regenerate star field for new screen size
                            self.star_field.generate_stars(self.current_width, self.current_height)
                    elif event.type == pygame.KEYDOWN:
                        self.keys_pressed.add(event.key)
                        if event.key == pygame.K_SPACE and self.game_state == "waiting":
                            # Start the game
                            self.game_state = "playing"
                            self.init_ship()
                            self.spawn_asteroids()
                            self.spawn_ufo()  # Start with 1 UFO
                            # Start star explosion effect on game start
                            self.star_explosion_active = True
                            self.star_field.start_explosion(self.current_width, self.current_height)
                        elif event.key == pygame.K_r and self.game_state == "game_over":
                            self.restart_game()
                        elif event.key == pygame.K_p and self.game_state == "playing":
                            self.game_state = "paused"
                        elif event.key == pygame.K_p and self.game_state == "paused":
                            self.game_state = "playing"
                    elif event.type == pygame.KEYUP:
                        self.keys_pressed.discard(event.key)
                
                # Update and draw
                self.handle_input(dt)
                self.update(dt)
                self.draw()
                
                # Update the display
                pygame.display.flip()
                
        except Exception as e:
            get_logger().error(f"Game crashed: {str(e)}")
            get_logger().error(f"Traceback: {traceback.format_exc()}")
            print(f"Game crashed! Check gamelog.txt for details.")
            print(f"Error: {str(e)}")
            pygame.quit()
        finally:
            # Clean up music player
            if self.music_player:
                self.music_player.close()
            get_logger().info("Game ended")

def main():
    print("Asteroids Deluxe")
    print("Controls:")
    print("  Arrow Keys: Rotate & Thrust")
    print("  WASD: W/S Thrust, A/D Strafe")
    print("  Space: Shoot")
    print("  Q/E/B: Ability (when ready)")
    print("  F1: Debug Mode")
    print("  R: Restart (Game Over)")
    print("  P: Pause")
    print("  ESC: Quit")
    print()
    
    game = Game()
    game.run()
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()