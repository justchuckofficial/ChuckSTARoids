import warnings
import os
import sys

# Suppress pygame warnings
warnings.filterwarnings("ignore", category=UserWarning, module="pygame")
warnings.filterwarnings("ignore", message="pkg_resources is deprecated")
warnings.filterwarnings("ignore", category=DeprecationWarning)

import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
import pygame
import math
import random
import logging
import traceback
from datetime import datetime, timedelta
import time
import threading
import numpy as np
import requests
import json
from typing import List, Tuple
import gc  # For garbage collection

# Import music system
from music import EnhancedMusicPlayer, EnhancedAAGACAStyles


class ImageCache:
    """Efficient image caching system for rotated and scaled images"""
    
    def __init__(self, max_cache_size=1000):
        self.rotation_cache = {}
        self.shadow_cache = {}
        self.scale_cache = {}
        self.max_cache_size = max_cache_size
        self.cache_hits = 0
        self.cache_misses = 0
    
    def get_rotated_image(self, base_image, angle):
        """Get rotated image from cache or create new one"""
        # Round angle to reduce cache entries (0.1 degree precision)
        angle_key = round(angle, 1)
        cache_key = (id(base_image), angle_key)
        
        if cache_key in self.rotation_cache:
            self.cache_hits += 1
            return self.rotation_cache[cache_key]
        
        # Cache miss - create new rotated image
        self.cache_misses += 1
        if len(self.rotation_cache) > self.max_cache_size:
            # Clear oldest entries (simple FIFO)
            self.rotation_cache.clear()
        
        rotated = pygame.transform.rotate(base_image, angle)
        self.rotation_cache[cache_key] = rotated
        return rotated
    
    def get_shadow_image(self, base_image, scale, alpha, angle=0):
        """Get shadow image from cache or create new one"""
        # Round values to reduce cache entries
        scale_key = round(scale, 2)
        alpha_key = int(alpha)
        angle_key = round(angle, 1)
        cache_key = (id(base_image), scale_key, alpha_key, angle_key)
        
        if cache_key in self.shadow_cache:
            self.cache_hits += 1
            return self.shadow_cache[cache_key]
        
        # Cache miss - create new shadow image
        self.cache_misses += 1
        if len(self.shadow_cache) > self.max_cache_size:
            self.shadow_cache.clear()
        
        # Create shadow: rotate -> scale -> apply shadow effect
        if angle != 0:
            shadow = pygame.transform.rotate(base_image, angle)
        else:
            shadow = base_image.copy()
        
        shadow = pygame.transform.scale_by(shadow, scale)
        shadow.fill((0, 0, 0, 255), special_flags=pygame.BLEND_MULT)
        shadow.set_alpha(alpha)
        
        self.shadow_cache[cache_key] = shadow
        return shadow
    
    def get_scaled_image(self, base_image, scale):
        """Get scaled image from cache or create new one"""
        scale_key = round(scale, 2)
        cache_key = (id(base_image), scale_key)
        
        if cache_key in self.scale_cache:
            self.cache_hits += 1
            return self.scale_cache[cache_key]
        
        # Cache miss - create new scaled image
        self.cache_misses += 1
        if len(self.scale_cache) > self.max_cache_size:
            self.scale_cache.clear()
        
        scaled = pygame.transform.scale_by(base_image, scale)
        self.scale_cache[cache_key] = scaled
        return scaled
    
    def clear_cache(self):
        """Clear all caches"""
        self.rotation_cache.clear()
        self.shadow_cache.clear()
        self.scale_cache.clear()
    
    def get_cache_stats(self):
        """Get cache performance statistics"""
        total_requests = self.cache_hits + self.cache_misses
        hit_rate = (self.cache_hits / total_requests * 100) if total_requests > 0 else 0
        return {
            'hits': self.cache_hits,
            'misses': self.cache_misses,
            'hit_rate': hit_rate,
            'total_entries': len(self.rotation_cache) + len(self.shadow_cache) + len(self.scale_cache)
        }


# Global image cache instance
image_cache = ImageCache()


class ShadowSurfaceOptimizer:
    """Optimized shadow surface creation for minimal memory usage"""
    
    @staticmethod
    def create_minimal_shadow_surface(points, alpha=107):
        """Create a minimal shadow surface for polygon shadows"""
        if not points or len(points) < 3:
            return None
        
        # Calculate bounding box for shadow
        min_x = min(p[0] for p in points)
        max_x = max(p[0] for p in points)
        min_y = min(p[1] for p in points)
        max_y = max(p[1] for p in points)
        
        # Add padding for anti-aliasing
        padding = 5
        width = int(max_x - min_x + padding * 2)
        height = int(max_y - min_y + padding * 2)
        
        # Ensure minimum size
        width = max(width, 10)
        height = max(height, 10)
        
        # Create minimal surface
        shadow_surface = pygame.Surface((width, height), pygame.SRCALPHA)
        
        # Adjust points to surface coordinates
        adjusted_points = [(p[0] - min_x + padding, p[1] - min_y + padding) for p in points]
        pygame.draw.polygon(shadow_surface, (0, 0, 0, alpha), adjusted_points)
        
        return shadow_surface, (min_x - padding, min_y - padding)
    
    @staticmethod
    def create_cached_polygon_shadow(points, alpha=107, cache_key=None):
        """Create or retrieve cached polygon shadow"""
        if cache_key is None:
            cache_key = hash(tuple(points) + (alpha,))
        
        # Check if we have a cached version
        if hasattr(ShadowSurfaceOptimizer, '_polygon_cache'):
            if cache_key in ShadowSurfaceOptimizer._polygon_cache:
                return ShadowSurfaceOptimizer._polygon_cache[cache_key]
        else:
            ShadowSurfaceOptimizer._polygon_cache = {}
        
        # Create new shadow surface
        result = ShadowSurfaceOptimizer.create_minimal_shadow_surface(points, alpha)
        if result:
            ShadowSurfaceOptimizer._polygon_cache[cache_key] = result
            # Limit cache size
            if len(ShadowSurfaceOptimizer._polygon_cache) > 100:
                # Clear oldest entries (simple approach)
                ShadowSurfaceOptimizer._polygon_cache.clear()
        
        return result


def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


# Comprehensive game logging system
class GameLogger:
    """Handles all game event logging to ChuckSTARoidsHiScores.txt with timestamps
    
    HIGH SCORE PRESERVATION POLICY:
    - All high score file operations preserve high scores at the top of the file
    - _write_log() always appends (preserves existing content)
    - _ensure_log_file() always appends (preserves existing content)
    - clear_gamelog_preserve_scores() extracts scores before clearing
    - _ensure_high_scores_preserved() can be called before any operation
    """
    
    def __init__(self):
        self.log_file = "ChuckSTARoidsHiScores.txt"
        self.high_scores = []  # List to store high scores with timestamps
        self._ensure_log_file()
        self._load_high_scores()
    
    def _ensure_log_file(self):
        """Ensure the log file exists and add session header (preserves high scores)"""
        try:
            # Always append to preserve existing content including high scores
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(f"\n{'='*60}\n")
                f.write(f"NEW GAME SESSION STARTED: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"{'='*60}\n")
        except Exception as e:
            print(f"Warning: Could not create log file: {e}")
    
    def _write_log(self, message):
        """Write a timestamped message to the log file (always preserves high scores)"""
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]  # Include milliseconds
            # Always append to preserve existing content including high scores
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(f"[{timestamp}] {message}\n")
        except Exception as e:
            print(f"Warning: Could not write to log file: {e}")
            import traceback
            traceback.print_exc()
    
    def log_score_event(self, points, event_type, total_score, multiplier, multiplier_gained):
        """Log score events with multiplier information"""
        self._write_log(f"SCORE: +{points} points ({event_type}) - Total: {total_score} x{multiplier:.2f}")
    
    def log_player_hit_asteroid(self, shield_hits_remaining, total_lives):
        """Log when player gets hit by asteroid"""
        if shield_hits_remaining > 0:
            self._write_log(f"PLAYER HIT: Asteroid collision - Shield hit, {shield_hits_remaining} shields remaining")
        else:
            self._write_log(f"PLAYER HIT: Asteroid collision - Ship destroyed, {total_lives} lives remaining")
    
    def log_player_hit_ufo(self, shield_hits_remaining, total_lives):
        """Log when player gets hit by UFO"""
        if shield_hits_remaining > 0:
            self._write_log(f"PLAYER HIT: UFO collision - Shield hit, {shield_hits_remaining} shields remaining")
        else:
            self._write_log(f"PLAYER HIT: UFO collision - Ship destroyed, {total_lives} lives remaining")
    
    def log_player_hit_boss_shot(self, shield_hits_remaining, total_lives):
        """Log when player gets hit by boss shot"""
        if shield_hits_remaining > 0:
            self._write_log(f"PLAYER HIT: Boss shot - Shield hit, {shield_hits_remaining} shields remaining")
        else:
            self._write_log(f"PLAYER HIT: Boss shot - Ship destroyed, {total_lives} lives remaining")
    
    def log_player_hit_ufo_shot(self, shield_hits_remaining, total_lives):
        """Log when player gets hit by UFO shot"""
        if shield_hits_remaining > 0:
            self._write_log(f"PLAYER HIT: UFO shot - Shield hit, {shield_hits_remaining} shields remaining")
        else:
            self._write_log(f"PLAYER HIT: UFO shot - Ship destroyed, {total_lives} lives remaining")
    
    def log_player_death(self, total_lives, level, score):
        """Log player death"""
        self._write_log(f"PLAYER DEATH: Lives remaining: {total_lives}, Level: {level}, Score: {score}")
    
    def log_new_level(self, level, asteroids_count, boss_count):
        """Log new level start with asteroid count"""
        self._write_log(f"NEW LEVEL: Level {level} started")
        self._write_log(f"LEVEL {level} ASTEROIDS: {asteroids_count}")
    
    def log_ufo_spawn(self, ufo_type, level):
        """Log when a UFO is spawned"""
        self._write_log(f"UFO SPAWNED: {ufo_type} on level {level}")
    
    def log_boss_spawn(self, boss_count, level):
        """Log when boss(es) are spawned"""
        if boss_count == 1:
            self._write_log(f"BOSS SPAWNED: 1 boss on level {level}")
        else:
            self._write_log(f"BOSS SPAWNED: {boss_count} bosses on level {level}")
    
    def log_game_start(self):
        """Log game start"""
        self._write_log("GAME STARTED")
    
    def log_game_over(self, final_score, final_level):
        """Log game over"""
        self._write_log(f"GAME OVER: Final Score: {final_score}, Final Level: {final_level}")
        # Add explicit final score entry for easier parsing
        self._write_log(f"FINAL SCORE: {final_score}")
        # Add score to high scores list
        self.add_high_score(final_score)
    
    def log_ability_use(self, ability_type):
        """Log ability usage"""
        self._write_log(f"ABILITY USED: {ability_type}")
    
    def _load_high_scores(self):
        """Load existing high scores with timestamps from the main log file"""
        from datetime import datetime
        try:
            if os.path.exists(self.log_file):
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    for line in lines:
                        # Only process "FINAL SCORE:" lines to avoid duplicates
                        if "FINAL SCORE:" in line:
                            # Extract score and timestamp from the line
                            try:
                                # Extract timestamp (format: [YYYY-MM-DD HH:MM:SS.mmm])
                                timestamp = None
                                if "[" in line and "]" in line:
                                    timestamp_part = line.split("[")[1].split("]")[0]
                                    # Try to parse the timestamp with milliseconds
                                    try:
                                        timestamp = datetime.strptime(timestamp_part, "%Y-%m-%d %H:%M:%S.%f")
                                    except ValueError:
                                        try:
                                            timestamp = datetime.strptime(timestamp_part, "%Y-%m-%d %H:%M:%S")
                                        except ValueError:
                                            # If timestamp parsing fails, use current time
                                            timestamp = datetime.now()
                                
                                score_part = line.split("FINAL SCORE:")[1].strip()
                                score = int(score_part.replace(",", ""))
                                
                                # Store as tuple (score, timestamp)
                                self.high_scores.append((score, timestamp or datetime.now()))
                            except (ValueError, IndexError):
                                continue
                # Remove duplicates and sort scores in descending order, keep top 10
                # Use a set to remove duplicates based on score only
                seen_scores = set()
                unique_scores = []
                for score, timestamp in self.high_scores:
                    if score not in seen_scores:
                        seen_scores.add(score)
                        unique_scores.append((score, timestamp))
                
                self.high_scores = sorted(unique_scores, key=lambda x: x[0], reverse=True)[:10]
        except Exception as e:
            print(f"Warning: Could not load high scores: {e}")
            self.high_scores = []
    
    def add_high_score(self, score):
        """Add a new high score with current timestamp"""
        if score > 0:
            from datetime import datetime
            self.high_scores.append((score, datetime.now()))
            # Remove duplicates and sort by score, keep top 10
            self.high_scores = sorted(set(self.high_scores), key=lambda x: x[0], reverse=True)[:10]
    
    def _ensure_high_scores_preserved(self):
        """Ensure high scores are up-to-date before any high score file modification"""
        # Always reload high scores to catch any new scores from current session
        self._load_high_scores()
    
    def clear_gamelog_preserve_scores(self):
        """Clear the high score file while preserving high scores at the top"""
        from datetime import datetime
        try:
            # Ensure high scores are preserved before any modification
            self._ensure_high_scores_preserved()
            
            # Create new content with high scores at the top
            new_content = "=== CHUCKSTEROIDS HIGH SCORES ===\n"
            if self.high_scores:
                for i, (score, timestamp) in enumerate(self.high_scores, 1):
                    # Format timestamp as MM/DD/YYYY HH:MM
                    timestamp_str = timestamp.strftime("%m/%d/%Y %H:%M")
                    new_content += f"{i:2d}. {score:,} - {timestamp_str}\n"
            else:
                new_content += "No scores yet\n"
            new_content += "=" * 30 + "\n\n"
            
            # Add session header for new game
            new_content += f"{'='*60}\n"
            new_content += f"NEW GAME SESSION STARTED: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            new_content += f"{'='*60}\n"
            
            # Write the new content to the main log file
            with open(self.log_file, 'w', encoding='utf-8') as f:
                f.write(new_content)
                
        except Exception as e:
            print(f"Warning: Could not clear main log while preserving scores: {e}")
            import traceback
            traceback.print_exc()
    
    def get_top_local_score(self):
        """Get the top local score from high_scores"""
        if not self.high_scores:
            return None
        try:
            # Return the highest score (first in sorted list)
            return self.high_scores[0][0]
        except (IndexError, TypeError):
            return None

# Initialize global game logger
game_logger = GameLogger()

# Setup legacy logging for compatibility (keeping existing functionality)
def setup_logging():
    """Setup logging to gamelog.txt for debugging"""
    # Only configure if not already configured
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('gamelog.txt')
                # Removed StreamHandler(sys.stdout) to mute console output
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


# Utility functions for common calculations
def get_rotation_degrees(angle):
    """Convert angle to rotation degrees for pygame.transform.rotate"""
    return -math.degrees(angle) - 90


def is_invulnerability_flashing(invulnerable_time):
    """Check if invulnerability flash should be active"""
    return int(invulnerable_time * 40) % 2


def load_image_with_alpha(filename):
    """Load image and convert to alpha for better performance"""
    image = pygame.image.load(get_resource_path(filename))
    return image.convert_alpha()


def get_asteroid_shake_params(size):
    """Get screen shake parameters for asteroid destruction by size"""
    shake_map = {
        9: (12, 0.75),  # Large shake for size 9
        8: (10, 0.5),   # Base shake for size 8
        7: (8, 0.4),    # Medium shake for size 7
        6: (6, 0.30),   # Medium shake for size 6
        5: (5, 0.20),   # Small shake for size 5
    }
    return shake_map.get(size, (0, 0))  # No shake for sizes 1-4


def get_shield_damage_shake_params(shield_hits, time_dilation_factor):
    """Get screen shake parameters for shield damage"""
    shake_map = {
        2: (1, 0.2),   # Lost first shield (3/3 -> 2/3) - Light shake
        1: (3, 0.4),   # Lost second shield (2/3 -> 1/3) - Medium shake
        0: (5, 0.6),   # Lost last shield (1/3 -> 0/3) - Strong shake
    }
    intensity, duration = shake_map.get(shield_hits, (0, 0))
    return intensity, duration, time_dilation_factor


def draw_ship_with_effects(ship, surface, position, rotation_angle, use_cache=True, draw_shadow=True):
    """Unified ship drawing with all effects (invulnerability, damage, etc.)"""
    if not ship.active or not ship.image:
        return
    
    # Draw shadow if requested
    if draw_shadow and use_cache:
        shadow_ship = image_cache.get_shadow_image(ship.image, 1.1, 107, rotation_angle)
        shadow_rect = shadow_ship.get_rect(center=(int(position.x + 10), int(position.y + 10)))
        surface.blit(shadow_ship, shadow_rect, special_flags=pygame.BLEND_ALPHA_SDL2)
    
    # Draw main ship with effects
    if use_cache:
        rotated_ship = image_cache.get_rotated_image(ship.image, rotation_angle)
    else:
        rotated_ship = pygame.transform.rotate(ship.image, rotation_angle)
    
    ship_rect = rotated_ship.get_rect(center=(int(position.x), int(position.y)))
    
    # Apply visual effects
    if ship.invulnerable and is_invulnerability_flashing(ship.invulnerable_time):
        # Cyan flash effect when invulnerable
        cyan_ship = ship.image.copy()
        cyan_ship.fill((0, 255, 255, 128), special_flags=pygame.BLEND_MULT)
        if use_cache:
            cyan_ship = image_cache.get_rotated_image(cyan_ship, rotation_angle)
        else:
            cyan_ship = pygame.transform.rotate(cyan_ship, rotation_angle)
        surface.blit(cyan_ship, ship_rect)
    elif ship.red_flash_timer > 0:
        # Red flash effect when taking damage
        red_ship = ship.image.copy()
        red_ship.fill((255, 0, 0, 128), special_flags=pygame.BLEND_MULT)
        if use_cache:
            red_ship = image_cache.get_rotated_image(red_ship, rotation_angle)
        else:
            red_ship = pygame.transform.rotate(red_ship, rotation_angle)
        surface.blit(red_ship, ship_rect)
    else:
        # Normal ship drawing
        surface.blit(rotated_ship, ship_rect)

# Initialize Pygame
pygame.init()

# Constants
SCREEN_WIDTH = 1000  # 25% bigger (800 * 1.25)
SCREEN_HEIGHT = 600  # 25% bigger (600 * 1.25)
FPS = 60

# Particle system limits
MAX_PARTICLES = 1500  # Global particle limit for performance
PARTICLE_SOFT_LIMIT = 750  # Start reducing particle generation (50% of original)

# Asteroid system limits
MAX_ASTEROIDS = 300  # Global asteroid limit for performance

# Window resizing
RESIZABLE = True
MIN_WIDTH = 420
MIN_HEIGHT = 420

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
        self.rotation_smoothing = 0.8  # Smoothing factor (0.0 = no smoothing, 1.0 = maximum smoothing)
        self.target_rotation_speed = 0  # Target rotation speed for smoothing
        self.max_speed = 1000000000  # 10x increase from 100M to 1B speed
        self.invulnerable = False
        self.invulnerable_time = 0
        self.thrusting = False
        self.shoot_timer = 0
        self.shoot_interval = 0.09   # Starting rate of fire (slowest)
        self.min_shoot_interval = 0.042  # Fastest possible rate (peak)
        self.max_shoot_interval = 0.17   # Slowest possible rate (5.9 shots/sec)
        self.rof_progression_time = 0    # Time since shooting start for ROF curve
        self.rof_curve_duration = 11.38  # 11.38 seconds total curve duration
        self.rof_peak_time = 0.5         # Time to reach peak speed
        self.rof_peak_reached = False    # Track if we've reached peak for spark effect
        self.asteroid_interval_bonus = 0.0  # Bonus to shoot interval from destroyed asteroids
        
        # Shield system
        self.shield_hits = 3  # Can take 3 hits
        self.max_shield_hits = 3
        self.shield_recharge_time = 0
        self.shield_recharge_duration = 3.0  # 3 seconds per hit
        self.shield_damage_timer = 0  # Timer for shield damage visual
        self.shield_damage_duration = 1.0  # Show shield for 1 second after damage
        
        # Red flash effect when taking damage
        self.red_flash_timer = 0.0  # Timer for red flash effect
        self.red_flash_duration = 0.1  # Flash for 0.1 seconds (game time affected)
        
        # Speed decay
        self.speed_decay_rate = 0.275  # 50% increase in deceleration (was 0.55, now 0.275 = 72.5% decay per second)
        
        # Rotation tracking for "spinning trick" achievement
        self.total_rotations = 0.0
        self.last_angle = self.angle  # Initialize to current angle
        self.spinning_trick_shown = False
        self.is_spinning = False  # Track if currently spinning
        
        # Speed tracking for "interstellar" achievement
        self.interstellar_timer = 0.0
        self.interstellar_threshold = 11.38  # seconds at 100% speed
        self.interstellar_shown = False
        self.interstellar_threshold_crossed = False  # Track if we've crossed the threshold
        self.is_at_max_speed = False  # Track if currently at 100% speed
        
        # Deceleration tracking for time dilation
        self.last_velocity = Vector2D(0, 0)  # Previous frame velocity
        self.deceleration_rate = 0.0  # Current deceleration rate
        self.time_dilation = 1.0  # Time dilation factor (1.0 = normal time)
        
        # Turning speed tracking for time dilation
        self.turning_speed = 0.0  # Current turning speed in degrees per second
        self.last_angle = 0.0  # Previous frame angle for turning calculation
        self.accumulated_turning_degrees = 0.0  # Total degrees turned continuously
        self.was_turning = False  # Track if turning in previous frame
        
        # Progressive shooting tracking
        self.shot_count = 0  # Number of shots in current sequence
        self.was_shooting = False  # Previous frame shooting state for reset detection
        
        # Shield recharge pulse effect
        self.shield_recharge_pulse_timer = 0.0  # Timer for shield recharge pulse effect
        self.shield_recharge_pulse_duration = 1.0  # Duration of pulse effect (2x longer)
        self.shield_full_flash_timer = 0.0  # Timer for full shield flash effect
        self.shield_full_flash_duration = 0.5  # Duration of full shield flash
        self.shield_full_hold_timer = 0.0  # Timer for holding full shields at 100% opacity
        self.shield_full_hold_duration = 1.0  # Hold duration for full shields
        self.shield_full_fade_timer = 0.0  # Timer for fading full shields to 0%
        self.shield_full_fade_duration = 1.0  # Fade duration for full shields
        self.shield_charged_by_ability = False  # Flag to track if shields were charged via ability
        
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
        
        # Ability recharge pulse effect (like shield recharge)
        self.ability_recharge_pulse_timer = 0.0  # Timer for ability recharge pulse effect
        self.ability_recharge_pulse_duration = 0.5  # Duration of pulse effect
        
        # Ability particle rotation system
        self.ability_particle_rotation = 0.0  # Current rotation angle for ability particles
        self.ability_particle_rotation_speed = 2 * math.pi / 3.0  # 1 rotation per 3 seconds
        
        # 2x charged ability particle system
        self.ability_2x_particle_timer = 0.0  # Timer for generating 2x charged particles
        self.ability_2x_particle_interval = 0.75  # Generate 5 particles every 0.75 seconds (6.67 per second)
        self.ability_2x_particle_rotation = 0.0  # Current rotation for 2x charged particles
        self.ability_hold_timer = 0.0  # Timer for holding at 100% opacity when fully charged
        self.ability_hold_duration = 1.0  # Hold for 1 second at 100% opacity
        self.ability_fade_timer = 0.0  # Timer for fading from 100% to 33% opacity
        self.ability_fade_duration = 0.5  # Fade duration (0.5s for 1st charge, 1.0s for 2nd charge)
        self.ability_fully_charged_pulse_timer = 0.0  # Timer for pulsing when fully charged (independent of time effects)
        self.ability_flash_count = 0  # Number of flashes (2 for 1st charge, 3 for 2nd charge)
        
        # Level transition system
        self.level_transition_delay = 0.0
        self.level_flash_timer = 0.0
        self.level_flash_duration = 0.4
        self.level_flash_count = 0
        self.pending_level = None
        
        # Load ship image
        try:
            self.image = pygame.image.load(get_resource_path("xwing.gif"))
            self.image = self.image.convert_alpha()
            self.image = pygame.transform.smoothscale(self.image, (40, 40))
        except:
            self.image = None
        
    def rotate_left(self, dt):
        # Set target rotation speed for smoothing
        self.target_rotation_speed = -self.rotation_speed
    
    def rotate_right(self, dt):
        # Set target rotation speed for smoothing
        self.target_rotation_speed = self.rotation_speed
    
    def stop_rotation(self):
        # Stop rotation smoothly
        self.target_rotation_speed = 0
    
    def apply_rotation(self, raw_dt, rotation_scale=1.0):
        # Apply smoothed rotation based on target speed
        # Use raw frame time (not dilated) for consistent rotation regardless of time effects
        if abs(self.target_rotation_speed) > 0:
            # Cap dt to prevent excessive rotation at very low FPS
            capped_dt = min(raw_dt, 1.0 / 60.0)  # Cap at 60 FPS equivalent
            # Apply rotation scale to slow down rotation when many asteroids are present
            scaled_rotation_speed = self.target_rotation_speed * rotation_scale
            self.angle += scaled_rotation_speed * capped_dt
    
    def thrust(self, dt):
        self.thrusting = True
        
        # Get acceleration multiplier based on current speed
        thrust_multiplier = self.get_acceleration_multiplier()
        effective_thrust_power = self.thrust_power * thrust_multiplier
        
        # Rotate thrust vector 90 degrees clockwise so up arrow moves ship to the right
        thrust_vector = Vector2D(effective_thrust_power, 0).rotate(self.angle)
        self.velocity.x += thrust_vector.x * dt
        self.velocity.y += thrust_vector.y * dt
        
        # Limit max speed
        speed = self.velocity.magnitude()
        if speed > self.max_speed:
            self.velocity.x = (self.velocity.x / speed) * self.max_speed
            self.velocity.y = (self.velocity.y / speed) * self.max_speed
    
    def reverse_thrust(self, dt):
        self.thrusting = True
        
        # Get acceleration multiplier based on current speed
        thrust_multiplier = self.get_acceleration_multiplier()
        effective_thrust_power = self.thrust_power * thrust_multiplier
        
        # Reverse thrust vector (opposite direction)
        thrust_vector = Vector2D(-effective_thrust_power, 0).rotate(self.angle)
        self.velocity.x += thrust_vector.x * dt
        self.velocity.y += thrust_vector.y * dt
        
        # Limit max speed
        speed = self.velocity.magnitude()
        if speed > self.max_speed:
            self.velocity.x = (self.velocity.x / speed) * self.max_speed
            self.velocity.y = (self.velocity.y / speed) * self.max_speed
    
    def stop_thrust(self):
        self.thrusting = False
    
    def rapid_decelerate(self, dt):
        """Rapid exponential deceleration using CTRL keys - 2x normal decay rate"""
        self.thrusting = True  # Mark as thrusting for visual effects
        
        # Use exponential decay at 2x the normal rate
        # Square the decay rate for 2x effect (0.275^2 = 0.075625)
        rapid_decay_rate = self.speed_decay_rate ** 2
        
        # Apply exponential decay to both velocity components
        self.velocity.x *= rapid_decay_rate ** dt
        self.velocity.y *= rapid_decay_rate ** dt
    
    def get_acceleration_multiplier(self):
        """Calculate acceleration multiplier based on current speed"""
        current_speed = self.velocity.magnitude()
        speed_percent = current_speed / 1000.0 * 100  # Convert to percentage
        
        if speed_percent < 50.0:
            # Below 50% speed: 25% boost
            return 1.25
        elif speed_percent < 90.0:
            # Between 50% and 90% speed: linear interpolation from 1.0 to 0.01
            # At 50% speed: 1.0 (100% normal)
            # At 90% speed: 0.01 (1% normal)
            progress = (speed_percent - 50.0) / 40.0  # 0.0 to 1.0 as speed goes from 50% to 90%
            return 1.0 - (0.99 * progress)  # 1.0 to 0.01
        elif speed_percent < 100.0:
            # Between 90% and 100% speed: linear interpolation from 0.01 to 1.0
            # At 90% speed: 0.01 (1% normal)
            # At 100% speed: 1.0 (100% normal)
            progress = (speed_percent - 90.0) / 10.0  # 0.0 to 1.0 as speed goes from 90% to 100%
            return 0.01 + (0.99 * progress)  # 0.01 to 1.0
        else:
            # At or above 100% speed: 100% of normal
            return 1.0
    
    def strafe_left(self, dt):
        """Strafe left (perpendicular to ship's facing direction)"""
        self.thrusting = True
        
        # Get acceleration multiplier based on current speed
        thrust_multiplier = self.get_acceleration_multiplier()
        effective_thrust_power = self.thrust_power * thrust_multiplier
        
        # Strafe vector is 90 degrees counterclockwise from thrust direction
        strafe_vector = Vector2D(0, -effective_thrust_power).rotate(self.angle)
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
        
        # Get acceleration multiplier based on current speed
        thrust_multiplier = self.get_acceleration_multiplier()
        effective_thrust_power = self.thrust_power * thrust_multiplier
        
        # Strafe vector is 90 degrees clockwise from thrust direction
        strafe_vector = Vector2D(0, effective_thrust_power).rotate(self.angle)
        self.velocity.x += strafe_vector.x * dt
        self.velocity.y += strafe_vector.y * dt
        
        # Limit max speed
        speed = self.velocity.magnitude()
        if speed > self.max_speed:
            self.velocity.x = (self.velocity.x / speed) * self.max_speed
            self.velocity.y = (self.velocity.y / speed) * self.max_speed
    
    def update(self, dt, screen_width=None, screen_height=None, time_dilation_factor=1.0, raw_dt=None, multiplier=1.0, asteroid_count=0):
        # Use raw frame time for pulsing effects (independent of time dilation)
        pulse_dt = raw_dt if raw_dt is not None else dt
        
        # Calculate deceleration rate before updating position
        current_speed = self.velocity.magnitude()
        last_speed = self.last_velocity.magnitude()
        
        # Calculate deceleration rate (negative when slowing down)
        if dt > 0:
            self.deceleration_rate = (current_speed - last_speed) / dt
        else:
            self.deceleration_rate = 0.0
        
        # Calculate turning speed (degrees per second) and accumulate continuous turning
        if dt > 0:
            # Calculate angle difference, handling wraparound
            angle_diff = self.angle - self.last_angle
            # Normalize angle difference to [-π, π]
            while angle_diff > math.pi:
                angle_diff -= 2 * math.pi
            while angle_diff < -math.pi:
                angle_diff += 2 * math.pi
            # Convert to degrees per second
            self.turning_speed = abs(angle_diff) * 180 / math.pi / dt
            
            # Accumulate continuous turning degrees
            if self.turning_speed > 0:
                # Add degrees turned this frame
                degrees_this_frame = self.turning_speed * dt
                self.accumulated_turning_degrees += degrees_this_frame
                self.was_turning = True
            else:
                # Reset accumulation when not turning
                if self.was_turning:
                    self.accumulated_turning_degrees = 0.0
                self.was_turning = False
        else:
            self.turning_speed = 0.0
            if self.was_turning:
                self.accumulated_turning_degrees = 0.0
            self.was_turning = False
        
        # Store current velocity for next frame
        self.last_velocity = Vector2D(self.velocity.x, self.velocity.y)
        # Note: last_angle is now handled in the rotation tracking code
        
        super().update(dt, screen_width, screen_height)
        if self.invulnerable:
            self.invulnerable_time -= dt
            if self.invulnerable_time <= 0:
                self.invulnerable = False
        
        # Update rate of fire progression based on shooting state
        is_shooting = self.shoot_timer > 0
        self.update_rate_of_fire(dt, is_shooting)
        
        # Update shoot timer (affected by time dilation)
        if self.shoot_timer > 0:
            self.shoot_timer -= dt
        
        
        # Update shield recharge (subject to time dilation and multiplier)
        if self.shield_hits < self.max_shield_hits:
            # Apply multiplier to recharge speed (higher multiplier = faster recharge)
            # Use square root of multiplier to make recharge times increase half as much
            recharge_multiplier = max(0.1, math.sqrt(multiplier))  # Minimum 0.1x speed (10x slower max)
            self.shield_recharge_time += dt * recharge_multiplier
            if self.shield_recharge_time >= self.shield_recharge_duration:
                # Trigger celebration animation for any shield recharge
                self.shield_recharge_pulse_timer = self.shield_recharge_pulse_duration
                # Trigger ring pulse when shield charges
                self.shield_pulse_timer = 1.0  # 1 second pulse
                
                self.shield_hits += 1
                self.shield_recharge_time = 0
                
                # Reset ability flag for natural charging
                self.shield_charged_by_ability = False
                
                # Only trigger victory flash for 3rd shield (full shields)
                if self.shield_hits == self.max_shield_hits:
                    self.shield_full_flash_timer = self.shield_full_flash_duration
        
        # Update shield damage visual timer (NOT affected by time dilation - uses raw frame time)
        if self.shield_damage_timer > 0:
            self.shield_damage_timer -= pulse_dt
        
        # Update red flash timer (GAME TIME AFFECTED - uses dilated time)
        if self.red_flash_timer > 0:
            self.red_flash_timer -= dt
        
        # Update shield recharge pulse timer (NOT affected by time dilation - uses raw frame time)
        if self.shield_recharge_pulse_timer > 0:
            self.shield_recharge_pulse_timer -= pulse_dt
        
        # Update shield full flash timer (NOT affected by time dilation - uses raw frame time)
        if self.shield_full_flash_timer > 0:
            self.shield_full_flash_timer -= pulse_dt
            # Only activate hold stage for 3rd shield (full shields) - skip for 1st and 2nd
            if self.shield_full_flash_timer <= 0 and self.shield_hits == self.max_shield_hits:
                # Only activate hold stage for ability-charged shields
                if self.shield_charged_by_ability:
                    # Set hold duration for ability-charged shields
                    self.shield_full_hold_duration = 0.333  # 0.333 seconds for ability-charged shields
                    # Activate hold stage
                    self.shield_full_hold_timer = self.shield_full_hold_duration
                else:
                    # Skip hold stage for naturally charged shields - go directly to fade
                    self.shield_full_fade_timer = self.shield_full_fade_duration
                
                # Reset the ability flag
                self.shield_charged_by_ability = False
        
        # Update shield full hold timer (GAME TIME AFFECTED - uses dilated time)
        if self.shield_full_hold_timer > 0:
            self.shield_full_hold_timer -= dt
            # Start fade timer when hold ends
            if self.shield_full_hold_timer <= 0:
                self.shield_full_fade_timer = self.shield_full_fade_duration
        
        # Update shield full fade timer (GAME TIME AFFECTED - uses dilated time)
        if self.shield_full_fade_timer > 0:
            self.shield_full_fade_timer -= dt
        
        # Update ability timer (affected by time dilation only, not multiplier)
        if self.ability_charges < self.max_ability_charges and not self.ability_used:
            # Ability recharge is NOT affected by score multiplier
            self.ability_timer += dt
            # Determine charge duration based on game state and charge number
            if self.ability_charges == 0 and self.is_first_game:
                # First charge of first game: 5 seconds
                charge_duration = self.first_charge_duration
            else:
                # All other charges: 10 seconds
                charge_duration = self.ability_duration
            if self.ability_timer >= charge_duration:
                self.ability_charges += 1
                self.ability_timer = 0.0
                self.ability_ready = True  # Any charge makes ability ready
                
                # Trigger flash effect when ability charges
                self.ability_recharge_pulse_timer = self.ability_recharge_pulse_duration
                
                # Set flash count and fade duration based on charge number
                if self.ability_charges == 1:
                    self.ability_flash_count = 2  # 2 flashes for 1st charge
                    self.ability_fade_duration = 0.5  # 0.5 second fade
                elif self.ability_charges == self.max_ability_charges:
                    self.ability_flash_count = 4  # 4 flashes for 2nd charge
                    self.ability_fade_duration = 1.0  # 1.0 second fade
                    self.ability_hold_timer = self.ability_hold_duration
                    self.ability_fully_charged_pulse_timer = 0.0  # Start pulsing immediately
                
                # Mark that we're no longer in first game after first charge
                if self.is_first_game and self.ability_charges == 1:
                    self.is_first_game = False
        elif self.ability_used:
            # Reset ability after use
            self.ability_used = False
            self.ability_ready = self.ability_charges > 0
            if self.ability_charges > 0:
                self.ability_timer = 0.0
        
        # Update ability recharge pulse timer (NOT affected by time dilation - uses raw frame time)
        if self.ability_recharge_pulse_timer > 0:
            self.ability_recharge_pulse_timer -= pulse_dt
        
        # Update ability hold timer (GAME TIME AFFECTED - uses dilated time)
        if self.ability_hold_timer > 0:
            self.ability_hold_timer -= dt
            # Start fade timer when hold period ends
            if self.ability_hold_timer <= 0 and self.ability_charges == self.max_ability_charges:
                self.ability_fade_timer = self.ability_fade_duration
        
        # Update ability fade timer (GAME TIME AFFECTED - uses dilated time)
        if self.ability_fade_timer > 0:
            self.ability_fade_timer -= dt
            # Start pulsing when fade period ends
            if self.ability_fade_timer <= 0:
                self.ability_fully_charged_pulse_timer = 0.0
        
        # Update ability fully charged pulse timer (NOT affected by time dilation - uses raw frame time)
        if self.ability_charges == self.max_ability_charges and self.ability_fade_timer <= 0:
            self.ability_fully_charged_pulse_timer += pulse_dt
        
        # Update 2x charged ability particle generation (affected by time dilation)
        if self.ability_charges == self.max_ability_charges:
            self.ability_2x_particle_timer += dt
            # Update rotation for clockwise particle generation (1 rotation per 3 seconds)
            self.ability_2x_particle_rotation += self.ability_particle_rotation_speed * dt
        
        # Note: Ability particles now use player angle directly instead of rotation
        
        # Update ring pulse timers (NOT AFFECTED BY TIME DILATION - uses raw frame time)
        self.ring_pulse_timer += pulse_dt
        if self.shield_pulse_timer > 0:
            self.shield_pulse_timer -= pulse_dt
        
        # Apply speed decay
        if not self.thrusting:
            # Only decay when not thrusting
            current_speed = self.velocity.magnitude()
            speed_percent = current_speed / 1000.0 * 100  # Convert to percentage
            
            # Use much faster decay when speed is below 10%
            if speed_percent < 10.0:
                # Much faster decay to quickly reach 0% (doubled from 4th power to 8th power)
                decay_rate = self.speed_decay_rate ** 8  # 8th power for very fast decay (doubled)
            else:
                decay_rate = self.speed_decay_rate
            
            self.velocity.x *= decay_rate ** dt
            self.velocity.y *= decay_rate ** dt
        
        
        # Track speed for "interstellar" achievement (trigger once when reaching 1000 speed)
        current_speed = self.velocity.magnitude()
        max_speed = 1000.0  # 100% speed threshold
        self.is_at_max_speed = current_speed >= max_speed
        
        # Only trigger once when first crossing the 1000 speed threshold
        # Use a separate flag to track if we've already crossed the threshold
        if not hasattr(self, 'interstellar_threshold_crossed'):
            self.interstellar_threshold_crossed = False
            
        if not self.interstellar_threshold_crossed and current_speed >= max_speed:
            self.interstellar_shown = True
            self.interstellar_threshold_crossed = True
        
        # Calculate rotation speed scaling based on asteroid count
        # Normal speed at 20 asteroids, 50% speed at 100 asteroids
        asteroid_count = max(0, asteroid_count)  # Ensure non-negative
        if asteroid_count <= 20:
            rotation_scale = 1.0  # Full speed at 20 or fewer asteroids
        elif asteroid_count >= 100:
            rotation_scale = 0.5  # 50% speed at 100 or more asteroids
        else:
            # Linear interpolation between 20 and 100 asteroids
            # Scale from 1.0 at 20 to 0.5 at 100
            progress = (asteroid_count - 20) / (100 - 20)  # 0 to 1
            rotation_scale = 1.0 - (progress * (1.0 - 0.5))  # 1.0 to 0.5
        
        # Apply rotation smoothing with scaled speed (use raw frame time, not dilated time)
        self.apply_rotation(raw_dt, rotation_scale)
    
    def draw(self, screen):
        if not self.active:
            return
            
        # Draw ship using image (fallback image created if needed)
            rotation_angle = get_rotation_degrees(self.angle)
            draw_ship_with_effects(self, screen, self.position, rotation_angle, use_cache=True, draw_shadow=True)
        
        
    def draw_ship_shadow(self, screen):
        """Draw only the ship shadow (for proper layering)"""
        if not self.active:
            return
            
        # Use cached shadow image (fallback image created if needed)
            rotation_angle = get_rotation_degrees(self.angle)
            shadow_ship = image_cache.get_shadow_image(self.image, 1.1, 107, rotation_angle)
            shadow_rect = shadow_ship.get_rect(center=(int(self.position.x + 10), int(self.position.y + 10)))
            screen.blit(shadow_ship, shadow_rect, special_flags=pygame.BLEND_ALPHA_SDL2)
        
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
                
                # Try fire.gif image with rotation
                flame_image = pygame.image.load(get_resource_path("fire.gif"))
                # Scale thrust width based on player speed
                thrust_height = max(5, thrust_width // 2)  # Height is half the width
                flame_image = pygame.transform.scale(flame_image, (thrust_width, thrust_height))
                # Rotate the flame 180 degrees and match ship rotation
                rotated_flame = pygame.transform.rotate(flame_image, -math.degrees(self.angle) + 180)
                flame_rect = rotated_flame.get_rect(center=(int(flame_x), int(flame_y)))
                screen.blit(rotated_flame, flame_rect)
        
        # Draw shield with new opacity system
        if self.shield_hits > 0:
            shield_radius = self.radius + 15
            pulse_intensity = 0.0  # Start invisible
            fade_progress = 0.0  # Initialize fade_progress to prevent UnboundLocalError
            
            # Shield damage - remaining shields pulse 10%-100% (2 cycles in 0.5s) with 7% offset
            if self.shield_damage_timer > 0:
                pulse = (self.shield_damage_duration - self.shield_damage_timer) / self.shield_damage_duration
                pulse_intensity = 0.1 + 0.9 * math.sin(pulse * math.pi * 8)  # 4 cycles in 0.5s, 10%-100%
            # Shield recharge - current shields pulse 0%-100% (4 cycles in 1.0s) with 10% offset
            elif self.shield_recharge_pulse_timer > 0:
                pulse = (self.shield_recharge_pulse_duration - self.shield_recharge_pulse_timer) / self.shield_recharge_pulse_duration
                pulse_intensity = 0.5 + 0.5 * math.sin(pulse * math.pi * 8)  # 4 cycles in 1.0s, 0%-100%
            # Shield charging - ring that is charging fades 30%-100%, others pulse 1 cycle per 0.5s
            elif self.shield_hits < self.max_shield_hits:
                recharge_progress = self.shield_recharge_time / self.shield_recharge_duration
                pulse_intensity = 0.3 + 0.7 * recharge_progress  # Fade from 30% to 100%
            # Shield full flash - flash 0%-100% (4 times in 0.5s) with 10% offset
            elif self.shield_full_flash_timer > 0:
                pulse = (self.shield_full_flash_duration - self.shield_full_flash_timer) / self.shield_full_flash_duration
                pulse_intensity = 0.5 + 0.5 * math.sin(pulse * math.pi * 8)  # 4 cycles in 0.5s, 0%-100%
            # Shield full hold - 100% opacity
            elif self.shield_full_hold_timer > 0:
                pulse_intensity = 1.0  # Full opacity during hold
            # Shield full fade - fade from 100% to 0% (smooth animation)
            elif self.shield_full_fade_timer > 0:
                fade_progress = self.shield_full_fade_timer / self.shield_full_fade_duration
                # Smooth fade using ease-out curve
                pulse_intensity = fade_progress * fade_progress  # Quadratic ease-out: 100% to 0%
            # Otherwise - invisible (full shields after fade)
            
            # Only draw circles if they should be visible
            if pulse_intensity > 0:
                # Draw circles for each shield hit (outline only, no fill)
                for i in range(self.shield_hits):
                    # Add 10% offset between shield rings for pulsing effect
                    shield_phase = (self.shield_pulse_timer * 2) + (i * 0.10 * math.pi)  # 1 pulse per second, 10% offset
                    shield_pulse = 0.5 + 0.5 * math.sin(shield_phase)  # 0.5 to 1.0 multiplier
                    
                    # During celebration animation (recharge pulse), show only current shield level
                    if self.shield_recharge_pulse_timer > 0:
                        # Show only rings up to current shield level during celebration
                        if i < self.shield_hits:
                            # Enhanced ripple effect with better oscillation for 2nd recharge
                            if self.shield_hits == 2:
                                # Special oscillation for 2 rings - create wave that moves between them
                                wave_phase = (self.shield_pulse_timer * 4) + (i * 0.5 * math.pi)  # 4x speed, 50% offset
                                # Create alternating pattern: ring 0 bright when ring 1 dim, and vice versa
                                oscillation = 0.2 + 0.8 * math.sin(wave_phase)  # 20%-100% range
                                ring_intensity = pulse_intensity * oscillation
                            else:
                                # Standard ripple for 1st and 3rd recharge
                                ripple_phase = (self.shield_pulse_timer * 3) + (i * 0.3 * math.pi)  # 3x faster, 30% offset
                                ripple_pulse = 0.3 + 0.7 * math.sin(ripple_phase)  # 30%-100% range
                                ring_intensity = pulse_intensity * ripple_pulse
                        else:
                            continue  # Skip drawing rings beyond current level
                    # For charging shields, only the charging ring fades, others pulse
                    elif self.shield_hits < self.max_shield_hits and i == self.shield_hits - 1:
                        # This is the charging ring - use fade intensity
                        ring_intensity = pulse_intensity
                    elif self.shield_hits < self.max_shield_hits:
                        # Handle different shield charging states
                        if self.shield_hits == 1:
                            # 1st shield fully charged, 2nd charging - keep 1st at 100% opacity
                            if i == 0:  # First ring (fully charged)
                                ring_intensity = 1.0  # 100% opacity
                            else:  # Second ring (charging)
                                ring_intensity = pulse_intensity  # Use charging intensity
                        elif self.shield_hits == 2:
                            # 2nd shield fully charged, 3rd charging - pulse both rings like ability rings
                            pulse_cycle = (self.ring_pulse_timer * 1) % 1.0  # 1-second cycle
                            # Add 33% offset per ring (0%, 33% for 2 rings)
                            ring_offset = i * 0.33
                            pulse_progress = (pulse_cycle + ring_offset) % 1.0
                            # Pulse from 25% to 100% opacity
                            ring_intensity = 0.25 + 0.75 * (0.5 + 0.5 * math.sin(pulse_progress * 2 * math.pi))
                        elif self.shield_hits == 3:
                            # All 3 shields fully charged - use ability-style pulsing for all rings
                            pulse_cycle = (self.ring_pulse_timer * 1) % 1.0  # 1-second cycle
                            # Add 33% offset per ring (0%, 33%, 66% for 3 rings)
                            ring_offset = i * 0.33
                            pulse_progress = (pulse_cycle + ring_offset) % 1.0
                            # Pulse from 25% to 100% opacity
                            ring_intensity = 0.25 + 0.75 * (0.5 + 0.5 * math.sin(pulse_progress * 2 * math.pi))
                        else:
                            # Other rings - pulse 2 cycles per 0.5s (game time affected)
                            pulse_cycle = (self.shield_pulse_timer * 4) % 0.5  # 0.5 second cycle with 2 pulses
                            pulse_progress = pulse_cycle / 0.5
                            ring_intensity = 0.1 + 0.9 * (0.5 + 0.5 * math.sin(pulse_progress * 4 * math.pi))  # 10%-100%
                    else:
                        # Full shields - use main pulse intensity with 10% delay per ring
                        if self.shield_full_fade_timer > 0:
                            # Calculate individual ring fade with 10% delay per ring
                            # Inside ring (i=0) fades first, outside ring (i=2) fades last
                            ring_delay = i * 0.1  # 10% delay per ring (0%, 10%, 20%)
                            ring_fade_progress = max(0, min(1, (fade_progress - ring_delay) / (1 - ring_delay)))
                            ring_intensity = ring_fade_progress * ring_fade_progress  # Quadratic ease-out
                        else:
                            ring_intensity = pulse_intensity
                    
                    # For 1st shield fully charged, don't apply shield_pulse to keep it at 100% opacity
                    if self.shield_hits == 1 and i == 0:
                        alpha = int(255 * ring_intensity)  # No shield_pulse multiplier
                    else:
                        alpha = int(255 * ring_intensity * shield_pulse)
                    alpha = max(0, min(255, alpha))  # Clamp alpha to valid range
                    color = (0, 100, 255, alpha)
                    # Draw outline circle (width parameter makes it outline only)
                    # Ensure minimum width of 1 to avoid filled circles
                    # For 1st shield fully charged, don't apply shield_pulse to width either
                    if self.shield_hits == 1 and i == 0:
                        width = max(1, int(4 * ring_intensity))  # 2x thickness, no shield_pulse multiplier
                    else:
                        width = max(1, int(4 * ring_intensity * shield_pulse))  # 2x thickness as ability rings
                    
                    # Create surface with alpha for transparency (like ability rings)
                    circle_radius = shield_radius + i * 5
                    circle_surface = pygame.Surface((circle_radius * 2, circle_radius * 2), pygame.SRCALPHA)
                    pygame.draw.circle(circle_surface, (0, 100, 255, alpha), 
                                    (circle_radius, circle_radius), 
                                    circle_radius, width)
                    screen.blit(circle_surface, (int(self.position.x - circle_radius), int(self.position.y - circle_radius)))
        
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
        """Draw ability rings with shield-like recharge behavior"""
        base_radius = self.radius + 10  # Inside the smallest shield
        
        # Only show ability rings when charging or during pulse effects
        if self.ability_charges < self.max_ability_charges or self.ability_recharge_pulse_timer > 0 or self.ability_hold_timer > 0 or self.ability_fade_timer > 0 or (self.ability_charges == self.max_ability_charges and self.ability_fade_timer <= 0):
            pulse_intensity = 0.0  # Start invisible
            
            # Flash effect when ability just recharged
            if self.ability_recharge_pulse_timer > 0:
                pulse = (self.ability_recharge_pulse_duration - self.ability_recharge_pulse_timer) / self.ability_recharge_pulse_duration
                # Flash 0% to 100% opacity (2 times for 1st charge, 3 times for 2nd charge in 0.5 seconds)
                flash_frequency = self.ability_flash_count * 2  # 4 for 1st charge, 6 for 2nd charge
                pulse_intensity = 0.5 + 0.5 * math.sin(pulse * math.pi * flash_frequency)  # 0% to 100%
            # Charging phase
            elif self.ability_charges < self.max_ability_charges:
                # Calculate progress for current charge
                if self.ability_charges == 0:
                    charge_duration = self.first_charge_duration if self.is_first_game else self.ability_duration
                    ability_progress = self.ability_timer / charge_duration
                else:
                    ability_progress = self.ability_timer / self.ability_duration
                
                # Opacity fade: 0% at 0% progress, 75% at 99% progress, 100% at 100% progress
                if ability_progress < 0.99:
                    opacity_progress = ability_progress / 0.99  # Scale 0-99% to 0-1
                    pulse_intensity = 0.75 * opacity_progress  # 0% to 75%
                else:
                    pulse_intensity = 0.75 + 0.25 * ((ability_progress - 0.99) / 0.01)  # 75% to 100% in last 1%
                
                # Add pulsing effect during recharge
                pulse = ability_progress * math.pi * 4  # 4 pulses during recharge
                pulse_intensity = pulse_intensity * (0.5 + 0.5 * math.sin(pulse))
            # Hold period - 100% opacity
            elif self.ability_hold_timer > 0:
                pulse_intensity = 1.0  # Full opacity during hold
            # Fade period - fade from 100% to 33% opacity (smooth animation)
            elif self.ability_fade_timer > 0:
                fade_progress = self.ability_fade_timer / self.ability_fade_duration
                # Smooth fade using ease-out curve
                smooth_fade = fade_progress * fade_progress  # Quadratic ease-out
                pulse_intensity = 0.33 + 0.67 * smooth_fade  # 100% to 33%
            # Pulsing period - pulse between 25% and 100% opacity with 33% offset per ring
            elif self.ability_charges == self.max_ability_charges:
                # This will be calculated per ring in the drawing loop below
                pulse_intensity = 1.0  # Base intensity, will be modified per ring
            # Otherwise - invisible
            
            # Only draw rings if they should be visible
            if pulse_intensity > 0:
                # Draw rings for each charge
                for charge in range(self.max_ability_charges):
                    ability_radius = base_radius + (charge * 3)  # 3 pixel separation
                    
                    # Determine if this charge is ready
                    is_ready = charge < self.ability_charges
                    
                    if is_ready:
                        # Ready phase: full circle
                        # Color based on number of charges
                        if self.ability_charges == 1:  # 1 charge = purple (ready state)
                            red = 147
                            green = 20
                            blue = 255
                        else:  # 2 charges = hot pink
                            red = 255
                            green = 20
                            blue = 147
                        
                        # Apply opacity based on charge state
                        if self.ability_charges == 1 and charge == 0:
                            # First ring after charging: keep at 100% opacity
                            base_opacity = 1.0
                        elif self.ability_charges == 2 and charge == 0:
                            # First ring when second is charging: keep at 100% opacity
                            base_opacity = 1.0
                        elif self.ability_charges == self.max_ability_charges:
                            # Both charges at 100%: rhythmic pulse with 33% offset per ring
                            pulse_cycle = (self.ability_fully_charged_pulse_timer * 1) % 1.0  # 1-second cycle
                            # Add 33% offset per ring (0%, 33%, 66% for 3 rings)
                            ring_offset = charge * 0.33
                            pulse_progress = (pulse_cycle + ring_offset) % 1.0
                            # Pulse from 25% to 100% opacity
                            base_opacity = 0.25 + 0.75 * (0.5 + 0.5 * math.sin(pulse_progress * 2 * math.pi))
                        else:
                            # Normal pulsing: 33%-100% opacity range
                            base_opacity = 0.33 + 0.67 * pulse_intensity
                        alpha = int(255 * base_opacity)
                        color = (red, green, blue, alpha)
                        
                        # Draw full circle with shield-like thickness
                        # Thickness varies from 1 to 3 based on pulse intensity
                        thickness = 1 + int(2 * pulse_intensity)  # 1 to 3 thickness
                        width = max(1, thickness)
                        
                        # Create surface with alpha for transparency
                        circle_surface = pygame.Surface((ability_radius * 2, ability_radius * 2), pygame.SRCALPHA)
                        pygame.draw.circle(circle_surface, (red, green, blue, alpha), 
                                        (ability_radius, ability_radius), 
                                        ability_radius, width)
                        screen.blit(circle_surface, (int(self.position.x - ability_radius), int(self.position.y - ability_radius)))
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
                                
                                # Color and opacity based on which ring is charging
                                if charge == 0:
                                    # First ring: original purple with opacity fade (0% to 100%)
                                    if ability_progress < 0.99:
                                        opacity_progress = ability_progress / 0.99  # Scale 0-99% to 0-1
                                        charging_opacity = opacity_progress  # 0% to 100%
                                    else:
                                        charging_opacity = 1.0  # 100% at completion
                                    color = (128, 0, 255, int(255 * charging_opacity))  # Original purple
                                else:
                                    # Second ring: brighter purple at 100% opacity
                                    charging_opacity = 1.0  # Always 100% opacity
                                    color = (147, 20, 255, 255)  # Brighter purple at full opacity
                                
                                # Draw arc with shield-like thickness
                                # Thickness varies from 1 to 3 based on charging progress
                                thickness = 1 + int(2 * ability_progress)  # 1 to 3 thickness
                                width = max(1, thickness)
                                pygame.draw.arc(arc_surface, color, pygame.Rect(0, 0, arc_rect.width, arc_rect.height), start_angle, end_angle, width)
                                screen.blit(arc_surface, arc_rect)
    
    def update_rate_of_fire(self, dt, is_shooting):
        """Update rate of fire with aggressive ramp up to peak, then gentle ramp down over sustained shooting"""
        if is_shooting:
            # Only progress the curve when actively shooting
            self.rof_progression_time += dt
            
            # Check if we just reached the peak
            if self.rof_progression_time >= self.rof_peak_time and not self.rof_peak_reached:
                self.rof_peak_reached = True
                # Return True to indicate peak was reached (for spark effect)
                return True
            
            if self.rof_progression_time <= self.rof_peak_time:
                # Aggressive ramp up phase: 0.09s to 0.042s over 0.5 seconds
                progress = self.rof_progression_time / self.rof_peak_time
                # More aggressive curve for ramp up (quartic)
                smooth_progress = progress * progress * progress * progress
                self.shoot_interval = 0.09 + (self.min_shoot_interval - 0.09) * smooth_progress - self.asteroid_interval_bonus
            else:
                # Gentle ramp down phase: 0.042s to 0.17s over remaining time
                remaining_time = self.rof_curve_duration - self.rof_peak_time
                progress = (self.rof_progression_time - self.rof_peak_time) / remaining_time
                progress = min(progress, 1.0)  # Cap at 1.0
                # Gentle ease-out curve for ramp down (quadratic)
                smooth_progress = 1 - (1 - progress) * (1 - progress)
                self.shoot_interval = self.min_shoot_interval + (self.max_shoot_interval - self.min_shoot_interval) * smooth_progress - self.asteroid_interval_bonus
        else:
            # Reset curve when not shooting
            self.rof_progression_time = 0
            self.rof_peak_reached = False
            self.shoot_interval = 0.09 - self.asteroid_interval_bonus  # Start slow
        
        return False

class BossWeaponBullet(GameObject):
    """Special bullet class for boss weapon - uses starshot.gif (already 2x size)"""
    def __init__(self, x, y, vx, vy, angle=None):
        super().__init__(x, y, vx, vy)
        # No lifespan limit - bullets persist until collision
        self.is_ufo_bullet = True  # Use starshot.gif
        
        # Use provided angle or calculate from velocity for rotation
        if angle is not None:
            self.angle = angle
        else:
            self.angle = math.atan2(vy, vx)
        
        # Force exact dimensions for starshot.gif
        self.scaled_width = 32
        self.scaled_height = 8
        
        # Load bullet image and scale to exact dimensions
        try:
            self.image = pygame.image.load(get_resource_path("starshot.gif"))
            # Scale to exact 32x8 dimensions regardless of original image size
            self.image = pygame.transform.scale(self.image, (self.scaled_width, self.scaled_height))
        except Exception as e:
            # Fallback to tieshot.gif if starshot.gif doesn't exist
            try:
                self.image = pygame.image.load(get_resource_path("tieshot.gif"))
                # Scale to exact 32x8 dimensions
                self.image = pygame.transform.scale(self.image, (self.scaled_width, self.scaled_height))
            except Exception as e2:
                self.image = None
        
        # Dynamic hitbox radius based on actual bullet dimensions
        self.radius = max(2, min(self.scaled_width, self.scaled_height) // 2)
    
    def update(self, dt, screen_width=None, screen_height=None):
        # No lifespan limit - bullets persist until collision
        super().update(dt, screen_width, screen_height)
    
    def draw(self, screen):
        if self.active:
            if self.image:
                # Draw bullet using cached rotated image
                rotation_degrees = -math.degrees(self.angle)
                rotated_image = image_cache.get_rotated_image(self.image, rotation_degrees)
                bullet_rect = rotated_image.get_rect(center=(int(self.position.x), int(self.position.y)))
                screen.blit(rotated_image, bullet_rect)
            else:
                # Fallback to ellipse - match actual bullet dimensions
                color = RED
                # Draw ellipse to match bullet shape and size
                ellipse_rect = pygame.Rect(
                    int(self.position.x - self.scaled_width // 2),
                    int(self.position.y - self.scaled_height // 2),
                    self.scaled_width,
                    self.scaled_height
                )
                pygame.draw.ellipse(screen, color, ellipse_rect)


class Bullet(GameObject):
    def __init__(self, x, y, vx, vy, is_ufo_bullet=False, angle=None):
        super().__init__(x, y, vx, vy)
        self.max_distance = 1000.0  # units - distance-based expiration
        self.distance_traveled = 0.0
        self.is_ufo_bullet = is_ufo_bullet
        # Use provided angle or calculate from velocity for rotation
        if angle is not None:
            self.angle = angle
        else:
            self.angle = math.atan2(vy, vx)
        
        # Calculate velocity-based scaling (0.75x to 1.5x based on speed)
        velocity_magnitude = math.sqrt(vx*vx + vy*vy)
        # Scale: 300=0.75x, 400=1.0x, 500=1.5x
        if velocity_magnitude <= 300:
            self.velocity_scale = 0.75
        elif velocity_magnitude >= 500:
            self.velocity_scale = 1.5
        elif velocity_magnitude <= 400:
            # Linear interpolation between 300 and 400 (0.75x to 1.0x)
            progress = (velocity_magnitude - 300) / (400 - 300)
            self.velocity_scale = 0.75 + (progress * 0.25)  # 0.75 to 1.0
        else:
            # Linear interpolation between 400 and 500 (1.0x to 1.5x)
            progress = (velocity_magnitude - 400) / (500 - 400)
            self.velocity_scale = 1.0 + (progress * 0.5)  # 1.0 to 1.5
        
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
                self.image = pygame.image.load(get_resource_path("tieshot.gif"))
            else:
                self.image = pygame.image.load(get_resource_path("shot.gif"))
            # Scale bullet based on velocity
            self.image = pygame.transform.scale(self.image, (self.scaled_width, self.scaled_height))
        except Exception as e:
            self.image = None
    
    def update(self, dt, screen_width=None, screen_height=None):
        # Store previous position for distance calculation
        prev_x = self.position.x
        prev_y = self.position.y
        
        super().update(dt, screen_width, screen_height)
        
        # Calculate distance traveled this frame, accounting for screen wrapping
        width = screen_width if screen_width is not None else SCREEN_WIDTH
        height = screen_height if screen_height is not None else SCREEN_HEIGHT
        
        # Calculate actual distance traveled, accounting for screen wrapping
        dx = self.position.x - prev_x
        dy = self.position.y - prev_y
        
        # Check if wrapping occurred and adjust distance calculation
        if abs(dx) > width / 2:  # Likely wrapped horizontally
            dx = dx - width if dx > 0 else dx + width
        if abs(dy) > height / 2:  # Likely wrapped vertically
            dy = dy - height if dy > 0 else dy + height
            
        distance_this_frame = math.sqrt(dx*dx + dy*dy)
        self.distance_traveled += distance_this_frame
        
        # Check if bullet has traveled maximum distance
        if self.distance_traveled >= self.max_distance:
            self.active = False
    
    def draw(self, screen):
        if self.active:
            if self.image:
                # Draw bullet using cached rotated image
                rotation_degrees = -math.degrees(self.angle)
                rotated_image = image_cache.get_rotated_image(self.image, rotation_degrees)
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
    def __init__(self, x, y, size=3, level=1):
        super().__init__(x, y)
        self.size = size  # 9=XXXL, 8=XXL, 7=XL, 6=L, 5=M, 4=S, 3=XS, 2=XXS, 1=XXS
        self.creation_time = time.time()  # Track when asteroid was created
        
        # Calculate shadow probability based on level: (100 - (current level * 10))% chance, minimum 1%
        shadow_probability = max(0.01, (100 - (level * 10)) / 100.0)
        self.has_shadow = random.random() < shadow_probability
        
        # Match hitbox to visual size better (custom sizes)
        base_radius = 50  # Base radius for 100% scale
        scale_factors = {9: 7.5, 8: 6.0, 7: 4.5, 6: 3.0, 5: 1.5, 4: 1.0, 3: 0.75, 2: 0.5, 1: 0.25}
        
        # Optimized hitbox scale and offset values from testing
        hitbox_scales = {9: 0.9310, 8: 0.9520, 7: 0.9760, 6: 0.9830, 5: 1.0000, 4: 1.0000, 3: 1.0000, 2: 1.0000, 1: 1.0000}
        hitbox_offset_x = {9: 8.0000, 8: 6.0000, 7: 5.0000, 6: 3.0000, 5: 2.0000, 4: 1.0000, 3: 1.0000, 2: 0.6667, 1: 0.3333}
        hitbox_offset_y = {9: -17.0000, 8: -15.0000, 7: -9.0000, 6: -5.0000, 5: -3.0000, 4: -2.0000, 3: -1.3333, 2: -0.6667, 1: -0.3333}
        
        # Calculate optimized hitbox radius
        base_radius_calc = base_radius * scale_factors.get(size, 1.0) * 0.925  # Original calculation
        self.radius = int(base_radius_calc * hitbox_scales.get(size, 1.0))  # Apply optimized scale
        
        # Store hitbox offset values
        self.hitbox_offset_x = hitbox_offset_x.get(size, 0.0)
        self.hitbox_offset_y = hitbox_offset_y.get(size, 0.0)
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
            self.image = pygame.image.load(get_resource_path("roid.gif"))
            self.image = self.image.convert_alpha()
            # New size hierarchy scaling (custom sizes)
            base_size = 100  # Base size for 100% scale
            scale_factors = {9: 7.5, 8: 6.0, 7: 4.5, 6: 3.0, 5: 1.5, 4: 1.0, 3: 0.75, 2: 0.5, 1: 0.25}
            scale = int(base_size * scale_factors.get(size, 1.0))
            self.image = pygame.transform.smoothscale(self.image, (scale, scale))
        except:
            # If image loading fails, create a simple fallback image
            self.image = self.create_fallback_image()
    
    def get_hitbox_center(self):
        """Get the actual hitbox center position (asteroid position + offset)"""
        return Vector2D(
            self.position.x + self.hitbox_offset_x,
            self.position.y + self.hitbox_offset_y
        )
    
    def draw_shadow_only(self, screen, screen_width=None, screen_height=None):
        """Draw only the shadow of the asteroid (for proper layering)"""
        if not self.active or not self.has_shadow:
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
        
        # Draw shadow at all calculated positions
        for pos_x, pos_y in positions:
            # Use cached shadow image (fallback image created if needed)
                rotation_angle = -math.degrees(self.rotation_angle)
                # Dynamic shadow size: (100% + (3 * size level)%) = 1.0 + (0.03 * size)
                shadow_scale = 1.0 + (0.03 * self.size)
                # Dynamic shadow offset: (10 * size level) pixels
                shadow_offset = 10 * self.size
                # Dynamic shadow opacity: Custom formula for specified values
                if self.size == 1:
                    shadow_alpha = int(255 * 0.40)  # 40%
                elif self.size == 2:
                    shadow_alpha = int(255 * 0.50)  # 50%
                elif self.size == 3:
                    shadow_alpha = int(255 * 0.55)  # 55%
                elif self.size == 4:
                    shadow_alpha = int(255 * 0.60)  # 60%
                elif self.size == 5:
                    shadow_alpha = int(255 * 0.70)  # 70%
                elif self.size == 6:
                    shadow_alpha = int(255 * 0.80)  # 80%
                elif self.size == 7:
                    shadow_alpha = int(255 * 0.85)  # 85%
                elif self.size == 8:
                    shadow_alpha = int(255 * 0.90)  # 90%
                else:  # Size 9 and above - no shadows
                    shadow_alpha = 0
                if shadow_alpha > 0:  # Only draw shadow if opacity > 0
                    shadow_asteroid = image_cache.get_shadow_image(self.image, shadow_scale, shadow_alpha, rotation_angle)
                    shadow_rect = shadow_asteroid.get_rect(center=(int(pos_x + shadow_offset), int(pos_y + shadow_offset)))
                    screen.blit(shadow_asteroid, shadow_rect, special_flags=pygame.BLEND_ALPHA_SDL2)
    
    def draw_main_only(self, screen, screen_width=None, screen_height=None):
        """Draw only the main asteroid (without shadow, for proper layering)"""
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
            # Draw asteroid using image (fallback image created if needed)
            rotated_asteroid = pygame.transform.rotate(self.image, -math.degrees(self.rotation_angle))
            asteroid_rect = rotated_asteroid.get_rect(center=(int(pos_x), int(pos_y)))
            screen.blit(rotated_asteroid, asteroid_rect)
    
    def create_fallback_image(self):
        """Create a simple circular fallback image when roid.gif fails to load"""
        # Create a simple circular image as fallback
        size = int(self.radius * 2)
        surface = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(surface, WHITE, (size // 2, size // 2), int(self.radius), 2)
        return surface
    
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
            # Draw asteroid using cached rotated image (fallback image created if needed)
            rotation_degrees = -math.degrees(self.rotation_angle)
            rotated_asteroid = image_cache.get_rotated_image(self.image, rotation_degrees)
            asteroid_rect = rotated_asteroid.get_rect(center=(int(pos_x), int(pos_y)))
            
            # Draw shadow first (behind the asteroid) - all asteroids have shadows
            if self.has_shadow:
                # Dynamic shadow size: (100% + (3 * size level)%) = 1.0 + (0.03 * size)
                shadow_scale = 1.0 + (0.03 * self.size)
                # Dynamic shadow offset: (10 * size level) pixels
                shadow_offset = 10 * self.size
                # Dynamic shadow opacity: Custom formula for specified values
                if self.size == 1:
                    shadow_alpha = int(255 * 0.40)  # 40%
                elif self.size == 2:
                    shadow_alpha = int(255 * 0.50)  # 50%
                elif self.size == 3:
                    shadow_alpha = int(255 * 0.55)  # 55%
                elif self.size == 4:
                    shadow_alpha = int(255 * 0.60)  # 60%
                elif self.size == 5:
                    shadow_alpha = int(255 * 0.70)  # 70%
                elif self.size == 6:
                    shadow_alpha = int(255 * 0.80)  # 80%
                elif self.size == 7:
                    shadow_alpha = int(255 * 0.85)  # 85%
                elif self.size == 8:
                    shadow_alpha = int(255 * 0.90)  # 90%
                else:  # Size 9 and above - no shadows
                    shadow_alpha = 0
                if shadow_alpha > 0:  # Only draw shadow if opacity > 0
                    shadow_asteroid = image_cache.get_shadow_image(self.image, shadow_scale, shadow_alpha, rotation_degrees)
                    shadow_rect = shadow_asteroid.get_rect(center=(int(pos_x + shadow_offset), int(pos_y + shadow_offset)))
                    screen.blit(shadow_asteroid, shadow_rect, special_flags=pygame.BLEND_ALPHA_SDL2)
            
            # Draw main asteroid
            screen.blit(rotated_asteroid, asteroid_rect)
        
        
    
    def split(self, projectile_velocity=None, level=1):
        # Special XXS splitting behavior
        if self.size == 2:  # XXS asteroid
            if random.random() < 0.25:  # 25% chance to split into 2 XXXS
                new_asteroids = []
                for i in range(2):
                    new_asteroid = Asteroid(self.position.x, self.position.y, 1, level)  # XXXS
                    
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
                new_asteroid = Asteroid(self.position.x, self.position.y, self.size - 1, level)
                
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

class AbilityAsteroid(Asteroid):
    """Special asteroid that grants ability charges when destroyed"""
    
    def __init__(self, x, y, size=3, level=1, ability_charges=1):
        super().__init__(x, y, size, level)
        self.ability_charges = ability_charges  # Number of ability charges to grant
        self.is_ability_asteroid = True
        
        # Visual distinction - add a glowing effect
        self.glow_timer = 0.0
        self.glow_duration = 2.0  # Glow cycle duration
        self.glow_intensity = 0.0
        
        # Different color tint for ability asteroids
        self.color_tint = (100, 255, 100)  # Green tint for ability asteroids
        
    def update(self, dt, screen_width=None, screen_height=None, player_speed=0, time_dilation_factor=1.0):
        """Update asteroid with glowing effect"""
        super().update(dt, screen_width, screen_height, player_speed, time_dilation_factor)
        
        # Update glow effect
        self.glow_timer += dt
        if self.glow_timer >= self.glow_duration:
            self.glow_timer = 0.0
        
        # Calculate glow intensity (0.5 to 1.0)
        self.glow_intensity = 0.5 + 0.5 * math.sin((self.glow_timer / self.glow_duration) * 2 * math.pi)
    
    def draw(self, screen, screen_width=None, screen_height=None):
        """Draw ability asteroid with special glowing effect"""
        if not self.active:
            return
        
        # Call parent draw method first
        super().draw(screen, screen_width, screen_height)
        
        # Add glowing ring effect
        if self.glow_intensity > 0:
            # Draw glowing ring around the asteroid
            glow_radius = int(self.radius * (1.2 + 0.3 * self.glow_intensity))
            glow_alpha = int(100 * self.glow_intensity)
            
            # Create a surface for the glow effect
            glow_surface = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
            glow_color = (*self.color_tint, glow_alpha)
            
            # Draw the glow ring
            pygame.draw.circle(glow_surface, glow_color, (glow_radius, glow_radius), glow_radius, 3)
            
            # Blit the glow effect
            glow_rect = glow_surface.get_rect(center=(int(self.position.x), int(self.position.y)))
            screen.blit(glow_surface, glow_rect)
    
    def split(self, projectile_velocity=None, level=1):
        """Ability asteroids don't split - they just grant ability charges"""
        return []
    
    def grant_ability_charges(self, ship):
        """Grant ability charges to the ship"""
        if hasattr(ship, 'ability_charges') and hasattr(ship, 'max_ability_charges'):
            ship.ability_charges = min(ship.ability_charges + self.ability_charges, ship.max_ability_charges)
            return True
        return False

class AdvancedUFO(GameObject):
    def __init__(self, x, y, ai_personality="aggressive"):
        super().__init__(x, y)
        
        # Basic properties
        self.base_radius = 26  # Base radius for scaling
        self.radius = 26  # Current radius (will be scaled)
        self.speed = 100
        self.max_speed = 150
        self.acceleration = 50
        self.rotation_speed = 2.0  # Base rotation speed for UFOs
        
        # AI Personality Types
        self.personality = ai_personality  # "aggressive", "defensive", "tactical", "swarm", "deadly"
        
        # Hitbox scaling and offset system
        self.hitbox_scale = 1.0  # Scale factor for hitbox
        self.hitbox_offset_x = 0  # Horizontal offset in pixels
        self.hitbox_offset_y = 0  # Vertical offset in pixels
        
        # Set personality-specific hitbox data
        self.set_personality_hitbox_data()
        
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
        self.individual_accuracy_multiplier = 1.0  # Fixed at 1.0 for consistent boss accuracy
        self.aggression_level = 1.0
        self.bullets_fired = 0  # Track bullets fired by this UFO
        self.max_bullets = 5  # Will be set based on level
        
        # Set accuracy modifiers based on personality - ALL BOSS SHOTS ARE 150% ACCURATE
        # All UFOs now have 150% accuracy regardless of personality
        self.accuracy_modifier = 1.5  # 150% accuracy for all boss shots
        
        # Deadly AI enhancements
        if ai_personality == "deadly":
            self.speed = 120  # 20% faster
            self.max_speed = 180  # 20% faster max speed
            self.shoot_interval = 0.7  # 30% faster shooting
            # accuracy_modifier already set to 1.5 above for all bosses
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
        
        # Tweening system for smooth movement
        self.tweened_velocity = Vector2D(self.velocity.x, self.velocity.y)  # Start with current velocity
        self.target_velocity = Vector2D(0, 0)  # AI-calculated target velocity
        self.velocity_tween_speed = 3.0  # How fast to interpolate (higher = more responsive)
        self.position_tween_speed = 2.0  # How fast to interpolate position changes
        
        # Spinout "Burst into Flames" effect properties
        self.spinout_active = False
        self.spinout_timer = 0.0
        self.spinout_duration = 3.0  # 3 seconds duration
        self.spinout_flame_scale = 0.0  # 0% to 100% scaling over random 1-3 seconds
        self.spinout_flame_scale_timer = 0.0
        self.spinout_flame_scale_duration = random.uniform(1.0, 3.0)  # Random 1-3 seconds to scale up
        self.spinout_spark_timer = 0.0
        self.spinout_spark_interval = 1.0 / random.uniform(20.1, 42)  # 20-42 sparks per second (avoid division by zero)
        self.spinout_movement_type = None  # "straight" or "spiral"
        self.spinout_spiral_angle = 0.0
        self.spinout_spiral_radius = 0.0
        self.spinout_spiral_center = Vector2D(0, 0)
        self.spinout_rotation_speed_multiplier = 1.0  # Will be set to random 1x-10x
        self.spinout_target_rotation_speed = 0.0
        self.spinout_original_max_speed = self.max_speed
        self.spinout_collision_delay_timer = 0.0
        self.spinout_collision_delay = random.uniform(0.5, 1.5)  # Random delay 0.5-1.5 seconds before explosion
        
        # Visual rotation angle for spinout flame (separate from movement angle)
        self.visual_rotation_angle = 0.0
        
        # UFO smoke.gif properties (similar to player fire system)
        self.thrusting = True  # UFOs always have thrust
        
        # Load UFO image based on personality
        try:
            # Map personality to image file
            image_files = {
                "aggressive": "tie.gif",
                "defensive": "tieb.gif", 
                "deadly": "tiei.gif",
                "tactical": "tiea.gif",
                "swarm": "tiefo.gif"
            }
            
            # Get image file for this personality, default to tie.gif
            image_file = image_files.get(self.personality, "tie.gif")
            
            self.image = pygame.image.load(get_resource_path(image_file))
            self.image = self.image.convert_alpha()
            
            # Set image size based on personality and hitbox scale
            if self.personality == "swarm":
                base_image_size = 48
            else:
                base_image_size = 52  # Base size for others
                
            # Scale image based on visual scale (hitbox_scale is used for visual scaling only)
            image_size = int(base_image_size * self.hitbox_scale)
            self.image = pygame.transform.smoothscale(self.image, (image_size, image_size))
            
            # Apply image-specific transformations
            if self.personality == "aggressive":
                # Flip tie.gif horizontally then rotate 90 degrees clockwise then rotate 180 degrees
                self.image = pygame.transform.flip(self.image, True, False)
                self.image = pygame.transform.rotate(self.image, -90)
                self.image = pygame.transform.rotate(self.image, 180)
            elif self.personality == "deadly":
                # Rotate tiei.gif 90 degrees counter-clockwise, flip horizontally, flip vertically, and rotate 180 degrees
                self.image = pygame.transform.rotate(self.image, 90)
                self.image = pygame.transform.flip(self.image, True, False)
                self.image = pygame.transform.flip(self.image, False, True)
                self.image = pygame.transform.rotate(self.image, 180)
            elif self.personality in ["defensive", "tactical", "swarm"]:
                # Flip tieb.gif, tiea.gif, and tiefo.gif horizontally then rotate 90 degrees counter-clockwise
                self.image = pygame.transform.flip(self.image, True, False)
                self.image = pygame.transform.rotate(self.image, 90)
        except Exception as e:
            self.image = None
        
        # Load spinout flame image
        try:
            self.spinout_flame_image = pygame.image.load(get_resource_path("spinout.gif"))
            self.spinout_flame_image = self.spinout_flame_image.convert_alpha()
            # Scale to 10% (95% smaller than original)
            original_size = self.spinout_flame_image.get_size()
            self.spinout_flame_image = pygame.transform.smoothscale(
                self.spinout_flame_image, 
                (int(original_size[0] * 0.1), int(original_size[1] * 0.1))
            )
        except Exception as e:
            self.spinout_flame_image = None
        
        # Update hitbox based on personality data
        self.update_hitbox()
    
    def set_personality_hitbox_data(self):
        """Set hitbox scale and offset data based on UFO personality"""
        hitbox_data = {
            "aggressive": {
                "scale": 1.000,
                "offset_x": 0,
                "offset_y": 0
            },
            "defensive": {
                "scale": 1.103,
                "offset_x": 0,
                "offset_y": 1
            },
            "tactical": {
                "scale": 1.050,
                "offset_x": 0,
                "offset_y": 0
            },
            "swarm": {
                "scale": 1.158,
                "offset_x": 1,
                "offset_y": 2
            },
            "deadly": {
                "scale": 1.340,
                "offset_x": -3,
                "offset_y": 2
            }
        }
        
        data = hitbox_data.get(self.personality, hitbox_data["aggressive"])
        self.hitbox_scale = data["scale"]
        self.hitbox_offset_x = data["offset_x"]
        self.hitbox_offset_y = data["offset_y"]
    
    def update_hitbox(self):
        """Update the hitbox radius - keep constant at base radius, don't scale"""
        self.radius = self.base_radius  # Keep hitbox radius constant at 26px
    
    def get_hitbox_center(self):
        """Get the actual hitbox center position (UFO position + offsets)"""
        return Vector2D(
            self.position.x + self.hitbox_offset_x,
            self.position.y + self.hitbox_offset_y
        )
    
    def ease_out_cubic(self, t):
        """Cubic ease-out for smooth deceleration"""
        return 1 - pow(1 - t, 3)
    
    def ease_in_out_quad(self, t):
        """Quadratic ease-in-out for natural movement"""
        return 2 * t * t if t < 0.5 else 1 - pow(-2 * t + 2, 2) / 2
    
    def update(self, dt, ship_pos, screen_width=None, screen_height=None, time_dilation_factor=1.0, explosion_system=None):
        super().update(dt, screen_width, screen_height)
        
        # Handle spinout effect
        if self.spinout_active:
            return False  # Don't shoot during spinout
        
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
    
    def draw_ufo_shadow(self, screen, shake_x=0, shake_y=0):
        """Draw only the UFO shadow (for proper layering)"""
        if not self.active:
            return
            
        if self.image:
            # Calculate shadow alpha
            if self.spinout_active:
                # Fade shadow from 33% to 0% over 0.2 seconds
                fade_progress = min(self.spinout_timer / 0.2, 1.0)  # 0.0 to 1.0
                shadow_alpha = int(84 * (1.0 - fade_progress))  # 84 to 0
            else:
                shadow_alpha = 84  # 33% opacity
            
            # Use cached shadow image
            if self.spinout_active:
                rotation_angle = self.visual_rotation_angle
            else:
                rotation_angle = self.angle
            
            rotation_degrees = -math.degrees(rotation_angle) - 90
            shadow_ufo = image_cache.get_shadow_image(self.image, 1.2, shadow_alpha, rotation_degrees)
            shadow_rect = shadow_ufo.get_rect(center=(int(self.position.x + 8 + shake_x), int(self.position.y + 8 + shake_y)))
            screen.blit(shadow_ufo, shadow_rect, special_flags=pygame.BLEND_ALPHA_SDL2)
        else:
            # Fallback UFO shadow - optimized
            if self.spinout_active:
                fade_progress = min(self.spinout_timer / 0.2, 1.0)
                shadow_alpha = int(84 * (1.0 - fade_progress))
            else:
                shadow_alpha = 84
            
            # Create minimal shadow surface for UFO fallback
            shadow_points = []
            # Create UFO shape points (ellipse + rectangle)
            center_x = self.position.x + 8 + shake_x
            center_y = self.position.y + 8 + shake_y
            
            # Ellipse shadow
            ellipse_rect = (center_x - self.radius * 1.2, center_y - self.radius/2 * 1.2,
                           self.radius * 2 * 1.2, self.radius * 1.2)
            # Rectangle shadow
            rect_rect = (center_x - self.radius/2 * 1.2, center_y - self.radius/4 * 1.2,
                        self.radius * 1.2, self.radius/2 * 1.2)
            
            # Use optimized shadow surface creation
            shadow_result = ShadowSurfaceOptimizer.create_minimal_shadow_surface([], shadow_alpha)
            if shadow_result:
                shadow_surface, shadow_pos = shadow_result
                # Draw shapes on the minimal surface
                pygame.draw.ellipse(shadow_surface, (0, 0, 0, shadow_alpha), 
                                  (ellipse_rect[0] - shadow_pos[0], ellipse_rect[1] - shadow_pos[1],
                                   ellipse_rect[2], ellipse_rect[3]))
                pygame.draw.rect(shadow_surface, (0, 0, 0, shadow_alpha),
                                (rect_rect[0] - shadow_pos[0], rect_rect[1] - shadow_pos[1],
                                 rect_rect[2], rect_rect[3]))
                screen.blit(shadow_surface, shadow_pos)
    
    def draw_ufo_smoke(self, screen, shake_x=0, shake_y=0):
        """Draw smoke.gif behind UFO based on velocity, similar to player fire system"""
        if not self.thrusting or not self.active:
            return
            
        # Calculate smoke width based on UFO speed (3x longer than player)
        ufo_speed = self.velocity.magnitude()
        ufo_speed_percent = min(ufo_speed / 1000.0 * 100, 100)  # Cap at 100%
        # Scale from 0 width at 0% speed to 180 width at 100% speed (3x player's 60)
        thrust_width = int((ufo_speed_percent / 100.0) * 180)
        
        if thrust_width > 0:  # Only draw if there's thrust
            # Position smoke behind the UFO (opposite direction of movement)
            smoke_angle = self.angle + math.pi
            smoke_x = self.position.x + math.cos(smoke_angle) * 40 + shake_x
            smoke_y = self.position.y + math.sin(smoke_angle) * 40 + shake_y
            
            # Try smoke.gif image with rotation
            smoke_image = pygame.image.load(get_resource_path("smoke.gif"))
            # Scale smoke width based on UFO speed (2x wider than player)
            smoke_height = max(10, thrust_width)  # Height equals width (2x player's height)
            smoke_image = pygame.transform.scale(smoke_image, (thrust_width, smoke_height))
            # Rotate the smoke 180 degrees and match UFO rotation
            rotated_smoke = pygame.transform.rotate(smoke_image, -math.degrees(self.angle) + 180)
            
            # Apply 50% transparency to smoke
            smoke_surface = pygame.Surface(rotated_smoke.get_size(), pygame.SRCALPHA)
            smoke_surface.blit(rotated_smoke, (0, 0))
            smoke_surface.set_alpha(128)  # 50% transparency (128/255)
            
            smoke_rect = smoke_surface.get_rect(center=(int(smoke_x), int(smoke_y)))
            screen.blit(smoke_surface, smoke_rect)
    
    def draw(self, screen, debug_mode=False, shake_x=0, shake_y=0):
        if not self.active:
            return
        
        # Draw spinout flame effect first (behind UFO)
        if self.spinout_active:
            self.draw_spinout(screen, shake_x, shake_y)
        
        # Draw UFO smoke.gif (behind UFO, in front of spinout)
        self.draw_ufo_smoke(screen, shake_x, shake_y)
            
        if self.image:
            # Draw UFO using cached rotated image
            # During spinout, use visual rotation angle; otherwise use movement angle
            if self.spinout_active:
                rotation_angle = self.visual_rotation_angle
            else:
                rotation_angle = self.angle
            rotation_degrees = -math.degrees(rotation_angle) - 90
            rotated_ufo = image_cache.get_rotated_image(self.image, rotation_degrees)
            ufo_rect = rotated_ufo.get_rect(center=(int(self.position.x), int(self.position.y)))
            
            # Shadow fade during spinout over 0.2 seconds
            if self.spinout_active:
                # Fade shadow from 33% to 0% over 0.2 seconds
                fade_progress = min(self.spinout_timer / 0.2, 1.0)  # 0.0 to 1.0
                shadow_alpha = int(84 * (1.0 - fade_progress))  # 84 to 0
            else:
                shadow_alpha = 84  # 33% opacity
            
            # Draw main UFO
            screen.blit(rotated_ufo, ufo_rect)
        else:
            # Fallback to original UFO shape (no rotation for fallback)
            # Draw shadow first
            shadow_surface = pygame.Surface((screen.get_width(), screen.get_height()), pygame.SRCALPHA)
            
            # Shadow fade during spinout over 0.2 seconds
            if self.spinout_active:
                # Fade shadow from 33% to 0% over 0.2 seconds
                fade_progress = min(self.spinout_timer / 0.2, 1.0)  # 0.0 to 1.0
                shadow_alpha = int(84 * (1.0 - fade_progress))  # 84 to 0
            else:
                shadow_alpha = 84  # 33% opacity
            
            pygame.draw.ellipse(shadow_surface, (0, 0, 0, shadow_alpha), 
                              (self.position.x - self.radius * 1.2 + 8, self.position.y - self.radius/2 * 1.2 + 8,
                               self.radius * 2 * 1.2, self.radius * 1.2))  # 20% bigger
            pygame.draw.rect(shadow_surface, (0, 0, 0, shadow_alpha),
                            (self.position.x - self.radius/2 * 1.2 + 8, self.position.y - self.radius/4 * 1.2 + 8,
                             self.radius * 1.2, self.radius/2 * 1.2))  # 20% bigger
            screen.blit(shadow_surface, (0, 0))
            
            # Draw main UFO
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
            
            # Add spinout info if applicable
            if self.spinout_active:
                debug_text += " (SPINOUT)"
            
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
        self.behavior_weights["avoid_asteroids"] = 0.5
    
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
            # Store AI target velocity
            self.target_velocity = final_velocity
        else:
            # No movement target - gradually slow down
            self.target_velocity = Vector2D(0, 0)
        
        # Tween towards target velocity for smooth movement
        if self.target_velocity.magnitude() > 0:
            # Smooth velocity interpolation
            velocity_diff = self.target_velocity - self.tweened_velocity
            self.tweened_velocity += velocity_diff * self.velocity_tween_speed * dt
            
            # Use tweened velocity for actual movement
            self.velocity = self.tweened_velocity
        else:
            # No movement - gradually slow down using ease-out
            current_speed = self.tweened_velocity.magnitude()
            if current_speed > 0.1:  # Only slow down if moving
                # Apply ease-out deceleration
                decel_factor = self.ease_out_cubic(1.0 - self.velocity_tween_speed * dt * 0.5)
                self.tweened_velocity = self.tweened_velocity * decel_factor
                self.velocity = self.tweened_velocity
            else:
                # Stop completely
                self.tweened_velocity = Vector2D(0, 0)
                self.velocity = self.tweened_velocity
        
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
        if self.shoot_timer >= self.shoot_interval and self.bullets_fired < self.max_bullets:
            self.shoot_timer = 0
            return True
        return False
    
    def calculate_predictive_aim(self, player_pos, player_vel, bullet_speed):
        """Calculate predictive aiming for moving targets"""
        if not player_pos or not player_vel:
            return math.atan2(player_pos.y - self.position.y, player_pos.x - self.position.x)
        
        # Calculate time for bullet to reach player
        dx = player_pos.x - self.position.x
        dy = player_pos.y - self.position.y
        distance = math.sqrt(dx*dx + dy*dy)
        
        if distance == 0:
            return 0
        
        # Simple predictive calculation
        # Time = distance / bullet_speed
        time_to_target = distance / bullet_speed
        
        # Predict where player will be
        predicted_x = player_pos.x + player_vel.x * time_to_target
        predicted_y = player_pos.y + player_vel.y * time_to_target
        
        # Aim at predicted position
        return math.atan2(predicted_y - self.position.y, predicted_x - self.position.x)
    
    def get_level_accuracy_penalty(self, level):
        """Get level-based accuracy penalty"""
        if level >= 5:
            return 1.0  # No penalty at level 5+
        elif level == 1:
            return 0.5  # 50% accuracy at level 1
        elif level == 2:
            return 0.3  # 30% accuracy at level 2
        elif level == 3:
            return 0.2  # 20% accuracy at level 3
        elif level == 4:
            return 0.1  # 10% accuracy at level 4
        else:
            return 1.0  # Default to no penalty
    
    def apply_accuracy_modifier(self, base_angle, accuracy_modifier, level_penalty=1.0):
        """Apply accuracy modifier with random spread, including level penalty and individual multiplier"""
        # BOSS SHOTS ARE ALWAYS 150% ACCURATE - IGNORE ALL PENALTIES
        if accuracy_modifier >= 1.5:
            return base_angle  # Perfect accuracy guaranteed for boss shots
        
        # Combine all accuracy modifiers for non-boss shots
        combined_accuracy = accuracy_modifier * self.individual_accuracy_multiplier * level_penalty
        
        if combined_accuracy >= 1.0:
            return base_angle  # Perfect accuracy
        
        # Calculate spread based on combined accuracy modifier
        # 0.75 accuracy = ±0.25 radians spread
        spread = (1.0 - combined_accuracy) * 0.5  # Max spread of 0.5 radians
        angle_offset = random.uniform(-spread, spread)
        
        return base_angle + angle_offset
    
    def trigger_spinout(self):
        """Trigger the spinout 'Burst into Flames' effect"""
        try:
            # Ensure rotation_speed exists
            if not hasattr(self, 'rotation_speed'):
                self.rotation_speed = 2.0
            
            self.spinout_active = True
            self.spinout_timer = 0.0
            self.spinout_duration = 3.0  # 3 seconds duration
            self.spinout_flame_scale = 0.0
            self.spinout_flame_scale_timer = 0.0
            self.spinout_flame_scale_duration = random.uniform(1.0, 3.0)  # Random 1-3 seconds to scale up
            self.spinout_spark_timer = 0.0
            self.spinout_spark_interval = 1.0 / random.uniform(20.1, 42)  # 20-42 sparks per second (avoid division by zero)
            self.spinout_collision_delay_timer = 0.0
            self.spinout_collision_delay = random.uniform(0.5, 1.5)  # Random delay 0.5-1.5 seconds before explosion
            
            # Set movement type (100% straight, 0% spiral)
            self.spinout_movement_type = "straight"
            
            # Set rotation speed multiplier (1x to 10x)
            self.spinout_rotation_speed_multiplier = random.uniform(1.0, 10.0)
            self.spinout_target_rotation_speed = self.rotation_speed * self.spinout_rotation_speed_multiplier
            
            # Initialize visual rotation angle for spinout flame
            self.visual_rotation_angle = 0.0
            
            # Set up movement
            # Random speed multiplier between 3x and 5x
            self.spinout_speed_multiplier = random.uniform(3.0, 5.0)
            
            if self.spinout_movement_type == "straight":
                # Random direction with random velocity 100-250
                angle = random.uniform(0, 2 * math.pi)
                random_speed = random.uniform(100, 250)
                self.velocity = Vector2D(math.cos(angle), math.sin(angle)) * random_speed
            else:
                # Spiral outward - set up spiral parameters at fixed 250 speed
                self.spinout_spiral_center = Vector2D(self.position.x, self.position.y)
                self.spinout_spiral_angle = 0.0
                self.spinout_spiral_radius = 0.0
                # Start with current velocity direction for spiral at 250 units/second
                current_angle = math.atan2(self.velocity.y, self.velocity.x)
                self.velocity = Vector2D(math.cos(current_angle), math.sin(current_angle)) * 250
            
            # Velocity is now set directly above based on movement type
            
        except Exception as e:
            # Don't raise the exception, just set a default rotation speed and continue
            if not hasattr(self, 'rotation_speed'):
                self.rotation_speed = 2.0
    
    def update_spinout(self, dt, explosion_system, game_instance=None):
        """Update spinout effect"""
        try:
            if not self.spinout_active:
                return
            
            # Apply time dilation to spinout timers
            time_dilation_factor = 1.0
            if game_instance and hasattr(game_instance, 'time_dilation_factor'):
                time_dilation_factor = game_instance.time_dilation_factor
            
            self.spinout_timer += dt * time_dilation_factor
            self.spinout_collision_delay_timer += dt * time_dilation_factor
        
            # Update flame scaling (0% to 100% over random 1-3 seconds)
            self.spinout_flame_scale_timer += dt * time_dilation_factor
            if self.spinout_flame_scale_timer < self.spinout_flame_scale_duration:
                self.spinout_flame_scale = self.spinout_flame_scale_timer / self.spinout_flame_scale_duration
            else:
                self.spinout_flame_scale = 1.0
            
            # Update movement
            if self.spinout_movement_type == "spiral":
                # Large expanding spiral movement at 250 units/second
                self.spinout_spiral_angle += dt * 2.0  # Spiral rotation speed
                self.spinout_spiral_radius += dt * 250  # Spiral expansion rate (250 units/second)
                
                # Ensure minimum radius of 50px
                if self.spinout_spiral_radius < 50:
                    self.spinout_spiral_radius = 50
                
                # Logarithmic spiral: r = a * e^(b * θ)
                a = 50  # Minimum radius (50px)
                b = 0.05  # Growth rate for smooth expansion
                r = max(a, self.spinout_spiral_radius)
                
                # Convert to cartesian
                x = self.spinout_spiral_center.x + r * math.cos(self.spinout_spiral_angle)
                y = self.spinout_spiral_center.y + r * math.sin(self.spinout_spiral_angle)
                
                # Update velocity to move towards spiral position at 250 units/second
                target_pos = Vector2D(x, y)
                direction = target_pos - self.position
                if direction.magnitude() > 0:
                    direction = direction.normalize()
                    self.velocity = direction * 250  # Fixed 250 units/second for spiral
            
            # Update rotation speed gradually from 1x to target (1x-10x)
            current_rotation_speed = self.rotation_speed
            target_rotation_speed = self.spinout_target_rotation_speed
            if current_rotation_speed < target_rotation_speed:
                self.rotation_speed = min(target_rotation_speed, current_rotation_speed + dt * 5.0)
            
            # Update visual rotation angle for spinout flame (separate from movement angle)
            self.visual_rotation_angle += self.rotation_speed * dt * time_dilation_factor
            
            # Update UFO's angle to match current movement direction during spinout
            if self.velocity.magnitude() > 0:
                self.angle = math.atan2(self.velocity.y, self.velocity.x)
            
            # Debug logging for UFO spinout state
            
            # Generate sparks (matching Copy 3 exactly)
            self.spinout_spark_timer += dt * time_dilation_factor
            if self.spinout_spark_timer >= self.spinout_spark_interval:
                self.spinout_spark_timer = 0.0
                self.spinout_spark_interval = 1.0 / random.uniform(20.1, 42)  # New random interval (avoid division by zero)
                
                # Generate 1-20 sparks per burst (matching Copy 3)
                num_sparks = random.randint(1, 20)
                for _ in range(num_sparks):
                    # 66% firey, 34% electric (matching Copy 3)
                    if random.random() < 0.66:
                        # Firey colors (red/orange/yellow) - matching Copy 3
                        colors = [(255, 100, 0), (255, 150, 0), (255, 200, 0), (255, 50, 0)]
                        color = random.choice(colors)
                    else:
                        # Electric colors (blue/white) - matching Copy 3
                        colors = [(0, 150, 255), (100, 200, 255), (255, 255, 255), (0, 100, 255)]
                        color = random.choice(colors)
                    
                    # Add spinout spark using regular explosion system (matching Copy 3)
                    if game_instance and hasattr(game_instance, 'explosions'):
                        game_instance.explosions.add_explosion(
                        self.position.x + random.uniform(-10, 10),
                        self.position.y + random.uniform(-10, 10),
                        num_particles=1,
                            color=color,
                            is_ufo=True
                    )
            
            # Check if spinout duration is over (5 seconds)
            if self.spinout_timer >= self.spinout_duration:
                self.spinout_active = False
                self.active = False  # UFO dies after 5 seconds
                
                # Add final explosion and score when spinout ends (matching Copy 3)
                if game_instance and hasattr(game_instance, 'explosions'):
                    game_instance.explosions.add_explosion(self.position.x, self.position.y, 
                                            num_particles=90, 
                                            color=(0, 150, 255), is_ufo=True)  # Electric blue
                    game_instance.explosions.add_explosion(self.position.x, self.position.y, 
                                            num_particles=10, 
                                            color=(255, 255, 255), is_ufo=True)  # Bright white
                
                # Add score for UFO destruction
                if game_instance:
                    game_instance.add_score(200, "ufo collision")
        
        except Exception as e:
            # Disable spinout to prevent further crashes
            self.spinout_active = False
    
    def draw_spinout(self, screen, shake_x=0, shake_y=0):
        """Draw spinout flame effect"""
        try:
            if not self.spinout_active or not self.spinout_flame_image:
                return
            
            # Scale the flame image based on current scale
            if self.spinout_flame_scale > 0:
                # Create scaled version
                original_size = self.spinout_flame_image.get_size()
                scaled_size = (
                    int(original_size[0] * self.spinout_flame_scale),
                    int(original_size[1] * self.spinout_flame_scale)
                )
                
                if scaled_size[0] > 0 and scaled_size[1] > 0:
                    scaled_flame = pygame.transform.smoothscale(self.spinout_flame_image, scaled_size)
                    # Rotate the flame to be parallel to UFO's movement direction (180 degrees behind)
                    rotated_flame = pygame.transform.rotate(scaled_flame, -math.degrees(self.angle) + 180)
                    # Apply screen shake offset to flame position to match UFO
                    flame_x = int(self.position.x + shake_x)
                    flame_y = int(self.position.y + shake_y)
                    flame_rect = rotated_flame.get_rect(center=(flame_x, flame_y))
                    screen.blit(rotated_flame, flame_rect)
        
        except Exception as e:
            # Disable spinout to prevent further crashes
            self.spinout_active = False


class AbilityUFO(AdvancedUFO):
    """Special UFO that grants ability charges when destroyed"""
    
    def __init__(self, x, y, ai_personality="aggressive", ability_charges=1):
        super().__init__(x, y, ai_personality)
        self.ability_charges = ability_charges  # Number of ability charges to grant
        self.is_ability_ufo = True
        
        # Visual distinction - add a pulsing glow effect
        self.glow_timer = 0.0
        self.glow_duration = 1.5  # Glow cycle duration
        self.glow_intensity = 0.0
        
        # Different color tint for ability UFOs
        self.color_tint = (255, 100, 255)  # Purple tint for ability UFOs
        
        # Slightly different behavior - more aggressive but slower
        self.speed = self.speed * 0.8  # 20% slower
        self.max_speed = self.max_speed * 0.8
        self.aggression_level = self.aggression_level * 1.5  # 50% more aggressive
        
    def update(self, dt, screen_width=None, screen_height=None, player_speed=0, time_dilation_factor=1.0):
        """Update UFO with glowing effect"""
        super().update(dt, screen_width, screen_height, player_speed, time_dilation_factor)
        
        # Update glow effect
        self.glow_timer += dt
        if self.glow_timer >= self.glow_duration:
            self.glow_timer = 0.0
        
        # Calculate glow intensity (0.3 to 1.0)
        self.glow_intensity = 0.3 + 0.7 * math.sin((self.glow_timer / self.glow_duration) * 2 * math.pi)
    
    def draw(self, screen, screen_width=None, screen_height=None):
        """Draw ability UFO with special glowing effect"""
        if not self.active:
            return
        
        # Call parent draw method first
        super().draw(screen, screen_width, screen_height)
        
        # Add pulsing glow effect around the UFO
        if self.glow_intensity > 0:
            # Draw pulsing glow ring around the UFO
            glow_radius = int(self.radius * (1.3 + 0.4 * self.glow_intensity))
            glow_alpha = int(120 * self.glow_intensity)
            
            # Create a surface for the glow effect
            glow_surface = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
            glow_color = (*self.color_tint, glow_alpha)
            
            # Draw the glow ring
            pygame.draw.circle(glow_surface, glow_color, (glow_radius, glow_radius), glow_radius, 4)
            
            # Blit the glow effect
            glow_rect = glow_surface.get_rect(center=(int(self.position.x), int(self.position.y)))
            screen.blit(glow_surface, glow_rect)
    
    def grant_ability_charges(self, ship):
        """Grant ability charges to the ship"""
        if hasattr(ship, 'ability_charges') and hasattr(ship, 'max_ability_charges'):
            ship.ability_charges = min(ship.ability_charges + self.ability_charges, ship.max_ability_charges)
            return True
        return False


class BossEnemy(GameObject):
    def __init__(self, x, y, direction="right", screen_width=1000, screen_height=750, level=3):
        super().__init__(x, y)
        self.active = True
        self.direction = direction  # "left" or "right"
        self.screen_width = screen_width
        self.screen_height = screen_height
        
        # Movement parameters
        self.speed = random.uniform(25, 75)  # 25-75 units per second
        self.base_amplitude = 20  # Base 20px amplitude for sine wave
        if level == 0:  # Title screen boss
            self.amplitude = 20  # Fixed 20px amplitude for title screen
        else:
            self.random_multiplier = random.uniform(0.1, 2.0)  # Random multiplier between 0.1 and 2
            self.amplitude = self.base_amplitude + (level * self.random_multiplier)  # Level-based amplitude
        self.frequency = 0.1  # 0.1 cycle per second
        self.sine_timer = 0.0
        
        # Boss weapon system
        self.weapon_active = True
        self.weapon_timer = 0.0
        self.weapon_delay = 2.0  # 2 second delay before weapon starts firing
        self.weapon_delay_timer = 0.0
        self.cycle_timer = 0.0
        self.cycle_duration = 6.0  # 6 seconds per cycle
        self.current_cycle = 0  # 0 = one-at-a-time, 1 = all-at-once
        self.cycle_count = 0  # Track total cycles for simultaneous mode timing
        self.shot_timer = 0.0
        self.shot_interval = 0.25  # 0.25 seconds between shots when firing one-at-a-time
        self.current_gun_index = 0
        self.shot_count = 0  # Track shots fired for player targeting
        self.asteroid_targets = []
        self.weapon_bullets = []
        
        # Calculate center line for sine wave based on direction
        if level == 0:  # Title screen boss - between game title and press space text
            # Game title: center - 100, Press space: center + 30
            # Midpoint: center - 100 + (130 / 2) = center - 35
            self.center_y = (screen_height // 2) - 35  # Between title and press space
        elif direction in ["left_top", "right_top"]:
            # Top 2/5: 40% down from top
            self.center_y = (screen_height * 2) // 5
        elif direction in ["left_bottom", "right_bottom"]:
            # Bottom 4/5: 80% down from top
            self.center_y = (screen_height * 4) // 5
        else:
            # Default to top 2/5 for backward compatibility
            self.center_y = (screen_height * 2) // 5
        
        # Set initial position and velocity based on direction
        # Direction format: "left_top", "right_bottom", etc.
        if direction == "left":
            self.position.x = -300  # Start off-screen left
            self.velocity = Vector2D(self.speed, 0)
            self.flip_horizontal = True  # Left side bosses are flipped
            # For title screen bosses, set Y between title and press space
            if level == 0:
                self.position.y = (screen_height // 2) - 35
        elif direction == "right":
            self.position.x = screen_width + 300  # Start off-screen right
            self.velocity = Vector2D(-self.speed, 0)
            self.flip_horizontal = False  # Right side bosses are not flipped
            # For title screen bosses, set Y between title and press space
            if level == 0:
                self.position.y = (screen_height // 2) - 35
        elif direction == "left_top":
            self.position.x = -300  # Start off-screen left
            self.position.y = (screen_height * 2) // 5  # Top 2/5 line
            self.velocity = Vector2D(self.speed, 0)
            self.flip_horizontal = True  # Left side bosses are flipped
        elif direction == "right_top":
            self.position.x = screen_width + 300  # Start off-screen right
            self.position.y = (screen_height * 2) // 5  # Top 2/5 line
            self.velocity = Vector2D(-self.speed, 0)
            self.flip_horizontal = False  # Right side bosses are not flipped
        elif direction == "left_bottom":
            self.position.x = -300  # Start off-screen left
            self.position.y = (screen_height * 4) // 5  # Bottom 4/5 line
            self.velocity = Vector2D(self.speed, 0)
            self.flip_horizontal = True  # Left side bosses are flipped
        elif direction == "right_bottom":
            self.position.x = screen_width + 300  # Start off-screen right
            self.position.y = (screen_height * 4) // 5  # Bottom 4/5 line
            self.velocity = Vector2D(-self.speed, 0)
            self.flip_horizontal = False  # Right side bosses are not flipped
        else:  # Default to right for backward compatibility
            self.position.x = screen_width + 300  # Start off-screen right
            self.velocity = Vector2D(-self.speed, 0)
            self.flip_horizontal = False  # Right side bosses are not flipped
        
        # Load and scale stard.gif image
        try:
            self.image = pygame.image.load(get_resource_path("stard.gif"))
            self.image = self.image.convert_alpha()
            # Scale to 500px
            self.image = pygame.transform.smoothscale(self.image, (500, 500))
            
            # Flip horizontally only if coming from the left side
            if self.flip_horizontal:
                self.image = pygame.transform.flip(self.image, True, False)
                
        except Exception as e:
            # Image loading failed - continue without image
            self.image = None
        
        # Set radius for collision detection (if needed later) - 250px radius for 500px image
        self.radius = 250
        
        # Gun positions for weapon system (no visual particles)
        self.gun_positions = []
        
        # Polygon hitbox points (relative to boss center)
        # Original points from 750x750 bossbox.py: [(823,430), (670,394), (602,335), (580,237), (452,245), 
        # (433,316), (280,367), (82,372), (80,400), (553,510), (822,447)]
        # These points need to be scaled from 750x750 to 500x500 and made relative to center
        # Scale factor = 500/750 = 2/3
        # Center of 750x750 image = (375, 375), center of 500x500 image = (250, 250)
        scale_factor = 500.0 / 750.0  # 2/3
        
        # Convert each point: (original_x - 375) * scale_factor, (original_y - 375) * scale_factor
        # Additional adjustment: moved 50px left (-50) and 15px up (-15)
        self.hitbox_points = [
            (int((823 - 375) * scale_factor) - 50, int((430 - 375) * scale_factor) - 15),   # Point 1: (249, 22)
            (int((670 - 375) * scale_factor) - 50, int((394 - 375) * scale_factor) - 15),   # Point 2: (147, -2)
            (int((602 - 375) * scale_factor) - 50, int((335 - 375) * scale_factor) - 15),   # Point 3: (101, -42)
            (int((580 - 375) * scale_factor) - 50, int((237 - 375) * scale_factor) - 15),   # Point 4: (87, -107)
            (int((452 - 375) * scale_factor) - 50, int((245 - 375) * scale_factor) - 15),   # Point 5: (1, -102)
            (int((433 - 375) * scale_factor) - 50, int((316 - 375) * scale_factor) - 15),   # Point 6: (-11, -54)
            (int((280 - 375) * scale_factor) - 50, int((367 - 375) * scale_factor) - 15),   # Point 7: (-113, -20)
            (int((82 - 375) * scale_factor) - 50, int((372 - 375) * scale_factor) - 15),    # Point 8: (-245, -17)
            (int((80 - 375) * scale_factor) - 50, int((400 - 375) * scale_factor) - 15),    # Point 9: (-247, 2)
            (int((553 - 375) * scale_factor) - 50, int((510 - 375) * scale_factor) - 15),   # Point 10: (69, 75)
            (int((822 - 375) * scale_factor) - 50, int((447 - 375) * scale_factor) - 15)    # Point 11: (248, 33)
        ]
        
    
    def point_in_polygon(self, point_x, point_y):
        """Check if a point is inside the boss's polygon hitbox"""
        # Convert world coordinates to local coordinates relative to boss center
        # Boss center is at (position.x, position.y), hitbox points are relative to this center
        local_x = point_x - self.position.x
        local_y = point_y - self.position.y
        
        # Apply horizontal flip if needed
        if self.flip_horizontal:
            local_x = -local_x
        
        # Ray casting algorithm for point-in-polygon test
        n = len(self.hitbox_points)
        inside = False
        
        j = n - 1
        for i in range(n):
            if ((self.hitbox_points[i][1] > local_y) != (self.hitbox_points[j][1] > local_y)) and \
               (local_x < (self.hitbox_points[j][0] - self.hitbox_points[i][0]) * 
                (local_y - self.hitbox_points[i][1]) / 
                (self.hitbox_points[j][1] - self.hitbox_points[i][1]) + self.hitbox_points[i][0]):
                inside = not inside
            j = i
        
        return inside
    
    def polygon_circle_collision(self, circle_center_x, circle_center_y, circle_radius):
        """Check if a circle (asteroid) collides with the boss polygon"""
        # First check if circle center is inside polygon
        if self.point_in_polygon(circle_center_x, circle_center_y):
            return True
        
        # Check if any edge of the polygon intersects with the circle
        n = len(self.hitbox_points)
        for i in range(n):
            # Get current and next point (with wraparound)
            p1 = self.hitbox_points[i]
            p2 = self.hitbox_points[(i + 1) % n]
            
            # Convert to world coordinates
            if self.flip_horizontal:
                world_p1_x = self.position.x - p1[0]
                world_p1_y = self.position.y + p1[1]
                world_p2_x = self.position.x - p2[0]
                world_p2_y = self.position.y + p2[1]
            else:
                world_p1_x = self.position.x + p1[0]
                world_p1_y = self.position.y + p1[1]
                world_p2_x = self.position.x + p2[0]
                world_p2_y = self.position.y + p2[1]
            
            # Check distance from circle center to line segment
            dist = self.point_to_line_distance(circle_center_x, circle_center_y, 
                                             world_p1_x, world_p1_y, 
                                             world_p2_x, world_p2_y)
            
            if dist <= circle_radius:
                return True
        
        return False
    
    def point_to_line_distance(self, px, py, x1, y1, x2, y2):
        """Calculate distance from point (px, py) to line segment from (x1, y1) to (x2, y2)"""
        # Vector from line start to end
        dx = x2 - x1
        dy = y2 - y1
        
        # Vector from line start to point
        px_rel = px - x1
        py_rel = py - y1
        
        # Length squared of line segment
        line_length_sq = dx * dx + dy * dy
        
        if line_length_sq == 0:
            # Line segment is actually a point
            return math.sqrt(px_rel * px_rel + py_rel * py_rel)
        
        # Project point onto line
        t = max(0, min(1, (px_rel * dx + py_rel * dy) / line_length_sq))
        
        # Closest point on line segment
        closest_x = x1 + t * dx
        closest_y = y1 + t * dy
        
        # Distance from point to closest point on line
        return math.sqrt((px - closest_x) ** 2 + (py - closest_y) ** 2)
    
    def polygon_circle_collision_with_wrapping(self, circle_center_x, circle_center_y, circle_radius, screen_width, screen_height):
        """Check if a circle (asteroid) collides with the boss polygon, accounting for screen wrapping"""
        # Calculate all possible wrapped positions for the circle
        wrapped_positions = [(circle_center_x, circle_center_y)]  # Main position
        
        # Horizontal wrapping
        if circle_center_x < circle_radius:
            wrapped_positions.append((circle_center_x + screen_width, circle_center_y))
        elif circle_center_x > screen_width - circle_radius:
            wrapped_positions.append((circle_center_x - screen_width, circle_center_y))
        
        # Vertical wrapping
        if circle_center_y < circle_radius:
            wrapped_positions.append((circle_center_x, circle_center_y + screen_height))
        elif circle_center_y > screen_height - circle_radius:
            wrapped_positions.append((circle_center_x, circle_center_y - screen_height))
        
        # Corner wrapping (when circle is in corner)
        if (circle_center_x < circle_radius and circle_center_y < circle_radius):
            wrapped_positions.append((circle_center_x + screen_width, circle_center_y + screen_height))
        elif (circle_center_x > screen_width - circle_radius and circle_center_y < circle_radius):
            wrapped_positions.append((circle_center_x - screen_width, circle_center_y + screen_height))
        elif (circle_center_x < circle_radius and circle_center_y > screen_height - circle_radius):
            wrapped_positions.append((circle_center_x + screen_width, circle_center_y - screen_height))
        elif (circle_center_x > screen_width - circle_radius and circle_center_y > screen_height - circle_radius):
            wrapped_positions.append((circle_center_x - screen_width, circle_center_y - screen_height))
        
        # Check collision at each wrapped position
        for wrapped_x, wrapped_y in wrapped_positions:
            if self.polygon_circle_collision(wrapped_x, wrapped_y, circle_radius):
                return True
        
        return False
    
    def draw_hitbox(self, screen):
        """Draw the polygon hitbox for debugging"""
        if len(self.hitbox_points) < 3:
            return
            
        # Get screen shake offset if available
        shake_x = 0
        shake_y = 0
        if hasattr(screen, 'shake_x'):
            shake_x = screen.shake_x
            shake_y = screen.shake_y
            
        # Convert local hitbox points to world coordinates
        # Boss sprite is drawn at (position.x - 250, position.y - 250) to center the 500x500 image
        # Hitbox points are already relative to the center of the 500x500 image
        world_points = []
        for point in self.hitbox_points:
            world_x = self.position.x + (point[0] if not self.flip_horizontal else -point[0]) + shake_x
            world_y = self.position.y + point[1] + shake_y
            world_points.append((world_x, world_y))
        
        # Draw polygon outline
        pygame.draw.polygon(screen, (255, 0, 255), world_points, 2)  # Magenta outline
        
        # Draw vertices
        for point in world_points:
            pygame.draw.circle(screen, (255, 255, 0), (int(point[0]), int(point[1])), 3)  # Yellow vertices
    
    def update(self, dt, screen_width=None, screen_height=None, asteroids=None, player=None):
        if not self.active:
            return
            
        # Update sine wave timer
        self.sine_timer += dt
        
        # Calculate sine wave offset based on movement direction
        sine_offset = self.amplitude * math.sin(self.frequency * self.sine_timer * 2 * math.pi)
        
        # Update position - all bosses move horizontally with sine wave on y-axis
        self.position.x += self.velocity.x * dt
        self.position.y = self.center_y + sine_offset
        
        # Generate gun positions if not already generated
        if not self.gun_positions:
            self.generate_gun_positions()
        
        # Update gun positions to follow boss (only if we have positions)
        if self.gun_positions:
            self.update_gun_positions()
        
        # Update weapon system if asteroids and player are provided
        if asteroids is not None and player is not None and hasattr(self, 'weapon_active'):
            self.update_weapon_system(dt, asteroids, player)
        
        # Update weapon bullets
        if hasattr(self, 'weapon_bullets'):
            self.update_weapon_bullets(dt, screen_width, screen_height)
        
        # Check if boss has crossed the entire screen (all bosses move horizontally)
        if self.direction in ["right", "right_top", "right_bottom"] and self.position.x > self.screen_width + 300:
            # Boss has moved completely off the right side
            self.active = False
        elif self.direction in ["left", "left_top", "left_bottom"] and self.position.x < -300:
            # Boss has moved completely off the left side
                self.active = False
    
    def generate_gun_positions(self):
        """Generate gun positions for weapon system (no visual particles)"""
        if not self.active:
            return
            
        # Clear any existing gun positions
        self.gun_positions.clear()
        
        # Generate 12 gun positions in a perfect circle around the boss center
        for i in range(12):
            # Calculate angle for this gun (evenly distributed around circle)
            angle = (i / 12.0) * 2 * math.pi
            
            # Fixed position on 50px radius circle (100px diameter), offset 15px to the right
            gun_x = self.position.x + 15 + math.cos(angle) * 50
            gun_y = self.position.y + math.sin(angle) * 50
            
            self.gun_positions.append((gun_x, gun_y))
        
        # Generate 12 gun positions in a 500px line through the center of the circle, rotated 5 degrees counter-clockwise
        rotation_angle = -5 * math.pi / 180  # Convert 5 degrees to radians (negative for counter-clockwise)
        cos_angle = math.cos(rotation_angle)
        sin_angle = math.sin(rotation_angle)
        
        for i in range(12):
            # Calculate position along 500px line centered on the circle
            line_center_x = self.position.x + 15  # Circle center X
            line_center_y = self.position.y       # Circle center Y
            
            # Start with horizontal line from -250 to +250 (500px total)
            line_offset = -250 + (i / 11.0) * 500  # Distribute evenly along 500px line
            line_x = line_offset  # Horizontal offset from center
            line_y = 0            # No vertical offset initially
            
            # Rotate the line 5 degrees counter-clockwise
            rotated_x = line_x * cos_angle - line_y * sin_angle
            rotated_y = line_x * sin_angle + line_y * cos_angle
            
            # Apply rotation and center offset
            gun_x = line_center_x + rotated_x
            gun_y = line_center_y + rotated_y
            
            self.gun_positions.append((gun_x, gun_y))
    
    def update_gun_positions(self):
        """Update gun positions to follow boss position"""
        if not self.gun_positions or not self.active or len(self.gun_positions) < 24:
            return
            
        # Update circle gun positions (first 12)
        for i in range(12):
            if i < len(self.gun_positions):
                angle = (i / 12.0) * 2 * math.pi
                gun_x = self.position.x + 15 + math.cos(angle) * 50
                gun_y = self.position.y + math.sin(angle) * 50
                self.gun_positions[i] = (gun_x, gun_y)
        
        # Update line gun positions (next 12) - 500px line rotated 5 degrees counter-clockwise
        rotation_angle = -5 * math.pi / 180  # Convert 5 degrees to radians (negative for counter-clockwise)
        cos_angle = math.cos(rotation_angle)
        sin_angle = math.sin(rotation_angle)
        
        for i in range(12, 24):
            if i < len(self.gun_positions):
                line_index = i - 12  # Convert to 0-11 range
                line_center_x = self.position.x + 15  # Circle center X
                line_center_y = self.position.y       # Circle center Y
                
                # Start with horizontal line from -250 to +250 (500px total)
                line_offset = -250 + (line_index / 11.0) * 500  # Distribute evenly along 500px line
                line_x = line_offset  # Horizontal offset from center
                line_y = 0            # No vertical offset initially
                
                # Rotate the line 5 degrees counter-clockwise
                rotated_x = line_x * cos_angle - line_y * sin_angle
                rotated_y = line_x * sin_angle + line_y * cos_angle
                
                # Apply rotation and center offset
                gun_x = line_center_x + rotated_x
                gun_y = line_center_y + rotated_y
                self.gun_positions[i] = (gun_x, gun_y)
    
    
    def get_asteroids_by_distance_from_player(self, asteroids, player):
        """Get all asteroids sorted by distance from player"""
        if not asteroids or not player:
            return []
        
        asteroid_distances = []
        for asteroid in asteroids:
            if asteroid.active:
                # Calculate distance from player to asteroid
                dx = asteroid.position.x - player.position.x
                dy = asteroid.position.y - player.position.y
                distance = math.sqrt(dx*dx + dy*dy)
                asteroid_distances.append((distance, asteroid))
        
        # Sort by distance (closest first), randomize if distances are equal
        asteroid_distances.sort(key=lambda x: (x[0], random.random()))
        
        return [asteroid for _, asteroid in asteroid_distances]
    
    def fire_weapon_shot(self, target_asteroid, gun_index):
        """Fire a single shot from specified gun towards target asteroid"""
        if not self.gun_positions or gun_index >= len(self.gun_positions):
            return
        
        # Get gun position from gun positions
        gun_x, gun_y = self.gun_positions[gun_index]
        
        # Calculate direction from gun to target asteroid
        dx = target_asteroid.position.x - gun_x
        dy = target_asteroid.position.y - gun_y
        distance = math.sqrt(dx*dx + dy*dy)
        
        if distance > 0:
            # Normalize direction and set speed (50% slower than regular UFO shots)
            speed = 200.0  # 50% slower than regular UFO shots (400)
            vx = (dx / distance) * speed
            vy = (dy / distance) * speed
            
            # Create boss weapon bullet
            bullet = BossWeaponBullet(gun_x, gun_y, vx, vy)
            self.weapon_bullets.append(bullet)
    
    def fire_weapon_shot_at_player(self, player, gun_index):
        """Fire a single shot from specified gun towards player"""
        if not self.gun_positions or gun_index >= len(self.gun_positions):
            return
        
        # Get gun position from gun positions
        gun_x, gun_y = self.gun_positions[gun_index]
        
        # Calculate direction from gun to player
        dx = player.position.x - gun_x
        dy = player.position.y - gun_y
        distance = math.sqrt(dx*dx + dy*dy)
        
        if distance > 0:
            # Normalize direction and set speed (50% slower than regular UFO shots)
            speed = 200.0  # 50% slower than regular UFO shots (400)
            vx = (dx / distance) * speed
            vy = (dy / distance) * speed
            
            # Create boss weapon bullet
            bullet = BossWeaponBullet(gun_x, gun_y, vx, vy)
            self.weapon_bullets.append(bullet)
    
    def update_weapon_system(self, dt, asteroids, player):
        """Update the boss weapon system"""
        if not self.weapon_active or not self.active or not self.gun_positions:
            return
        
        # Update weapon delay timer
        self.weapon_delay_timer += dt
        
        # Don't start firing until delay has passed
        if self.weapon_delay_timer < self.weapon_delay:
            return
        
        # Update weapon timers (only after delay)
        self.weapon_timer += dt
        self.cycle_timer += dt
        self.shot_timer += dt
        
        # Get asteroids sorted by distance from player
        self.asteroid_targets = self.get_asteroids_by_distance_from_player(asteroids, player)
        
        if not self.asteroid_targets:
            return  # No targets available
        
        # Check if we need to start a new cycle
        if self.cycle_timer >= self.cycle_duration:
            self.cycle_timer = 0.0
            self.cycle_count += 1
            
            # Simultaneous mode only occurs every 4th cycle (cycles 3, 7, 11, etc.)
            if self.cycle_count % 4 == 3:
                self.current_cycle = 1  # All-at-once mode
            else:
                self.current_cycle = 0  # One-at-a-time mode
                
            self.current_gun_index = 0
            self.shot_timer = 0.0
        
        # Fire shots based on current cycle
        if self.current_cycle == 0:  # One-at-a-time mode
            if self.shot_timer >= self.shot_interval:
                # Every 4th shot targets the player
                if self.shot_count % 4 == 3 and player:
                    self.fire_weapon_shot_at_player(player, self.current_gun_index % len(self.gun_positions))
                else:
                    # Fire one shot from current gun at asteroid
                    target_index = self.current_gun_index % len(self.asteroid_targets)
                    target_asteroid = self.asteroid_targets[target_index]
                    self.fire_weapon_shot(target_asteroid, self.current_gun_index % len(self.gun_positions))
                
                self.shot_count += 1
                # Move to next gun
                self.current_gun_index = (self.current_gun_index + 1) % len(self.gun_positions)
                self.shot_timer = 0.0
                
        else:  # All-at-once mode
            if self.shot_timer >= self.shot_interval:
                # Fire from all guns simultaneously
                num_guns = len(self.gun_positions)
                for gun_index in range(num_guns):
                    # Every 4th shot targets the player
                    if self.shot_count % 4 == 3 and player:
                        self.fire_weapon_shot_at_player(player, gun_index)
                    else:
                        target_index = gun_index % len(self.asteroid_targets)
                        target_asteroid = self.asteroid_targets[target_index]
                        self.fire_weapon_shot(target_asteroid, gun_index)
                    self.shot_count += 1
                
                self.shot_timer = 0.0
    
    def update_weapon_bullets(self, dt, screen_width=None, screen_height=None):
        """Update boss weapon bullets"""
        if not hasattr(self, 'weapon_bullets') or not self.weapon_bullets:
            return
            
        # Update existing bullets
        for bullet in self.weapon_bullets[:]:  # Use slice to avoid modification during iteration
            if bullet.active:
                bullet.update(dt, screen_width, screen_height)
            else:
                self.weapon_bullets.remove(bullet)
    
    def draw_weapon_bullets(self, screen):
        """Draw boss weapon bullets"""
        if not hasattr(self, 'weapon_bullets') or not self.weapon_bullets:
            return
            
        for bullet in self.weapon_bullets:
            if bullet.active:
                bullet.draw(screen)

    def draw(self, screen, screen_width=None, screen_height=None):
        if not self.active or self.image is None:
            return
            
        # Get screen shake offset if available
        shake_x = 0
        shake_y = 0
        if hasattr(screen, 'shake_x'):
            shake_x = screen.shake_x
            shake_y = screen.shake_y
        
        # Draw the boss image
        x = int(self.position.x - 250 + shake_x)  # Center the 500px image
        y = int(self.position.y - 250 + shake_y)
        
        # Draw boss shadow first (behind the boss)
        shadow_image = pygame.transform.scale_by(self.image, 1.333)  # Make shadow 33.3% bigger
        shadow_image.fill((0, 0, 0, 255), special_flags=pygame.BLEND_MULT)  # Make it black first
        shadow_image.set_alpha(168)  # 66% opacity
        shadow_x = x + 15
        shadow_y = y + 15
        screen.blit(shadow_image, (shadow_x, shadow_y), special_flags=pygame.BLEND_ALPHA_SDL2)
        
        # Draw main boss image
        # Ensure the image is drawn even when off-screen
        # pygame.blit handles off-screen coordinates correctly
        screen.blit(self.image, (x, y))
        


class Particle:
    def __init__(self, x, y, vx, vy, color, lifetime=1.0, size=2.0, use_raw_time=False):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.lifetime = lifetime
        self.max_lifetime = lifetime
        self.size = size
        self.active = True
        self.use_raw_time = use_raw_time  # Flag to use raw frame time instead of dilated time
    
    def update(self, dt, screen_width=None, screen_height=None):
        if not self.active:
            return
            
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.lifetime -= dt
        
        # Screen wrapping for particles
        if screen_width is not None and screen_height is not None:
            if self.x < 0:
                self.x = screen_width
            elif self.x > screen_width:
                self.x = 0
            if self.y < 0:
                self.y = screen_height
            elif self.y > screen_height:
                self.y = 0
        
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


class SpinoutParticle:
    """Dedicated particle class for spinout sparks with specific properties"""
    def __init__(self, x, y, vx, vy, color, lifetime=None, size=None, spark_type="firey"):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        # Randomize lifetime between 0.5-1.5 seconds if not specified
        self.lifetime = lifetime if lifetime is not None else random.uniform(0.5, 1.5)
        self.max_lifetime = self.lifetime
        # Randomize size between 1.0-3.0 pixels if not specified
        self.size = size if size is not None else random.uniform(1.0, 3.0)
        self.spark_type = spark_type  # "firey" or "electric"
        self.active = True
        self.initial_velocity = math.sqrt(vx*vx + vy*vy)  # Store initial speed for physics
        self.use_raw_time = False  # SpinoutParticles use normal time dilation
    
    def update(self, dt, screen_width=None, screen_height=None):
        if not self.active:
            return
            
        # Apply physics - constant velocity (no deceleration to match Copy 3)
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.lifetime -= dt
        
        # No flickering effects to match Copy (3)
        
        # Screen wrapping for particles
        if screen_width is not None and screen_height is not None:
            if self.x < 0:
                self.x = screen_width
            elif self.x > screen_width:
                self.x = 0
            if self.y < 0:
                self.y = screen_height
            elif self.y > screen_height:
                self.y = 0
        
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
        
        # Simple particle rendering to match Copy (3)
        radius = max(1, int(self.size))
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), radius)


class ExplosionSystem:
    def __init__(self):
        self.particles = []
        self.particle_priorities = []  # Track particle priorities for cleanup
    
    def _check_particle_limit(self, priority=1):
        """Check if we can add more particles, cleanup if needed"""
        current_count = len(self.particles)
        
        # If we're at the hard limit, clean up old low-priority particles
        if current_count >= MAX_PARTICLES:
            self._cleanup_old_particles(priority)
            return len(self.particles) < MAX_PARTICLES
        
        # If we're approaching the soft limit, reduce particle generation
        if current_count >= PARTICLE_SOFT_LIMIT:
            # 50% chance to skip particle generation for low priority effects
            if priority < 3 and random.random() < 0.5:
                return False
        
        return True
    
    def _cleanup_old_particles(self, min_priority=1):
        """Remove oldest low-priority particles when at limit"""
        if len(self.particles) < MAX_PARTICLES:
            return
        
        # Create list of (index, priority, age) tuples for sorting
        particle_data = []
        for i, (particle, priority) in enumerate(zip(self.particles, self.particle_priorities)):
            if priority < min_priority:  # Only consider particles with lower priority
                # Use negative lifetime as age (older particles have less lifetime left)
                age = -particle.lifetime
                particle_data.append((i, priority, age))
        
        # Sort by priority (lowest first), then by age (oldest first)
        particle_data.sort(key=lambda x: (x[1], x[2]))
        
        # Remove up to 20% of particles or enough to get under soft limit
        particles_to_remove = min(
            len(particle_data),
            max(1, (len(self.particles) - PARTICLE_SOFT_LIMIT) // 2)
        )
        
        # Collect indices to remove (in reverse order to maintain validity)
        indices_to_remove = []
        for i in range(particles_to_remove):
            indices_to_remove.append(particle_data[i][0])
        
        # Sort indices in descending order for safe removal
        indices_to_remove.sort(reverse=True)
        
        # Remove particles and priorities
        for index in indices_to_remove:
            if index < len(self.particles):  # Safety check
                del self.particles[index]
                del self.particle_priorities[index]
    
    def add_explosion(self, x, y, num_particles=50, color=(255, 255, 0), asteroid_size=None, is_ufo=False, use_raw_time=False):
        # Determine priority: UFO explosions and large asteroids are high priority
        priority = 1  # Default low priority
        if is_ufo:
            priority = 5  # High priority for UFO explosions
        elif asteroid_size and asteroid_size >= 7:
            priority = 4  # High priority for large asteroids
        elif asteroid_size and asteroid_size >= 5:
            priority = 3  # Medium priority for medium asteroids
        
        # Check particle limit before adding
        if not self._check_particle_limit(priority):
            return
        
        for _ in range(int(num_particles)):
            # Random spawn position within diameter based on asteroid size
            if asteroid_size is not None:
                # All asteroid sizes: spawn within diameter radius
                spawn_radius = asteroid_size * 8  # Diameter increases with asteroid size
                spawn_angle = random.uniform(0, 2 * math.pi)
                spawn_distance = random.uniform(0, spawn_radius)
                spawn_x = x + math.cos(spawn_angle) * spawn_distance
                spawn_y = y + math.sin(spawn_angle) * spawn_distance
            elif is_ufo:
                # UFO particles: spawn within ±10 pixels of UFO center
                spawn_x = x + random.uniform(-10, 10)
                spawn_y = y + random.uniform(-10, 10)
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
                # UFO explosion particles - 50-200 units/second
                speed = random.uniform(50, 200)  # 50-200 units/second
            else:
                # Default speed for non-asteroid explosions (with 100% additional randomization)
                speed = random.uniform(25, 100) * random.uniform(0.5, 1.5)  # ±50% variation
            
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            
            # Random particle properties with different variation amounts
            if color == (75, 75, 75):  # Gray with random values 75-125
                particle_color = (
                    random.randint(75, 125),
                    random.randint(75, 125),
                    random.randint(75, 125)
                )
            elif color == (34, 9, 1):  # Dark brown - ±2 variation
                variation = 2
                particle_color = (
                    random.randint(max(0, color[0] - variation), min(255, color[0] + variation)),
                    random.randint(max(0, color[1] - variation), min(255, color[1] + variation)),
                    random.randint(max(0, color[2] - variation), min(255, color[2] + variation))
                )
            elif color == (98, 23, 8):  # Red-brown - ±4 variation
                variation = 4
                particle_color = (
                    random.randint(max(0, color[0] - variation), min(255, color[0] + variation)),
                    random.randint(max(0, color[1] - variation), min(255, color[1] + variation)),
                    random.randint(max(0, color[2] - variation), min(255, color[2] + variation))
                )
            elif color == (148, 27, 12):  # Orange-red - ±5 variation
                variation = 5
                particle_color = (
                    random.randint(max(0, color[0] - variation), min(255, color[0] + variation)),
                    random.randint(max(0, color[1] - variation), min(255, color[1] + variation)),
                    random.randint(max(0, color[2] - variation), min(255, color[2] + variation))
                )
            elif color == (188, 57, 8):  # Orange - ±10 variation
                variation = 10
                particle_color = (
                    random.randint(max(0, color[0] - variation), min(255, color[0] + variation)),
                    random.randint(max(0, color[1] - variation), min(255, color[1] + variation)),
                    random.randint(max(0, color[2] - variation), min(255, color[2] + variation))
                )
            elif color == (246, 170, 28):  # Golden - ±15 variation
                variation = 15
                particle_color = (
                    random.randint(max(0, color[0] - variation), min(255, color[0] + variation)),
                    random.randint(max(0, color[1] - variation), min(255, color[1] + variation)),
                    random.randint(max(0, color[2] - variation), min(255, color[2] + variation))
                )
            else:  # Default - ±50 variation
                variation = 50
                particle_color = (
                    random.randint(max(0, color[0] - variation), min(255, color[0] + variation)),
                    random.randint(max(0, color[1] - variation), min(255, color[1] + variation)),
                    random.randint(max(0, color[2] - variation), min(255, color[2] + variation))
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
            elif is_ufo:
                # UFO explosion properties: 0.5-1.5 seconds with ±20% variation, 1.0-3.0 pixels
                base_lifetime = random.uniform(0.5, 1.5)
                lifetime = base_lifetime * random.uniform(0.8, 1.2)  # ±20% variation
                size = random.uniform(1.0, 3.0)  # UFO explosion size: 1.0-3.0 pixels
            else:
                # Default properties for non-asteroid explosions
                base_lifetime = random.uniform(0.5, 1.5)
                lifetime = base_lifetime * random.uniform(0.8, 1.2)  # ±20% variation
                size = random.uniform(1.0, 1.5)  # Default explosion size
            
            particle = Particle(spawn_x, spawn_y, vx, vy, particle_color, lifetime, size, use_raw_time)
            self.particles.append(particle)
            self.particle_priorities.append(priority)
    
    def add_rainbow_explosion(self, x, y, num_particles=200):
        """Add rainbow color cycling particles for player death"""
        # Player death is highest priority
        priority = 6
        
        # Check particle limit before adding
        if not self._check_particle_limit(priority):
            return
            
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
            self.particle_priorities.append(priority)
    
    def add_ship_explosion(self, x, y, num_particles=150):
        """Add a ship explosion with 80% bright yellow and 20% white with various brightnesses"""
        # Ship explosion is high priority
        priority = 5
        
        # Check particle limit before adding
        if not self._check_particle_limit(priority):
            return
            
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
            self.particle_priorities.append(priority)
    
    def add_ufo_shot_hit(self, x, y):
        """Add small, slow, short-lived burst of 10 small green and white particles for UFO shot hits"""
        # Low priority for shot hits
        priority = 2
        
        # Check particle limit before adding
        if not self._check_particle_limit(priority):
            return
            
        # 4 white particles of various brightnesses (20-80%)
        for _ in range(4):
            # Random direction
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(20, 60)  # Slow speed
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            
            # White with varying brightness (20-80%)
            brightness = random.uniform(0.2, 0.8)
            color_value = int(255 * brightness)
            color = (color_value, color_value, color_value)
            
            # Short lifetime (0.3-0.8 seconds)
            lifetime = random.uniform(0.3, 0.8)
            
            # Small size (1-2 pixels)
            size = random.uniform(1.0, 2.0)
            
            particle = Particle(x, y, vx, vy, color, lifetime, size)
            self.particles.append(particle)
            self.particle_priorities.append(priority)
        
        # 6 green particles of various brightnesses (25-75%)
        for _ in range(6):
            # Random direction
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(20, 60)  # Slow speed
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            
            # Green with varying brightness (25-75%)
            brightness = random.uniform(0.25, 0.75)
            green_value = int(255 * brightness)
            color = (0, green_value, 0)
            
            # Short lifetime (0.3-0.8 seconds)
            lifetime = random.uniform(0.3, 0.8)
            
            # Small size (1-2 pixels)
            size = random.uniform(1.0, 2.0)
            
            particle = Particle(x, y, vx, vy, color, lifetime, size)
            self.particles.append(particle)
            self.particle_priorities.append(priority)
    
    def add_rof_peak_sparks(self, x, y, angle, num_particles=7):
        """Add specific mix of sparks from the front of the player when reaching ROF peak"""
        # Low priority for ROF sparks
        priority = 2
        
        # Check particle limit before adding
        if not self._check_particle_limit(priority):
            return
            
        # Define particle types: 3 red, 2 red-orange, 2 66% white
        particle_types = [
            "red", "red", "red",  # 3 red particles
            "red_orange", "red_orange",  # 2 red-orange particles
            "dim_white", "dim_white"  # 2 66% white particles
        ]
        
        for i, particle_type in enumerate(particle_types):
            # Spawn particles 20-25 units in front of the player
            spawn_distance = random.uniform(20, 25)
            spawn_x = x + math.cos(angle) * spawn_distance
            spawn_y = y + math.sin(angle) * spawn_distance
            
            # Random velocity in forward direction with slight spread
            spread_angle = angle + random.uniform(-math.pi/6, math.pi/6)  # ±30 degrees
            speed = random.uniform(30, 75)  # Slow particles (30-75 units/sec)
            vx = math.cos(spread_angle) * speed
            vy = math.sin(spread_angle) * speed
            
            # Set color based on particle type
            if particle_type == "red":
                # Red particles
                color = (random.randint(200, 255), random.randint(0, 50), random.randint(0, 50))
            elif particle_type == "red_orange":
                # Red-orange particles
                color = (random.randint(200, 255), random.randint(80, 120), random.randint(0, 30))
            else:  # dim_white
                # 66% white particles (66% of 255 = ~168)
                white_val = random.randint(150, 180)  # 66% white range
                color = (white_val, white_val, white_val)
            
            # Short-lived, small particles (0.5-0.75 seconds)
            lifetime = random.uniform(0.5, 0.75)
            size = random.uniform(1.0, 2.0)  # Small particles
            
            particle = Particle(spawn_x, spawn_y, vx, vy, color, lifetime, size)
            self.particles.append(particle)
            self.particle_priorities.append(priority)
    
    def update(self, dt, screen_width=None, screen_height=None, raw_dt=None):
        # Use list comprehension for more efficient cleanup
        # Keep both particles and priorities in sync
        active_particles = []
        active_priorities = []
        
        # Ensure both lists are the same length
        min_length = min(len(self.particles), len(self.particle_priorities))
        
        for i in range(min_length):
            particle = self.particles[i]
            if particle.active:
                active_particles.append(particle)
                active_priorities.append(self.particle_priorities[i])
        
        # Handle any remaining particles without priorities (assign default priority)
        for i in range(min_length, len(self.particles)):
            particle = self.particles[i]
            if particle.active:
                active_particles.append(particle)
                active_priorities.append(1)  # Default low priority
        
        self.particles = active_particles
        self.particle_priorities = active_priorities
        
        # Update particles with appropriate time (raw or dilated)
        for particle in self.particles:
            if particle.use_raw_time and raw_dt is not None:
                particle.update(raw_dt, screen_width, screen_height)
            else:
                particle.update(dt, screen_width, screen_height)
    
    def draw(self, screen):
        for particle in self.particles:
            particle.draw(screen)
    
    def add_shot_hit_particles(self, x, y):
        """Add particles when player shot hits an object"""
        # Low priority for shot hits
        priority = 2
        
        # Check particle limit before adding
        if not self._check_particle_limit(priority):
            return
            
        # 4 particles with color (255,75,62) with +/-5 variations
        for _ in range(4):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(60, 80)  # 60-80 units/second speed
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            
            # Color with +/-5 variations
            particle_color = (
                random.randint(250, 255),  # 255 +/- 5
                random.randint(70, 80),    # 75 +/- 5
                random.randint(57, 67)     # 62 +/- 5
            )
            
            particle = Particle(x, y, vx, vy, particle_color, 0.5, 2.0)  # 0.5 second life
            self.particles.append(particle)
            self.particle_priorities.append(priority)
        
        # 3 particles with color (255,229,72) with +/-10 variations
        for _ in range(3):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(60, 80)  # 60-80 units/second speed
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            
            # Color with +/-10 variations
            particle_color = (
                random.randint(245, 255),  # 255 +/- 10
                random.randint(219, 239),  # 229 +/- 10
                random.randint(62, 82)     # 72 +/- 10
            )
            
            particle = Particle(x, y, vx, vy, particle_color, 0.5, 2.0)  # 0.5 second life
            self.particles.append(particle)
            self.particle_priorities.append(priority)
        
        # 3 particles with color (x,x,x) where x=200-255
        for _ in range(3):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(60, 80)  # 60-80 units/second speed
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            
            # Random gray color with x=200-255
            gray_value = random.randint(200, 255)
            particle_color = (gray_value, gray_value, gray_value)
            
            particle = Particle(x, y, vx, vy, particle_color, 0.5, 2.0)  # 0.5 second life
            self.particles.append(particle)
            self.particle_priorities.append(priority)
    
    def add_boss_shot_hit_particles(self, x, y):
        """Add 2x scaled particles when boss shot hits an object"""
        # Medium priority for boss shot hits
        priority = 3
        
        # Check particle limit before adding
        if not self._check_particle_limit(priority):
            return
            
        # 4 particles with color (255,75,62) with +/-5 variations - 2x size
        for _ in range(4):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(60, 80)  # 60-80 units/second speed
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            
            # Color with +/-5 variations
            particle_color = (
                random.randint(250, 255),  # 255 +/- 5
                random.randint(70, 80),    # 75 +/- 5
                random.randint(57, 67)     # 62 +/- 5
            )
            
            particle = Particle(x, y, vx, vy, particle_color, 0.5, 4.0)  # 2x size (4.0 instead of 2.0)
            self.particles.append(particle)
            self.particle_priorities.append(priority)
        
        # 3 particles with color (255,229,72) with +/-10 variations - 2x size
        for _ in range(3):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(60, 80)  # 60-80 units/second speed
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            
            # Color with +/-10 variations
            particle_color = (
                random.randint(245, 255),  # 255 +/- 10
                random.randint(219, 239),  # 229 +/- 10
                random.randint(62, 82)     # 72 +/- 10
            )
            
            particle = Particle(x, y, vx, vy, particle_color, 0.5, 4.0)  # 2x size (4.0 instead of 2.0)
            self.particles.append(particle)
            self.particle_priorities.append(priority)
        
        # 3 particles with color (x,x,x) where x=200-255 - 2x size
        for _ in range(3):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(60, 80)  # 60-80 units/second speed
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            
            # Random gray color with x=200-255
            gray_value = random.randint(200, 255)
            particle_color = (gray_value, gray_value, gray_value)
            
            particle = Particle(x, y, vx, vy, particle_color, 0.5, 4.0)  # 2x size (4.0 instead of 2.0)
            self.particles.append(particle)
            self.particle_priorities.append(priority)
    
    def add_ability_particles(self, x, y, player_angle, player_speed):
        """Add electric blue/white particles in a 3x4 grid behind the player based on speed"""
        # Medium priority for ability particles
        priority = 3
        
        # Determine number of particles based on speed
        if player_speed >= 4000:
            num_particles = 12
        elif player_speed >= 3000:
            num_particles = 7
        elif player_speed >= 2000:
            num_particles = 5
        elif player_speed >= 1000:
            num_particles = 1
        else:
            return  # No particles below 1000 speed
        
        # Check particle limit before adding
        if not self._check_particle_limit(priority):
            return
        
        # Grid dimensions: 3 columns, 4 rows, 18px wide, 24px tall
        grid_width = 18.0
        grid_height = 24.0
        cols = 3
        rows = 4
        
        # Calculate grid positions
        grid_positions = []
        for row in range(rows):
            for col in range(cols):
                # Calculate position within grid (0,0 is top-left)
                grid_x = (col / (cols - 1)) * grid_width - grid_width / 2
                grid_y = (row / (rows - 1)) * grid_height - grid_height / 2
                grid_positions.append((grid_x, grid_y))
        
        # Generate particles in grid positions
        for i in range(min(num_particles, len(grid_positions))):
            grid_x, grid_y = grid_positions[i]
            
            # Rotate grid position to match player direction
            cos_angle = math.cos(player_angle)
            sin_angle = math.sin(player_angle)
            
            # Apply rotation to grid position
            particle_x = x + grid_x * cos_angle - grid_y * sin_angle
            particle_y = y + grid_x * sin_angle + grid_y * cos_angle
            
            # Low velocity - particles move slowly outward from grid
            speed = random.uniform(5, 15)  # Low velocity range
            # Random direction from the grid position
            random_angle = random.uniform(0, 2 * math.pi)
            vx = math.cos(random_angle) * speed
            vy = math.sin(random_angle) * speed
            
            # Electric blue and white colors
            electric_colors = [
                (0, 150, 255),    # Electric blue
                (0, 200, 255),    # Bright electric blue
                (100, 200, 255),  # Light electric blue
                (255, 255, 255),  # White
                (200, 230, 255),  # Light blue-white
                (150, 220, 255),  # Electric white
                (0, 150, 255),    # Electric blue
                (0, 200, 255),    # Bright electric blue
                (100, 200, 255),  # Light electric blue
                (255, 255, 255),  # White
                (200, 230, 255),  # Light blue-white
                (150, 220, 255)   # Electric white
            ]
            particle_color = random.choice(electric_colors)
            
            # 3 game second lifetime, small size
            particle = Particle(particle_x, particle_y, vx, vy, particle_color, 3.0, 1.0, use_raw_time=True)
            self.particles.append(particle)
            self.particle_priorities.append(priority)

    def add_2x_charged_ability_particles(self, x, y, rotation_angle, player_vx=0, player_vy=0):
        """Add 5 randomly pink/purple particles in a burst around the player when ability is 2x charged"""
        # Medium priority for 2x charged ability particles
        priority = 3
        
        # Check particle limit before adding
        if not self._check_particle_limit(priority):
            return
            
        # Pink and purple color variations (half brightness)
        pink_purple_colors = [
            (127, 52, 90),    # Hot pink (half brightness)
            (127, 10, 73),    # Deep pink (half brightness)
            (127, 96, 101),   # Light pink (half brightness)
            (127, 80, 61),    # Light salmon (half brightness)
            (127, 34, 0),     # Red orange (half brightness)
            (127, 49, 35),    # Tomato (half brightness)
            (93, 42, 105),    # Medium orchid (half brightness)
            (73, 56, 109),    # Medium slate blue (half brightness)
            (69, 21, 113),    # Blue violet (half brightness)
            (74, 0, 105),     # Dark violet (half brightness)
            (64, 0, 64),      # Purple (half brightness)
            (37, 0, 65)       # Indigo (half brightness)
        ]
        
        # Generate 5 particles in a burst around the current rotation angle
        for i in range(5):
            # Spread particles in a 10px diameter circle around the rotation angle
            # First get the base position at the rotation angle
            base_x = x + 15 * math.cos(rotation_angle)
            base_y = y + 15 * math.sin(rotation_angle)
            
            # Add random offset within 10px diameter (5px radius)
            offset_angle = random.uniform(0, 2 * math.pi)
            offset_distance = random.uniform(0, 5)  # 5px radius for 10px diameter
            
            particle_x = base_x + offset_distance * math.cos(offset_angle)
            particle_y = base_y + offset_distance * math.sin(offset_angle)
            
            # Low velocity - particles move slowly outward
            speed = random.uniform(5, 15)  # Low velocity range
            # Random direction from the circle position
            random_angle = random.uniform(0, 2 * math.pi)
            vx = math.cos(random_angle) * speed + player_vx
            vy = math.sin(random_angle) * speed + player_vy
            
            # Random pink/purple color
            particle_color = random.choice(pink_purple_colors)
            
            # 3 game second lifetime, small size
            particle = Particle(particle_x, particle_y, vx, vy, particle_color, 3.0, 1.0, use_raw_time=True)
            self.particles.append(particle)
            self.particle_priorities.append(priority)


class StarField:
    def __init__(self, num_stars=300):
        self.stars = []
        self.num_stars = num_stars
        self.last_speed_factor = 0.0  # For smoothing
        self.explosion_mode = False
        self.explosion_timer = 0.0
        self.explosion_duration = 0.25  # 2x sooner - very short explosion
        self.explosion_fade_mode = False
        self.explosion_fade_timer = 0.0
        self.explosion_fade_duration = 0.15  # 2x sooner - very short fade-out
        self.screen_center_x = 0
        self.screen_center_y = 0
        
        # Fade-in transition system
        self.fade_in_mode = False
        self.fade_in_timer = 0.0
        self.fade_in_duration = 0.4  # 0.4 seconds for visible fade-in
        self.fade_in_stars = []  # New stars that fade in gradually
        self.stars_per_fade_frame = 16  # How many stars to add per frame during fade-in
        
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
                'brightness': random.uniform(0.1, 1.2),
                'size': random.uniform(0.5, 2.0),
                'explosion_speed': random.uniform(400, 1000)  # Speed for explosion effect (doubled)
            }
            self.stars.append(star)
    
    def start_explosion(self, screen_width, screen_height):
        """Start the star explosion effect"""
        self.explosion_mode = True
        self.explosion_timer = 0.0
        self.screen_center_x = screen_width // 2
        self.screen_center_y = screen_height // 2
    
    def start_fade_in(self, screen_width, screen_height):
        """Start the fade-in transition after explosion"""
        self.fade_in_mode = True
        self.fade_in_timer = 0.0
        self.screen_center_x = screen_width // 2
        self.screen_center_y = screen_height // 2
        
        # Clear existing stars and prepare for gradual fade-in
        self.stars = []
        self.fade_in_stars = []
        
        # Generate all stars but don't add them yet - they'll fade in gradually
        for _ in range(self.num_stars):
            star = {
                'x': random.uniform(0, screen_width),
                'y': random.uniform(0, screen_height),
                'speed': random.uniform(0.5, 3.0),
                'brightness': random.uniform(0.1, 1.2),
                'size': random.uniform(0.5, 2.0),
                'explosion_speed': random.uniform(400, 1000),
                'fade_alpha': 0.0  # Start invisible
            }
            self.fade_in_stars.append(star)
    
    def update(self, ship_velocity, screen_width, screen_height, dt=0.016):
        if self.explosion_mode:
            # Update explosion timer
            self.explosion_timer += dt
            
            # Check if explosion should transition to fade-out
            if self.explosion_timer >= self.explosion_duration:
                self.explosion_mode = False
                self.explosion_fade_mode = True
                self.explosion_fade_timer = 0.0
            
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
        elif self.explosion_fade_mode:
            # Update explosion fade-out timer
            self.explosion_fade_timer += dt
            
            # Check if fade-out is complete
            if self.explosion_fade_timer >= self.explosion_fade_duration:
                self.explosion_fade_mode = False
                self.explosion_fade_timer = 0.0
                # Clear stars and start fade-in
                self.stars = []
                self.start_fade_in(screen_width, screen_height)
        elif self.fade_in_mode:
            # Update fade-in timer
            self.fade_in_timer += dt
            
            # Move stars in fade_in_stars list before adding them (so they're not static)
            if ship_velocity:
                speed_factor = min(ship_velocity.magnitude() / 100.0, 10.0)
                for star in self.fade_in_stars:
                    # Move stars opposite to ship movement (normal parallaxing)
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
            else:
                # If no ship velocity, still move stars to avoid them appearing stationary
                for star in self.fade_in_stars:
                    # Move stars in a gentle drift pattern
                    star['x'] += star['speed'] * 1.0 * dt
                    star['y'] += star['speed'] * 0.5 * dt
                    
                    # Wrap around screen
                    if star['x'] < 0:
                        star['x'] = screen_width
                    elif star['x'] > screen_width:
                        star['x'] = 0
                    if star['y'] < 0:
                        star['y'] = screen_height
                    elif star['y'] > screen_height:
                        star['y'] = 0
            
            # Gradually add stars to the main star list
            stars_to_add = min(self.stars_per_fade_frame, len(self.fade_in_stars))
            for _ in range(stars_to_add):
                if self.fade_in_stars:
                    star = self.fade_in_stars.pop(0)
                    star['fade_alpha'] = 0.0  # Start invisible
                    self.stars.append(star)
            
            # Update fade-in alpha for all visible stars
            for star in self.stars:
                if 'fade_alpha' in star:
                    # Gradually increase alpha over the fade-in duration
                    fade_progress = min(self.fade_in_timer / self.fade_in_duration, 1.0)
                    star['fade_alpha'] = fade_progress
            
            # Apply normal parallaxing behavior during fade-in
            # Always move stars during fade-in, even if ship_velocity is None
            if ship_velocity:
                speed_factor = min(ship_velocity.magnitude() / 100.0, 10.0)  # Cap at 10x speed for trails
                
                for star in self.stars:
                    # Move stars opposite to ship movement (normal parallaxing)
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
            else:
                # If no ship velocity, still move stars to avoid them appearing stationary
                for star in self.stars:
                    # Move stars in a gentle drift pattern to avoid stationary appearance
                    star['x'] += star['speed'] * 1.0 * dt  # Faster movement
                    star['y'] += star['speed'] * 0.5 * dt  # Slight vertical drift
                    
                    # Wrap around screen
                    if star['x'] < 0:
                        star['x'] = screen_width
                    elif star['x'] > screen_width:
                        star['x'] = 0
                    if star['y'] < 0:
                        star['y'] = screen_height
                    elif star['y'] > screen_height:
                        star['y'] = 0
            
            # Check if fade-in is complete
            if self.fade_in_timer >= self.fade_in_duration and not self.fade_in_stars:
                self.fade_in_mode = False
                self.fade_in_timer = 0.0
                # Remove fade_alpha from all stars as they're now fully visible
                for star in self.stars:
                    if 'fade_alpha' in star:
                        del star['fade_alpha']
                # Clear fade_in_stars list to free memory
                self.fade_in_stars.clear()
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
                # During explosion: bright stars with trails
                brightness = int(200 * star['brightness'] * 1.5)  # Brighter during explosion
                brightness = max(0, min(255, brightness))
                color = (brightness, brightness, brightness)
            elif self.explosion_fade_mode:
                # During explosion fade-out: stars fade from bright to transparent
                fade_progress = min(self.explosion_fade_timer / self.explosion_fade_duration, 1.0)
                base_brightness = int(200 * star['brightness'] * 1.5)  # Same as explosion brightness
                brightness = int(base_brightness * (1.0 - fade_progress))  # Fade from 100% to 0%
                brightness = max(0, min(255, brightness))
                color = (brightness, brightness, brightness)
            else:
                # Normal star behavior (including fade-in mode)
                # Calculate brightness based on speed with smoothing
                raw_speed_factor = min(ship_velocity.magnitude() / 100.0, 10.0)  # Match update method cap
                # Smooth the speed factor to reduce flickering
                speed_factor = self.last_speed_factor * 0.8 + raw_speed_factor * 0.2
                self.last_speed_factor = speed_factor
                
                # Base brightness calculation with depth-based dimming
                # Use star['speed'] as depth indicator: slower stars are further back
                depth_factor = star['speed']  # 0.5 to 3.0 range from star generation
                depth_brightness = (depth_factor - 0.5) / 2.5  # Normalize to 0.0 to 1.0
                depth_brightness = max(0.2, depth_brightness)  # Minimum 20% brightness even for far stars
                
                if speed_factor > 0.1:  # Threshold to switch between stationary and moving
                    # When moving: brightness scales with speed AND depth
                    base_brightness = min(speed_factor, 2.0)
                    brightness = int(200 * star['brightness'] * base_brightness * depth_brightness * 0.85)  # 15% dimmer
                else:
                    # When stationary or very slow: use individual star brightness with depth
                    brightness = int(200 * star['brightness'] * 0.3 * depth_brightness * 0.85)  # 15% dimmer
                
                # Clamp brightness to valid range
                brightness = max(0, min(255, brightness))
                color = (brightness, brightness, brightness)
            
            # Draw star with trail effect (works in normal, explosion, and explosion fade modes)
            if not self.explosion_mode and not self.explosion_fade_mode:
                # Normal mode: trails based on ship speed
                raw_speed_factor = min(ship_velocity.magnitude() / 100.0, 10.0)  # Match update method cap
                speed_factor = self.last_speed_factor * 0.8 + raw_speed_factor * 0.2
                if speed_factor >= 4.2:  # 42% of Player Speed % (420 units/second)
                    # Draw trail - starts at 42% Player Speed, max length at 100% Player Speed
                    # Scale from 0 to 30 pixels as speed goes from 4.2 to 10.0 speed_factor
                    trail_progress = min((speed_factor - 4.2) / 5.8, 1.0)  # 0 to 1 as speed goes from 4.2 to 10.0
                    trail_length = trail_progress * 840  # 0 to 840 pixels (100% longer)
                    trail_x = star['x'] + ship_velocity.x * star['speed'] * 0.01 * trail_length
                    trail_y = star['y'] + ship_velocity.y * star['speed'] * 0.01 * trail_length
                    trail_brightness = max(0, min(255, brightness//3))
                    # Electric blue hyperspace trail with alpha fade (fades to 90% transparent at 90%)
                    self.draw_normal_alpha_trail(screen, star['x'], star['y'], trail_x, trail_y, 
                                                trail_brightness, trail_length)
            elif self.explosion_mode or self.explosion_fade_mode:
                # Explosion mode: trails based on explosion movement
                # Calculate trail based on star's explosion movement direction
                dx = star['x'] - self.screen_center_x
                dy = star['y'] - self.screen_center_y
                distance = math.sqrt(dx*dx + dy*dy)
                if distance > 0:
                    dx /= distance
                    dy /= distance
                    # Trail length based on explosion speed
                    trail_length = 200  # 10x longer trails during explosion (was 20)
                    trail_x = star['x'] - dx * trail_length
                    trail_y = star['y'] - dy * trail_length
                    trail_brightness = max(0, min(255, brightness//3))
                    
                    # Create alpha trail with gradient fade
                    self.draw_alpha_trail(screen, star['x'], star['y'], trail_x, trail_y, 
                                        trail_brightness, trail_length)
            
            # Apply fade-in alpha if in fade-in mode
            if self.fade_in_mode and 'fade_alpha' in star:
                alpha = star['fade_alpha']
                # Apply alpha to the color
                color = (int(color[0] * alpha), int(color[1] * alpha), int(color[2] * alpha))
            
            # Draw star
            pygame.draw.circle(screen, color, (int(star['x']), int(star['y'])), max(1, int(star['size'])))
    
    def draw_alpha_trail(self, screen, start_x, start_y, end_x, end_y, brightness, trail_length):
        """Draw a trail with alpha gradient from full opacity at start to transparent at end"""
        if trail_length <= 0:
            return
            
        # Calculate trail direction and segments
        dx = end_x - start_x
        dy = end_y - start_y
        distance = math.sqrt(dx*dx + dy*dy)
        
        if distance <= 0:
            return
            
        # Normalize direction
        dx /= distance
        dy /= distance
        
        # Create segments for gradient effect (more segments for longer trails)
        num_segments = max(3, min(20, int(trail_length / 5)))  # 3-20 segments based on length
        segment_length = trail_length / num_segments
        
        # Electric blue base color
        base_r = brightness // 4
        base_g = brightness // 2  
        base_b = brightness
        
        # Draw each segment with decreasing alpha
        for i in range(num_segments):
            # Calculate segment start and end positions
            seg_start_x = start_x + dx * (i * segment_length)
            seg_start_y = start_y + dy * (i * segment_length)
            seg_end_x = start_x + dx * ((i + 1) * segment_length)
            seg_end_y = start_y + dy * ((i + 1) * segment_length)
            
            # Calculate alpha for this segment (1.0 at start, 0.1 at 90% of trail, 0.0 at end)
            # Fade to 90% transparency at 90% of the way, then fade to 100% transparency
            trail_progress = i / (num_segments - 1) if num_segments > 1 else 0.0
            if trail_progress <= 0.9:
                # 0% to 90% of trail: fade from 1.0 to 0.1 (90% transparency)
                alpha_progress = 1.0 - (trail_progress / 0.9) * 0.9
            else:
                # 90% to 100% of trail: fade from 0.1 to 0.0 (90% to 100% transparency)
                remaining_progress = (trail_progress - 0.9) / 0.1
                alpha_progress = 0.1 - (remaining_progress * 0.1)
            alpha = int(255 * alpha_progress)
            
            # Calculate bounding box for this segment
            min_x = min(seg_start_x, seg_end_x)
            min_y = min(seg_start_y, seg_end_y)
            max_x = max(seg_start_x, seg_end_x)
            max_y = max(seg_start_y, seg_end_y)
            
            # Create alpha surface for this segment
            surface_width = max(1, int(max_x - min_x) + 2)
            surface_height = max(1, int(max_y - min_y) + 2)
            segment_surface = pygame.Surface((surface_width, surface_height), pygame.SRCALPHA)
            
            # Calculate relative positions within the surface
            rel_start_x = seg_start_x - min_x + 1
            rel_start_y = seg_start_y - min_y + 1
            rel_end_x = seg_end_x - min_x + 1
            rel_end_y = seg_end_y - min_y + 1
            
            # Draw line on alpha surface
            pygame.draw.line(segment_surface, (base_r, base_g, base_b, alpha), 
                           (rel_start_x, rel_start_y), (rel_end_x, rel_end_y), 1)
            
            # Blit to screen at correct position
            screen.blit(segment_surface, (int(min_x - 1), int(min_y - 1)))
    
    def draw_normal_alpha_trail(self, screen, start_x, start_y, end_x, end_y, brightness, trail_length):
        """Draw a normal trail with alpha gradient that fades to transparency sooner"""
        if trail_length <= 0:
            return
            
        # Calculate trail direction and segments
        dx = end_x - start_x
        dy = end_y - start_y
        distance = math.sqrt(dx*dx + dy*dy)
        
        if distance <= 0:
            return
            
        # Normalize direction
        dx /= distance
        dy /= distance
        
        # Create segments for gradient effect (more segments for longer trails)
        num_segments = max(3, min(20, int(trail_length / 5)))  # 3-20 segments based on length
        segment_length = trail_length / num_segments
        
        # Electric blue base color
        base_r = brightness // 4
        base_g = brightness // 2  
        base_b = brightness
        
        # Draw each segment with decreasing alpha
        for i in range(num_segments):
            # Calculate segment start and end positions
            seg_start_x = start_x + dx * (i * segment_length)
            seg_start_y = start_y + dy * (i * segment_length)
            seg_end_x = start_x + dx * ((i + 1) * segment_length)
            seg_end_y = start_y + dy * ((i + 1) * segment_length)
            
            # Calculate alpha for this segment (1.0 at start, 0.1 at 90% of trail, 0.0 at end)
            # Fade to 90% transparency at 90% of the way, then fade to 100% transparency
            trail_progress = i / (num_segments - 1) if num_segments > 1 else 0.0
            if trail_progress <= 0.9:
                # 0% to 90% of trail: fade from 1.0 to 0.1 (90% transparency)
                alpha_progress = 1.0 - (trail_progress / 0.9) * 0.9
            else:
                # 90% to 100% of trail: fade from 0.1 to 0.0 (90% to 100% transparency)
                remaining_progress = (trail_progress - 0.9) / 0.1
                alpha_progress = 0.1 - (remaining_progress * 0.1)
            alpha = int(255 * alpha_progress)
            
            # Calculate bounding box for this segment
            min_x = min(seg_start_x, seg_end_x)
            min_y = min(seg_start_y, seg_end_y)
            max_x = max(seg_start_x, seg_end_x)
            max_y = max(seg_start_y, seg_end_y)
            
            # Create alpha surface for this segment
            surface_width = max(1, int(max_x - min_x) + 2)
            surface_height = max(1, int(max_y - min_y) + 2)
            segment_surface = pygame.Surface((surface_width, surface_height), pygame.SRCALPHA)
            
            # Calculate relative positions within the surface
            rel_start_x = seg_start_x - min_x + 1
            rel_start_y = seg_start_y - min_y + 1
            rel_end_x = seg_end_x - min_x + 1
            rel_end_y = seg_end_y - min_y + 1
            
            # Draw line on alpha surface
            pygame.draw.line(segment_surface, (base_r, base_g, base_b, alpha), 
                           (rel_start_x, rel_start_y), (rel_end_x, rel_end_y), 1)
            
            # Blit to screen at correct position
            screen.blit(segment_surface, (int(min_x - 1), int(min_y - 1)))


class Scoreboard:
    """Handles worldwide scoreboard integration with Google Sheets"""
    def __init__(self, api_url):
        self.api_url = api_url
        self.cached_scores = []
        self.cache_time = None
        self.cache_duration = 60  # 1 minute
        self.timeout = 10  # 10 seconds
        
    def get_scores(self):
        """Get top 10 scores from the API"""
        try:
            
            # Check if we have cached scores that are still fresh
            if (self.cached_scores and self.cache_time and 
                datetime.now() - self.cache_time < timedelta(seconds=self.cache_duration)):
                return self.cached_scores
            
            
            # Fetch fresh scores
            response = requests.get(
                f"{self.api_url}?action=get_scores",
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            if data.get('success'):
                self.cached_scores = data['data']['scores']
                self.cache_time = datetime.now()
                return self.cached_scores
            else:
                return self.cached_scores  # Return cached scores if available
                
        except requests.exceptions.RequestException as e:
            return self.cached_scores  # Return cached scores if available
        except Exception as e:
            return []
    
    def submit_score(self, player_name, score):
        """Submit a new score to the API"""
        try:
            # Validate inputs
            if not player_name or not isinstance(player_name, str):
                return False, "Invalid player name"
            
            if not isinstance(score, (int, float)) or score < 0:
                # print(f"[SCOREBOARD DEBUG] Invalid score: {score}")
                return False, "Invalid score"
            
            # Sanitize player name
            player_name = str(player_name).strip()[:50]  # Max 50 characters
            if not player_name:
                # print(f"[SCOREBOARD DEBUG] Empty player name after sanitization")
                return False, "Empty player name"
            
            # print(f"[SCOREBOARD DEBUG] submit_score() called - Player: {player_name}, Score: {score}")
            
            data = {
                'action': 'submit_score',
                'playerName': player_name,
                'score': int(score)  # Ensure integer
            }
            
            # print(f"[SCOREBOARD DEBUG] Sending POST request to: {self.api_url}")
            response = requests.post(
                self.api_url,
                json=data,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            if result.get('success'):
                # print(f"[SCOREBOARD DEBUG] Score submitted successfully: {result['data']}")
                # Clear cache to force refresh on next get_scores call
                self.cached_scores = []
                self.cache_time = None
                # print(f"[SCOREBOARD DEBUG] Cache cleared for fresh data")
                return True, result['data']
            else:
                # print(f"[SCOREBOARD DEBUG] API returned error: {result.get('error', 'Unknown error')}")
                return False, result.get('error', 'Unknown error')
                
        except requests.exceptions.RequestException as e:
            return False, f"Network error: {e}"
        except Exception as e:
            return False, f"Unexpected error: {e}"
    
    def submit_score_async(self, player_name, score, callback=None):
        """Submit score in background thread"""
        try:
            # print(f"[SCOREBOARD DEBUG] submit_score_async() called - Player: {player_name}, Score: {score}")
            
            def _submit():
                try:
                    success, message = self.submit_score(player_name, score)
                    if callback:
                        callback(success, message)
                except Exception as e:
                    # print(f"[SCOREBOARD DEBUG] Error in submission thread: {e}")
                    if callback:
                        callback(False, f"Submission error: {e}")
            
            thread = threading.Thread(target=_submit)
            thread.daemon = True
            thread.start()
            # print(f"[SCOREBOARD DEBUG] Score submission thread started")
            
        except Exception as e:
            # print(f"[SCOREBOARD DEBUG] Error starting submission thread: {e}")
            if callback:
                callback(False, f"Thread error: {e}")
    
    def force_refresh_cache(self):
        """Force refresh the score cache"""
        # print(f"[SCOREBOARD DEBUG] force_refresh_cache() called")
        self.cached_scores = []
        self.cache_time = None
        # print(f"[SCOREBOARD DEBUG] Cache cleared, will fetch fresh data on next get_scores() call")
    
    def get_scores_async(self, callback=None):
        """Get scores in background thread without blocking"""
        # print(f"[SCOREBOARD DEBUG] get_scores_async() called")
        
        def _load_scores():
            try:
                scores = self.get_scores()
                if callback:
                    callback(scores)
                # print(f"[SCOREBOARD DEBUG] Background score loading completed: {len(scores) if scores else 0} scores")
            except Exception as e:
                # print(f"[SCOREBOARD DEBUG] Error in background score loading: {e}")
                if callback:
                    callback([])
        
        thread = threading.Thread(target=_load_scores)
        thread.daemon = True
        thread.start()
        # print(f"[SCOREBOARD DEBUG] Background score loading thread started")
    
    def format_scores_display(self, scores):
        """Format scores for display in the game"""
        if not scores:
            return ["No scores available"]
        
        formatted = []
        for i, score in enumerate(scores[:10], 1):
            player = score.get('playerName', 'Unknown')[:15]  # Limit name length
            score_val = score.get('score', 0)
            formatted.append(f"{i:2d}. {player:<15} {score_val:,}")
        
        return formatted
    
    def get_top_score(self):
        """Get the top score from cached data, fetch if not cached"""
        if not self.cached_scores:
            # No cached scores, try to fetch them
            scores = self.get_scores()
            if not scores:
                return None
        
        try:
            # Get the first (highest) score from cached data
            top_score = self.cached_scores[0]
            return top_score.get('score', 0)
        except (IndexError, KeyError, TypeError):
            return None


class Game:
    def __init__(self):
        if RESIZABLE:
            self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)
        else:
            self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("chuckS T A Roids")
        self.clock = pygame.time.Clock()
        self.running = False
        self.score = 0
        self.lives = 3
        self.level = 1
        self.game_state = "waiting"  # waiting, playing, death_delay, game_over, paused
        
        # Scoreboard integration with error handling
        try:
            # Replace 'YOUR_WEB_APP_URL' with your actual Google Apps Script URL
            self.scoreboard = Scoreboard('https://script.google.com/macros/s/AKfycbxGpVUSJIJCAngvngXs5w1iWsGP_1QTcQu6iacpta_9_a8GWjpVOYIjyBUYmqjQ_RC4xg/exec')
            self.scoreboard_available = True
        except Exception as e:
            print(f"Warning: Failed to initialize scoreboard: {e}")
            self.scoreboard = None
            self.scoreboard_available = False
        
        self.show_scoreboard = False
        self.player_name_input = ""
        self.name_input_active = False
        self.scoreboard_scores = []
        self.scoreboard_loading = False  # Track if scores are being loaded
        
        # Score milestone tracking for rewards
        self.last_milestone_250k = 0  # Last 250k milestone reached (shield recharge)
        self.last_milestone_500k = 0  # Last 500k milestone reached (ability + shield recharge)
        self.last_milestone_1000k = 0  # Last 1000k milestone reached (extra life)
        
        # Debug mode
        self.debug_mode = False
        self.console_debug = True  # Enable console debugging for error tracking
        self.god_mode = False  # God mode for debug (no damage)
        
        # FPS tracking for debug display
        self.fps_history = []  # Store last 60 FPS values for smoothing
        self.current_fps = 0.0
        self.fps_update_timer = 0.0
        self.fps_update_interval = 0.1  # Update FPS display every 0.1 seconds
        
        # Adaptive collision detection system
        self.collision_timers = {
            'ship_asteroid': 0.0,
            'ship_ufo_bullet': 0.0,
            'ship_boss_weapon': 0.0,
            'ship_ufo': 0.0,
            'bullet_asteroid': 0.0,
            'bullet_ufo': 0.0,
            'ship_boss': 0.0,
            'bullet_boss': 0.0,
            'ufo_bullet_asteroid': 0.0,
            'ufo_asteroid': 0.0,
            'ufo_ufo': 0.0,
            'boss_weapon_asteroid': 0.0,
            'boss_weapon_ufo': 0.0,
            'boss_asteroid': 0.0,
            'boss_player_bullet': 0.0,
            'boss_ufo_bullet': 0.0
        }
        
        # Collision FPS settings (base FPS, reduced FPS, threshold)
        self.collision_fps_settings = {
            'ship_asteroid': (60, 45, 250),  # (normal_fps, reduced_fps, threshold)
            'ship_ufo_bullet': (60, 45, 250),
            'ship_boss_weapon': (30, 30, 0),  # No threshold needed
            'ship_ufo': (30, 30, 0),
            'bullet_asteroid': (30, 20, 1000),
            'bullet_ufo': (30, 30, 0),
            'ship_boss': (15, 15, 0),
            'bullet_boss': (15, 15, 0),
            'ufo_bullet_asteroid': (15, 10, 1000),
            'ufo_asteroid': (15, 15, 0),
            'ufo_ufo': (15, 15, 0),
            'boss_weapon_asteroid': (15, 15, 0),
            'boss_weapon_ufo': (5, 5, 0),
            'boss_asteroid': (5, 5, 0),
            'boss_player_bullet': (5, 5, 0),
            'boss_ufo_bullet': (5, 5, 0)
        }
        
        # Current collision FPS (for gradual transitions)
        self.current_collision_fps = {}
        for collision_type in self.collision_timers.keys():
            self.current_collision_fps[collision_type] = self.collision_fps_settings[collision_type][0]
        
        # Transition speed for gradual FPS changes
        self.fps_transition_speed = 10.0  # FPS per second
        
        # Key cooldown timers (independent of game time effects)
        self.f1_cooldown_timer = 0.0
        self.g_cooldown_timer = 0.0
        self.key1_cooldown_timer = 0.0
        self.key2_cooldown_timer = 0.0
        self.key3_cooldown_timer = 0.0
        self.key4_cooldown_timer = 0.0
        self.key5_cooldown_timer = 0.0
        self.key_cooldown_duration = 0.3  # 0.3 second cooldown
        
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
        self.star_explosion_duration = 0.25  # 0.25 seconds
        
        # Score pulse effect system
        self.score_pulse_timer = 0.0
        self.score_pulse_duration = 0.0
        self.score_pulse_intensity = 0.0  # 0.0 to 1.0 based on points earned
        self.last_score = 0
        self.score_change = 0
        
        # Combo multiplier system
        self.asteroids_destroyed_this_level = 0  # Count of asteroids destroyed by player
        self.ufos_killed_this_level = 0  # Count of UFOs killed by player
        self.last_multiplier = 1.0  # Track previous multiplier for pulse effect
        self.multiplier_pulse_timer = 0.0  # Timer for multiplier pulse effect
        self.multiplier_pulse_duration = 0.3  # Duration of multiplier pulse effect
        
        # Multiplier decay system
        self.multiplier_decay_timer = 0.0  # Timer for when decay should start
        self.multiplier_decay_delay = 0.5  # 0.5 seconds before decay starts
        self.multiplier_decay_duration = 5.0  # 5 seconds to decay from current to 1.0x
        self.multiplier_decay_start_value = 1.0  # Value when decay started
        self.is_decaying = False  # Whether currently in decay phase
        
        # Game objects
        self.ship = None
        self.bullets = []
        self.asteroids = []
        self.ufos = []
        self.ufo_bullets = []
        
        # Boss enemy system
        self.bosses = []
        self.boss_spawn_timer = 0.0
        self.boss_spawn_delay = 0.0  # 5-15 seconds delay
        self.boss_spawned_this_level = False
        
        # Track UFOs spawned on level 1 for 100% spinout chance
        self.ufos_spawned_level_1 = 0
        
        # Star field
        self.star_field = StarField(200)
        self.star_field.generate_stars(self.current_width, self.current_height)
        
        # Explosion system
        self.explosions = ExplosionSystem()
        
        
        # Pre-allocated lists for performance optimization
        self.temp_positions_1 = []
        self.temp_positions_2 = []
        
        # Input handling
        self.keys_pressed = set()
        
        # Spawn timer
        self.ufo_spawn_timer = 0
        self.ufo_spawn_interval = 1.0  # 1 second between UFO spawns
        self.initial_ufo_timer = 5.0  # 5 seconds before first UFOs spawn
        self.ufos_to_spawn = 0  # Number of UFOs to spawn this wave
        self.ufo_spawn_delay = 0  # Delay between individual UFO spawns
        self.ufo_spawn_types = None  # Specific types for level 1, None for others
        self.ufo_spawn_type_index = 0  # Track current type in cycle for level 1
        self.ufo_spawn_corner = None  # Random corner for this level
        self.ufo_mass_spawn = False  # 10% chance for mass spawn from all corners
        
        # Mass spawn burst system
        self.ufo_burst_spawn = False  # Whether we're in burst spawn mode
        self.ufo_burst_count = 0  # Number of UFOs per burst (4 for 8+ UFOs)
        self.ufo_burst_delay = 0  # Delay between bursts
        self.ufo_burst_interval = 1.0  # 1 second between bursts
        self.ufo_burst_corners = [(0, 0), (0, 0), (0, 0), (0, 0)]  # Pre-allocated corner list for bursts
        
        # Spinning trick message
        self.spinning_trick_timer = 0.0
        self.show_spinning_trick = False
        
        # Interstellar message
        self.interstellar_timer = 0.0
        self.show_interstellar = False
        
        # God mode message
        self.god_mode_timer = 0.0
        self.show_god_mode = False
        self.god_mode_was_on = False  # Track previous god mode state
        
        # Ludicrous speed message (5000 speed)
        self.ludicrous_speed_timer = 0.0
        self.show_ludicrous_speed = False
        self.ludicrous_speed_shown = False  # Track if already shown
        
        # Plaid message (10000 speed)
        self.plaid_timer = 0.0
        self.show_plaid = False
        self.plaid_shown = False  # Track if already shown
        
        # Score milestone messages
        self.show_250k_message = False
        self.show_500k_message = False
        self.show_1m_message = False
        self.message_250k_timer = 0.0
        self.message_500k_timer = 0.0
        self.message_1m_timer = 0.0
        
        # Screen shake variables
        self.screen_shake_intensity = 0
        self.screen_shake_duration = 0
        self.screen_shake_timer = 0
        self.game_over_timer = 0  # Timer for game over state
        self.death_delay_timer = 0  # Timer for death delay state
        
        # Time dilation system (Superhot-style)
        self.time_dilation_factor = 1.0  # 1.0 = normal time, 0.01 = 100x slower
        
        # Music system
        self.music_player = None
        self.music_playing = False
        self.title_music_played = False
    
        # Title screen animation timers
        self.title_start_timer = 0.0  # Timer for title screen animations
        self.title_boss_spawn_timer = 0.0  # Timer for title screen boss spawn delay
        self.press_space_alpha = 0  # Alpha for "PRESS SPACE TO START" fade-in
        self.controls_alpha = 0  # Alpha for controls text fade-in
        self.game_over_alpha = 0  # Alpha for game over text fade-in
        
        
        # Sine wave movement for title screen UFOs (legacy system)
        self.sine_wave_timer = 0.0  # Timer for sine wave movement
        self.title_ufo_wave_data = []  # Store wave data for each title UFO
        self.ufo_respawn_timer = 0.0  # Timer for UFO respawning
        self.title_ufos_initialized = False  # Flag to prevent multiple initial spawns
        self.ufos_destroyed = 0  # Count of UFOs destroyed
        
        # Virtual ship for title screen movement mechanics
        self.title_ship = None  # Will be created when needed
        
        # Shooting prevention timer for new game start
        self.game_start_timer = 0.0  # Timer to prevent shooting for first 0.5 seconds
    
    def add_ufo(self, ufo):
        """Add UFO to the game and track first UFOs on level 1"""
        self.ufos.append(ufo)
        
        # Log UFO spawn
        ufo_type = getattr(ufo, 'personality', 'unknown')
        game_logger.log_ufo_spawn(ufo_type, self.level)
        
        # Track UFOs on level 1 for 100% spinout chance
        if self.level == 1:  # All UFOs on level 1
            self.ufos_spawned_level_1 += 1
    
    def add_boss(self, boss):
        """Add boss to the game with logging"""
        self.bosses.append(boss)
        # Log boss spawn (count will be logged separately when multiple bosses spawn)
        
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
        """Calculate time dilation factor based on ship movement, shooting, and turning"""
        if not self.ship:
            self.time_dilation_factor = 1.0
            return
        
        # Get player speed magnitude
        player_speed = self.ship.velocity.magnitude()
        
        # Check for shooting action
        is_shooting = self.ship.shoot_timer > 0 or pygame.K_SPACE in self.keys_pressed
        
        # Reset shot count when player stops shooting
        if self.ship.was_shooting and not is_shooting:
            self.ship.shot_count = 0
        
        # Update shooting state for next frame
        self.ship.was_shooting = is_shooting
        
        # Calculate shooting-based forward movement (progressive)
        shooting_forward_movement = 0.0
        if is_shooting:
            # Progressive shooting contribution: 200, 300, 400, 500, 500+
            if self.ship.shot_count == 1:
                shooting_forward_movement = 200.0
            elif self.ship.shot_count == 2:
                shooting_forward_movement = 300.0
            elif self.ship.shot_count == 3:
                shooting_forward_movement = 400.0
            else:  # 4th shot and beyond
                shooting_forward_movement = 500.0
        
        # Calculate turning-based movement with acceleration curve and 100% game speed cap
        # Base multiplier starts at 0.01, accelerates up to 0.1 at 1000 degrees
        base_multiplier = 0.01
        max_multiplier = 0.1
        acceleration_threshold = 1000.0  # degrees where we reach max multiplier
        max_turning_contribution = 250.0  # Cap turning at 250 movement units (25% game speed)
        
        if self.ship.accumulated_turning_degrees <= 0:
            turning_movement = 0.0
        elif self.ship.accumulated_turning_degrees >= acceleration_threshold:
            # Use max multiplier for degrees beyond threshold
            turning_movement = (acceleration_threshold * base_multiplier + 
                              (self.ship.accumulated_turning_degrees - acceleration_threshold) * max_multiplier)
        else:
            # Accelerate from base to max multiplier
            progress = self.ship.accumulated_turning_degrees / acceleration_threshold
            # Use quadratic curve for smooth acceleration
            current_multiplier = base_multiplier + (max_multiplier - base_multiplier) * (progress ** 2)
            turning_movement = self.ship.accumulated_turning_degrees * current_multiplier
        
        # Cap turning movement at 25% game speed (250 movement units)
        turning_movement = min(turning_movement, max_turning_contribution)
        
        # Total effective movement = actual movement + shooting forward movement + turning movement
        total_movement = player_speed + shooting_forward_movement + turning_movement
        
        # Calculate time dilation based on total movement with new curve
        # 0-1000 movement = 0.01x to 1.0x (nearly frozen to normal speed)
        # 1000-2000 movement = 1.0x to 5.0x (normal speed to 5x speed)
        # 2000+ movement = Custom curve matching the table values
        if total_movement >= 10000.0:
            target_dilation = 0.01  # Nearly frozen
        elif total_movement >= 9000.0:
            target_dilation = 0.1
        elif total_movement >= 8000.0:
            target_dilation = 0.2
        elif total_movement >= 7000.0:
            target_dilation = 0.3
        elif total_movement >= 6000.0:
            target_dilation = 0.4
        elif total_movement >= 5000.0:
            target_dilation = 0.5
        elif total_movement >= 4000.0:
            target_dilation = 0.75
        elif total_movement >= 3000.0:
            target_dilation = 2.5
        elif total_movement >= 2000.0:
            target_dilation = 5.0
        elif total_movement >= 1000.0:
            # Linear interpolation between 1.0x at 1000 and 5.0x at 2000
            speed_ratio = (total_movement - 1000.0) / (2000.0 - 1000.0)
            target_dilation = 1.0 + (5.0 - 1.0) * speed_ratio
        else:
            # Linear interpolation between 0.01x at 0 and 1.0x at 1000
            speed_ratio = min(total_movement / 1000.0, 1.0)
            target_dilation = 0.01 + (1.0 - 0.01) * speed_ratio
        
        # Smooth transition to target dilation
        if target_dilation > self.time_dilation_factor:
            # Accelerating: smooth interpolation
            dilation_diff = target_dilation - self.time_dilation_factor
            self.time_dilation_factor += dilation_diff * 2.0 * dt  # Fast acceleration
        else:
            # Decaying: use ship's decay rate for consistency
            current_speed = self.ship.velocity.magnitude()
            
            # Calculate current turning movement with same acceleration curve and cap
            base_multiplier = 0.01
            max_multiplier = 0.1
            acceleration_threshold = 1000.0
            max_turning_contribution = 250.0  # Cap turning at 250 movement units (25% game speed)
            
            if self.ship.accumulated_turning_degrees <= 0:
                current_turning = 0.0
            elif self.ship.accumulated_turning_degrees >= acceleration_threshold:
                current_turning = (acceleration_threshold * base_multiplier + 
                                 (self.ship.accumulated_turning_degrees - acceleration_threshold) * max_multiplier)
            else:
                progress = self.ship.accumulated_turning_degrees / acceleration_threshold
                current_multiplier = base_multiplier + (max_multiplier - base_multiplier) * (progress ** 2)
                current_turning = self.ship.accumulated_turning_degrees * current_multiplier
            
            # Cap turning movement at 25% game speed (250 movement units)
            current_turning = min(current_turning, max_turning_contribution)
            
            current_total = current_speed + current_turning
            
            # Use much faster decay when total movement is below 5% of 1000
            if current_total < 50.0:  # 5% of 1000
                # Even faster decay when movement is very low - 2x the below-10% decay
                decay_rate = (self.ship.speed_decay_rate ** 4) ** 2  # 8th power for extremely fast decay
            elif current_total < 100.0:  # 10% of 1000
                # Much faster decay to quickly reach 0%
                decay_rate = self.ship.speed_decay_rate ** 4  # 4th power for very fast decay
            else:
                decay_rate = self.ship.speed_decay_rate
            
            self.time_dilation_factor *= decay_rate ** dt
        
        # Clamp to valid range (0.01x to 5.0x)
        self.time_dilation_factor = max(0.01, min(5.0, self.time_dilation_factor))
        
        # Initial scoreboard refresh if no cached scores
        if self.scoreboard_available and self.scoreboard:
            # Check if we have no cached scores and refresh once
            if not self.scoreboard.cached_scores:
                self.scoreboard.force_refresh_cache()
        
        # Note: high score file clearing is handled in restart_game() and other appropriate places
    
    def apply_shake_offset(self, x, y, shake_x, shake_y):
        """Apply screen shake offset to coordinates"""
        return x + shake_x, y + shake_y
    
    def init_music_player(self):
        """Initialize the music player if not already initialized"""
        if self.music_player is None:
            try:
                self.music_player = EnhancedMusicPlayer()
            except Exception as e:
                # Music player initialization failed - continue without music
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
                    # Title music playback failed - continue silently
                    pass
    
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
                    # Level music playback failed - continue silently
                    pass
    
    def stop_music(self):
        """Stop any currently playing music"""
        if self.music_player and self.music_playing:
            try:
                self.music_player.stop()
                self.music_playing = False
            except Exception as e:
                # Music stop failed - continue silently
                pass
    
    def init_ship(self):
        self.ship = Ship(self.current_width // 2, self.current_height // 2)
        self.ship.invulnerable = True
        self.ship.invulnerable_time = 3.0
    
    def calculate_multiplier(self):
        """Calculate the current score multiplier"""
        # Combo component: based on score pulse duration
        combo_bonus = self.score_pulse_duration
        
        # Level component: asteroids and UFOs destroyed by player
        asteroid_bonus = self.asteroids_destroyed_this_level * 0.01
        ufo_bonus = self.ufos_killed_this_level * 0.1
        
        # Calculate base multiplier: max(1.0, base + combo + level bonuses)
        base_multiplier = max(1.0, 1.0 + combo_bonus + asteroid_bonus + ufo_bonus)
        
        # Apply decay if currently decaying
        if self.is_decaying:
            # Calculate decay progress (0.0 to 1.0)
            decay_progress = min(self.multiplier_decay_timer / self.multiplier_decay_duration, 1.0)
            
            # Linear interpolation from start value to 1.0
            multiplier = self.multiplier_decay_start_value + (1.0 - self.multiplier_decay_start_value) * decay_progress
        else:
            multiplier = base_multiplier
            
        return multiplier
    
    def add_score(self, points, event_type=""):
        """Add points to score and trigger pulse effect"""
        # Reset decay system when new points are earned
        self.multiplier_decay_timer = 0.0
        self.is_decaying = False
        
        # Store old score for logging
        old_score = self.score
        
        # Calculate multiplier and apply to points
        multiplier = self.calculate_multiplier()
        multiplied_points = int(points * multiplier)
        
        # Calculate multiplier gained from this event based on event type
        multiplier_gained = 0.0
        if event_type in ["asteroid shot", "asteroid shield", "asteroid collision"]:
            multiplier_gained = 0.01  # +0.01 per asteroid destroyed
        elif event_type in ["ufo shot", "ufo collision", "ufo spun out"]:
            multiplier_gained = 0.1   # +0.1 per UFO killed
        elif event_type == "ufo spinout collision":
            multiplier_gained = 0.0   # No multiplier gain for UFO-asteroid collisions
        
        self.score += multiplied_points
        self.score_change = multiplied_points
        self.trigger_score_pulse()
        
        # Log score event using new comprehensive logging system
        game_logger.log_score_event(multiplied_points, event_type, self.score, multiplier, multiplier_gained)
        
        # Check for score milestones and give rewards
        self.check_score_milestones()
    
    def trigger_score_pulse(self):
        """Trigger score pulse effect based on points earned"""
        # Calculate pulse duration based on new ranges:
        # 0-999 points: 0.1-1.0s
        # 1000-4999 points: 1.0-2.5s  
        # 5000-9999 points: 2.5-5.0s
        # 10000+ points: 5.0s
        if self.score_change <= 999:
            pulse_duration = 0.1 + (self.score_change / 999.0) * 0.9  # 0.1 to 1.0
        elif self.score_change <= 4999:
            pulse_duration = 1.0 + ((self.score_change - 1000) / 3999.0) * 1.5  # 1.0 to 2.5
        elif self.score_change <= 9999:
            pulse_duration = 2.5 + ((self.score_change - 5000) / 4999.0) * 2.5  # 2.5 to 5.0
        else:
            pulse_duration = 5.0  # Cap at 5.0s
        
        # Calculate pulse intensity: 0.0 to 1.0 based on points earned
        # 100 points = 0.1 intensity, 1000 points = 1.0 intensity
        self.score_pulse_intensity = min(self.score_change / 1000.0, 1.0)
        
        # Set pulse duration and reset timer
        self.score_pulse_duration = pulse_duration
        self.score_pulse_timer = 0.0
    
    def check_score_milestones(self):
        """Check for score milestones and give appropriate rewards"""
        if not self.ship:
            return
            
        # Every 1,000,000 points: give +1 maximum lives and add ship indicator (capped at 5)
        # Check highest priority first
        current_1000k_milestone = self.score // 1000000
        if current_1000k_milestone > self.last_milestone_1000k:
            self.last_milestone_1000k = current_1000k_milestone
            if self.lives < 5:
                self.lives += 1  # Add one life (capped at 5)
            # Clear lower priority messages and show 1M message
            self.show_250k_message = False
            self.show_500k_message = False
            self.show_1m_message = True
            self.message_1m_timer = 3.0  # Show for 3 seconds
            # Still recharge shields and abilities for 1M milestone
            self.recharge_all_shields()
            self.recharge_all_abilities()
        
        # Every 500,000 points: recharge all shields and both ability rings
        current_500k_milestone = self.score // 500000
        if current_500k_milestone > self.last_milestone_500k:
            self.last_milestone_500k = current_500k_milestone
            self.recharge_all_shields()
            self.recharge_all_abilities()
            # Clear lower priority message and show 500k message
            self.show_250k_message = False
            self.show_500k_message = True
            self.message_500k_timer = 3.0  # Show for 3 seconds
        
        # Every 250,000 points: recharge all shields to maximum
        current_250k_milestone = self.score // 250000
        if current_250k_milestone > self.last_milestone_250k:
            self.last_milestone_250k = current_250k_milestone
            self.recharge_all_shields()
            # Show 250k message
            self.show_250k_message = True
            self.message_250k_timer = 3.0  # Show for 3 seconds
    
    def recharge_all_shields(self):
        """Recharge all player shields to maximum with animation"""
        if not self.ship:
            return
            
        # Set shields to maximum
        self.ship.shield_hits = self.ship.max_shield_hits
        
        # Trigger shield recharge animation
        self.ship.shield_recharge_pulse_timer = self.ship.shield_recharge_pulse_duration
        self.ship.shield_pulse_timer = 1.0  # 1 second pulse
        
        # Reset shield recharge time
        self.ship.shield_recharge_time = 0
        
        # Mark that shields were charged via score milestone
        self.ship.shield_charged_by_ability = True
    
    def recharge_all_abilities(self):
        """Recharge both ability rings to maximum with animation"""
        if not self.ship:
            return
            
        # Set abilities to maximum
        self.ship.ability_charges = self.ship.max_ability_charges
        self.ship.ability_ready = True
        
        # Trigger ability recharge animation
        self.ship.ability_recharge_pulse_timer = self.ship.ability_recharge_pulse_duration
        
        # Set up for 2x charged ability effects
        self.ship.ability_flash_count = 4  # 4 flashes for 2nd charge
        self.ship.ability_fade_duration = 1.0  # 1.0 second fade
        self.ship.ability_hold_timer = self.ship.ability_hold_duration
        self.ship.ability_fully_charged_pulse_timer = 0.0  # Start pulsing immediately
        
        # Reset ability timer
        self.ship.ability_timer = 0.0
    
    def update_score_pulse(self, dt):
        """Update score pulse effect (independent of time scale) - 24fps update rate"""
        if self.score_pulse_timer < self.score_pulse_duration:
            # Limit update rate to 24fps (1/24 = 0.0417 seconds)
            self.score_pulse_timer += min(dt, 1.0/24.0)
    
    def update_multiplier_decay(self, dt):
        """Update multiplier decay system"""
        # Only update decay during playing state
        if self.game_state != "playing":
            return
            
        # If not currently decaying, check if we should start
        if not self.is_decaying:
            # Start decay timer if score pulse has ended
            if self.score_pulse_timer >= self.score_pulse_duration:
                self.multiplier_decay_timer += dt
                
                # Start decay after delay
                if self.multiplier_decay_timer >= self.multiplier_decay_delay:
                    # Start decaying from current multiplier value
                    self.multiplier_decay_start_value = self.calculate_multiplier()
                    self.is_decaying = True
                    self.multiplier_decay_timer = 0.0  # Reset timer for decay progress
        else:
            # Currently decaying - update decay progress
            self.multiplier_decay_timer += dt
            
            # Check if decay is complete
            if self.multiplier_decay_timer >= self.multiplier_decay_duration:
                self.is_decaying = False
                self.multiplier_decay_timer = 0.0
    
    def draw_score_with_pulse(self, surface, dt):
        """Draw score with pulse effect"""
        # Update pulse timer
        self.update_score_pulse(dt)
        
        # Calculate current multiplier
        current_multiplier = self.calculate_multiplier()
        
        # Check if multiplier increased (for pulse effect)
        if current_multiplier > self.last_multiplier:
            self.multiplier_pulse_timer = self.multiplier_pulse_duration
            self.last_multiplier = current_multiplier
        
        # Update multiplier pulse timer
        if self.multiplier_pulse_timer > 0:
            self.multiplier_pulse_timer -= dt
        
        # Calculate current opacity and size
        if self.score_pulse_timer < self.score_pulse_duration:
            # During pulse: fade up to bright white, then fade down
            if self.score_pulse_timer <= 0.1:
                # Fade up to bright white over 0.1 seconds
                progress = self.score_pulse_timer / 0.1
                opacity = 0.5 + (0.5 * progress)  # 50% to 100%
            else:
                # Fade down to 50% over remaining duration
                fade_progress = (self.score_pulse_timer - 0.1) / (self.score_pulse_duration - 0.1)
                opacity = 1.0 - (0.5 * fade_progress)  # 100% to 50%
            
            # Calculate size scaling based on new ranges:
            # 0-999 points: 1.0x
            # 1000-4999 points: 1.0x-1.5x
            # 5000-9999 points: 1.5x-2.0x
            # 10000+ points: 2.0x-3.0x
            if self.score_change <= 999:
                size_scale = 1.0  # No scaling for small scores
            elif self.score_change <= 4999:
                # Linear scaling from 1.0x at 1000 points to 1.5x at 4999 points
                size_scale = 1.0 + ((self.score_change - 1000) / 3999.0) * 0.5  # 1.0 to 1.5
            elif self.score_change <= 9999:
                # Linear scaling from 1.5x at 5000 points to 2.0x at 9999 points
                size_scale = 1.5 + ((self.score_change - 5000) / 4999.0) * 0.5  # 1.5 to 2.0
            else:
                # Linear scaling from 2.0x at 10000 points to 3.0x at 100000+ points
                size_scale = 2.0 + ((self.score_change - 10000) / 90000.0) * 1.0  # 2.0 to 3.0
                size_scale = min(size_scale, 3.0)  # Cap at 3x
        else:
            # Normal state: 50% opacity, normal size
            opacity = 0.5
            size_scale = 1.0
        
        # Create font with scaled size
        base_font_size = 36
        scaled_font_size = int(base_font_size * size_scale)
        font = pygame.font.Font(None, scaled_font_size)
        
        # Render score text
        score_text = str(self.score)
        score_surface = font.render(score_text, True, WHITE)
        score_surface.set_alpha(int(255 * opacity))
        
        # Center the score (below level)
        score_rect = score_surface.get_rect(center=(self.current_width//2, 60))
        surface.blit(score_surface, score_rect)
        
        # Draw multiplier if > 1.5x
        if current_multiplier > 1.5:
            # Calculate multiplier color (white to green gradient)
            # White at 1.5x, green at 4.5x+
            color_progress = min((current_multiplier - 1.5) / 3.0, 1.0)  # 0.0 to 1.0
            
            # For white: all RGB values are 255
            # For green: red and blue decrease, green stays 255
            red = int(255 * (1.0 - color_progress))  # 255 to 0
            green = 255  # Always 255 (white to green)
            blue = int(255 * (1.0 - color_progress))  # 255 to 0
            
            multiplier_color = (red, green, blue)
            
            # Apply pulse effect to multiplier if it just increased
            multiplier_opacity = opacity
            if self.multiplier_pulse_timer > 0:
                pulse_progress = self.multiplier_pulse_timer / self.multiplier_pulse_duration
                multiplier_opacity = min(1.0, opacity + (0.5 * pulse_progress))  # Extra brightness during pulse
            
            # Render multiplier text
            multiplier_text = f"x{current_multiplier:.1f}"
            multiplier_surface = font.render(multiplier_text, True, multiplier_color)
            multiplier_surface.set_alpha(int(255 * multiplier_opacity))
            
            # Position multiplier to the right of score
            multiplier_rect = multiplier_surface.get_rect(center=(self.current_width//2 + 100, 60))
            surface.blit(multiplier_surface, multiplier_rect)
    
    def spawn_asteroids(self, count=None):
        # New table-based asteroid spawning system
        # Check asteroid limit before spawning
        if not self._check_asteroid_limit():
            return  # Skip spawning if at limit
        
        # Get spawn configuration for current level
        spawn_config = self._get_asteroid_spawn_config(self.level)
        if not spawn_config:
            return
        
        # Spawn guaranteed asteroids
        for size_config in spawn_config['guaranteed']:
            if len(self.asteroids) >= MAX_ASTEROIDS:
                break
            size = self._get_random_size_from_config(size_config)
            x, y = self.get_edge_position()
            
            # 5% chance to spawn ability asteroid
            if random.random() < 0.05:
                asteroid = AbilityAsteroid(x, y, size, self.level, ability_charges=1)
            else:
                asteroid = Asteroid(x, y, size, self.level)
            self.asteroids.append(asteroid)
        
        # Spawn probabilistic asteroids
        for prob_config in spawn_config['probabilistic']:
            if len(self.asteroids) >= MAX_ASTEROIDS:
                break
            if random.random() < prob_config['chance']:
                size = self._get_random_size_from_config(prob_config['size_config'])
                x, y = self.get_edge_position()
                
                # 5% chance to spawn ability asteroid
                if random.random() < 0.05:
                    asteroid = AbilityAsteroid(x, y, size, self.level, ability_charges=1)
                else:
                    asteroid = Asteroid(x, y, size, self.level)
                self.asteroids.append(asteroid)
    
    def _get_asteroid_spawn_config(self, level):
        """Get asteroid spawn configuration for a given level"""
        # Asteroid spawn table based on the provided data
        spawn_table = {
            1: {
                'guaranteed': ['789', '456'],
                'probabilistic': []
            },
            2: {
                'guaranteed': ['789', '456', '123'],
                'probabilistic': []
            },
            3: {
                'guaranteed': ['9', '78', '56', '34'],
                'probabilistic': []
            },
            4: {
                'guaranteed': ['789', '456', '123'],
                'probabilistic': [
                    {'chance': 0.75, 'size_config': '456'},
                    {'chance': 0.75, 'size_config': '123'}
                ]
            },
            5: {
                'guaranteed': ['789', '456', '123'],
                'probabilistic': [
                    {'chance': 0.75, 'size_config': '456'},
                    {'chance': 0.75, 'size_config': '123'},
                    {'chance': 0.75, 'size_config': '456'}
                ]
            },
            6: {
                'guaranteed': ['9', '78', '56', '34', '12', '8', '34'],
                'probabilistic': []
            },
            7: {
                'guaranteed': ['789', '456', '123', '456', '123'],
                'probabilistic': [
                    {'chance': 0.66, 'size_config': '456'},
                    {'chance': 0.66, 'size_config': '789'},
                    {'chance': 0.66, 'size_config': '456'}
                ]
            },
            8: {
                'guaranteed': ['789', '456', '123', '456', '123'],
                'probabilistic': [
                    {'chance': 0.66, 'size_config': '456'},
                    {'chance': 0.66, 'size_config': '789'},
                    {'chance': 0.66, 'size_config': '456'},
                    {'chance': 0.66, 'size_config': '123'}
                ]
            },
            9: {
                'guaranteed': ['9', '78', '56', '34', '12', '8', '34', '56', '34', '12'],
                'probabilistic': []
            },
            10: {
                'guaranteed': ['789', '456', '123', '456', '123', '456', '789'],
                'probabilistic': [
                    {'chance': 0.50, 'size_config': '456'},
                    {'chance': 0.50, 'size_config': '123'},
                    {'chance': 0.50, 'size_config': '456'},
                    {'chance': 0.50, 'size_config': '789'}
                ]
            },
            11: {
                'guaranteed': ['789', '456', '123', '456', '123', '456', '789'],
                'probabilistic': [
                    {'chance': 0.50, 'size_config': '456'},
                    {'chance': 0.50, 'size_config': '123'},
                    {'chance': 0.50, 'size_config': '456'},
                    {'chance': 0.50, 'size_config': '789'},
                    {'chance': 0.50, 'size_config': '456'}
                ]
            },
            12: {
                'guaranteed': ['9', '9', '7', '7', '7', '7', '56', '56', '56', '56', '34', '34', '34'],
                'probabilistic': []
            },
            13: {
                'guaranteed': ['789', '456', '123', '456', '123', '456', '789'],
                'probabilistic': [
                    {'chance': 0.33, 'size_config': '456'},
                    {'chance': 0.33, 'size_config': '123'},
                    {'chance': 0.33, 'size_config': '456'},
                    {'chance': 0.33, 'size_config': '789'},
                    {'chance': 0.33, 'size_config': '456'},
                    {'chance': 0.33, 'size_config': '123'},
                    {'chance': 0.33, 'size_config': '456'}
                ]
            },
            14: {
                'guaranteed': ['789', '456', '123', '456', '123', '456', '789'],
                'probabilistic': [
                    {'chance': 0.33, 'size_config': '456'},
                    {'chance': 0.33, 'size_config': '123'},
                    {'chance': 0.33, 'size_config': '456'},
                    {'chance': 0.33, 'size_config': '789'},
                    {'chance': 0.33, 'size_config': '456'},
                    {'chance': 0.33, 'size_config': '123'},
                    {'chance': 0.33, 'size_config': '456'},
                    {'chance': 0.33, 'size_config': '789'}
                ]
            },
            15: {
                'guaranteed': ['9', '78', '56', '34', '12', '8', '34', '56', '34', '12', '7', '34', '56', '34', '12', '6'],
                'probabilistic': []
            },
            16: {
                'guaranteed': ['789', '456', '123', '456', '123'],
                'probabilistic': [
                    {'chance': 0.50, 'size_config': '456'},
                    {'chance': 0.50, 'size_config': '789'},
                    {'chance': 0.50, 'size_config': '456'},
                    {'chance': 0.50, 'size_config': '123'},
                    {'chance': 0.50, 'size_config': '456'},
                    {'chance': 0.50, 'size_config': '789'},
                    {'chance': 0.50, 'size_config': '456'},
                    {'chance': 0.50, 'size_config': '123'},
                    {'chance': 0.50, 'size_config': '456'},
                    {'chance': 0.50, 'size_config': '789'},
                    {'chance': 0.50, 'size_config': '456'},
                    {'chance': 0.50, 'size_config': '123'}
                ]
            },
            17: {
                'guaranteed': ['789', '456', '123', '456', '123', '456', '789', '456', '123', '456'],
                'probabilistic': [
                    {'chance': 0.50, 'size_config': '789'},
                    {'chance': 0.50, 'size_config': '456'},
                    {'chance': 0.50, 'size_config': '123'},
                    {'chance': 0.50, 'size_config': '456'},
                    {'chance': 0.50, 'size_config': '789'},
                    {'chance': 0.50, 'size_config': '456'},
                    {'chance': 0.50, 'size_config': '123'},
                    {'chance': 0.50, 'size_config': '456'}
                ]
            },
            18: {
                'guaranteed': ['9', '9', '8', '8', '7', '7', '7', '6', '6', '5', '5', '4', '4', '3', '3', '2', '2', '1', '1'],
                'probabilistic': []
            },
            19: {
                'guaranteed': ['789', '456', '123', '456', '123'],
                'probabilistic': [
                    {'chance': 0.75, 'size_config': '456'},
                    {'chance': 0.75, 'size_config': '789'},
                    {'chance': 0.75, 'size_config': '456'},
                    {'chance': 0.75, 'size_config': '123'},
                    {'chance': 0.75, 'size_config': '456'},
                    {'chance': 0.75, 'size_config': '789'},
                    {'chance': 0.75, 'size_config': '456'},
                    {'chance': 0.75, 'size_config': '123'},
                    {'chance': 0.75, 'size_config': '456'},
                    {'chance': 0.75, 'size_config': '789'},
                    {'chance': 0.75, 'size_config': '456'},
                    {'chance': 0.75, 'size_config': '123'},
                    {'chance': 0.75, 'size_config': '456'},
                    {'chance': 0.75, 'size_config': '789'},
                    {'chance': 0.75, 'size_config': '456'}
                ]
            },
            20: {
                'guaranteed': ['789', '45', '123', '67', '123', '45', '89', '67', '123', '45'],
                'probabilistic': [
                    {'chance': 0.75, 'size_config': '89'},
                    {'chance': 0.75, 'size_config': '67'},
                    {'chance': 0.75, 'size_config': '123'},
                    {'chance': 0.75, 'size_config': '45'},
                    {'chance': 0.75, 'size_config': '89'},
                    {'chance': 0.75, 'size_config': '67'},
                    {'chance': 0.75, 'size_config': '123'},
                    {'chance': 0.75, 'size_config': '45'},
                    {'chance': 0.75, 'size_config': '89'},
                    {'chance': 0.75, 'size_config': '67'},
                    {'chance': 0.75, 'size_config': '123'}
                ]
            },
            21: {
                'guaranteed': ['9', '9', '9', '8', '8', '8', '7', '7', '7', '6', '6', '6', '5', '5', '5', '4', '4', '4', '3', '3', '3', '9'],
                'probabilistic': []
            }
        }
        
        # For levels beyond 21, use the pattern: (current level) × 1 random sized asteroids
        if level > 21:
            return {
                'guaranteed': [],
                'probabilistic': [
                    {'chance': 1.0, 'size_config': '123456789'}  # Random size from 1-9
                    for _ in range(level)
                ]
            }
        
        return spawn_table.get(level, None)
    
    def _get_random_size_from_config(self, size_config):
        """Convert size configuration string to random size"""
        if len(size_config) == 1:
            # Single size
            return int(size_config)
        else:
            # Multiple sizes, pick one randomly
            return random.choice([int(s) for s in size_config])
    
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
    
    def _check_asteroid_limit(self):
        """Check if we're at the asteroid limit and clean up if needed"""
        if len(self.asteroids) >= MAX_ASTEROIDS:
            self._cleanup_old_asteroids()
            return len(self.asteroids) < MAX_ASTEROIDS
        return True
    
    def _cleanup_old_asteroids(self):
        """Remove newest asteroids when at limit (delete newest ones)"""
        if len(self.asteroids) < MAX_ASTEROIDS:
            return
        
        # Sort asteroids by creation time (newest first)
        sorted_asteroids = sorted(self.asteroids, key=lambda a: a.creation_time, reverse=True)
        
        # Calculate how many to remove (keep only MAX_ASTEROIDS - 10 for buffer)
        asteroids_to_remove = len(self.asteroids) - (MAX_ASTEROIDS - 10)
        
        # Get the newest asteroids to remove
        asteroids_to_delete = sorted_asteroids[:asteroids_to_remove]
        
        # Remove them from the main list
        for asteroid in asteroids_to_delete:
            if asteroid in self.asteroids:
                self.asteroids.remove(asteroid)
    
    def _add_asteroids_with_limit(self, new_asteroids):
        """Add new asteroids while respecting the asteroid limit"""
        if not new_asteroids:
            return
        
        # Check if we can add all asteroids
        if len(self.asteroids) + len(new_asteroids) <= MAX_ASTEROIDS:
            self.asteroids.extend(new_asteroids)
        else:
            # Add as many as we can
            available_slots = MAX_ASTEROIDS - len(self.asteroids)
            if available_slots > 0:
                self.asteroids.extend(new_asteroids[:available_slots])
    
    def spawn_ufo(self):
        side = random.randint(0, 1)
        if side == 0:  # Left
            x = 0
            y = random.uniform(0, self.current_height)
        else:  # Right
            x = self.current_width
            y = random.uniform(0, self.current_height)
        
        # Level-based personality selection with 10% deadly chance
        if random.random() < 0.1:
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
        
        # 3% chance to spawn ability UFO
        if random.random() < 0.03:
            ufo = AbilityUFO(x, y, personality, ability_charges=1)
        else:
            ufo = AdvancedUFO(x, y, personality)
        self.add_ufo(ufo)
    
    def spawn_ufo_from_corner(self):
        # Pick a random corner
        corners = [
            (0, 0),  # Top-left
            (self.current_width, 0),  # Top-right
            (0, self.current_height),  # Bottom-left
            (self.current_width, self.current_height)  # Bottom-right
        ]
        x, y = random.choice(corners)
        
        # Level-based personality selection with 10% deadly chance
        if random.random() < 0.1:
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
        
        self.add_ufo(AdvancedUFO(x, y, personality))
    
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
        self.add_ufo(AdvancedUFO(x, y, personality))
    
    def spawn_ufo_with_personality_at_corner(self, personality, corner, speed_multiplier=1.0):
        """Spawn a UFO with a specific personality at a specific corner with optional speed multiplier"""
        x, y = corner
        ufo = AdvancedUFO(x, y, personality)
        # Apply speed multiplier (25% to 100% = 0.25 to 1.0)
        ufo.speed *= speed_multiplier
        ufo.max_speed *= speed_multiplier
        ufo.acceleration *= speed_multiplier
        self.add_ufo(ufo)
    
    def spawn_ufo_from_selected_corner(self):
        """Spawn a UFO with random personality from the selected corner for this level"""
        x, y = self.ufo_spawn_corner
        
        # Level-based personality selection with 10% deadly chance
        if random.random() < 0.1:
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
        
        self.add_ufo(AdvancedUFO(x, y, personality))
    
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
            
            # Level-based personality selection with 10% deadly chance
            if random.random() < 0.1:
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
            
            self.add_ufo(AdvancedUFO(x, y, personality))
    
    def spawn_ufo_burst(self, num_ufos):
        """Spawn a burst of UFOs (up to 4) with one per corner"""
        corners = [
            (0, 0),  # Top-left
            (self.current_width, 0),  # Top-right
            (0, self.current_height),  # Bottom-left
            (self.current_width, self.current_height)  # Bottom-right
        ]
        
        # Spawn up to 4 UFOs, one per corner
        for i in range(min(num_ufos, 4)):
            x, y = corners[i]
            
            # Level-based personality selection with 10% deadly chance
            if random.random() < 0.1:
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
            
            self.add_ufo(AdvancedUFO(x, y, personality))
    
    def handle_input(self, dt):
        
        # C key to clear image cache and refresh scoreboard (debug feature)
        if pygame.K_c in self.keys_pressed:
            self.clear_image_cache()
            # Also refresh scoreboard cache
            if self.scoreboard_available and self.scoreboard:
                self.scoreboard.force_refresh_cache()
                if self.show_scoreboard:
                    # Load scores in background
                    self.load_scoreboard_background()
                    # print(f"[SCOREBOARD DEBUG] C key pressed - refreshed scoreboard cache and updated display")
            
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
        
        # CTRL keys for rapid deceleration
        left_ctrl_pressed = pygame.K_LCTRL in self.keys_pressed
        right_ctrl_pressed = pygame.K_RCTRL in self.keys_pressed
        
        # Rotation (arrow keys only)
        if left_rotate_pressed:
            if self.ship:
                self.ship.rotate_left(dt)
                self.ship.is_spinning = True
        elif right_rotate_pressed:
            if self.ship:
                self.ship.rotate_right(dt)
                self.ship.is_spinning = True
        else:
            if self.ship:
                self.ship.stop_rotation()
                self.ship.is_spinning = False
            
        # Strafe (A and D keys)
        if self.ship:
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
            
        # Rapid deceleration (CTRL keys)
        if left_ctrl_pressed or right_ctrl_pressed:
            self.ship.rapid_decelerate(dt)
            
        if pygame.K_SPACE in self.keys_pressed:
            self.shoot_continuous()
        
        # Ability activation (Q, E, or B keys) - only for in-game, title screen handled in KEYDOWN
        if (pygame.K_q in self.keys_pressed or pygame.K_e in self.keys_pressed or pygame.K_b in self.keys_pressed):
            if self.game_state == "playing":
                self.activate_ability()
        
        # Debug mode toggle (F1 key) - with cooldown
        if pygame.K_F1 in self.keys_pressed and self.f1_cooldown_timer <= 0:
            self.debug_mode = not self.debug_mode
            self.f1_cooldown_timer = self.key_cooldown_duration
        
        # God mode toggle (G key) - only works in debug mode, with cooldown
        if pygame.K_g in self.keys_pressed and self.debug_mode and self.g_cooldown_timer <= 0:
            self.god_mode = not self.god_mode
            status = "ENABLED" if self.god_mode else "DISABLED"
            game_logger._write_log(f"GOD MODE: {status}")
            self.g_cooldown_timer = self.key_cooldown_duration
        
        # Debug point bonuses (1, 2, 3 keys) - only work in debug mode, with cooldowns
        if self.debug_mode:
            # Key 1: 100,000 points
            if pygame.K_1 in self.keys_pressed and self.key1_cooldown_timer <= 0:
                self.add_score(100000, "debug key 1")
                self.key1_cooldown_timer = self.key_cooldown_duration
            
            # Key 2: 250,000 points
            if pygame.K_2 in self.keys_pressed and self.key2_cooldown_timer <= 0:
                self.add_score(250000, "debug key 2")
                self.key2_cooldown_timer = self.key_cooldown_duration
            
            # Key 3: 500,000 points
            if pygame.K_3 in self.keys_pressed and self.key3_cooldown_timer <= 0:
                self.add_score(500000, "debug key 3")
                self.key3_cooldown_timer = self.key_cooldown_duration
            
            # Key 4: Spawn boss
            if pygame.K_4 in self.keys_pressed and self.key4_cooldown_timer <= 0:
                # Choose random direction for boss
                direction = random.choice(["left", "right"])
                # Let BossEnemy constructor handle off-screen positioning
                boss = BossEnemy(0, 0, direction, self.current_width, self.current_height)
                self.add_boss(boss)
                game_logger.log_boss_spawn(1, self.level)
                self.key4_cooldown_timer = self.key_cooldown_duration
            
            # Key 5: Advance level
            if pygame.K_5 in self.keys_pressed and self.key5_cooldown_timer <= 0:
                # Only advance level if in playing state
                if self.game_state == "playing":
                    self.advance_level()
                    self.key5_cooldown_timer = self.key_cooldown_duration
    
    def shoot(self):
        if not self.ship or len(self.bullets) < 20:  # Check if ship exists and limit bullets (5x increase from 4)
            if not self.ship:
                return  # Exit early if no ship
            return  # Exit early if too many bullets
        
        try:
            # Scale bullet speed based on current rate of fire
            base_speed = 400
            # Scale from 400@0.09 to 500@0.042 to 300@0.17
            if self.ship.shoot_interval >= 0.17:
                # At slowest speed (0.17) and slower, use 0.75x base speed
                speed_multiplier = 0.75
            elif self.ship.shoot_interval <= 0.042:
                # At peak speed (0.042) and faster, use 1.25x base speed (500/400)
                speed_multiplier = 1.25
            else:
                # Linear interpolation between 0.09 and 0.17 (0.09=1.0x, 0.17=0.75x)
                progress = (self.ship.shoot_interval - 0.09) / (0.17 - 0.09)
                speed_multiplier = 1.0 - (progress * 0.25)  # 1.0 to 0.75
            
            bullet_speed = base_speed * speed_multiplier
            angle = self.ship.angle
            
            # Add player velocity to bullet velocity
            vx = math.cos(angle) * bullet_speed + self.ship.velocity.x
            vy = math.sin(angle) * bullet_speed + self.ship.velocity.y
            
            # Spawn bullet slightly in front of the rocket
            bullet_x = self.ship.position.x + math.cos(angle) * 25
            bullet_y = self.ship.position.y + math.sin(angle) * 25
            
            bullet = Bullet(bullet_x, bullet_y, vx, vy, is_ufo_bullet=False, angle=angle)
            self.bullets.append(bullet)
            
            # Add screen shake based on current rate of fire
            shake_intensity, shake_duration = self.get_rof_screen_shake(self.ship.shoot_interval)
            if shake_intensity > 0:
                self.add_screen_shake(shake_intensity, shake_duration)
        except Exception as e:
            # Don't crash, just continue
            pass
    
    def shoot_continuous(self):
        # Prevent shooting for first 0.5 seconds after game start
        if self.game_state == "playing" and self.game_start_timer < 0.5:
            return
            
        # Check if ship exists
        if not self.ship:
            return
        
        try:
            # Check if enough time has passed since last shot
            if self.ship.shoot_timer <= 0 and len(self.bullets) < 40:  # 5x increased bullet limit
                # Increment shot count for progressive shooting
                self.ship.shot_count += 1
                # Scale bullet speed based on current rate of fire
                base_speed = 400
                # Scale from 400@0.09 to 500@0.042 to 300@0.17
                if self.ship.shoot_interval >= 0.17:
                    # At slowest speed (0.17) and slower, use 0.75x base speed
                    speed_multiplier = 0.75
                elif self.ship.shoot_interval <= 0.042:
                    # At peak speed (0.042) and faster, use 1.25x base speed (500/400)
                    speed_multiplier = 1.25
                else:
                    # Linear interpolation between 0.09 and 0.17 (0.09=1.0x, 0.17=0.75x)
                    progress = (self.ship.shoot_interval - 0.09) / (0.17 - 0.09)
                    speed_multiplier = 1.0 - (progress * 0.25)  # 1.0 to 0.75
                
                bullet_speed = base_speed * speed_multiplier
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
                
                # Add screen shake based on current rate of fire
                shake_intensity, shake_duration = self.get_rof_screen_shake(self.ship.shoot_interval)
                if shake_intensity > 0:
                    self.add_screen_shake(shake_intensity, shake_duration)
        except Exception as e:
            # Don't crash, just continue
            pass
    
    def add_screen_shake(self, intensity, duration):
        """Add screen shake with random intensity (1-5/10) and specified duration"""
        self.screen_shake_intensity = intensity
        self.screen_shake_timer = duration
    
    def get_rof_screen_shake(self, shoot_interval):
        """Calculate screen shake intensity based on rate of fire with quadratic ramp"""
        # Scale from 0 intensity at 0.09s+ to 3.0/10 intensity at 0.042s
        if shoot_interval >= 0.09:
            return 0.0, 0.0  # No shake for slow firing
        elif shoot_interval <= 0.042:
            return 3.0, 0.1  # Maximum shake for fast firing
        else:
            # Quadratic interpolation between 0.042 and 0.09 (quickly rising at the end)
            progress = (shoot_interval - 0.042) / (0.09 - 0.042)
            # Use quadratic curve: intensity rises quickly at the end
            quadratic_progress = progress * progress
            intensity = 3.0 - (quadratic_progress * 3.0)  # 3.0 to 0
            duration = 0.1 - (quadratic_progress * 0.1)     # 0.1 to 0
            return intensity, duration
    
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
                    new_asteroids = asteroid.split(level=self.level)
                    if new_asteroids:
                        # Add the new asteroids to the game
                        for new_asteroid in new_asteroids:
                            # All asteroids have shadows (hardcoded in Asteroid.__init__)
                            self.asteroids.append(new_asteroid)
                    
                    # Generate explosion particles with new color distribution
                    total_particles = 20 + asteroid.size * 5
                    
                    # 40% gray particles (75-125 range)
                    self.explosions.add_explosion(asteroid.position.x, asteroid.position.y, 
                                                num_particles=int(total_particles * 0.40), 
                                                color=(75, 75, 75), asteroid_size=asteroid.size, is_ufo=False, use_raw_time=True)  # Gray
                    # 20% dark brown particles
                    self.explosions.add_explosion(asteroid.position.x, asteroid.position.y, 
                                                num_particles=int(total_particles * 0.20), 
                                                color=(34, 9, 1), asteroid_size=asteroid.size, is_ufo=False, use_raw_time=True)  # Dark brown
                    # 15% red-brown particles
                    self.explosions.add_explosion(asteroid.position.x, asteroid.position.y, 
                                                num_particles=int(total_particles * 0.15), 
                                                color=(98, 23, 8), asteroid_size=asteroid.size, is_ufo=False, use_raw_time=True)  # Red-brown
                    # 10% orange-red particles
                    self.explosions.add_explosion(asteroid.position.x, asteroid.position.y, 
                                                num_particles=int(total_particles * 0.10), 
                                                color=(148, 27, 12), asteroid_size=asteroid.size, is_ufo=False, use_raw_time=True)  # Orange-red
                    # 8% orange particles
                    self.explosions.add_explosion(asteroid.position.x, asteroid.position.y, 
                                                num_particles=int(total_particles * 0.08), 
                                                color=(188, 57, 8), asteroid_size=asteroid.size, is_ufo=False, use_raw_time=True)  # Orange
                    # 7% golden particles
                    self.explosions.add_explosion(asteroid.position.x, asteroid.position.y, 
                                                num_particles=int(total_particles * 0.07), 
                                                color=(246, 170, 28), asteroid_size=asteroid.size, is_ufo=False, use_raw_time=True)  # Golden
                    
                    # Add score (like normal asteroid hit)
                    self.add_score(asteroid.size * 1, "asteroid shot")
                    
                    # Remove the original asteroid
                    asteroid.active = False
                    self.asteroids.remove(asteroid)
                else:
                    # Asteroid is destroyed - generate explosion and add score
                    self.explosions.add_explosion(asteroid.position.x, asteroid.position.y, 
                                                num_particles=20 + asteroid.size * 5, 
                                                color=(255, 255, 0), 
                                                asteroid_size=asteroid.size, is_ufo=False, use_raw_time=True)
                    self.add_score(asteroid.size * 1, "asteroid shot")
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
        
        # Charge one shield ring per ability blast
        if self.ship and self.ship.shield_hits < self.ship.max_shield_hits:
            # Increase shield hits by 1 (charge one ring)
            self.ship.shield_hits += 1
            
            # Trigger shield recharge animation for the newly charged ring
            self.ship.shield_recharge_pulse_timer = self.ship.shield_recharge_pulse_duration
            
            # Reset shield recharge time to show the charging progress
            self.ship.shield_recharge_time = 0
            
            # Mark that shields were charged via ability
            self.ship.shield_charged_by_ability = True
            
            # Trigger full shield flash if this completes the shields
            if self.ship.shield_hits == self.ship.max_shield_hits:
                self.ship.shield_full_flash_timer = self.ship.shield_full_flash_duration

    def generate_title_ability_particles(self):
        """Generate 200 ability particles centered from game title on title screen and destroy all UFOs"""
        # Center position of the game title
        center_x = self.current_width // 2
        center_y = self.current_height // 2 - 100  # Title position
        
        # Destroy all visible UFOs on title screen
        for ufo in self.ufos[:]:
            if ufo.active:
                # Add explosion particles for each destroyed UFO (5 bright white, 45 electric blue)
                
                # 5 bright white particles (matching Copy 3)
                self.explosions.add_explosion(ufo.position.x, ufo.position.y, 
                                            num_particles=5, 
                                            color=(255, 255, 255), is_ufo=True)  # Bright white
                
                # 45 electric blue particles (matching Copy 3)
                self.explosions.add_explosion(ufo.position.x, ufo.position.y, 
                                            num_particles=45, 
                                            color=(0, 150, 255), is_ufo=True)  # Electric blue
                
                # Mark UFO as inactive
                ufo.active = False
        
        # Clean up inactive UFOs and their wave data
        self.ufos = [ufo for ufo in self.ufos if ufo.active]
        self.title_ufo_wave_data = self.title_ufo_wave_data[:len(self.ufos)]
        
        # Generate 200 purple and pink particles with enhanced effects
        # Use high priority for title screen effects
        priority = 5
        
        # Check particle limit before adding
        if not self.explosions._check_particle_limit(priority):
            return
            
        for _ in range(200):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(80, 300)  # Increased speed range
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            
            # Enhanced color variety - purple, pink, and electric blue
            color_choice = random.random()
            if color_choice < 0.4:
                color = (255, 0, 255)  # Purple
            elif color_choice < 0.8:
                color = (255, 100, 255)  # Pink
            else:
                color = (100, 200, 255)  # Electric blue
            
            # Create particle with varied size and lifetime
            particle = Particle(
                x=center_x,
                y=center_y,
                vx=vx,
                vy=vy,
                color=color,
                size=random.uniform(2, 5),  # Larger particles
                lifetime=random.uniform(1.5, 3.0),  # Longer lifetime
                use_raw_time=True
            )
            self.explosions.particles.append(particle)
            self.explosions.particle_priorities.append(priority)
        
        # Add screen shake for visual impact
        self.trigger_screen_shake(8, 0.5)  # Stronger shake for UFO destruction

    def activate_ability(self):
        """Activate the asteroid breaking ability if ready"""
        try:
            if self.ship.ability_charges > 0 and not self.ship.ability_used and not self.ability_breaking:
                # Use all available charges (both rings go to 0%)
                charges_used = self.ship.ability_charges
                self.ship.ability_charges = 0
                self.ship.ability_ready = False
                self.ship.ability_timer = 0.0  # Reset timer to start charging from 0
            
                # Determine blast count based on charges used
                # 1 charge = 2 blasts, 2 charges = 4 blasts
                if charges_used == 1:
                    self.ability_blast_count = 2
                else:  # charges_used == 2
                    self.ability_blast_count = 4
                
                # Log ability usage
                game_logger.log_ability_use(f"asteroid_breaking_{charges_used}_charges")
                
                # Start the break sequence
                self.ability_breaking = True
                self.ability_break_count = 0
                self.ability_break_timer = 0.0
                self.ability_break_delay = random.uniform(0.2, 0.42)
                
                # Reset multiplier to 1x after using ability
                self.asteroids_destroyed_this_level = 0
                self.ufos_killed_this_level = 0
                self.last_multiplier = 1.0
                self.multiplier_pulse_timer = 0.0
                self.multiplier_decay_timer = 0.0
                self.is_decaying = False
                self.multiplier_decay_start_value = 1.0
                
                # Generate particles for all objects on first break
                total_asteroids = sum(1 for asteroid in self.asteroids if asteroid.active)
                total_ufos = sum(1 for ufo in self.ufos if ufo.active)
                total_objects = total_asteroids + total_ufos
                
                if total_objects > 0:
                    particles_per_object = 10  # 10 particles per asteroid/UFO
                    
                    # Generate particles for all asteroids (6 white, 2 yellow, 2 red)
                    for asteroid in self.asteroids[:]:
                        if asteroid.active:
                            # 6 white particles
                            self.explosions.add_explosion(asteroid.position.x, asteroid.position.y, 
                                                        num_particles=6, color=(255, 255, 255), 
                                                        asteroid_size=asteroid.size, is_ufo=False, use_raw_time=True)
                            # 2 yellow particles
                            self.explosions.add_explosion(asteroid.position.x, asteroid.position.y, 
                                                        num_particles=2, color=(255, 255, 0), 
                                                        asteroid_size=asteroid.size, is_ufo=False, use_raw_time=True)
                            # 2 red particles
                            self.explosions.add_explosion(asteroid.position.x, asteroid.position.y, 
                                                        num_particles=2, color=(255, 0, 0), 
                                                        asteroid_size=asteroid.size, is_ufo=False, use_raw_time=True)
                    
                    # Generate particles for all UFOs (6 white, 2 yellow, 2 red)
                    for ufo in self.ufos[:]:
                        if ufo.active:
                            # 6 white spinout sparks
                            for _ in range(6):
                                self.explosions.add_explosion(
                                    ufo.position.x,
                                    ufo.position.y,
                                    num_particles=1,
                                    color=(255, 255, 255),  # White
                                    is_ufo=True,
                                    use_raw_time=True
                                )
                            # 2 yellow spinout sparks
                            for _ in range(2):
                                self.explosions.add_explosion(
                                    ufo.position.x,
                                    ufo.position.y,
                                    num_particles=1,
                                    color=(255, 200, 0),  # Orange-yellow
                                    is_ufo=True,
                                    use_raw_time=True
                                )
                            # 2 red spinout sparks
                            for _ in range(2):
                                self.explosions.add_explosion(
                                    ufo.position.x,
                                    ufo.position.y,
                                    num_particles=1,
                                    color=(255, 50, 0),  # Red-orange
                                    is_ufo=True,
                                    use_raw_time=True
                                )
                
                # Generate 200 purple and pink particles from player
                # Use high priority for ability particles
                priority = 4
                
                # Check particle limit before adding
                if not self.explosions._check_particle_limit(priority):
                    return
                    
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
                    self.explosions.particle_priorities.append(priority)
        except Exception as e:
            # Log the error and continue without crashing
            print(f"Error in activate_ability: {e}")
            import traceback
            traceback.print_exc()
    
    def check_collisions(self):
        # Bullet vs Asteroid (with screen wrapping) - Medium Priority
        if self.should_check_collision('bullet_asteroid', 1.0/60.0):
            for bullet in self.bullets[:]:
                if not bullet.active:
                    continue
                for asteroid in self.asteroids[:]:
                    if not asteroid.active:
                        continue
                    # Check collision with screen wrapping
                    if self.check_wrapped_collision(bullet.position, asteroid.get_hitbox_center(), bullet.radius, asteroid.radius):
                        # Hit!
                        bullet.active = False
                        asteroid.active = False
                        
                        # Add shot hit particles
                        self.explosions.add_shot_hit_particles(asteroid.position.x, asteroid.position.y)
                        
                        # Add screen shake for asteroid sizes 5+ only
                        intensity, duration = get_asteroid_shake_params(asteroid.size)
                        if intensity > 0:
                            self.trigger_screen_shake(intensity, duration)
                        
                        # Add explosion particles (new scaling formula)
                        total_particles = int((20 + ((2 * asteroid.size) * 20)) * 0.5)  # 50% fewer particles
                        
                        # 40% gray particles (75-125 range)
                        self.explosions.add_explosion(asteroid.position.x, asteroid.position.y, 
                                                    num_particles=int(total_particles * 0.40), 
                                                    color=(75, 75, 75), asteroid_size=asteroid.size)  # Gray
                        # 20% dark brown particles
                        self.explosions.add_explosion(asteroid.position.x, asteroid.position.y, 
                                                    num_particles=int(total_particles * 0.20), 
                                                    color=(34, 9, 1), asteroid_size=asteroid.size)  # Dark brown
                        # 15% red-brown particles
                        self.explosions.add_explosion(asteroid.position.x, asteroid.position.y, 
                                                    num_particles=int(total_particles * 0.15), 
                                                    color=(98, 23, 8), asteroid_size=asteroid.size)  # Red-brown
                        # 10% orange-red particles
                        self.explosions.add_explosion(asteroid.position.x, asteroid.position.y, 
                                                    num_particles=int(total_particles * 0.10), 
                                                    color=(148, 27, 12), asteroid_size=asteroid.size)  # Orange-red
                        # 8% orange particles
                        self.explosions.add_explosion(asteroid.position.x, asteroid.position.y, 
                                                    num_particles=int(total_particles * 0.08), 
                                                    color=(188, 57, 8), asteroid_size=asteroid.size)  # Orange
                        # 7% golden particles
                        self.explosions.add_explosion(asteroid.position.x, asteroid.position.y, 
                                                    num_particles=int(total_particles * 0.07), 
                                                    color=(246, 170, 28), asteroid_size=asteroid.size)  # Golden
                        
                        # Add score (size 4 = 44 points, size 3 = 33, etc.)
                        self.asteroids_destroyed_this_level += 1  # Track asteroid destroyed by player
                        self.add_score(asteroid.size * 11, "asteroid shot")
                        
                        # Check if this is an ability asteroid and grant ability charges
                        if hasattr(asteroid, 'is_ability_asteroid') and asteroid.is_ability_asteroid:
                            if asteroid.grant_ability_charges(self.ship):
                                # Add special score bonus for ability asteroid
                                self.add_score(100, "ability asteroid")
                                # Add special explosion effect
                                self.explosions.add_explosion(asteroid.position.x, asteroid.position.y, 
                                                            num_particles=30, 
                                                            color=(100, 255, 100), is_ufo=False)  # Green explosion
                        
                        # Increase shot rate for destroying asteroid
                        self.ship.asteroid_interval_bonus += 0.0001
                        
                        # Split asteroid with projectile velocity (only if not ability asteroid)
                        if not (hasattr(asteroid, 'is_ability_asteroid') and asteroid.is_ability_asteroid):
                            new_asteroids = asteroid.split(bullet.velocity, self.level)
                            self._add_asteroids_with_limit(new_asteroids)
                            break
        
        # Bullet vs UFO (with screen wrapping) - Medium Priority
        if self.should_check_collision('bullet_ufo', 1.0/60.0):
            for bullet in self.bullets[:]:
                if not bullet.active:
                    continue
                for ufo in self.ufos[:]:
                    if not ufo.active:
                        continue
                    if self.check_wrapped_collision(bullet.position, ufo.get_hitbox_center(), bullet.radius, ufo.radius):
                        # Hit!
                        bullet.active = False
                        
                        # Check if UFO is in spinout mode
                        if ufo.spinout_active:
                            # Check if collision delay has passed - if so, UFO can be destroyed
                            if hasattr(ufo, 'spinout_collision_delay_timer') and hasattr(ufo, 'spinout_collision_delay'):
                                if ufo.spinout_collision_delay_timer >= ufo.spinout_collision_delay:
                                    # Delay has passed - UFO can be destroyed by bullets
                                    ufo.active = False
                                    
                                    # Add dedicated spinout explosion particles for UFO
                                    # Generate 45 electric sparks
                                    for _ in range(45):
                                        self.explosions.add_explosion(
                                            ufo.position.x,
                                            ufo.position.y,
                                            (0, 150, 255),  # Electric blue
                                            "electric"
                                    )
                                    
                                    # Generate 30 bright white sparks
                                    for _ in range(30):
                                        self.explosions.add_explosion(
                                            ufo.position.x,
                                            ufo.position.y,
                                            (255, 255, 255),  # Bright white
                                            "electric"
                                        )
                                    self.ufos_killed_this_level += 1  # Track UFO killed by player
                                    self.add_score(500, "ufo shot")  # 500 points for destroying UFO with shot
                                    break
                                else:
                                    # Delay hasn't passed - UFO is still immune to projectiles
                                    # Add dedicated spinout sparks for shot hit
                                    for _ in range(4):
                                        if random.random() < 0.66:
                                            # Firey sparks
                                            colors = [(255, 100, 0), (255, 150, 0), (255, 200, 0), (255, 50, 0)]
                                            color = random.choice(colors)
                                            spark_type = "firey"
                                        else:
                                            # Electric sparks
                                            colors = [(0, 150, 255), (100, 200, 255), (255, 255, 255), (0, 100, 255)]
                                            color = random.choice(colors)
                                            spark_type = "electric"
                                        
                                        self.explosions.add_explosion(
                                            ufo.position.x,
                                            ufo.position.y,
                                            color,
                                            spark_type
                                        )
                                    break
                            else:
                                # No delay system - UFO is immune to projectiles
                                # Add dedicated spinout sparks for shot hit
                                for _ in range(4):
                                    if random.random() < 0.66:
                                        # Firey sparks
                                        colors = [(255, 100, 0), (255, 150, 0), (255, 200, 0), (255, 50, 0)]
                                        color = random.choice(colors)
                                        spark_type = "firey"
                                    else:
                                        # Electric sparks
                                        colors = [(0, 150, 255), (100, 200, 255), (255, 255, 255), (0, 100, 255)]
                                        color = random.choice(colors)
                                        spark_type = "electric"
                                    
                                    self.explosions.add_explosion(
                                        ufo.position.x,
                                        ufo.position.y,
                                        color,
                                        spark_type
                                    )
                                break
                        
                        # Check for spinout chance
                        spinout_chance = 0.10  # 10% chance by default
                        
                        # All UFOs on level 1 have 100% chance to spinout
                        if self.level == 1:
                            spinout_chance = 1.0
                        
                        if random.random() < spinout_chance:
                            # Trigger spinout effect
                            ufo.trigger_spinout()
                            
                            # Add dedicated spinout sparks for shot hit (UFO is still alive during spinout)
                            # Generate 4 sparks for shot hit - mix of firey and electric
                            for _ in range(4):
                                if random.random() < 0.66:
                                    # Firey sparks
                                    colors = [(255, 100, 0), (255, 150, 0), (255, 200, 0), (255, 50, 0)]
                                    color = random.choice(colors)
                                    spark_type = "firey"
                                else:
                                    # Electric sparks
                                    colors = [(0, 150, 255), (100, 200, 255), (255, 255, 255), (0, 100, 255)]
                                    color = random.choice(colors)
                                    spark_type = "electric"
                                
                                self.explosions.add_explosion(
                                    ufo.position.x,
                                    ufo.position.y,
                                    color,
                                    spark_type
                                )
                            
                            # Add screen shake for UFO hit (not destruction yet)
                            self.trigger_screen_shake(6, 0.3)  # Slightly less shake for hit vs destruction
                            
                            # Don't add score yet - will be added when spinout ends
                        else:
                            # Normal destruction
                            ufo.active = False
                            
                            # Add shot hit particles
                            self.explosions.add_shot_hit_particles(ufo.position.x, ufo.position.y)
                            
                            # Add screen shake for UFO destruction
                            self.trigger_screen_shake(8, 0.5)  # UFO shake
                            
                            # Add dedicated spinout explosion particles (90% electric blue, 10% bright white)
                            total_particles = int(40 * 1.5 * 1.5)  # 50% more particles (60 * 1.5 = 90)
                            
                            # 90% electric blue sparks
                            for _ in range(int(total_particles * 0.90)):
                                self.explosions.add_explosion(
                                    ufo.position.x,
                                    ufo.position.y,
                                    (0, 150, 255),  # Electric blue
                                    "electric"
                                )
                            
                            # 10% bright white sparks
                            for _ in range(int(total_particles * 0.10)):
                                self.explosions.add_explosion(
                                    ufo.position.x,
                                    ufo.position.y,
                                    (255, 255, 255),  # Bright white
                                    "electric"
                                )
                            
                            self.ufos_killed_this_level += 1  # Track UFO killed by player
                            self.add_score(500, "ufo shot")  # 500 points for destroying UFO with shot
                            
                            # Check if this is an ability UFO and grant ability charges
                            if hasattr(ufo, 'is_ability_ufo') and ufo.is_ability_ufo:
                                if ufo.grant_ability_charges(self.ship):
                                    # Add special score bonus for ability UFO
                                    self.add_score(200, "ability ufo")
                                    # Add special spinout explosion effect
                                    for _ in range(40):
                                        self.explosions.add_explosion(
                                            ufo.position.x,
                                            ufo.position.y,
                                            (100, 200, 255),  # Light blue explosion
                                            "electric"
                                        )
                            break
        
        # Ship vs Asteroid (with screen wrapping) - High Priority
        if self.ship.active and not self.ship.invulnerable and not self.god_mode:
            if self.should_check_collision('ship_asteroid', 1.0/60.0):
                for asteroid in self.asteroids:
                    if not asteroid.active:
                        continue
                    if self.check_wrapped_collision(self.ship.position, asteroid.get_hitbox_center(), self.ship.radius, asteroid.radius):
                        # Collision!
                        if self.ship.shield_hits > 0:
                            # Shield absorbs hit
                            self.ship.shield_hits -= 1
                            # Log player hit by asteroid (shield absorbed)
                            game_logger.log_player_hit_asteroid(self.ship.shield_hits, self.lives)
                            
                            # Don't reset recharge timer - let charging continue
                            self.ship.shield_damage_timer = self.ship.shield_damage_duration  # Show shield visual
                            self.ship.red_flash_timer = self.ship.red_flash_duration  # Trigger red flash
                            
                            # Add camera shake based on remaining shields (subject to time dilation)
                            intensity, duration, time_dilation = get_shield_damage_shake_params(self.ship.shield_hits, self.time_dilation_factor)
                            if intensity > 0:
                                self.trigger_screen_shake(intensity, duration, time_dilation)
                            
                            asteroid.active = False  # Destroy asteroid
                            
                            # Add explosion particles (with randomized lifetimes)
                            self.explosions.add_explosion(asteroid.position.x, asteroid.position.y, 
                                                        num_particles=20 + asteroid.size * 20, 
                                                        color=(0, 150, 255))  # Blue explosion
                            
                            # Add score for destroying asteroid with shield
                            self.asteroids_destroyed_this_level += 1  # Track asteroid destroyed by player
                            self.add_score(asteroid.size * 11, "asteroid shield")
                            
                            # Increase shot rate for destroying asteroid
                            self.ship.asteroid_interval_bonus += 0.0001
                        else:
                            # No shield, ship destroyed
                            # Log player hit by asteroid (ship destroyed)
                            game_logger.log_player_hit_asteroid(0, self.lives)
                            
                            # Trigger red flash before death
                            self.ship.red_flash_timer = self.ship.red_flash_duration  # Trigger red flash
                            # Add rainbow explosion for dramatic death effect
                            self.explosions.add_ship_explosion(self.ship.position.x, self.ship.position.y, 150)
                            self.ship.active = False
                            asteroid.active = False
                            self.lives -= 1
                            
                            # Reset multiplier system on death
                            self.asteroids_destroyed_this_level = 0
                            self.ufos_killed_this_level = 0
                            self.last_multiplier = 1.0
                            
                            # Reset asteroid interval bonus on death
                            self.ship.asteroid_interval_bonus = 0.0
                            self.multiplier_pulse_timer = 0.0
                            
                            # Reset decay system on death
                            self.multiplier_decay_timer = 0.0
                            self.is_decaying = False
                            self.multiplier_decay_start_value = 1.0
                            
                            if self.lives <= 0:
                                # Log player death
                                game_logger.log_player_death(self.lives, self.level, self.score)
                                # Start death delay period - let game world play for 2 seconds
                                self.game_state = "death_delay"
                                self.death_delay_timer = 0  # Start death delay timer
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
                if self.check_wrapped_collision(ufo.get_hitbox_center(), asteroid.get_hitbox_center(), ufo.radius, asteroid.radius):
                    # UFO hits asteroid - break the asteroid
                    asteroid.active = False
                    
                    # Check for spinout chance (5% for UFO vs Asteroid collision)
                    if not ufo.spinout_active and random.random() < 0.05:  # 5% chance
                        # Trigger spinout effect
                        ufo.trigger_spinout()
                        
                        # Add dedicated spinout sparks for shot hit (UFO is still alive during spinout)
                        # Generate 4 sparks for shot hit - mix of firey and electric
                        for _ in range(4):
                            if random.random() < 0.66:
                                # Firey sparks
                                colors = [(255, 100, 0), (255, 150, 0), (255, 200, 0), (255, 50, 0)]
                                color = random.choice(colors)
                                spark_type = "firey"
                            else:
                                # Electric sparks
                                colors = [(0, 150, 255), (100, 200, 255), (255, 255, 255), (0, 100, 255)]
                                color = random.choice(colors)
                                spark_type = "electric"
                            
                            self.explosions.add_explosion(
                                ufo.position.x,
                                ufo.position.y,
                                color,
                                spark_type
                            )
                        
                        # Add screen shake for UFO hit
                        self.trigger_screen_shake(6, 0.3)
                    
                    # Check if UFO is in spinout mode
                    if ufo.spinout_active:
                        # UFO in spinout mode - damage asteroid instantly
                        asteroid.active = False
                        
                        # Use dedicated spinout sparks instead of default particles
                        # Generate 15 spinout sparks for asteroid destruction
                        for _ in range(15):
                            if random.random() < 0.7:  # 70% electric blue sparks
                                color = (0, 150, 255)  # Electric blue
                                spark_type = "electric"
                            else:  # 30% bright white sparks
                                color = (255, 255, 255)  # Bright white
                                spark_type = "firey"
                            
                            self.explosions.add_explosion(
                                asteroid.position.x,
                                asteroid.position.y,
                                color,
                                spark_type
                            )
                        
                        self.add_score(asteroid.size * 11, "ufo spinout collision")
                        self.trigger_screen_shake(4, 0.2)
                        
                        # Check if delay has passed for UFO explosion
                        try:
                            if hasattr(ufo, 'spinout_collision_delay_timer') and hasattr(ufo, 'spinout_collision_delay'):
                                if ufo.spinout_collision_delay_timer >= ufo.spinout_collision_delay:
                                    # UFO in spinout mode and delay has passed - UFO explodes
                                    ufo.active = False
                                    
                                    # Add dedicated spinout explosion particles for UFO
                                    # Generate 90 electric blue sparks
                                    for _ in range(90):
                                        self.explosions.add_explosion(
                                            ufo.position.x,
                                            ufo.position.y,
                                            (0, 150, 255),  # Electric blue
                                            "electric"
                                        )
                                    
                                    # Generate 10 bright white sparks
                                    for _ in range(10):
                                        self.explosions.add_explosion(
                                            ufo.position.x,
                                            ufo.position.y,
                                            (255, 255, 255),  # Bright white
                                            "electric"
                                        )
                                    
                                    # Add score for UFO destruction after spinout
                                    self.add_score(200, "ufo spun out")
                        except Exception as e:
                            # Just destroy the UFO if there's an error
                            ufo.active = False
                            # Add dedicated spinout explosion particles for UFO
                            for _ in range(90):
                                self.explosions.add_explosion(
                                    ufo.position.x,
                                    ufo.position.y,
                                    (0, 150, 255),  # Electric blue
                                    "electric"
                                )
                            self.add_score(200, "ufo collision")
                        # If delay hasn't passed, UFO continues spinning but asteroid is still destroyed
                    
                    # Add screen shake for asteroid sizes 5+ only
                    intensity, duration = get_asteroid_shake_params(asteroid.size)
                    if intensity > 0:
                        self.trigger_screen_shake(intensity, duration)
                    
                    # Add explosion particles
                    total_particles = int((20 + ((2 * asteroid.size) * 20)) * 0.5)  # 50% fewer particles
                    
                    # 30% Gray particles (75, 75, 75) with ±50 value variations (75-125 range)
                    self.explosions.add_explosion(asteroid.position.x, asteroid.position.y, 
                                                num_particles=int(total_particles * 0.30), 
                                                color=(75, 75, 75), asteroid_size=asteroid.size)  # Gray
                    # 5% Dark brown particles (34, 9, 1) with ±2 color variations
                    self.explosions.add_explosion(asteroid.position.x, asteroid.position.y, 
                                                num_particles=int(total_particles * 0.05), 
                                                color=(34, 9, 1), asteroid_size=asteroid.size)  # Dark brown
                    # 5% Red-brown particles (98, 23, 8) with ±4 color variations
                    self.explosions.add_explosion(asteroid.position.x, asteroid.position.y, 
                                                num_particles=int(total_particles * 0.05), 
                                                color=(98, 23, 8), asteroid_size=asteroid.size)  # Red-brown
                    # 20% Red particles (255, 50, 50) - Bright red
                    self.explosions.add_explosion(asteroid.position.x, asteroid.position.y, 
                                                num_particles=int(total_particles * 0.20), 
                                                color=(255, 50, 50), asteroid_size=asteroid.size)  # Red
                    # 5% Orange-red particles (148, 27, 12) with ±5 color variations
                    self.explosions.add_explosion(asteroid.position.x, asteroid.position.y, 
                                                num_particles=int(total_particles * 0.05), 
                                                color=(148, 27, 12), asteroid_size=asteroid.size)  # Orange-red
                    # 5% Orange particles (188, 57, 8) with ±10 color variations
                    self.explosions.add_explosion(asteroid.position.x, asteroid.position.y, 
                                                num_particles=int(total_particles * 0.05), 
                                                color=(188, 57, 8), asteroid_size=asteroid.size)  # Orange
                    # 15% Orange particles (255, 150, 0) - Orange-red
                    self.explosions.add_explosion(asteroid.position.x, asteroid.position.y, 
                                                num_particles=int(total_particles * 0.15), 
                                                color=(255, 150, 0), asteroid_size=asteroid.size)  # Orange
                    # 5% Golden particles (246, 170, 28) with ±15 color variations
                    self.explosions.add_explosion(asteroid.position.x, asteroid.position.y, 
                                                num_particles=int(total_particles * 0.05), 
                                                color=(246, 170, 28), asteroid_size=asteroid.size)  # Golden
                    # 10% Yellow particles (255, 255, 100) - Bright yellow
                    self.explosions.add_explosion(asteroid.position.x, asteroid.position.y, 
                                                num_particles=int(total_particles * 0.10), 
                                                color=(255, 255, 100), asteroid_size=asteroid.size)  # Yellow
                    
                    # No points for UFO-asteroid collision
                    
                    # Split asteroid with UFO velocity
                    new_asteroids = asteroid.split(ufo.velocity, self.level)
                    self._add_asteroids_with_limit(new_asteroids)
                    break
        
        # UFO vs UFO (with screen wrapping) - 5% chance to spinout on collision
        for i, ufo1 in enumerate(self.ufos[:]):
            if not ufo1.active:
                continue
            for j, ufo2 in enumerate(self.ufos[i+1:], i+1):  # Avoid checking same pair twice
                if not ufo2.active:
                    continue
                if self.check_wrapped_collision(ufo1.position, ufo2.position, ufo1.radius, ufo2.radius):
                    # UFO collision - 75% chance for either to spinout
                    if not ufo1.spinout_active and not ufo2.spinout_active and random.random() < 0.75:  # 75% chance
                        # Randomly choose which UFO spins out
                        if random.random() < 0.5:
                            ufo1.trigger_spinout()
                        else:
                            ufo2.trigger_spinout()
                    
                    # Handle collision damage based on spinout state
                    if ufo1.spinout_active:
                        # UFO1 in spinout - damage UFO2 instantly
                        ufo2.active = False
                        # Add dedicated spinout explosion particles for UFO2
                        for _ in range(45):
                            self.explosions.add_explosion(
                                ufo2.position.x,
                                ufo2.position.y,
                                (0, 150, 255),  # Electric blue
                                "electric"
                            )
                        for _ in range(5):
                            self.explosions.add_explosion(
                                ufo2.position.x,
                                ufo2.position.y,
                                (255, 255, 255),  # Bright white
                                "electric"
                            )
                        self.add_score(200, "ufo collision")
                        
                        # Check if delay has passed for UFO1 explosion
                        try:
                            if hasattr(ufo1, 'spinout_collision_delay_timer') and hasattr(ufo1, 'spinout_collision_delay'):
                                if ufo1.spinout_collision_delay_timer >= ufo1.spinout_collision_delay:
                                    ufo1.active = False
                                    # Add dedicated spinout explosion particles for UFO1
                                    for _ in range(45):
                                        self.explosions.add_explosion(
                                            ufo1.position.x,
                                            ufo1.position.y,
                                            (0, 150, 255),  # Electric blue
                                            "electric"
                                        )
                                    for _ in range(5):
                                        self.explosions.add_explosion(
                                            ufo1.position.x,
                                            ufo1.position.y,
                                            (255, 255, 255),  # Bright white
                                            "electric"
                                        )
                                    self.add_score(200, "ufo spun out")
                        except Exception as e:
                            ufo1.active = False
                            # Add dedicated spinout explosion particles for UFO1
                            for _ in range(45):
                                self.explosions.add_explosion(
                                    ufo1.position.x,
                                    ufo1.position.y,
                                    (0, 150, 255),  # Electric blue
                                    "electric"
                                )
                            self.add_score(200, "ufo collision")
                    elif ufo2.spinout_active:
                        # UFO2 in spinout - damage UFO1 instantly
                        ufo1.active = False
                        # Add dedicated spinout explosion particles for UFO1
                        for _ in range(45):
                            self.explosions.add_explosion(
                                ufo1.position.x,
                                ufo1.position.y,
                                (0, 150, 255),  # Electric blue
                                "electric"
                            )
                        for _ in range(5):
                            self.explosions.add_explosion(
                                ufo1.position.x,
                                ufo1.position.y,
                                (255, 255, 255),  # Bright white
                                "electric"
                            )
                        self.add_score(200, "ufo collision")
                        
                        # Check if delay has passed for UFO2 explosion
                        try:
                            if hasattr(ufo2, 'spinout_collision_delay_timer') and hasattr(ufo2, 'spinout_collision_delay'):
                                if ufo2.spinout_collision_delay_timer >= ufo2.spinout_collision_delay:
                                    ufo2.active = False
                                    # Add dedicated spinout explosion particles for UFO2
                                    for _ in range(45):
                                        self.explosions.add_explosion(
                                            ufo2.position.x,
                                            ufo2.position.y,
                                            (0, 150, 255),  # Electric blue
                                            "electric"
                                        )
                                    for _ in range(5):
                                        self.explosions.add_explosion(
                                            ufo2.position.x,
                                            ufo2.position.y,
                                            (255, 255, 255),  # Bright white
                                            "electric"
                                        )
                                    self.add_score(200, "ufo spun out")
                        except Exception as e:
                            ufo2.active = False
                            # Add dedicated spinout explosion particles for UFO2
                            for _ in range(45):
                                self.explosions.add_explosion(
                                    ufo2.position.x,
                                    ufo2.position.y,
                                    (0, 150, 255),  # Electric blue
                                    "electric"
                                )
                            self.add_score(200, "ufo collision")
                    else:
                        # Neither in spinout - normal collision damage
                        ufo1.active = False
                        ufo2.active = False
                        # Add dedicated spinout explosion particles for UFO1
                        for _ in range(45):
                            self.explosions.add_explosion(
                                ufo1.position.x,
                                ufo1.position.y,
                                (0, 150, 255),  # Electric blue
                                "electric"
                            )
                        for _ in range(5):
                            self.explosions.add_explosion(
                                ufo1.position.x,
                                ufo1.position.y,
                                (255, 255, 255),  # Bright white
                                "electric"
                            )
                        self.add_score(200, "ufo collision")
                        # Add dedicated spinout explosion particles for UFO2
                        for _ in range(45):
                            self.explosions.add_explosion(
                                ufo2.position.x,
                                ufo2.position.y,
                                (0, 150, 255),  # Electric blue
                                "electric"
                            )
                        for _ in range(5):
                            self.explosions.add_explosion(
                                ufo2.position.x,
                                ufo2.position.y,
                                (255, 255, 255),  # Bright white
                                "electric"
                            )
                        self.add_score(200, "ufo collision")
                    break
        
        # Ship vs UFO (with screen wrapping)
        if self.ship.active and not self.ship.invulnerable and not self.god_mode:
            for ufo in self.ufos:
                if not ufo.active:
                    continue
                if self.check_wrapped_collision(self.ship.position, ufo.get_hitbox_center(), self.ship.radius, ufo.radius):
                    # Collision!
                    
                    # Check if UFO is in spinout mode
                    if ufo.spinout_active:
                        # UFO in spinout mode - damage player instantly
                        if self.ship.shield_hits > 0:
                            # Shield absorbs hit
                            self.ship.shield_hits -= 1
                            # Log player hit by UFO (spinout mode, shield absorbed)
                            game_logger.log_player_hit_ufo(self.ship.shield_hits, self.lives)
                            
                            # Don't reset recharge timer - let charging continue
                            self.ship.shield_damage_timer = self.ship.shield_damage_duration  # Show shield visual
                            self.ship.red_flash_timer = self.ship.red_flash_duration  # Trigger red flash
                            
                            # Add camera shake based on remaining shields (subject to time dilation)
                            if self.ship.shield_hits == 2:  # Lost first shield (3/3 -> 2/3)
                                self.trigger_screen_shake(1, 0.2, self.time_dilation_factor)  # Light shake
                            elif self.ship.shield_hits == 1:  # Lost second shield (2/3 -> 1/3)
                                self.trigger_screen_shake(3, 0.4, self.time_dilation_factor)  # Medium shake
                            elif self.ship.shield_hits == 0:  # Lost last shield (1/3 -> 0/3)
                                self.trigger_screen_shake(5, 0.6, self.time_dilation_factor)  # Strong shake
                        else:
                            # No shields - ship destroyed
                            # Log player hit by UFO (spinout mode, ship destroyed)
                            game_logger.log_player_hit_ufo(0, self.lives)
                            
                            self.ship.active = False
                            self.trigger_screen_shake(8, 1.0, self.time_dilation_factor)  # Strong shake
                            
                            # Add explosion particles
                            self.explosions.add_explosion(self.ship.position.x, self.ship.position.y, 
                                                        num_particles=120, 
                                                        color=(255, 100, 0), is_ufo=False)
                            self.explosions.add_explosion(self.ship.position.x, self.ship.position.y, 
                                                        num_particles=20, 
                                                        color=(255, 255, 255), is_ufo=False)
                            
                            # Set game over state
                            self.game_state = "game_over"
                            self.game_over_timer = 0.0
                            
                            # Log game over
                            game_logger.log_game_over(self.score, self.level)
                        
                        # Check if delay has passed for UFO explosion
                        try:
                            if hasattr(ufo, 'spinout_collision_delay_timer') and hasattr(ufo, 'spinout_collision_delay'):
                                if ufo.spinout_collision_delay_timer >= ufo.spinout_collision_delay:
                                    # UFO in spinout mode and delay has passed - UFO explodes
                                    ufo.active = False
                                    
                                    # Add dedicated spinout explosion particles
                                    for _ in range(45):  # 50% more particles (30 * 1.5 = 45)
                                        self.explosions.add_explosion(
                                            ufo.position.x,
                                            ufo.position.y,
                                            (0, 150, 255),  # Blue explosion
                                            "electric"
                                        )
                                    
                                    # Add score for UFO destruction after spinout
                                    self.add_score(250, "ufo spun out")  # 250 points for destroying UFO after spinout
                        except Exception as e:
                            ufo.active = False
                            # Add dedicated spinout explosion particles
                            for _ in range(45):
                                self.explosions.add_explosion(
                                    ufo.position.x,
                                    ufo.position.y,
                                    (0, 150, 255),  # Blue explosion
                                    "electric"
                                )
                            self.add_score(250, "ufo collision")  # 250 points for destroying UFO by collision
                        # If delay hasn't passed, UFO continues spinning but collision still occurs
                    else:
                        # Normal collision (UFO not in spinout)
                        if self.ship.shield_hits > 0:
                            # Shield absorbs hit
                            self.ship.shield_hits -= 1
                            # Log player hit by UFO (normal collision, shield absorbed)
                            game_logger.log_player_hit_ufo(self.ship.shield_hits, self.lives)
                            
                            # Don't reset recharge timer - let charging continue
                            self.ship.shield_damage_timer = self.ship.shield_damage_duration  # Show shield visual
                            self.ship.red_flash_timer = self.ship.red_flash_duration  # Trigger red flash
                            
                            # Add camera shake based on remaining shields (subject to time dilation)
                            if self.ship.shield_hits == 2:  # Lost first shield (3/3 -> 2/3)
                                self.trigger_screen_shake(1, 0.2, self.time_dilation_factor)  # Light shake
                            elif self.ship.shield_hits == 1:  # Lost second shield (2/3 -> 1/3)
                                self.trigger_screen_shake(3, 0.4, self.time_dilation_factor)  # Medium shake
                            elif self.ship.shield_hits == 0:  # Lost last shield (1/3 -> 0/3)
                                self.trigger_screen_shake(5, 0.6, self.time_dilation_factor)  # Strong shake
                            
                            ufo.active = False  # Destroy UFO
                            
                            # Add dedicated spinout explosion particles
                            for _ in range(45):  # 50% more particles (30 * 1.5 = 45)
                                self.explosions.add_explosion(
                                    ufo.position.x,
                                    ufo.position.y,
                                    (0, 150, 255),  # Blue explosion
                                    "electric"
                                )
                            
                            # Add score for destroying UFO with shield collision
                            self.ufos_killed_this_level += 1  # Track UFO killed by player
                            self.add_score(250, "ufo collision")  # 250 points for destroying UFO by collision
                        else:
                            # No shield, ship destroyed
                            # Log player hit by UFO (normal collision, ship destroyed)
                            game_logger.log_player_hit_ufo(0, self.lives)
                            
                            # Trigger red flash before death
                            self.ship.red_flash_timer = self.ship.red_flash_duration  # Trigger red flash
                            # Add rainbow explosion for dramatic death effect
                            self.explosions.add_ship_explosion(self.ship.position.x, self.ship.position.y, 150)
                            self.ship.active = False
                            ufo.active = False
                            self.lives -= 1
                            
                            # Reset asteroid interval bonus on death
                            self.ship.asteroid_interval_bonus = 0.0
                            if self.lives <= 0:
                                # Start death delay period - let game world play for 2 seconds
                                self.game_state = "death_delay"
                                self.death_delay_timer = 0  # Start death delay timer
                            else:
                                # Still alive - trigger screen shake
                                self.trigger_screen_shake(7, 0.6)  # Level 7 shake for player death
                                self.init_ship()
                    break
        
        # Ship vs UFO bullets
        if self.ship.active and not self.ship.invulnerable and not self.god_mode:
            for bullet in self.ufo_bullets[:]:
                if not bullet.active:
                    continue
                if self.check_wrapped_collision(self.ship.position, bullet.position, self.ship.radius, bullet.radius):
                    # Hit!
                    bullet.active = False
                    
                    # Add small particle effect for UFO shot hit
                    self.explosions.add_ufo_shot_hit(bullet.position.x, bullet.position.y)
                    
                    if self.ship.shield_hits > 0:
                        # Shield absorbs hit
                        self.ship.shield_hits -= 1
                        # Log player hit by UFO shot (shield absorbed)
                        game_logger.log_player_hit_ufo_shot(self.ship.shield_hits, self.lives)
                        
                        # Don't reset recharge timer - let charging continue
                        self.ship.shield_damage_timer = self.ship.shield_damage_duration  # Show shield visual
                        self.ship.red_flash_timer = self.ship.red_flash_duration  # Trigger red flash
                        
                        # Add camera shake based on remaining shields (subject to time dilation)
                        intensity, duration, time_dilation = get_shield_damage_shake_params(self.ship.shield_hits, self.time_dilation_factor)
                        if intensity > 0:
                            self.trigger_screen_shake(intensity, duration, time_dilation)
                        
                        # Add shield hit particles
                        self.explosions.add_explosion(self.ship.position.x, self.ship.position.y, 
                                                    num_particles=25, 
                                                    color=(0, 150, 255))  # Blue shield hit explosion
                    else:
                        # No shield, ship destroyed
                        # Log player hit by UFO shot (ship destroyed)
                        game_logger.log_player_hit_ufo_shot(0, self.lives)
                        
                        # Trigger red flash before death
                        self.ship.red_flash_timer = self.ship.red_flash_duration  # Trigger red flash
                        # Add rainbow explosion for dramatic death effect
                        self.explosions.add_ship_explosion(self.ship.position.x, self.ship.position.y, 150)
                        self.ship.active = False
                        self.lives -= 1
                        
                        # Reset multiplier system on death
                        self.asteroids_destroyed_this_level = 0
                        self.ufos_killed_this_level = 0
                        self.last_multiplier = 1.0
                        self.multiplier_pulse_timer = 0.0
                        
                        # Reset decay system on death
                        self.multiplier_decay_timer = 0.0
                        self.is_decaying = False
                        self.multiplier_decay_start_value = 1.0
                        
                        # Reset asteroid interval bonus on death
                        self.ship.asteroid_interval_bonus = 0.0
                        
                        if self.lives <= 0:
                            # Start death delay period - let game world play for 2 seconds
                            self.game_state = "death_delay"
                            self.death_delay_timer = 0  # Start death delay timer
                        else:
                            # Still alive - trigger screen shake
                            self.trigger_screen_shake(7, 0.6)  # Level 7 shake for player death
                            self.init_ship()
                    break
        
        # UFO bullets vs Asteroids (100% blockable, 33% chance to break)
        for bullet in self.ufo_bullets[:]:
            if not bullet.active:
                continue
            for asteroid in self.asteroids[:]:
                if not asteroid.active:
                    continue
                if self.check_wrapped_collision(bullet.position, asteroid.get_hitbox_center(), bullet.radius, asteroid.radius):
                    # UFO bullet hits asteroid - always blocked
                    bullet.active = False
                    
                    # Add small particle effect for UFO shot hit
                    self.explosions.add_ufo_shot_hit(bullet.position.x, bullet.position.y)
                    
                    # 33% chance to break the asteroid
                    if random.random() < 0.33:  # 33% chance
                        asteroid.active = False
                        
                    # Add screen shake for asteroid sizes 5+ only
                    intensity, duration = get_asteroid_shake_params(asteroid.size)
                    if intensity > 0:
                        self.trigger_screen_shake(intensity, duration)
                        
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
                        
                        # Add score (size 4 = 44 points, size 3 = 33, etc.)
                        self.add_score(asteroid.size * 11, "asteroid collision")
                        
                        # Split asteroid with UFO bullet velocity
                        new_asteroids = asteroid.split(bullet.velocity, self.level)
                        self._add_asteroids_with_limit(new_asteroids)
                    break
        
        # Boss weapon bullets vs Asteroids (same behavior as regular bullets)
        for boss in self.bosses[:]:
            for bullet in boss.weapon_bullets[:]:
                if not bullet.active:
                    continue
                for asteroid in self.asteroids[:]:
                    if not asteroid.active:
                        continue
                    if self.check_wrapped_collision(bullet.position, asteroid.get_hitbox_center(), bullet.radius, asteroid.radius):
                        # Hit!
                        bullet.active = False
                        asteroid.active = False
                        
                        # Add boss shot hit particles (2x scaled)
                        self.explosions.add_boss_shot_hit_particles(asteroid.position.x, asteroid.position.y)
                        
                        # Add screen shake for asteroid sizes 5+ only
                        intensity, duration = get_asteroid_shake_params(asteroid.size)
                        if intensity > 0:
                            self.trigger_screen_shake(intensity, duration)
                        
                        # Add explosion particles (new scaling formula)
                        total_particles = int((20 + ((2 * asteroid.size) * 20)) * 0.5)  # 50% fewer particles
                        
                        # 40% gray particles (75-125 range)
                        self.explosions.add_explosion(asteroid.position.x, asteroid.position.y, 
                                                    num_particles=int(total_particles * 0.40), 
                                                    color=(75, 75, 75), asteroid_size=asteroid.size)  # Gray
                        # 20% dark brown particles
                        self.explosions.add_explosion(asteroid.position.x, asteroid.position.y, 
                                                    num_particles=int(total_particles * 0.20), 
                                                    color=(34, 9, 1), asteroid_size=asteroid.size)  # Dark brown
                        # 15% red-brown particles
                        self.explosions.add_explosion(asteroid.position.x, asteroid.position.y, 
                                                    num_particles=int(total_particles * 0.15), 
                                                    color=(98, 23, 8), asteroid_size=asteroid.size)  # Red-brown
                        # 10% orange-red particles
                        self.explosions.add_explosion(asteroid.position.x, asteroid.position.y, 
                                                    num_particles=int(total_particles * 0.10), 
                                                    color=(148, 27, 12), asteroid_size=asteroid.size)  # Orange-red
                        # 8% orange particles
                        self.explosions.add_explosion(asteroid.position.x, asteroid.position.y, 
                                                    num_particles=int(total_particles * 0.08), 
                                                    color=(188, 57, 8), asteroid_size=asteroid.size)  # Orange
                        # 7% golden particles
                        self.explosions.add_explosion(asteroid.position.x, asteroid.position.y, 
                                                    num_particles=int(total_particles * 0.07), 
                                                    color=(246, 170, 28), asteroid_size=asteroid.size)  # Golden
                        
                        # No score for boss destroying asteroids
                        # Boss-destroyed asteroids don't count toward player tracking
                        
                        # Split asteroid with projectile velocity
                        new_asteroids = asteroid.split(bullet.velocity, self.level)
                        self._add_asteroids_with_limit(new_asteroids)
                        break
        
        # Boss weapon bullets vs Player (with screen wrapping) - Player is hit like normal
        for boss in self.bosses[:]:
            for bullet in boss.weapon_bullets[:]:
                if not bullet.active:
                    continue
                if self.ship.active and not self.ship.invulnerable and not self.god_mode:
                    if self.check_wrapped_collision(bullet.position, self.ship.position, bullet.radius, self.ship.radius):
                        # Boss weapon bullet hits player - player is hit like normal
                        bullet.active = False
                        
                        # Add boss shot hit particles (2x scaled)
                        self.explosions.add_boss_shot_hit_particles(self.ship.position.x, self.ship.position.y)
                        
                        if self.ship.shield_hits > 0:
                            # Shield absorbs hit
                            self.ship.shield_hits -= 1
                            # Log player hit by boss shot (shield absorbed)
                            game_logger.log_player_hit_boss_shot(self.ship.shield_hits, self.lives)
                            
                            # Don't reset recharge timer - let charging continue
                            self.ship.shield_damage_timer = self.ship.shield_damage_duration  # Show shield visual
                            self.ship.red_flash_timer = self.ship.red_flash_duration  # Trigger red flash
                            
                            # Add camera shake based on remaining shields (subject to time dilation)
                            if self.ship.shield_hits == 2:  # Lost first shield (3/3 -> 2/3)
                                self.trigger_screen_shake(1, 0.2, self.time_dilation_factor)  # Light shake
                            elif self.ship.shield_hits == 1:  # Lost second shield (2/3 -> 1/3)
                                self.trigger_screen_shake(3, 0.4, self.time_dilation_factor)  # Medium shake
                            elif self.ship.shield_hits == 0:  # Lost last shield (1/3 -> 0/3)
                                self.trigger_screen_shake(5, 0.6, self.time_dilation_factor)  # Strong shake
                        else:
                            # No shields - ship destroyed
                            # Log player hit by boss shot (ship destroyed)
                            game_logger.log_player_hit_boss_shot(0, self.lives)
                            
                            # Trigger red flash before death
                            self.ship.red_flash_timer = self.ship.red_flash_duration  # Trigger red flash
                            # Add rainbow explosion for dramatic death effect
                            self.explosions.add_ship_explosion(self.ship.position.x, self.ship.position.y, 150)
                            self.ship.active = False
                            self.lives -= 1
                            
                            # Reset multiplier system on death
                            self.asteroids_destroyed_this_level = 0
                            self.ufos_killed_this_level = 0
                            self.last_multiplier = 1.0
                            self.multiplier_pulse_timer = 0.0
                            
                            # Reset decay system on death
                            self.multiplier_decay_timer = 0.0
                            self.is_decaying = False
                            self.multiplier_decay_start_value = 1.0
                            
                            # Reset asteroid interval bonus on death
                            self.ship.asteroid_interval_bonus = 0.0
                            
                            # Reset ship state
                            self.ship.velocity = Vector2D(0, 0)  # Stop ship movement
                            self.ship.angular_velocity = 0  # Stop ship rotation
                            self.ship.angle = 0  # Reset ship angle
                            
                            # Add camera shake for death (subject to time dilation)
                            self.trigger_screen_shake(8, 0.8, self.time_dilation_factor)  # Death shake
                            
                            if self.lives <= 0:
                                # Start death delay period - let game world play for 2 seconds
                                self.game_state = "death_delay"
                                self.death_delay_timer = 0  # Start death delay timer
                            else:
                                # Still alive - trigger screen shake
                                self.trigger_screen_shake(7, 0.6)  # Level 7 shake for player death
                                self.init_ship()
                        
                        break
        
        # Boss weapon bullets vs UFOs (with screen wrapping) - Collision but no damage
        for boss in self.bosses[:]:
            for bullet in boss.weapon_bullets[:]:
                if not bullet.active:
                    continue
                for ufo in self.ufos[:]:
                    if not ufo.active:
                        continue
                    if self.check_wrapped_collision(bullet.position, ufo.get_hitbox_center(), bullet.radius, ufo.radius):
                        # Boss weapon bullet hits UFO - bullet destroyed but UFO takes no damage
                        bullet.active = False
                        
                        # Add boss shot hit particles (2x scaled)
                        self.explosions.add_boss_shot_hit_particles(ufo.position.x, ufo.position.y)
                        break
        
        # Boss vs Asteroids (with screen wrapping) - Boss hits asteroids like normal
        for boss in self.bosses[:]:
            if not boss.active:
                continue
            for asteroid in self.asteroids[:]:
                if not asteroid.active:
                    continue
                if boss.polygon_circle_collision_with_wrapping(asteroid.get_hitbox_center().x, asteroid.get_hitbox_center().y, asteroid.radius, self.current_width, self.current_height):
                    # Boss collision behavior based on asteroid size
                    if asteroid.size >= 3:  # Sizes 3-9: Split the asteroid
                        # Mark asteroid for destruction
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
                        # Size 4: No screen shake
                        
                        # Add explosion particles (with randomized lifetimes)
                        total_particles = int((20 + ((2 * asteroid.size) * 20)) * 0.5)  # 50% fewer particles
                        
                        # 40% Gray particles (75-125 range)
                        self.explosions.add_explosion(asteroid.position.x, asteroid.position.y, 
                                                    num_particles=int(total_particles * 0.40), 
                                                    color=(75, 75, 75), asteroid_size=asteroid.size)  # Gray
                        # 20% dark brown particles
                        self.explosions.add_explosion(asteroid.position.x, asteroid.position.y, 
                                                    num_particles=int(total_particles * 0.20), 
                                                    color=(34, 9, 1), asteroid_size=asteroid.size)  # Dark brown
                        # 15% red-brown particles
                        self.explosions.add_explosion(asteroid.position.x, asteroid.position.y, 
                                                    num_particles=int(total_particles * 0.15), 
                                                    color=(98, 23, 8), asteroid_size=asteroid.size)  # Red-brown
                        # 10% orange-red particles
                        self.explosions.add_explosion(asteroid.position.x, asteroid.position.y, 
                                                    num_particles=int(total_particles * 0.10), 
                                                    color=(148, 27, 12), asteroid_size=asteroid.size)  # Orange-red
                        # 8% orange particles
                        self.explosions.add_explosion(asteroid.position.x, asteroid.position.y, 
                                                    num_particles=int(total_particles * 0.08), 
                                                    color=(188, 57, 8), asteroid_size=asteroid.size)  # Orange
                        # 7% golden particles
                        self.explosions.add_explosion(asteroid.position.x, asteroid.position.y, 
                                                    num_particles=int(total_particles * 0.07), 
                                                    color=(246, 170, 28), asteroid_size=asteroid.size)  # Golden
                        
                        # Add score (size 4 = 44 points, size 5 = 55, etc.)
                        self.add_score(asteroid.size * 11, "asteroid collision")
                        
                        # Split asteroid with 2x boss velocity
                        boss_velocity_2x = Vector2D(boss.velocity.x * 2, boss.velocity.y * 2)
                        new_asteroids = asteroid.split(boss_velocity_2x, self.level)
                        self._add_asteroids_with_limit(new_asteroids)
                        
                        # Check if new asteroids are still colliding with boss and handle accordingly
                        self.check_new_asteroid_boss_collisions(new_asteroids, boss)
                    
                    # Sizes 1-2: Pass through boss unharmed (do nothing)
                    break
        
        # Boss vs Player (with screen wrapping) - Player is hit like normal
        for boss in self.bosses[:]:
            if not boss.active:
                continue
            if self.ship.active and not self.ship.invulnerable and not self.god_mode:
                if boss.point_in_polygon(self.ship.position.x, self.ship.position.y):
                    # Boss hits player - player is hit like normal
                    if self.ship.shield_hits > 0:
                        # Shield absorbs hit
                        self.ship.shield_hits -= 1
                        # Don't reset recharge timer - let charging continue
                        self.ship.shield_damage_timer = self.ship.shield_damage_duration  # Show shield visual
                        self.ship.red_flash_timer = self.ship.red_flash_duration  # Trigger red flash
                        
                        # Add camera shake based on remaining shields (subject to time dilation)
                        intensity, duration, time_dilation = get_shield_damage_shake_params(self.ship.shield_hits, self.time_dilation_factor)
                        if intensity > 0:
                            self.trigger_screen_shake(intensity, duration, time_dilation)
                        
                        # Add explosion particles (with randomized lifetimes)
                        self.explosions.add_explosion(self.ship.position.x, self.ship.position.y, 
                                                    num_particles=20, 
                                                    color=(0, 100, 255))  # Blue explosion
                    else:
                        # No shield, ship destroyed
                        # Trigger red flash before death
                        self.ship.red_flash_timer = self.ship.red_flash_duration  # Trigger red flash
                        # Add rainbow explosion for dramatic death effect
                        self.explosions.add_ship_explosion(self.ship.position.x, self.ship.position.y, 150)
                        self.ship.active = False
                        self.lives -= 1
                        
                        # Reset multiplier system on death
                        self.asteroids_destroyed_this_level = 0
                        self.ufos_killed_this_level = 0
                        self.last_multiplier = 1.0
                        self.multiplier_pulse_timer = 0.0
                        
                        # Reset decay system on death
                        self.multiplier_decay_timer = 0.0
                        self.is_decaying = False
                        self.multiplier_decay_start_value = 1.0
                        
                        # Reset asteroid interval bonus on death
                        self.ship.asteroid_interval_bonus = 0.0
                        
                        if self.lives <= 0:
                            # Start death delay period - let game world play for 2 seconds
                            self.game_state = "death_delay"
                            self.death_delay_timer = 0  # Start death delay timer
                        else:
                            # Still alive - trigger screen shake
                            self.trigger_screen_shake(7, 0.6)  # Level 7 shake for player death
                            self.init_ship()
                    break
        
        # Boss vs Player Shots (with screen wrapping) - Shot collides with boss
        for boss in self.bosses[:]:
            if not boss.active:
                continue
            for bullet in self.bullets[:]:
                if not bullet.active:
                    continue
                # Check polygon hitbox collision
                if boss.point_in_polygon(bullet.position.x, bullet.position.y):
                    # Player shot hits boss - shot is destroyed
                    bullet.active = False
                    
                    # Add shot hit particles
                    self.explosions.add_shot_hit_particles(bullet.position.x, bullet.position.y)
                    break
        
        # Boss vs UFO Shots (with screen wrapping) - Shot collides with boss
        for boss in self.bosses[:]:
            if not boss.active:
                continue
            for bullet in self.ufo_bullets[:]:
                if not bullet.active:
                    continue
                # Check polygon hitbox collision
                if boss.point_in_polygon(bullet.position.x, bullet.position.y):
                    # UFO shot hits boss - shot is destroyed
                    bullet.active = False
                    
                    # Add small particle effect for UFO shot hit
                    self.explosions.add_ufo_shot_hit(bullet.position.x, bullet.position.y)
                    break
    
    def update(self, dt):
        # Update key cooldown timers (independent of game time effects)
        if self.f1_cooldown_timer > 0:
            self.f1_cooldown_timer -= dt
        if self.g_cooldown_timer > 0:
            self.g_cooldown_timer -= dt
        if self.key1_cooldown_timer > 0:
            self.key1_cooldown_timer -= dt
        if self.key2_cooldown_timer > 0:
            self.key2_cooldown_timer -= dt
        if self.key3_cooldown_timer > 0:
            self.key3_cooldown_timer -= dt
        if self.key4_cooldown_timer > 0:
            self.key4_cooldown_timer -= dt
        if self.key5_cooldown_timer > 0:
            self.key5_cooldown_timer -= dt
        
        # Play title music when in waiting state
        if self.game_state == "waiting":
            self.play_title_music()
            
            # Update title screen animations
            self.title_start_timer += dt
            self.title_boss_spawn_timer += dt
            
            # Delay "PRESS SPACE TO START" by 2 seconds, then fade in over 4 seconds, then pulse
            if self.title_start_timer < 2.0:
                self.press_space_alpha = 0  # Hidden for first 2 seconds
            elif self.title_start_timer < 6.0:  # Fade in over 4 seconds (2-6 seconds)
                fade_progress = (self.title_start_timer - 2.0) / 4.0  # 0 to 1 over 4 seconds
                self.press_space_alpha = min(255, fade_progress * 255)
            else:
                # Pulse between 25% and 100% opacity in 4-second intervals, smoothly transitioning from current fade
                pulse_time = self.title_start_timer - 6.0  # Time since fade completed
                pulse_cycle = (pulse_time % 4.0) / 4.0  # 0 to 1 over 4 seconds
                base_alpha = 64 + (191 * (0.5 + 0.5 * math.sin(pulse_cycle * 2 * math.pi)))  # 64-255 (25%-100%)
                
                # Smooth transition: start from current fade alpha (255) and blend to pulse
                if pulse_time < 1.0:  # First second of pulsing
                    transition_progress = pulse_time  # 0 to 1 over 1 second
                    self.press_space_alpha = int(255 * (1 - transition_progress) + base_alpha * transition_progress)
                else:
                    self.press_space_alpha = int(base_alpha)
            
            # Controls fade in after press space to start fades in (starts at 6 seconds, fades over 3 seconds)
            if self.title_start_timer < 6.0:
                self.controls_alpha = 0  # Hidden until press space fades in
            elif self.title_start_timer < 9.0:  # Fade in over 3 seconds (6-9 seconds)
                fade_progress = (self.title_start_timer - 6.0) / 3.0  # 0 to 1 over 3 seconds
                self.controls_alpha = min(255, fade_progress * 255)
            else:
                self.controls_alpha = 255  # Fully visible
            
            # Update virtual ship with full game movement mechanics
            self.update_title_ship(dt)
            
            # Update screen shake
            self.update_screen_shake(dt)
            
            # Update starfield with ship velocity (like in game)
            ship_velocity = self.title_ship.velocity if self.title_ship else Vector2D(0, 0)
            self.star_field.update(ship_velocity, self.current_width, self.current_height, dt)
            
            # Update sine wave timer
            self.sine_wave_timer += dt
            
            # Simulate level 10 UFO spawning (no time effects, no player ship)
            self.update_title_screen_ufos(dt)
            
            # Update title screen bosses
            for boss in self.bosses[:]:
                boss.update(dt, self.current_width, self.current_height, self.asteroids, self.ship)
                if not boss.active:
                    self.bosses.remove(boss)
            
            # Spawn title screen boss after 11.38 seconds if none exist
            if len(self.bosses) == 0 and self.title_boss_spawn_timer >= 11.38:
                direction = random.choice(["left", "right"])
                boss = BossEnemy(0, 0, direction, self.current_width, self.current_height, level=0)
                self.bosses.append(boss)  # No logging for title screen boss
            
            # Update explosion particles on title screen
            self.explosions.update(dt, self.current_width, self.current_height)
            
            
            return
        
        # Handle death delay state - let game world play for 2 seconds before showing game over
        if self.game_state == "death_delay":
            # Update death delay timer (use normal time, not dilated)
            self.death_delay_timer += dt
            
            # Continue updating the game world during death delay
            # Calculate dilated time for non-player objects
            dilated_dt = dt * self.time_dilation_factor
            
            # Update all game objects normally (copy from main game loop)
            # Update bullets (affected by time dilation)
            self.bullets = [bullet for bullet in self.bullets if bullet.active]
            for bullet in self.bullets:
                bullet.update(dilated_dt, self.current_width, self.current_height)
            
            # Update asteroids (affected by time dilation)
            for asteroid in self.asteroids[:]:
                player_speed = 0  # No ship during death delay
                asteroid.update(dilated_dt, self.current_width, self.current_height, player_speed, 1.0)
                if not asteroid.active:
                    self.asteroids.remove(asteroid)
            
            # Update UFOs (affected by time dilation)
            for ufo in self.ufos[:]:
                # Provide environmental context to UFO
                ufo.player_position = Vector2D(0, 0)  # No ship during death delay
                ufo.player_velocity = Vector2D(0, 0)  # No ship during death delay
                ufo.player_bullets = self.bullets
                ufo.other_ufos = [u for u in self.ufos if u != ufo]
                ufo.asteroids = self.asteroids
                ufo.screen_width = self.current_width
                ufo.screen_height = self.current_height
                ufo.time_dilation_factor = self.time_dilation_factor
                
                # Set bullet limit based on level
                ufo.max_bullets = 5 + ((self.level // 2) * 5)
                
                should_shoot = ufo.update(dilated_dt, Vector2D(0, 0), self.current_width, self.current_height, self.time_dilation_factor, self.explosions)
                if not ufo.active:
                    self.ufos.remove(ufo)
            
            # Update UFO bullets (affected by time dilation)
            self.ufo_bullets = [bullet for bullet in self.ufo_bullets if bullet.active]
            for bullet in self.ufo_bullets:
                bullet.update(dilated_dt, self.current_width, self.current_height)
            
            # Update explosion particles
            self.explosions.update(dilated_dt, self.current_width, self.current_height)
            
            
            # Update star field with no ship velocity since ship is destroyed
            self.star_field.update(Vector2D(0, 0), self.current_width, self.current_height, dilated_dt)
            
            # After 2 seconds, transition to game over
            if self.death_delay_timer >= 2.0:
                self.game_state = "game_over"
                self.game_over_timer = 0  # Start game over timer
                
                # Log game over
                game_logger.log_game_over(self.score, self.level)
                
                # Stop music on game over
                self.stop_music()
                # Start star explosion effect
                self.star_explosion_active = True
                self.star_field.start_explosion(self.current_width, self.current_height)
                
                # Automatically load scoreboard in background
                if self.scoreboard_available and self.scoreboard:
                    self.load_scoreboard_background()
                
                # Automatically trigger name input if score qualifies
                if self.score > 1000:  # Minimum score threshold
                    self.name_input_active = True
                    self.player_name_input = ""
                    print(f"[SCOREBOARD DEBUG] Auto-triggered name input for score: {self.score}")
            
            return
        
        # Handle game over state - need to update star explosion and timers
        if self.game_state == "game_over":
            # Update star explosion effect
            if self.star_explosion_active:
                self.star_explosion_timer += dt  # Use normal time, not dilated
                if self.star_explosion_timer >= self.star_explosion_duration:
                    # Explosion finished, start smooth fade-in transition
                    self.star_explosion_active = False
                    self.star_explosion_timer = 0.0
                    self.star_field.explosion_mode = False
                    # Start the smooth fade-in transition instead of immediate regeneration
                    self.star_field.start_fade_in(self.current_width, self.current_height)
            
            # Update star field during explosion, explosion fade, or fade-in
            # Use normal time (dt) for explosions to keep them independent of game time effects
            if self.star_explosion_active or self.star_field.fade_in_mode or self.star_field.explosion_fade_mode:
                self.star_field.update(None, self.current_width, self.current_height, dt)
            
            # Update game over timer and stop screen shake after 3 seconds
            self.game_over_timer += dt  # Use normal time, not dilated time
            if self.game_over_timer >= 3.0:  # After 3 seconds
                # Force stop all screen shake for game over
                self.screen_shake_intensity = 0
                self.screen_shake_timer = 0
                self.screen_shake_duration = 0
            
            # Fade in game over text over 2 seconds (starts after star explosion)
            if not self.star_explosion_active:
                if self.game_over_alpha < 255:
                    self.game_over_alpha = min(255, ((self.game_over_timer - 0.5) / 2.0) * 255)
                    if self.game_over_alpha < 0:
                        self.game_over_alpha = 0
            
            # Update explosion particles
            self.explosions.update(dt, self.current_width, self.current_height)
            
            return
        
        if self.game_state not in ["playing", "paused", "death_delay"]:
            return
        
        # Update game start timer to prevent shooting for first 0.5 seconds
        if self.game_state == "playing":
            self.game_start_timer += dt
        
        # Calculate time dilation based on player movement (Superhot-style)
        self.calculate_time_dilation(dt)
        
        # Update screen shake
        self.update_screen_shake(dt)
        
        # Update multiplier decay system
        self.update_multiplier_decay(dt)
        
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
            # Update ship's time dilation factor
            self.ship.time_dilation = self.time_dilation_factor
            # Get current multiplier for recharge speed bonus
            current_multiplier = self.calculate_multiplier()
            self.ship.update(dilated_dt, self.current_width, self.current_height, 1.0, dt, current_multiplier, len(self.asteroids))
            
            # Track rotations for "spinning trick" achievement
            if not self.ship.spinning_trick_shown:
                # Calculate angle difference, handling wraparound
                angle_diff = self.ship.angle - self.ship.last_angle
                # Normalize angle difference to [-π, π]
                while angle_diff > math.pi:
                    angle_diff -= 2 * math.pi
                while angle_diff < -math.pi:
                    angle_diff += 2 * math.pi
                
                # Add to total rotations (convert to full rotations) - only while spinning
                if self.ship.is_spinning:
                    rotation_add = abs(angle_diff) / (2 * math.pi)
                    self.ship.total_rotations += rotation_add
                    
                    # Update last_angle AFTER calculating the difference
                    self.ship.last_angle = self.ship.angle
                    
                    # Check if we've reached 11.38 rotations - show immediately
                    if self.ship.total_rotations >= 11.38:
                        # Show the message immediately
                        self.show_spinning_trick = True
                        self.spinning_trick_timer = 3.0  # Show for 3 seconds
                        # Clear any other messages
                        self.show_interstellar = False
                        self.show_god_mode = False
                        self.show_ludicrous_speed = False
                        self.show_plaid = False
                        self.interstellar_timer = 0.0
                        self.god_mode_timer = 0.0
                        self.ludicrous_speed_timer = 0.0
                        self.plaid_timer = 0.0
                else:
                    # Reset rotation counter when not spinning
                    self.ship.total_rotations = 0.0
                    # Update last_angle even when not spinning to prevent large jumps
                    self.ship.last_angle = self.ship.angle
            
            # Generate ability particles based on speed
            current_speed = self.ship.velocity.magnitude()
            if current_speed >= 1000:
                self.explosions.add_ability_particles(
                    self.ship.position.x,
                    self.ship.position.y,
                    self.ship.angle,
                    current_speed
                )
            
            # Generate 2x charged ability particles (pink/purple particles in circle)
            if (self.ship.ability_charges == self.ship.max_ability_charges and 
                self.ship.ability_2x_particle_timer >= self.ship.ability_2x_particle_interval):
                self.explosions.add_2x_charged_ability_particles(
                    self.ship.position.x,
                    self.ship.position.y,
                    self.ship.ability_2x_particle_rotation,
                    self.ship.velocity.x,
                    self.ship.velocity.y
                )
                # Reset timer after generating particles
                self.ship.ability_2x_particle_timer = 0.0
            
            # Check for ROF peak reached and trigger spark effect
            is_shooting = pygame.K_SPACE in self.keys_pressed
            if is_shooting:
                rof_peak_reached = self.ship.update_rate_of_fire(dilated_dt, is_shooting)
                if rof_peak_reached:
                    # Trigger spark effect at the front of the ship
                    self.explosions.add_rof_peak_sparks(
                        self.ship.position.x, 
                        self.ship.position.y, 
                        self.ship.angle, 
                        num_particles=7
                    )
            # Update star field with ship velocity (affected by time dilation)
            # But use normal time during explosions to keep them independent of game time effects
            if self.star_explosion_active or self.star_field.fade_in_mode or self.star_field.explosion_fade_mode:
                self.star_field.update(None, self.current_width, self.current_height, dt)
            else:
                self.star_field.update(self.ship.velocity, self.current_width, self.current_height, dilated_dt)
        elif self.star_explosion_active or self.star_field.fade_in_mode or self.star_field.explosion_fade_mode:
            # Update star field during explosion, explosion fade, or fade-in even when ship is not active
            # Use normal time (dt) for explosions to keep them independent of game time effects
            self.star_field.update(None, self.current_width, self.current_height, dt)
        
        # Update star explosion effect
        if self.star_explosion_active:
            self.star_explosion_timer += dt  # Use normal time, not dilated
            if self.star_explosion_timer >= self.star_explosion_duration:
                # Explosion finished, start smooth fade-in transition
                self.star_explosion_active = False
                self.star_explosion_timer = 0.0
                self.star_field.explosion_mode = False
                # Start the smooth fade-in transition instead of immediate regeneration
                self.star_field.start_fade_in(self.current_width, self.current_height)
            
            
        
        # Update explosion particles (affected by time dilation)
        self.explosions.update(dilated_dt, self.current_width, self.current_height, dt)
        
        
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
        
        # Update game over timer and stop screen shake after 3 seconds (NOT affected by time dilation)
        if self.game_state == "game_over":
            self.game_over_timer += dt  # Use normal time, not dilated time
            if self.game_over_timer >= 3.0:  # After 3 seconds
                # Force stop all screen shake for game over
                self.screen_shake_intensity = 0
                self.screen_shake_timer = 0
                self.screen_shake_duration = 0
        
        # Update bullets (affected by time dilation) - use list comprehension for efficiency
        self.bullets = [bullet for bullet in self.bullets if bullet.active]
        for bullet in self.bullets:
            bullet.update(dilated_dt, self.current_width, self.current_height)
        
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
            
            # Set bullet limit based on level: 5 + ((level/2) * 5), rounded down
            ufo.max_bullets = 5 + ((self.level // 2) * 5)
            
            should_shoot = ufo.update(dilated_dt, self.ship.position if self.ship else Vector2D(0, 0), self.current_width, self.current_height, self.time_dilation_factor, self.explosions)
            
            # Handle spinout effects that need game instance
            if ufo.spinout_active and hasattr(ufo, 'update_spinout'):
                try:
                    ufo.update_spinout(dilated_dt, self.explosions, self)
                except Exception as e:
                    # Disable spinout to prevent further crashes
                    ufo.spinout_active = False
            if should_shoot and self.ship:
                # UFO shoots at ship with enhanced aiming
                bullet_speed = 200
                
                # Choose aiming method based on personality
                if ufo.personality in ["tactical", "swarm", "deadly"]:
                    # Use predictive aiming
                    angle = ufo.calculate_predictive_aim(self.ship.position, self.ship.velocity, bullet_speed)
                else:
                    # Use direct aiming
                    angle = math.atan2(self.ship.position.y - ufo.position.y,
                                     self.ship.position.x - ufo.position.x)
                
                # Apply accuracy modifier with level penalty
                level_penalty = ufo.get_level_accuracy_penalty(self.level)
                angle = ufo.apply_accuracy_modifier(angle, ufo.accuracy_modifier, level_penalty)
                
                vx = math.cos(angle) * bullet_speed
                vy = math.sin(angle) * bullet_speed
                ufo_bullet = Bullet(ufo.position.x, ufo.position.y, vx, vy, is_ufo_bullet=True)
                self.ufo_bullets.append(ufo_bullet)
                
                # Increment bullet count for this UFO
                ufo.bullets_fired += 1
            
            if not ufo.active:
                # Reset bullet count when UFO is destroyed
                ufo.bullets_fired = 0
                self.ufos.remove(ufo)
        
        # Update UFO bullets (affected by time dilation) - use list comprehension for efficiency
        self.ufo_bullets = [bullet for bullet in self.ufo_bullets if bullet.active]
        for bullet in self.ufo_bullets:
            bullet.update(dilated_dt, self.current_width, self.current_height)
        
        # Update bosses (affected by time dilation)
        for boss in self.bosses[:]:
            boss.update(dilated_dt, self.current_width, self.current_height, self.asteroids, self.ship)
            if not boss.active:
                self.bosses.remove(boss)
        
        # Spawn bosses based on new level-based system
        if self.should_spawn_bosses() and not self.boss_spawned_this_level and self.boss_spawn_timer >= self.boss_spawn_delay:
            self.spawn_bosses_for_level()
            self.boss_spawned_this_level = True
        
        # Update boss spawn timer
        if self.should_spawn_bosses() and not self.boss_spawned_this_level:
            self.boss_spawn_timer += dilated_dt
        
        # Spawn UFOs with 5-second delay, then from random corner (affected by time dilation)
        if self.initial_ufo_timer > 0:
            self.initial_ufo_timer -= dilated_dt
            if self.initial_ufo_timer <= 0:
                # Determine how many UFOs to spawn based on level
                if self.level == 1:
                    self.ufos_to_spawn = 5  # Exactly 5 UFOs for level 1 (1 of each type)
                    self.ufo_spawn_types = ["aggressive", "defensive", "tactical", "swarm", "deadly"]  # One of each type
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
                
                # 10% chance for mass spawn from all corners (not for level 1)
                if self.level == 1:
                    self.ufo_mass_spawn = False  # Level 1 uses normal spawning
                else:
                    self.ufo_mass_spawn = random.random() < 0.1
                
                # Set up burst spawn system for mass spawn
                if self.ufo_mass_spawn:
                    if self.ufos_to_spawn < 8:
                        # Less than 8 UFOs: spawn all at once
                        self.ufo_burst_spawn = False
                    else:
                        # 8 or more UFOs: use burst system
                        self.ufo_burst_spawn = True
                        self.ufo_burst_count = 4  # 4 UFOs per burst
                        self.ufo_burst_delay = 0  # Start immediately
                
                self.ufo_spawn_delay = 0  # Start spawning immediately
        elif self.ufos_to_spawn > 0:
            if self.ufo_mass_spawn:
                if self.ufo_burst_spawn:
                    # Burst spawn: Spawn in 4-UFO bursts with 1-second intervals
                    self.ufo_burst_delay += dilated_dt
                    if self.ufo_burst_delay >= self.ufo_burst_interval:
                        self.ufo_burst_delay = 0
                        # Spawn up to 4 UFOs (one per corner)
                        ufos_to_spawn_this_burst = min(self.ufo_burst_count, self.ufos_to_spawn)
                        self.spawn_ufo_burst(ufos_to_spawn_this_burst)
                        self.ufos_to_spawn -= ufos_to_spawn_this_burst
                        
                        # If no more UFOs to spawn, finish mass spawn
                        if self.ufos_to_spawn <= 0:
                            self.ufo_mass_spawn = False
                            self.ufo_burst_spawn = False
                else:
                    # Mass spawn: Spawn all remaining UFOs at once from all corners (for <8 UFOs)
                    self.spawn_all_ufos_mass()
                    self.ufos_to_spawn = 0
                    self.ufo_mass_spawn = False
            else:
                # Normal spawn: One UFO per second from selected corner
                self.ufo_spawn_delay += dilated_dt
                if self.ufo_spawn_delay >= 1.0:  # 1 second between spawns
                    self.ufo_spawn_delay = 0
                    if self.level == 1 and self.ufo_spawn_types:
                        # Level 1: One of each type (use pop to remove each type after spawning)
                        personality = self.ufo_spawn_types.pop(0)  # Get next type and remove it
                        self.spawn_ufo_with_personality_at_corner(personality, self.ufo_spawn_corner)
                    elif self.ufo_spawn_types and len(self.ufo_spawn_types) > 0:
                        # Other levels: Use specific types in order
                        personality = self.ufo_spawn_types.pop(0)  # Get next type and remove it
                        self.spawn_ufo_with_personality_at_corner(personality, self.ufo_spawn_corner)
                    else:
                        # Other levels: Use normal random selection from selected corner
                        self.spawn_ufo_from_selected_corner()
                    
                    # Only decrement if not unlimited (level 1)
                    if self.ufos_to_spawn > 0:
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
        
        # Update collision FPS based on object counts
        self.update_collision_fps(dt)
        
        # Check collisions (affected by time dilation)
        try:
            self.check_collisions()
        except Exception as e:
            pass
        
        # Update spinning trick message timer (independent of time dilation)
        if self.show_spinning_trick and self.spinning_trick_timer > 0:
            self.spinning_trick_timer -= 1.0 / 60.0  # Use fixed 60 FPS timing
            if self.spinning_trick_timer <= 0:
                self.show_spinning_trick = False
                # Mark the achievement as shown only after the message has been displayed for 3 seconds
                if self.ship:
                    self.ship.spinning_trick_shown = True
        
        # Update interstellar message timer (independent of time dilation)
        if self.show_interstellar and self.interstellar_timer > 0:
            self.interstellar_timer -= 1.0 / 60.0  # Use fixed 60 FPS timing
            if self.interstellar_timer <= 0:
                self.show_interstellar = False
        
        # Update god mode message timer (independent of time dilation)
        if self.show_god_mode and self.god_mode_timer > 0:
            self.god_mode_timer -= 1.0 / 60.0  # Use fixed 60 FPS timing
            if self.god_mode_timer <= 0:
                self.show_god_mode = False
        
        # Update ludicrous speed message timer (independent of time dilation)
        if self.show_ludicrous_speed and self.ludicrous_speed_timer > 0:
            self.ludicrous_speed_timer -= 1.0 / 60.0  # Use fixed 60 FPS timing
            if self.ludicrous_speed_timer <= 0:
                self.show_ludicrous_speed = False
        
        # Update plaid message timer (independent of time dilation)
        if self.show_plaid and self.plaid_timer > 0:
            self.plaid_timer -= 1.0 / 60.0  # Use fixed 60 FPS timing
            if self.plaid_timer <= 0:
                self.show_plaid = False
        
        # Update score milestone message timers (independent of time dilation)
        if self.show_250k_message and self.message_250k_timer > 0:
            self.message_250k_timer -= 1.0 / 60.0  # Use fixed 60 FPS timing
            if self.message_250k_timer <= 0:
                self.show_250k_message = False
        
        if self.show_500k_message and self.message_500k_timer > 0:
            self.message_500k_timer -= 1.0 / 60.0  # Use fixed 60 FPS timing
            if self.message_500k_timer <= 0:
                self.show_500k_message = False
        
        if self.show_1m_message and self.message_1m_timer > 0:
            self.message_1m_timer -= 1.0 / 60.0  # Use fixed 60 FPS timing
            if self.message_1m_timer <= 0:
                self.show_1m_message = False
        
        # Spinning trick message is now shown immediately when 11.38 rotations is reached
        
        # Check for interstellar achievement (only if ship exists)
        if self.ship and self.ship.interstellar_shown and not self.show_interstellar:
            # Clear any existing messages
            if self.show_spinning_trick:
                # Mark spinning trick as shown if it was being displayed
                self.ship.spinning_trick_shown = True
            self.show_spinning_trick = False
            self.show_god_mode = False
            self.show_ludicrous_speed = False
            self.show_plaid = False
            self.spinning_trick_timer = 0.0
            self.god_mode_timer = 0.0
            self.ludicrous_speed_timer = 0.0
            self.plaid_timer = 0.0
            # Show interstellar message
            self.show_interstellar = True
            self.interstellar_timer = 3.0  # Show for 3 seconds
            # Reset the flag so it doesn't retrigger
            self.ship.interstellar_shown = False
        
        # Check for god mode message (show when god mode is toggled on)
        if self.god_mode and not self.god_mode_was_on and not self.show_god_mode:
            # Clear any existing messages
            if self.show_spinning_trick:
                # Mark spinning trick as shown if it was being displayed
                self.ship.spinning_trick_shown = True
            self.show_spinning_trick = False
            self.show_interstellar = False
            self.show_ludicrous_speed = False
            self.show_plaid = False
            self.spinning_trick_timer = 0.0
            self.interstellar_timer = 0.0
            self.ludicrous_speed_timer = 0.0
            self.plaid_timer = 0.0
            # Show god mode message
            self.show_god_mode = True
            self.god_mode_timer = 3.0  # Show for 3 seconds
        
        # Update god mode tracking
        self.god_mode_was_on = self.god_mode
        
        # Check for ludicrous speed achievement (trigger when first crossing 5000 speed)
        if self.ship and not self.ludicrous_speed_shown and self.ship.velocity.magnitude() >= 5000:
            # Clear any existing messages
            if self.show_spinning_trick:
                # Mark spinning trick as shown if it was being displayed
                self.ship.spinning_trick_shown = True
            self.show_spinning_trick = False
            self.show_interstellar = False
            self.show_god_mode = False
            self.show_plaid = False
            self.spinning_trick_timer = 0.0
            self.interstellar_timer = 0.0
            self.god_mode_timer = 0.0
            self.plaid_timer = 0.0
            # Show ludicrous speed message
            self.show_ludicrous_speed = True
            self.ludicrous_speed_timer = 3.0  # Show for 3 seconds
            self.ludicrous_speed_shown = True  # Mark as shown
        
        # Check for plaid achievement (trigger when first crossing 10000 speed)
        if self.ship and not self.plaid_shown and self.ship.velocity.magnitude() >= 10000:
            # Clear any existing messages
            if self.show_spinning_trick:
                # Mark spinning trick as shown if it was being displayed
                self.ship.spinning_trick_shown = True
            self.show_spinning_trick = False
            self.show_interstellar = False
            self.show_god_mode = False
            self.show_ludicrous_speed = False
            self.spinning_trick_timer = 0.0
            self.interstellar_timer = 0.0
            self.god_mode_timer = 0.0
            self.ludicrous_speed_timer = 0.0
            # Show plaid message
            self.show_plaid = True
            self.plaid_timer = 3.0  # Show for 3 seconds
            self.plaid_shown = True  # Mark as shown
        
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
        
        # Count asteroids for logging
        asteroids_count = len([a for a in self.asteroids if a.active])
        
        # Calculate expected boss count based on level (for logging purposes only)
        boss_count = 0
        if self.should_spawn_bosses():
            if self.level == 3:
                boss_count = 1
            elif self.level == 6:
                boss_count = 2
            elif self.level == 9:
                # Level 9 has 50% chance of 1 or 3 bosses - we'll log as "1-3"
                boss_count = "1-3 (random)"
            elif self.level >= 12:
                # Level 12+ has variable boss counts - we'll log as "variable"
                boss_count = "variable"
        
        # Log new level with asteroid count
        game_logger.log_new_level(self.level, asteroids_count, boss_count)
        
        # Reset first UFO counter for new level
        self.first_ufos_spawned_level_1 = 0
        
        # Play level music with 10% chance
        self.play_level_music()
        
        # Spawn UFOs for new level (1-3 randomly chosen x current level) after 5 second delay
        if self.level == 1:
            self.initial_ufo_timer = 5.0  # 5 second wait for level 1
            self.ufos_to_spawn = 5  # Exactly 5 UFOs for level 1 (1 of each type)
            self.ufo_spawn_types = ["aggressive", "defensive", "tactical", "swarm", "deadly"]  # One of each type
            # Pick a random corner for level 1
            corners = [
                (0, 0),  # Top-left
                (self.current_width, 0),  # Top-right
                (0, self.current_height),  # Bottom-left
                (self.current_width, self.current_height)  # Bottom-right
            ]
            self.ufo_spawn_corner = random.choice(corners)
        else:
            self.initial_ufo_timer = 5.0  # 5 second delay for other levels
            self.ufos_to_spawn = 0  # Will be set when timer expires
        
        # Reset level clear pause timer
        self.level_clear_pause_timer = 0.0
        
        # Clear all player shots and UFOs
        self.bullets.clear()
        self.ufo_bullets.clear()
        self.ufos.clear()
        
        # Clear bosses and reset boss spawning for new level
        self.bosses.clear()
        self.boss_spawned_this_level = False
        
        # Check if this level should spawn bosses
        if self.should_spawn_bosses():
            # Set random spawn delay between 5-15 seconds
            self.boss_spawn_delay = random.uniform(5.0, 15.0)
            self.boss_spawn_timer = 0.0
        
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
            
            # Reset asteroid interval bonus for new level
            self.ship.asteroid_interval_bonus = 0.0
        
        # Add 1 life on new level (maximum 5 lives)
        if self.lives < 5:
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
        
        # Animate from bottom to 20% from top during the 2 second pause
        start_y = self.current_height - 50
        end_y = int(self.current_height * 0.2)  # 20% from top of screen
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
    
    def draw_life_indicators(self, surface, start_y, dt):
        """Draw pulsing life indicators with ship images at 75% size"""
        if not hasattr(self, 'life_pulse_timer'):
            self.life_pulse_timer = 0.0
        
        # Apply time dilation to the pulse timer
        self.life_pulse_timer += dt * self.time_dilation_factor
        
        # Calculate spacing between life indicators
        ship_size = 30  # 75% of original size (40 * 0.75)
        spacing = 40
        
        # Draw zap emojis when god mode is active (above life indicators)
        if self.god_mode:
            # Use a system font that supports emojis better
            try:
                emoji_font = pygame.font.SysFont("segoeuiemoji", 20)
            except:
                emoji_font = pygame.font.Font(None, 20)
            
            zap_emoji = "⚡"
            
            # Render zap emojis with 50% opacity
            left_zap = emoji_font.render(zap_emoji, True, YELLOW)
            right_zap = emoji_font.render(zap_emoji, True, YELLOW)
            
            # Set 50% opacity for zap emojis
            left_zap.set_alpha(128)  # 50% opacity (255 * 0.5 = 127.5, rounded to 128)
            right_zap.set_alpha(128)
            
            # Position zap emojis on left and right of life indicators area
            life_center_x = self.current_width // 2
            left_zap_rect = left_zap.get_rect(center=(life_center_x - 60, start_y - 15))
            right_zap_rect = right_zap.get_rect(center=(life_center_x + 60, start_y - 15))
            
            # Draw zap emojis
            surface.blit(left_zap, left_zap_rect)
            surface.blit(right_zap, right_zap_rect)
        
        # Center the middle ship, with others to left and right (offset 16px right, moved 4px left)
        if self.lives == 1:
            start_x = self.current_width // 2 - ship_size // 2 + 16
        elif self.lives == 2:
            start_x = self.current_width // 2 - ship_size // 2 - spacing // 2 + 16
        else:
            # For 3+ lives, center the middle ship
            # Calculate total width and center the group
            total_width = (self.lives - 1) * spacing + ship_size
            start_x = (self.current_width - total_width) // 2 + 16
        
        for i in range(self.lives):
            # Calculate pulse opacity (50% to 100%) with 25% base opacity and 10% timing offset per life
            pulse_offset = i * 0.33333  # 10% offset per life (10% of 3.3333 seconds)
            pulse_cycle = (self.life_pulse_timer + pulse_offset) % 3.33333  # 3.3333 second cycle
            pulse_progress = pulse_cycle / 3.33333
            opacity = 0.25 + 0.75 * (0.5 + 0.5 * math.sin(pulse_progress * 2 * math.pi))  # 25% base + 0-75% pulse = 50% to 100%
            
            x = start_x + i * spacing
            y = start_y
            
            # Draw ship image (fallback image created if needed)
            if hasattr(self, 'ship') and self.ship and self.ship.image:
                # Scale ship image to 75% size
                scaled_ship = pygame.transform.scale(self.ship.image, (ship_size, ship_size))
                
                # Create surface with alpha for opacity
                ship_surface = pygame.Surface((ship_size, ship_size), pygame.SRCALPHA)
                ship_surface.blit(scaled_ship, (0, 0))
                
                # Apply opacity
                ship_surface.set_alpha(int(255 * opacity))
                ship_rect = ship_surface.get_rect(center=(x, y))
                surface.blit(ship_surface, ship_rect)
    
    def draw_speed_display(self, surface, start_y, dt):
        """Draw player speed and time scale display with 35% opacity"""
        if not self.ship:
            return
        
        # Get current speed
        current_speed = self.ship.velocity.magnitude()
        
        # Get current time scale percentage
        time_scale_percent = self.time_dilation_factor * 100
        
        # Format speed and time scale text
        speed_text = f"{current_speed:.0f}   {time_scale_percent:.1f}%"
        
        # Create font
        font = pygame.font.Font(None, 24)
        
        # Render text with 35% opacity
        text_surface = font.render(speed_text, True, (255, 255, 255))
        text_surface.set_alpha(int(255 * 0.35))  # 35% opacity
        
        # Center the text horizontally
        text_rect = text_surface.get_rect(center=(self.current_width // 2, start_y))
        
        # Draw the text
        surface.blit(text_surface, text_rect)
    
    def draw_progress_bars(self, surface):
        """Draw player speed and world speed progress bars"""
        if not self.ship:
            return
            
        # Calculate player speed percentage (0-100%)
        player_speed = self.ship.velocity.magnitude()
        player_speed_percent = min(player_speed / 1000.0, 1.0)  # Cap at 100%
        
        # Calculate world speed percentage (0-100%)
        world_speed_percent = min(self.time_dilation_factor, 1.0)  # Cap at 100%
        
        # Calculate progress bar width scaling based on player speed
        # 0 speed = 1x, 1000 = 1x, 2000 = 1.5x, 10000 = 3x
        if player_speed <= 1000:
            width_multiplier = 1.0
        elif player_speed <= 2000:
            # Linear interpolation between 1x and 1.5x from 1000 to 2000
            progress = (player_speed - 1000) / 1000
            width_multiplier = 1.0 + (progress * 0.5)
        else:
            # Linear interpolation between 1.5x and 3x from 2000 to 10000
            progress = min((player_speed - 2000) / 8000, 1.0)  # Cap at 10000
            width_multiplier = 1.5 + (progress * 1.5)
        
        # Player speed bar (green, left side, full height, scaled width)
        base_bar_width = 6  # 30% of 20px
        bar_width = int(base_bar_width * width_multiplier)
        bar_height = self.current_height
        bar_x = 0
        bar_y = 0
        
        # Fill bar based on speed (from bottom to top) with 42% opacity
        fill_height = int(bar_height * player_speed_percent)
        if fill_height > 0:
            # Create a surface with alpha for transparency
            bar_surface = pygame.Surface((bar_width, fill_height), pygame.SRCALPHA)
            pygame.draw.rect(bar_surface, (0, 255, 0, 107), (0, 0, bar_width, fill_height))  # 42% opacity (255 * 0.42 = 107)
            surface.blit(bar_surface, (bar_x, bar_y + bar_height - fill_height))
        
        # World speed bar (blue, bottom, full width, 30% thickness)
        bar_width = self.current_width
        bar_height = 6  # 30% of 20px
        bar_x = 0
        bar_y = self.current_height - bar_height
        
        # Fill bar based on world speed (from left to right) with 42% opacity
        fill_width = int(bar_width * world_speed_percent)
        if fill_width > 0:
            # Create a surface with alpha for transparency
            bar_surface = pygame.Surface((fill_width, bar_height), pygame.SRCALPHA)
            pygame.draw.rect(bar_surface, (0, 100, 255, 107), (0, 0, fill_width, bar_height))  # 42% opacity (255 * 0.42 = 107)
            surface.blit(bar_surface, (bar_x, bar_y))
    
    def create_gradient_title_text(self, text, font):
        """Create title text with bright yellow outline and gradient fill (yellow bottom to black top, black at 75% height)"""
        # Render the text to get dimensions
        text_surface = font.render(text, True, (255, 255, 255))  # White for dimensions
        width, height = text_surface.get_size()
        
        # Create surface for the final result
        result_surface = pygame.Surface((width, height), pygame.SRCALPHA)
        
        # Create outline by rendering text multiple times in different positions
        outline_color = (255, 255, 0)  # Bright yellow
        outline_thickness = 3
        
        # Render outline
        for x_offset in range(-outline_thickness, outline_thickness + 1):
            for y_offset in range(-outline_thickness, outline_thickness + 1):
                if x_offset == 0 and y_offset == 0:
                    continue  # Skip center, we'll do that with gradient
                outline_text = font.render(text, True, outline_color)
                result_surface.blit(outline_text, (x_offset, y_offset))
        
        # Create gradient fill - fade to black much closer to bottom (black at 75% height)
        for y in range(height):
            # Calculate gradient progress (0.0 at top, 1.0 at bottom)
            # Scale progress so black is reached at 75% height instead of 0%
            progress = y / height
            scaled_progress = min(1.0, progress * 1.33)  # Black reached at 75% height
            
            # Interpolate from black (0,0,0) at top to yellow (255,255,0) at bottom
            r = int(255 * scaled_progress)
            g = int(255 * scaled_progress)
            b = 0
            
            # Render text line with this color
            gradient_text = font.render(text, True, (r, g, b))
            
            # Extract this line from the gradient text
            line_rect = pygame.Rect(0, y, width, 1)
            line_surface = pygame.Surface((width, 1), pygame.SRCALPHA)
            line_surface.blit(gradient_text, (0, 0), line_rect)
            
            # Blit this line onto the result
            result_surface.blit(line_surface, (0, y))
        
        return result_surface

    def create_skewed_message_text(self, text_surface, skew_factor=0.15):
        """Create skewed message text - narrower at top, wider at bottom using 15 degree skew with 48 strips"""
        # Get original dimensions
        original_width, original_height = text_surface.get_size()
        
        # Safety check for very small text
        if original_height < 4:
            return text_surface
        
        # Calculate maximum width needed (bottom strip will be widest)
        max_width = int(original_width * (1.0 + skew_factor))
        
        # Create perspective effect with strips for smooth transition
        # Use larger surface to accommodate the skew
        perspective_surface = pygame.Surface((max_width, original_height), pygame.SRCALPHA)
        
        # Use 48 strips for smooth transition
        num_strips = 48
        strip_height = max(1, original_height // num_strips)
        
        for strip in range(num_strips):
            # Calculate y position for this strip
            y = strip * strip_height
            
            # Ensure we don't go beyond the text surface
            if y >= original_height:
                break
                
            # Calculate actual strip height (last strip might be different)
            actual_strip_height = min(strip_height, original_height - y)
            
            # Calculate skew factor for this strip (0 at top, skew_factor at bottom)
            strip_progress = strip / (num_strips - 1) if num_strips > 1 else 0
            current_skew = strip_progress * skew_factor
            
            # Calculate width for this strip (narrower at top, wider at bottom)
            strip_width = int(original_width * (1.0 + current_skew))
            
            # Extract this strip from the original text
            strip_rect = pygame.Rect(0, y, original_width, actual_strip_height)
            
            # Safety check for strip dimensions
            if strip_width > 0 and actual_strip_height > 0:
                try:
                    strip_surface = pygame.Surface((strip_width, actual_strip_height), pygame.SRCALPHA)
                    
                    # Scale this strip horizontally
                    scaled_strip = pygame.transform.scale(text_surface.subsurface(strip_rect), (strip_width, actual_strip_height))
                    strip_surface.blit(scaled_strip, (0, 0))
                    
                    # Center the strip horizontally within the larger surface
                    x_offset = (max_width - strip_width) // 2
                    perspective_surface.blit(strip_surface, (x_offset, y))
                except:
                    # Fallback: just blit the original strip if scaling fails
                    x_offset = (max_width - original_width) // 2
                    perspective_surface.blit(text_surface.subsurface(strip_rect), (x_offset, y))
        
        return perspective_surface

    def create_skewed_title_text(self, text_surface, pinch_factor=0.75):
        """Create skewed title text - narrower at top, wider at bottom using 48 strips"""
        # Get original dimensions
        original_width, original_height = text_surface.get_size()
        
        # Create perspective effect with 48 strips for smooth transition
        perspective_surface = pygame.Surface((original_width, original_height), pygame.SRCALPHA)
        
        # Use 48 strips as requested
        num_strips = 48
        strip_height = max(1, original_height // num_strips)
        
        for i in range(num_strips):
            y_start = i * strip_height
            y_end = min((i + 1) * strip_height, original_height)
            strip_height_actual = y_end - y_start
            
            if strip_height_actual <= 0:
                continue
                
            # Calculate width scaling factor for this strip
            # Use smooth interpolation from pinch_factor at top to 1.0 at bottom
            progress = i / (num_strips - 1)  # 0.0 at top, 1.0 at bottom
            
            # Smooth curve interpolation (ease-in-out cubic)
            smooth_progress = 3 * progress * progress - 2 * progress * progress * progress
            
            # Interpolate from pinch_factor to 1.0 with smooth curve
            width_scale = pinch_factor + (1.0 - pinch_factor) * smooth_progress
            
            # Extract this strip from the original text
            strip_rect = pygame.Rect(0, y_start, original_width, strip_height_actual)
            strip_surface = pygame.Surface((original_width, strip_height_actual), pygame.SRCALPHA)
            strip_surface.blit(text_surface, (0, 0), strip_rect)
            
            # Scale the strip horizontally
            scaled_width = max(1, int(original_width * width_scale))
            if scaled_width > 0 and strip_height_actual > 0:
                # Use smoothscale for better quality scaling
                scaled_strip = pygame.transform.smoothscale(strip_surface, (scaled_width, strip_height_actual))
                
                # Center the scaled strip horizontally
                x_offset = (original_width - scaled_width) // 2
                perspective_surface.blit(scaled_strip, (x_offset, y_start))
        
        return perspective_surface
    
    def return_to_title_screen(self, log_current_score=False):
        """Return to title screen with full game world reset"""
        # Log current score before returning to title screen if requested
        if log_current_score and self.score > 0:
            game_logger.log_game_over(self.score, self.level)
        
        # Set game state to waiting
        self.game_state = "waiting"
        
        # Clear any pressed keys from previous game state
        self.keys_pressed.clear()
        
        # Stop music
        self.stop_music()
        
        # Reset all game state
        self.score = 0
        self.lives = 3
        self.level = 1
        self.game_start_timer = 0.0
        
        # Reset score milestone tracking
        self.last_milestone_250k = 0
        self.last_milestone_500k = 0
        self.last_milestone_1000k = 0
        
        # Reset first UFO counter
        self.first_ufos_spawned_level_1 = 0
        
        # Clear all game objects
        self.bullets.clear()
        self.asteroids.clear()
        self.ufos.clear()
        self.ufo_bullets.clear()
        self.bosses.clear()
        
        # Reset boss spawning
        self.boss_spawned_this_level = False
        self.boss_spawn_timer = 0.0
        self.boss_spawn_delay = 0.0
        
        # Reset ship
        self.ship = None
        
        # Reset all timers and effects
        self.game_over_timer = 0.0
        self.game_over_alpha = 0
        self.death_delay_timer = 0.0
        self.star_explosion_active = False
        self.star_explosion_timer = 0.0
        self.screen_shake_intensity = 0
        self.screen_shake_timer = 0
        self.screen_shake_duration = 0
        
        # Reset ability system
        self.ability_breaking = False
        self.ability_break_count = 0
        self.ability_break_timer = 0.0
        self.ability_break_delay = 0.0
        self.ability_blast_count = 0
        
        # Reset time effects
        self.time_dilation_factor = 1.0
        self.time_advance_timer = 0.0
        
        # Reset title screen elements
        self.cleanup_title_screen()
        
        # Note: high score file clearing is handled elsewhere to avoid losing scores
        
        # Reset title screen timers
        self.title_start_timer = 0.0
        self.title_boss_spawn_timer = 0.0
        
        # Reset music flag to ensure title music plays again
        self.title_music_played = False
        
        # Reset star field
        self.star_field.explosion_mode = False
        self.star_field.explosion_fade_mode = False
        self.star_field.fade_in_mode = False
        self.star_field.fade_in_timer = 0.0
        
        # Clear all particles
        if hasattr(self, 'explosions'):
            self.explosions.particles.clear()
        
        
        # Reset spinning trick tracking
        self.show_spinning_trick = False
        self.spinning_trick_timer = 0.0

    def cleanup_title_screen(self):
        """Clean up title screen elements when starting the game"""
        # Clear title screen UFOs
        self.ufos.clear()
        self.ufo_bullets.clear()
        self.bosses.clear()
        
        # Reset boss spawning
        self.boss_spawned_this_level = False
        self.boss_spawn_timer = 0.0
        self.boss_spawn_delay = 0.0
        
        # Note: high score file clearing is handled in restart_game() and other appropriate places
        
        
        # Reset title screen timers
        self.title_start_timer = 0.0
        self.title_boss_spawn_timer = 0.0
        self.press_space_alpha = 0
        self.controls_alpha = 0
        self.game_over_alpha = 0
        self.figure8_timer = 0.0
        
        # Reset sine wave data
        self.sine_wave_timer = 0.0
        self.title_ufo_wave_data.clear()
        self.ufo_respawn_timer = 0.0
        self.ufos_destroyed = 0
        self.title_ufos_initialized = False
        
        # Reset music flag to ensure title music plays again
        self.title_music_played = False
        
        # Clear virtual ship
        self.title_ship = None
        
        # Reset UFO spawn timers
        self.initial_ufo_timer = 5.0  # 5 second wait for level 1
        self.ufos_to_spawn = 5  # Exactly 5 UFOs for level 1 (1 of each type)
        self.ufo_spawn_delay = 0
        # Pick a random corner for level 1
        corners = [
            (0, 0),  # Top-left
            (self.current_width, 0),  # Top-right
            (0, self.current_height),  # Bottom-left
            (self.current_width, self.current_height)  # Bottom-right
        ]
        self.ufo_spawn_corner = random.choice(corners)
        self.ufo_mass_spawn = False
        self.ufo_spawn_types = ["aggressive", "defensive", "tactical", "swarm", "deadly"]  # Cycle through all 5 types
        self.ufo_spawn_type_index = 0
        
        # Reset burst spawn system
        self.ufo_burst_spawn = False
        self.ufo_burst_count = 0
        self.ufo_burst_delay = 0
        
        # Clear explosion particles
        if hasattr(self, 'explosions'):
            self.explosions.particles.clear()
        
    
    def draw_ship_as_asteroid(self, surface, ship):
        """Draw the virtual ship as a size 2 asteroid at 50% opacity when moving"""
        if not ship or not ship.active:
            return
        
        # Only draw if ship is moving (velocity > 5 to avoid flickering)
        if ship.velocity.magnitude() > 5:
            # Create a temporary asteroid to draw
            temp_asteroid = Asteroid(ship.position.x, ship.position.y, size=2, level=self.level)
            temp_asteroid.rotation_angle = ship.angle  # Use ship's rotation
            
            # Draw asteroid directly on surface with alpha blending
            # Save current alpha blending mode
            old_alpha = surface.get_alpha()
            
            # Create a temporary surface for the asteroid
            temp_surface = pygame.Surface((self.current_width, self.current_height), pygame.SRCALPHA)
            temp_asteroid.draw(temp_surface, self.current_width, self.current_height)
            
            # Apply 50% opacity to the entire surface
            temp_surface.set_alpha(128)  # 50% opacity (128/255)
            
            # Blit the semi-transparent asteroid surface
            surface.blit(temp_surface, (0, 0))
    

    def spawn_title_sine_wave_ufo(self):
        """Spawn a UFO for title screen sine wave movement"""
        # Spawn from right side of screen
        start_x = self.current_width + 50
        start_y = self.current_height // 2 - 25  # Center between title and press space, moved up 25px
        
        # Create UFO
        ufo = AdvancedUFO(start_x, start_y, "aggressive")
        ufo.angle = math.radians(270)  # Start with 270 degrees (180 degrees from 90)
        
        # Calculate phase offset based on spawn order to spread out the waves
        phase_offset = (len(self.title_ufo_wave_data) * 2 * math.pi) / 7  # Spread 7 UFOs across full cycle
        
        # Generate varied sine wave parameters for this UFO
        wave_data = {
            'amplitude': random.uniform(20, 40),  # Varied wave height (20-40 pixels)
            'frequency': 1.0,  # Locked wave frequency (1.0 cycles/second)
            'phase_offset': phase_offset,  # Staggered phase offset for variety
            'vertical_center': self.current_height // 2 - 25,  # Locked to center between title and press space, moved up 25px
            'speed': random.uniform(80, 120),  # Varied horizontal speed (80-120 pixels/second)
            'rotation_speed': random.uniform(0.05, 0.2),  # Random rotation speed (0.05-0.2 radians/second) - 10x slower
            'rotation_direction': random.choice([-1, 1]),  # Random rotation direction
            'spawn_time': self.sine_wave_timer  # When this UFO was spawned
        }
        
        # Store wave data
        self.title_ufo_wave_data.append(wave_data)
        self.add_ufo(ufo)
    
    def update_title_sine_wave_ufos(self, dt):
        """Update sine wave movement for title screen UFOs with continuous wrapping"""
        self.sine_wave_timer += dt
        
        # Clean up inactive UFOs and their wave data
        active_ufos = []
        active_wave_data = []
        
        for i, ufo in enumerate(self.ufos[:]):
            if ufo.active and i < len(self.title_ufo_wave_data):
                active_ufos.append(ufo)
                active_wave_data.append(self.title_ufo_wave_data[i])
        
        # Update the lists
        self.ufos = active_ufos
        self.title_ufo_wave_data = active_wave_data
        
        # Update each active UFO's position based on sine wave
        for i, ufo in enumerate(self.ufos):
            if i < len(self.title_ufo_wave_data):
                wave_data = self.title_ufo_wave_data[i]
                
                # Calculate time since this UFO was spawned
                time_since_spawn = self.sine_wave_timer - wave_data['spawn_time']
                
                # Move horizontally from right to left
                ufo.position.x -= wave_data['speed'] * dt
                
                # Calculate sine wave Y position
                wave_phase = wave_data['frequency'] * time_since_spawn + wave_data['phase_offset']
                sine_y = wave_data['vertical_center'] + wave_data['amplitude'] * math.sin(wave_phase)
                ufo.position.y = sine_y
                
                # Random rotation between -10 and +10 degrees at random speeds, plus 270 degrees counter-clockwise
                rotation_change = wave_data['rotation_speed'] * wave_data['rotation_direction'] * dt
                ufo.angle += rotation_change
                
                # Keep angle within -10 and +10 degrees range (relative to 270 degrees counter-clockwise)
                base_angle = math.radians(270)  # 270 degrees counter-clockwise base (180 degrees from 90)
                max_angle = base_angle + math.radians(10)  # 270 + 10 degrees
                min_angle = base_angle - math.radians(10)  # 270 - 10 degrees
                
                if ufo.angle > max_angle:
                    ufo.angle = max_angle
                    wave_data['rotation_direction'] = -1  # Reverse direction
                elif ufo.angle < min_angle:
                    ufo.angle = min_angle
                    wave_data['rotation_direction'] = 1  # Reverse direction
                
                # Wrap UFO from left to right when it goes off screen
                if ufo.position.x < -100:
                    ufo.position.x = self.current_width + 100  # Wrap to right side
    
    def check_title_ufo_collisions(self):
        """Check for collisions between player asteroid and title screen UFOs"""
        if not self.title_ship:
            return
            
        # Get player asteroid radius (size 2 asteroid)
        player_radius = 20  # Approximate radius for size 2 asteroid
        
        for i, ufo in enumerate(self.ufos):
            if ufo.active:
                # Calculate distance between player and UFO
                dx = self.title_ship.position.x - ufo.position.x
                dy = self.title_ship.position.y - ufo.position.y
                distance = math.sqrt(dx*dx + dy*dy)
                
                # Check collision (UFO radius is 26)
                if distance < (player_radius + 26):
                    # UFO destroyed
                    ufo.active = False
                    self.ufos_destroyed += 1
                    
                    # Add screen shake for UFO destruction (same as in-game)
                    self.trigger_screen_shake(8, 0.5)
                    
                    # Add explosion particles (same as in-game UFO destruction)
                    total_particles = int(40 * 1.5 * 1.5)  # 50% more particles (60 * 1.5 = 90)
                    
                    # 90% electric blue spinout sparks
                    for _ in range(int(total_particles * 0.90)):
                        self.explosions.add_explosion(
                            ufo.position.x,
                            ufo.position.y,
                            (0, 150, 255),  # Electric blue
                            "electric"
                        )
                    
                    # 10% bright white spinout sparks
                    for _ in range(int(total_particles * 0.10)):
                        self.explosions.add_explosion(
                            ufo.position.x,
                            ufo.position.y,
                            (255, 255, 255),  # Bright white
                            "electric"
                        )
    
    def update_title_ufo_respawning(self, dt):
        """Handle UFO respawning after destruction - maintain exactly 7 active UFOs"""
        self.ufo_respawn_timer += dt
        
        # Only respawn after initial 7 UFOs have been spawned and after 9-second delay
        if self.ufos_to_spawn > 0 or self.title_start_timer < 9.0:
            return
        
        # Count active title screen UFOs
        active_ufos = sum(1 for ufo in self.ufos if ufo.active and ufo in [u for u in self.ufos if hasattr(u, 'position')])
        
        # If we have less than 7 active UFOs, respawn at 2-second intervals
        if active_ufos < 7 and self.ufo_respawn_timer >= 2.0:
            self.spawn_title_sine_wave_ufo()
            self.ufo_respawn_timer = 0.0
    
    def create_title_ship(self):
        """Create a virtual ship for title screen movement mechanics"""
        if self.title_ship is None:
            self.title_ship = Ship(self.current_width // 2, self.current_height // 2)
    
    def update_title_ship(self, dt):
        """Update the virtual ship with full game movement mechanics"""
        if self.title_ship is None:
            self.create_title_ship()
        
        # Handle input with full game mechanics
        left_rotate_pressed = pygame.K_LEFT in self.keys_pressed
        right_rotate_pressed = pygame.K_RIGHT in self.keys_pressed
        left_strafe_pressed = pygame.K_a in self.keys_pressed
        right_strafe_pressed = pygame.K_d in self.keys_pressed
        up_pressed = pygame.K_UP in self.keys_pressed or pygame.K_w in self.keys_pressed
        down_pressed = pygame.K_DOWN in self.keys_pressed or pygame.K_s in self.keys_pressed
        
        # Rotation (arrow keys only)
        if left_rotate_pressed:
            self.title_ship.rotate_left(dt)
        if right_rotate_pressed:
            self.title_ship.rotate_right(dt)
        
        # Thrust (up arrow or W key)
        if up_pressed:
            self.title_ship.thrust(dt)
        else:
            self.title_ship.stop_thrust()
        
        # Reverse thrust (down arrow or S key)
        if down_pressed:
            self.title_ship.reverse_thrust(dt)
        
        # Strafe (A and D keys)
        if left_strafe_pressed:
            self.title_ship.strafe_left(dt)
        if right_strafe_pressed:
            self.title_ship.strafe_right(dt)
        
        # Update ship physics
        self.title_ship.update(dt, self.current_width, self.current_height, 1.0, dt, 1.0, 0)
        
        # Trigger screen shake based on movement (like in game)
        if self.title_ship.velocity.magnitude() > 100:  # Moving fast
            self.trigger_screen_shake(2, 0.1, 1.0)
    
    def update_title_screen_ufos(self, dt):
        """Update UFOs on title screen - only sine wave UFOs, no corner spawning"""
        # Title screen uses only sine wave UFOs - no corner spawning system
        # The sine wave UFO spawning is handled by update_title_ufo_respawning()
        
        # Spawn initial 7 UFOs one at a time with 2-second intervals (delayed by 9 seconds)
        if not self.title_ufos_initialized and self.title_start_timer >= 9.0:
            # Start the spawning process after 9 second delay
            self.title_ufos_initialized = True
            self.ufos_to_spawn = 7
            self.ufo_spawn_delay = 0  # Start immediately after delay
        
        # Spawn UFOs one at a time with 2-second intervals
        if self.ufos_to_spawn > 0:
            self.ufo_spawn_delay += dt
            if self.ufo_spawn_delay >= 2.0:  # 2 seconds between spawns
                self.ufo_spawn_delay = 0
                self.spawn_title_sine_wave_ufo()
                self.ufos_to_spawn -= 1
        
        # Update sine wave movement for title screen UFOs
        self.update_title_sine_wave_ufos(dt)
        
        # Check for collisions between player asteroid and UFOs
        if self.title_ship and self.title_ship.velocity.magnitude() > 5:  # Only when moving
            self.check_title_ufo_collisions()
        
        # Handle UFO respawning
        self.update_title_ufo_respawning(dt)
        
        # Update UFO bullets
        for bullet in self.ufo_bullets[:]:
            if bullet.active:
                bullet.update(dt)
                # Remove bullets that go off screen
                if (bullet.x < -10 or bullet.x > self.current_width + 10 or
                    bullet.y < -10 or bullet.y > self.current_height + 10):
                    bullet.active = False
                    self.ufo_bullets.remove(bullet)
    
    
    def draw_title_screen_ufo(self, surface, ufo):
        """Draw a UFO on the title screen with special transformations for tie.gif"""
        if not ufo.active or not ufo.image:
            return
        
        # Apply additional transformations for aggressive personality (tie.gif) on title screen
        if ufo.personality == "aggressive":
            # Apply additional 90 degrees counter-clockwise rotation and horizontal flip
            title_image = pygame.transform.rotate(ufo.image, 90)
            title_image = pygame.transform.flip(title_image, True, False)
        else:
            # Use the regular image for other personalities
            title_image = ufo.image
        
        # Apply additional 180-degree rotation to all title screen UFOs
        title_image = pygame.transform.rotate(title_image, 180)
        
        # Calculate rotation for movement (same as regular UFO draw)
        rotated_image = pygame.transform.rotate(title_image, -math.degrees(ufo.angle) - 90)
        
        # Get the rect and center it on the UFO position
        rect = rotated_image.get_rect()
        rect.center = (int(ufo.position.x), int(ufo.position.y))
        
        # Draw the rotated image
        surface.blit(rotated_image, rect)

    def draw(self, dt=0.016):
        # Apply screen shake offset
        shake_x = int(self.screen_shake_x)
        shake_y = int(self.screen_shake_y)
        
        # Clear screen
        self.screen.fill(BLACK)
        draw_surface = self.screen
        
        # Draw star field background
        if self.ship:
            self.star_field.draw(draw_surface, self.ship.velocity)
        elif self.star_explosion_active or self.star_field.fade_in_mode or self.star_field.explosion_fade_mode:
            # Draw star field during explosion, explosion fade, or fade-in even when ship is not active
            self.star_field.draw(draw_surface, None)
        
        if self.game_state == "playing":
            # New detailed rendering order with interleaved shadows and asteroids
            
            # Bottom layer - Size 9 asteroids (no shadows)
            size_9_asteroids = [asteroid for asteroid in self.asteroids if asteroid.size == 9]
            for asteroid in size_9_asteroids:
                original_x = asteroid.position.x
                original_y = asteroid.position.y
                asteroid.position.x += shake_x
                asteroid.position.y += shake_y
                asteroid.draw_main_only(draw_surface, self.current_width, self.current_height)
                asteroid.position.x = original_x
                asteroid.position.y = original_y
            
            # Size 8 asteroids (no shadows)
            size_8_asteroids = [asteroid for asteroid in self.asteroids if asteroid.size == 8]
            for asteroid in size_8_asteroids:
                original_x = asteroid.position.x
                original_y = asteroid.position.y
                asteroid.position.x += shake_x
                asteroid.position.y += shake_y
                asteroid.draw_main_only(draw_surface, self.current_width, self.current_height)
                asteroid.position.x = original_x
                asteroid.position.y = original_y
            
            # Size 6 and 7 shadows (grouped layer underneath size 7)
            size_6_asteroids = [asteroid for asteroid in self.asteroids if asteroid.size == 6]
            size_7_asteroids = [asteroid for asteroid in self.asteroids if asteroid.size == 7]
            for asteroid in size_6_asteroids + size_7_asteroids:
                original_x = asteroid.position.x
                original_y = asteroid.position.y
                asteroid.position.x += shake_x
                asteroid.position.y += shake_y
                asteroid.draw_shadow_only(draw_surface, self.current_width, self.current_height)
                asteroid.position.x = original_x
                asteroid.position.y = original_y
            
            # Size 6 roids
            for asteroid in size_6_asteroids:
                original_x = asteroid.position.x
                original_y = asteroid.position.y
                asteroid.position.x += shake_x
                asteroid.position.y += shake_y
                asteroid.draw_main_only(draw_surface, self.current_width, self.current_height)
                asteroid.position.x = original_x
                asteroid.position.y = original_y
            
            # Size 7 roids
            for asteroid in size_7_asteroids:
                original_x = asteroid.position.x
                original_y = asteroid.position.y
                asteroid.position.x += shake_x
                asteroid.position.y += shake_y
                asteroid.draw_main_only(draw_surface, self.current_width, self.current_height)
                asteroid.position.x = original_x
                asteroid.position.y = original_y
            
            # Size 4 and 5 shadows (grouped layer underneath size 5)
            size_4_asteroids = [asteroid for asteroid in self.asteroids if asteroid.size == 4]
            size_5_asteroids = [asteroid for asteroid in self.asteroids if asteroid.size == 5]
            for asteroid in size_4_asteroids + size_5_asteroids:
                original_x = asteroid.position.x
                original_y = asteroid.position.y
                asteroid.position.x += shake_x
                asteroid.position.y += shake_y
                asteroid.draw_shadow_only(draw_surface, self.current_width, self.current_height)
                asteroid.position.x = original_x
                asteroid.position.y = original_y
            
            # Size 4 roids
            for asteroid in size_4_asteroids:
                original_x = asteroid.position.x
                original_y = asteroid.position.y
                asteroid.position.x += shake_x
                asteroid.position.y += shake_y
                asteroid.draw_main_only(draw_surface, self.current_width, self.current_height)
                asteroid.position.x = original_x
                asteroid.position.y = original_y
            
            # Size 5 roids
            for asteroid in size_5_asteroids:
                original_x = asteroid.position.x
                original_y = asteroid.position.y
                asteroid.position.x += shake_x
                asteroid.position.y += shake_y
                asteroid.draw_main_only(draw_surface, self.current_width, self.current_height)
                asteroid.position.x = original_x
                asteroid.position.y = original_y
            
            # Boss shadows
            for boss in self.bosses:
                original_x = boss.position.x
                original_y = boss.position.y
                boss.position.x += shake_x
                boss.position.y += shake_y
                # Draw boss shadow only
                shadow_image = pygame.transform.scale_by(boss.image, 1.333)  # Make shadow 33.3% bigger
                shadow_image.fill((0, 0, 0, 255), special_flags=pygame.BLEND_MULT)  # Make it black first
                shadow_image.set_alpha(168)  # 66% opacity
                shadow_x = int(boss.position.x - 250 + 15)
                shadow_y = int(boss.position.y - 250 + 15)
                draw_surface.blit(shadow_image, (shadow_x, shadow_y), special_flags=pygame.BLEND_ALPHA_SDL2)
                boss.position.x = original_x
                boss.position.y = original_y
            
            # Bosses
            for boss in self.bosses:
                original_x = boss.position.x
                original_y = boss.position.y
                boss.position.x += shake_x
                boss.position.y += shake_y
                # Draw main boss image only
                x = int(boss.position.x - 250)
                y = int(boss.position.y - 250)
                draw_surface.blit(boss.image, (x, y))
                boss.position.x = original_x
                boss.position.y = original_y
            
            # Explosion Particles
            self.explosions.draw(draw_surface)
            
            
            # Size 1, 2, and 3 shadows (grouped layer underneath size 3)
            size_1_asteroids = [asteroid for asteroid in self.asteroids if asteroid.size == 1]
            size_2_asteroids = [asteroid for asteroid in self.asteroids if asteroid.size == 2]
            size_3_asteroids = [asteroid for asteroid in self.asteroids if asteroid.size == 3]
            for asteroid in size_1_asteroids + size_2_asteroids + size_3_asteroids:
                original_x = asteroid.position.x
                original_y = asteroid.position.y
                asteroid.position.x += shake_x
                asteroid.position.y += shake_y
                asteroid.draw_shadow_only(draw_surface, self.current_width, self.current_height)
                asteroid.position.x = original_x
                asteroid.position.y = original_y
            
            # Size 1 roids
            for asteroid in size_1_asteroids:
                original_x = asteroid.position.x
                original_y = asteroid.position.y
                asteroid.position.x += shake_x
                asteroid.position.y += shake_y
                asteroid.draw_main_only(draw_surface, self.current_width, self.current_height)
                asteroid.position.x = original_x
                asteroid.position.y = original_y
            
            # Size 2 roids
            for asteroid in size_2_asteroids:
                original_x = asteroid.position.x
                original_y = asteroid.position.y
                asteroid.position.x += shake_x
                asteroid.position.y += shake_y
                asteroid.draw_main_only(draw_surface, self.current_width, self.current_height)
                asteroid.position.x = original_x
                asteroid.position.y = original_y
            
            # Size 3 roids
            for asteroid in size_3_asteroids:
                original_x = asteroid.position.x
                original_y = asteroid.position.y
                asteroid.position.x += shake_x
                asteroid.position.y += shake_y
                asteroid.draw_main_only(draw_surface, self.current_width, self.current_height)
                asteroid.position.x = original_x
                asteroid.position.y = original_y
            
            # UFO shadows
            for ufo in self.ufos:
                original_x = ufo.position.x
                original_y = ufo.position.y
                ufo.position.x += shake_x
                ufo.position.y += shake_y
                ufo.draw_ufo_shadow(draw_surface, shake_x, shake_y)
                ufo.position.x = original_x
                ufo.position.y = original_y
            
            # UFO particles (smoke)
            for ufo in self.ufos:
                original_x = ufo.position.x
                original_y = ufo.position.y
                ufo.position.x += shake_x
                ufo.position.y += shake_y
                ufo.draw_ufo_smoke(draw_surface, shake_x, shake_y)
                ufo.position.x = original_x
                ufo.position.y = original_y
            
            # UFO thrust (if any)
            # Note: UFO thrust is drawn as part of the UFO drawing, so we'll handle it in the main UFO draw
            
            # UFO spinout
            for ufo in self.ufos:
                original_x = ufo.position.x
                original_y = ufo.position.y
                ufo.position.x += shake_x
                ufo.position.y += shake_y
                if ufo.spinout_active:
                    ufo.draw_spinout(draw_surface, shake_x, shake_y)
                ufo.position.x = original_x
                ufo.position.y = original_y
            
            # UFOs (main UFO image only)
            for ufo in self.ufos:
                original_x = ufo.position.x
                original_y = ufo.position.y
                ufo.position.x += shake_x
                ufo.position.y += shake_y
                # Draw main UFO only (no shadow, smoke, or spinout)
                if ufo.image:
                    if ufo.spinout_active:
                        rotation_angle = ufo.visual_rotation_angle
                    else:
                        rotation_angle = ufo.angle
                    rotated_ufo = pygame.transform.rotate(ufo.image, -math.degrees(rotation_angle) - 90)
                    ufo_rect = rotated_ufo.get_rect(center=(int(ufo.position.x), int(ufo.position.y)))
                    draw_surface.blit(rotated_ufo, ufo_rect)
                else:
                    # Fallback UFO shape
                    pygame.draw.ellipse(draw_surface, WHITE, 
                                      (ufo.position.x - ufo.radius, ufo.position.y - ufo.radius/2,
                                       ufo.radius * 2, ufo.radius))
                    pygame.draw.rect(draw_surface, WHITE,
                                    (ufo.position.x - ufo.radius/2, ufo.position.y - ufo.radius/4,
                                     ufo.radius, ufo.radius/2))
                ufo.position.x = original_x
                ufo.position.y = original_y
            
            # Player shadow
            if self.ship:
                original_x = self.ship.position.x
                original_y = self.ship.position.y
                self.ship.position.x += shake_x
                self.ship.position.y += shake_y
                self.ship.draw_ship_shadow(draw_surface)
                self.ship.position.x = original_x
                self.ship.position.y = original_y
            
            # Player particles (if any)
            # Note: Player particles are drawn as part of ship drawing
            
            # Player thrust is now handled by the ship's own draw method
            
            # UFO & Player Bullets
            for bullet in self.bullets:
                original_x = bullet.position.x
                original_y = bullet.position.y
                bullet.position.x += shake_x
                bullet.position.y += shake_y
                bullet.draw(draw_surface)
                bullet.position.x = original_x
                bullet.position.y = original_y
            for bullet in self.ufo_bullets:
                original_x = bullet.position.x
                original_y = bullet.position.y
                bullet.position.x += shake_x
                bullet.position.y += shake_y
                bullet.draw(draw_surface)
                bullet.position.x = original_x
                bullet.position.y = original_y
            
            # Boss weapon bullets (same layer as other bullets)
            for boss in self.bosses:
                if boss.active:
                    for bullet in boss.weapon_bullets:
                        if bullet.active:
                            original_x = bullet.position.x
                            original_y = bullet.position.y
                            bullet.position.x += shake_x
                            bullet.position.y += shake_y
                            bullet.draw(draw_surface)
                            bullet.position.x = original_x
                            bullet.position.y = original_y
            
            # Player Ship (main ship only, no shadow or thrust)
            if self.ship:
                original_x = self.ship.position.x
                original_y = self.ship.position.y
                self.ship.position.x += shake_x
                self.ship.position.y += shake_y
                # Draw main ship only (no shadow or thrust)
                if self.ship.image:
                    rotation_angle = get_rotation_degrees(self.ship.angle)
                    draw_ship_with_effects(self.ship, draw_surface, self.ship.position, rotation_angle, use_cache=False, draw_shadow=False)
                else:
                    # Fallback triangle
                    points = []
                    for i in range(3):
                        angle = self.ship.angle + i * (2 * math.pi / 3)
                        x = self.ship.position.x + math.cos(angle) * self.ship.radius
                        y = self.ship.position.y + math.sin(angle) * self.ship.radius
                        points.append((x, y))
                    
                    color = WHITE
                    if self.ship.invulnerable and is_invulnerability_flashing(self.ship.invulnerable_time):
                        color = (0, 255, 255)
                    elif self.ship.red_flash_timer > 0:
                        color = (255, 0, 0)
                    pygame.draw.polygon(draw_surface, color, points)
                
                # Draw ability rings
                self.ship.draw_ability_rings(draw_surface)
                
                self.ship.position.x = original_x
                self.ship.position.y = original_y
            
            # Top layer - Debug displays if debug mode is enabled
            if self.debug_mode:
                self.draw_debug_hitboxes(draw_surface)
        else:
            # Draw ship during non-playing states (waiting, game_over, paused)
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
        
        # Create font for UI elements
        font = pygame.font.Font(None, 36)
        
        # Draw UI (only during gameplay)
        if self.game_state == "playing":
            # Level - centered with 75% opacity (above score)
            level_text = f"LEVEL {self.level}"
            level_surface = font.render(level_text, True, WHITE)
            level_surface.set_alpha(int(255 * 0.5))  # 50% opacity
            
            # Draw level text shadow first (behind the text)
            level_shadow_surface = pygame.transform.scale_by(level_surface, 1.1)  # Make shadow 10% bigger
            level_shadow_surface.fill((0, 0, 0, 255), special_flags=pygame.BLEND_MULT)  # Make it black first
            level_shadow_surface.set_alpha(128)  # 50% opacity
            level_shadow_rect = level_shadow_surface.get_rect(center=(self.current_width//2 + 3, 30 + 3))
            draw_surface.blit(level_shadow_surface, level_shadow_rect, special_flags=pygame.BLEND_ALPHA_SDL2)
            
            level_rect = level_surface.get_rect(center=(self.current_width//2, 30))
            draw_surface.blit(level_surface, level_rect)
            
            # Score - centered with pulse effect (below level)
            self.draw_score_with_pulse(draw_surface, dt)
            
            # Special messages - centered at y=150 with 15-degree skew
            message_y = 150
            if self.show_spinning_trick:
                spinning_font = pygame.font.Font(None, 36)
                spinning_text = spinning_font.render("I'll try spinning, that's a good trick!", True, YELLOW)
                # Apply 15-degree skew effect
                skewed_spinning_text = self.create_skewed_message_text(spinning_text, skew_factor=0.15)
                spinning_rect = skewed_spinning_text.get_rect(center=(self.current_width//2, message_y))
                draw_surface.blit(skewed_spinning_text, spinning_rect)
                message_y += 30
            elif self.show_interstellar:
                interstellar_font = pygame.font.Font(None, 36)
                interstellar_text = interstellar_font.render("Interstellar!", True, YELLOW)
                # Apply 15-degree skew effect
                skewed_interstellar_text = self.create_skewed_message_text(interstellar_text, skew_factor=0.15)
                interstellar_rect = skewed_interstellar_text.get_rect(center=(self.current_width//2, message_y))
                draw_surface.blit(skewed_interstellar_text, interstellar_rect)
                message_y += 30
            elif self.show_god_mode:
                god_mode_font = pygame.font.Font(None, 36)
                god_mode_text = god_mode_font.render("The Force is strong with this one...", True, YELLOW)
                # Apply 15-degree skew effect
                skewed_god_mode_text = self.create_skewed_message_text(god_mode_text, skew_factor=0.15)
                god_mode_rect = skewed_god_mode_text.get_rect(center=(self.current_width//2, message_y))
                draw_surface.blit(skewed_god_mode_text, god_mode_rect)
                message_y += 30
            elif self.show_ludicrous_speed:
                ludicrous_font = pygame.font.Font(None, 36)
                ludicrous_text = ludicrous_font.render("Ludicrous speed... Go!", True, YELLOW)
                # Apply 15-degree skew effect
                skewed_ludicrous_text = self.create_skewed_message_text(ludicrous_text, skew_factor=0.15)
                ludicrous_rect = skewed_ludicrous_text.get_rect(center=(self.current_width//2, message_y))
                draw_surface.blit(skewed_ludicrous_text, ludicrous_rect)
                message_y += 30
            elif self.show_plaid:
                plaid_font = pygame.font.Font(None, 36)
                plaid_text = plaid_font.render("You've gone... plaid!", True, YELLOW)
                # Apply 15-degree skew effect
                skewed_plaid_text = self.create_skewed_message_text(plaid_text, skew_factor=0.15)
                plaid_rect = skewed_plaid_text.get_rect(center=(self.current_width//2, message_y))
                draw_surface.blit(skewed_plaid_text, plaid_rect)
                message_y += 30
            
            # Score milestone messages with priority (1M > 500k > 250k)
            if self.show_1m_message:
                message_1m_font = pygame.font.Font(None, 36)
                message_1m_text = message_1m_font.render("~ one million points ~", True, YELLOW)
                # Apply 15-degree skew effect
                skewed_1m_text = self.create_skewed_message_text(message_1m_text, skew_factor=0.15)
                message_1m_rect = skewed_1m_text.get_rect(center=(self.current_width//2, message_y))
                draw_surface.blit(skewed_1m_text, message_1m_rect)
                message_y += 30
            elif self.show_500k_message:
                message_500k_font = pygame.font.Font(None, 36)
                message_500k_text = message_500k_font.render("500k Ability Double Charged!", True, YELLOW)
                # Apply 15-degree skew effect
                skewed_500k_text = self.create_skewed_message_text(message_500k_text, skew_factor=0.15)
                message_500k_rect = skewed_500k_text.get_rect(center=(self.current_width//2, message_y))
                draw_surface.blit(skewed_500k_text, message_500k_rect)
                message_y += 30
            elif self.show_250k_message:
                message_250k_font = pygame.font.Font(None, 36)
                message_250k_text = message_250k_font.render("250k Shields Recharged!", True, YELLOW)
                # Apply 15-degree skew effect
                skewed_250k_text = self.create_skewed_message_text(message_250k_text, skew_factor=0.15)
                message_250k_rect = skewed_250k_text.get_rect(center=(self.current_width//2, message_y))
                draw_surface.blit(skewed_250k_text, message_250k_rect)
                message_y += 30
            
            # Life indicators - pulsing ship images (centered below score)
            self.draw_life_indicators(draw_surface, 90, dt)  # Position below score at y=60
            
            # Speed display - below life indicators (HIDDEN)
            # self.draw_speed_display(draw_surface, 120, dt)  # Position below life indicators at y=120
            
            # Draw level flash effect
            if self.level_flash_timer > 0:
                self.draw_level_flash(draw_surface)
            
            
        
        
            
        
        
        if self.game_state == "waiting":
            # Draw starfield background with title ship velocity
            ship_velocity = self.title_ship.velocity if self.title_ship else Vector2D(0, 0)
            self.star_field.draw(draw_surface, ship_velocity)
            
            # Title - bright yellow outline with gradient fill (yellow bottom to black top)
            title_font = pygame.font.Font(None, 144)
            title_font.set_bold(True)
            
            # Create title with outline and gradient effect
            gradient_title = self.create_gradient_title_text("CHUCKSTAROIDS", title_font)
            
            # Apply skewed effect - narrower at top, wider at bottom
            skewed_title = self.create_skewed_title_text(gradient_title, pinch_factor=0.75)
            
            # Scale animation: 0 to 150% then back to 100% over 3 seconds
            # Phase 1: 0-150% curved (quick upward scaling) over first 2 seconds
            # Phase 2: 150%-100% slow linear scaling over last 1 second
            total_duration = 3.0
            phase1_duration = 2.0  # 0-150% curved (quick upward)
            phase2_duration = 1.0  # 150%-100% slow linear
            
            if self.title_start_timer <= phase1_duration:
                # Phase 1: Curved scaling from 0% to 150% (quick upward scaling)
                phase1_progress = self.title_start_timer / phase1_duration  # 0 to 1
                # Quadratic ease-in curve: starts slow, accelerates quickly
                curved_progress = phase1_progress * phase1_progress  # t^2 for quick upward scaling
                scale_factor = curved_progress * 1.5  # 0 to 1.5 (150%)
            elif self.title_start_timer <= total_duration:
                # Phase 2: Slow scaling down from 150% to 100%
                phase2_progress = (self.title_start_timer - phase1_duration) / phase2_duration  # 0 to 1
                # Slow linear scaling down: gentle, slow descent
                scale_factor = 1.5 - 0.5 * phase2_progress  # 1.5 to 1.0 (slow linear)
            else:
                # After animation completes, stay at 100%
                scale_factor = 1.0
            
            if scale_factor > 0:
                # Scale the title
                scaled_width = int(skewed_title.get_width() * scale_factor)
                scaled_height = int(skewed_title.get_height() * scale_factor)
                if scaled_width > 0 and scaled_height > 0:
                    scaled_title = pygame.transform.scale(skewed_title, (scaled_width, scaled_height))
                    
                    # Center the scaled title
                    title_rect = scaled_title.get_rect(center=(self.current_width//2, self.current_height//2 - 100))
                    draw_surface.blit(scaled_title, title_rect)
            
            # Add two blank lines above subtitle
            blank_font = pygame.font.Font(None, 32)
            blank_text1 = blank_font.render("", True, WHITE)
            blank_text2 = blank_font.render("", True, WHITE)
            blank_rect1 = blank_text1.get_rect(center=(self.current_width//2, self.current_height//2 - 80))
            blank_rect2 = blank_text2.get_rect(center=(self.current_width//2, self.current_height//2 - 60))
            draw_surface.blit(blank_text1, blank_rect1)
            draw_surface.blit(blank_text2, blank_rect2)
            
            # Subtitle with fade-in effect (200% bigger) - moved down 50px
            subtitle_font = pygame.font.Font(None, 64)
            subtitle_font.set_bold(True)
            subtitle_text = subtitle_font.render("PRESS SPACE TO START", True, WHITE)
            subtitle_rect = subtitle_text.get_rect(center=(self.current_width//2, self.current_height//2 + 30))
            
            # Apply fade-in effect to subtitle
            if self.press_space_alpha < 255:
                subtitle_surface = subtitle_text.copy()
                subtitle_surface.set_alpha(int(self.press_space_alpha))
                draw_surface.blit(subtitle_surface, subtitle_rect)
            else:
                draw_surface.blit(subtitle_text, subtitle_rect)
            
            # Top Score - displayed above controls with fade-in effect
            top_score_font = pygame.font.Font(None, 28)
            
            # Get local top score
            local_top_score = game_logger.get_top_local_score()
            local_score_display = f"{local_top_score:,}" if local_top_score is not None else "-"
            
            # Get global top score
            global_top_score = None
            if self.scoreboard_available and self.scoreboard:
                global_top_score = self.scoreboard.get_top_score()
            
            # Create the top score text based on availability
            if global_top_score is not None:
                # Both scores available - show full format
                top_score_text = top_score_font.render(f"TOP SCORES:  Worldwide #1: {global_top_score:,}  -  Local: {local_score_display}", True, (255, 215, 0))  # Gold color
            else:
                # No global score available - show simple format
                top_score_text = top_score_font.render(f"TOP SCORE: {local_score_display}", True, (255, 215, 0))  # Gold color
            top_score_rect = top_score_text.get_rect(center=(self.current_width//2, self.current_height//2 + 170))
            
            # Apply fade-in effect to top score (same timing as controls)
            if self.controls_alpha < 255:
                top_score_surface = top_score_text.copy()
                top_score_surface.set_alpha(int(self.controls_alpha))
                draw_surface.blit(top_score_surface, top_score_rect)
            else:
                draw_surface.blit(top_score_text, top_score_rect)
            
            # Controls - centered, smaller font (22pt), moved 200px lower with fade-in effect
            controls_font = pygame.font.Font(None, 22)
            controls_text1 = controls_font.render("MOVE - w a s d + arrow keys  .  SHOOT - space  .  BLAST - q e b  .  BRAKE - ctrl", True, (200, 200, 200))
            controls_text2 = controls_font.render("SCORES - tab  .  RESTART - r  .  PAUSE - p  .  DATA - f1  .  EXIT - esc", True, (200, 200, 200))
            controls_rect1 = controls_text1.get_rect(center=(self.current_width//2, self.current_height//2 + 200))
            controls_rect2 = controls_text2.get_rect(center=(self.current_width//2, self.current_height//2 + 220))
            
            # Apply fade-in effect to controls
            if self.controls_alpha < 255:
                controls_surface1 = controls_text1.copy()
                controls_surface2 = controls_text2.copy()
                controls_surface1.set_alpha(int(self.controls_alpha))
                controls_surface2.set_alpha(int(self.controls_alpha))
                draw_surface.blit(controls_surface1, controls_rect1)
                draw_surface.blit(controls_surface2, controls_rect2)
            else:
                draw_surface.blit(controls_text1, controls_rect1)
                draw_surface.blit(controls_text2, controls_rect2)
            
            # Draw explosion particles on title screen
            self.explosions.draw(draw_surface)
            
            
            # Draw virtual ship as size 3 asteroid when moving
            if self.title_ship:
                # Apply screen shake offset to ship position
                original_x = self.title_ship.position.x
                original_y = self.title_ship.position.y
                self.title_ship.position.x += shake_x
                self.title_ship.position.y += shake_y
                
                # Draw ship as size 3 asteroid when moving
                self.draw_ship_as_asteroid(draw_surface, self.title_ship)
                
                # Restore original position
                self.title_ship.position.x = original_x
                self.title_ship.position.y = original_y
            
            # Draw UFOs and UFO bullets (like level 10, no player elements)
            for ufo in self.ufos:
                if ufo.active:
                    self.draw_title_screen_ufo(draw_surface, ufo)
            
            # Draw title screen bosses
            for boss in self.bosses:
                if boss.active:
                    # Apply screen shake offset to boss position
                    original_x = boss.position.x
                    original_y = boss.position.y
                    boss.position.x += shake_x
                    boss.position.y += shake_y
                    boss.draw(draw_surface, self.current_width, self.current_height)
                    # Restore original position
                    boss.position.x = original_x
                    boss.position.y = original_y
            
            for bullet in self.ufo_bullets:
                if bullet.active:
                    bullet.draw(draw_surface)
            
            # Draw boss weapon bullets on title screen
            for boss in self.bosses:
                if boss.active:
                    for bullet in boss.weapon_bullets:
                        if bullet.active:
                            bullet.draw(draw_surface)
            
            # Draw scoreboard if showing
            if self.show_scoreboard:
                self.draw_scoreboard(draw_surface)
            
            
            # Draw scoreboard instructions
            if self.show_scoreboard:
                inst_font = pygame.font.Font(None, 20)
                inst_text = inst_font.render("C = Refresh  |  TAB = Close", True, (200, 200, 200))
                inst_rect = inst_text.get_rect(center=(self.current_width//2, self.current_height - 10))
                draw_surface.blit(inst_text, inst_rect)
        elif self.game_state == "death_delay":
            # During death delay, continue showing the game world normally
            # Draw star field with no ship velocity since ship is destroyed
            self.star_field.draw(draw_surface, Vector2D(0, 0))
            
            # Draw asteroids
            for asteroid in self.asteroids:
                if asteroid.active:
                    asteroid.draw(draw_surface)
            
            # Draw UFOs
            for ufo in self.ufos:
                if ufo.active:
                    ufo.draw(draw_surface)
            
            # Draw bullets
            for bullet in self.bullets:
                if bullet.active:
                    try:
                        bullet.draw(draw_surface)
                    except Exception as e:
                        pass
            
            # Draw UFO bullets
            for bullet in self.ufo_bullets:
                if bullet.active:
                    bullet.draw(draw_surface)
            
            # Draw boss weapon bullets
            for boss in self.bosses:
                if boss.active:
                    for bullet in boss.weapon_bullets:
                        if bullet.active:
                            bullet.draw(draw_surface)
            
            # Draw explosion particles
            self.explosions.draw(draw_surface)
            
            
            # Draw UI elements (score, lives, etc.) - copy from main game loop
            # Level - centered with 75% opacity (above score)
            level_text = f"LEVEL {self.level}"
            level_surface = font.render(level_text, True, WHITE)
            level_surface.set_alpha(int(255 * 0.5))  # 50% opacity
            level_rect = level_surface.get_rect(center=(self.current_width//2, 30))
            draw_surface.blit(level_surface, level_rect)
            
            # Score - centered with pulse effect (below level)
            self.draw_score_with_pulse(draw_surface, dt)
            
            # Life indicators - pulsing ship images (centered below score)
            self.draw_life_indicators(draw_surface, 90, dt)  # Position below score at y=60
        elif self.game_state == "game_over":
            # Always show game over text, but fade it in after star explosion
            # Create extra large font for game over text (200% increase = 3x size)
            game_over_font = pygame.font.Font(None, 108)  # 36 * 3 = 108
            game_over_text = game_over_font.render("GAME OVER", True, YELLOW)
            restart_text = font.render("Press R to restart", True, WHITE)
            
            # Create large font for score and level display
            large_font = pygame.font.Font(None, 32)
            large_font.set_bold(True)
            
            # Create score and level text
            score_text = large_font.render(f"SCORE: {self.score}", True, RED)
            level_text = large_font.render(f"LEVEL {self.level}", True, RED)
            
            # Calculate positions
            score_y = int(self.current_height * 0.25)
            level_y = score_y + 40  # 40 pixels below score
            game_over_y = level_y + 120  # 3 lines under level (40 * 3 = 120)
            restart_y = game_over_y + 120  # 3 lines under game over (40 * 3 = 120)
            
            # Apply fade-in effect to game over text (starts after star explosion)
            if not self.star_explosion_active and self.game_over_alpha < 255:
                game_over_surface = game_over_text.copy()
                restart_surface = restart_text.copy()
                score_surface = score_text.copy()
                level_surface = level_text.copy()
                game_over_surface.set_alpha(int(self.game_over_alpha))
                restart_surface.set_alpha(int(self.game_over_alpha))
                score_surface.set_alpha(int(self.game_over_alpha))
                level_surface.set_alpha(int(self.game_over_alpha))
                draw_surface.blit(score_surface, (self.current_width//2 - score_text.get_width()//2, score_y))
                draw_surface.blit(level_surface, (self.current_width//2 - level_text.get_width()//2, level_y))
                draw_surface.blit(game_over_surface, (self.current_width//2 - game_over_text.get_width()//2, game_over_y))
                draw_surface.blit(restart_surface, (self.current_width//2 - restart_text.get_width()//2, restart_y))
            elif not self.star_explosion_active:
                # Full opacity after fade-in
                draw_surface.blit(score_text, (self.current_width//2 - score_text.get_width()//2, score_y))
                draw_surface.blit(level_text, (self.current_width//2 - level_text.get_width()//2, level_y))
                draw_surface.blit(game_over_text, (self.current_width//2 - game_over_text.get_width()//2, game_over_y))
                draw_surface.blit(restart_text, (self.current_width//2 - restart_text.get_width()//2, restart_y))
            
            # Draw scoreboard if showing
            if self.show_scoreboard:
                self.draw_scoreboard(draw_surface)
            
            # Draw name input if active
            if self.name_input_active:
                self.draw_name_input(draw_surface)
            
            # Draw controls text at bottom
            scoreboard_font = pygame.font.Font(None, 24)
            
            # Show different instructions based on state
            if self.name_input_active:
                # Show name input instructions
                scoreboard_text = scoreboard_font.render("Enter your name for the leaderboard!", True, (255, 255, 0))
                scoreboard_rect = scoreboard_text.get_rect(center=(self.current_width//2, self.current_height - 30))
                draw_surface.blit(scoreboard_text, scoreboard_rect)
                
                inst_font = pygame.font.Font(None, 20)
                inst_text = inst_font.render("Type your name and press ENTER to submit, ESC to cancel", True, (200, 200, 200))
                inst_rect = inst_text.get_rect(center=(self.current_width//2, self.current_height - 10))
                draw_surface.blit(inst_text, inst_rect)
            else:
                # Show normal controls (no scoreboard text needed - it's now in controls line)
                pass
            
            # Draw scoreboard instructions
            if self.show_scoreboard:
                inst_font = pygame.font.Font(None, 20)
                inst_text = inst_font.render("C = Refresh  |  TAB = Close", True, (200, 200, 200))
                inst_rect = inst_text.get_rect(center=(self.current_width//2, self.current_height - 10))
                draw_surface.blit(inst_text, inst_rect)
            else:
                inst_font = pygame.font.Font(None, 20)
                inst_text = inst_font.render("TAB = View Leaderboard  |  R = Restart  |  ESC = Exit", True, (200, 200, 200))
                inst_rect = inst_text.get_rect(center=(self.current_width//2, self.current_height - 10))
                draw_surface.blit(inst_text, inst_rect)
        elif self.game_state == "paused":
            pause_text = font.render("PAUSED", True, YELLOW)
            resume_text = font.render("Press P to resume", True, WHITE)
            draw_surface.blit(pause_text, (self.current_width//2 - 60, self.current_height//2 - 50))
            draw_surface.blit(resume_text, (self.current_width//2 - 120, self.current_height//2))
        
        
        # Draw debug displays if debug mode is enabled
        if self.debug_mode:
            self.draw_debug_speed_display(draw_surface)
            self.draw_debug_rate_of_fire_display(draw_surface)
            self.draw_debug_controls_display(draw_surface)
            self.draw_debug_fps_display(draw_surface)
            self.draw_debug_memory_display(draw_surface)
            self.draw_debug_objects_display(draw_surface)
            self.draw_debug_performance_display(draw_surface)
            self.draw_debug_ai_display(draw_surface)
        
        # Draw progress bars (only during gameplay) - TOP LAYER
        if self.game_state == "playing":
            self.draw_progress_bars(draw_surface)
        
        # Apply screen shake by blitting with offset
        if self.screen_shake_intensity > 0:
            self.screen.blit(draw_surface, (shake_x, shake_y))
        else:
            self.screen.blit(draw_surface, (0, 0))
        
        pygame.display.flip()
    
    
    def restart_game(self, log_current_score=False):
        # Log current score before restarting if requested
        if log_current_score and self.score > 0:
            game_logger.log_game_over(self.score, self.level)
        
        # Start star explosion effect on restart
        self.star_explosion_active = True
        self.star_field.start_explosion(self.current_width, self.current_height)
        
        # Clear any pressed keys from previous game state
        self.keys_pressed.clear()
        
        # Reset game state
        self.score = 0
        self.lives = 3
        self.level = 1
        self.game_state = "playing"
        self.game_start_timer = 0.0  # Reset shooting prevention timer
        
        # Note: high score file clearing is handled elsewhere to avoid losing scores
        
        # Log game start
        game_logger.log_game_start()
        
        # Reset score milestone tracking
        self.last_milestone_250k = 0
        self.last_milestone_500k = 0
        self.last_milestone_1000k = 0
        
        # Reset multiplier system
        self.asteroids_destroyed_this_level = 0
        self.ufos_killed_this_level = 0
        self.last_multiplier = 1.0
        self.multiplier_pulse_timer = 0.0
        
        # Reset decay system
        self.multiplier_decay_timer = 0.0
        self.is_decaying = False
        self.multiplier_decay_start_value = 1.0
        
        # Reset first UFO counter
        self.first_ufos_spawned_level_1 = 0
        
        # Clear all object lists
        self.bullets.clear()
        self.asteroids.clear()
        self.ufos.clear()
        self.ufo_bullets.clear()
        self.bosses.clear()
        
        # Reset boss spawning
        self.boss_spawned_this_level = False
        self.boss_spawn_timer = 0.0
        self.boss_spawn_delay = 0.0
        
        # Clear explosion particles
        if hasattr(self, 'explosions'):
            self.explosions.particles.clear()
        
        
        # Clear starfield fade-in data
        if hasattr(self, 'star_field'):
            self.star_field.fade_in_stars.clear()
        
        # Reset timers
        self.score_pulse_timer = 0.0
        self.score_pulse_duration = 0.0
        self.star_explosion_timer = 0.0
        self.level_flash_timer = 0.0
        
        # Reset animation timers
        self.title_start_timer = 0.0
        self.title_boss_spawn_timer = 0.0
        self.press_space_alpha = 0
        self.game_over_alpha = 0
        
        self.init_ship()
        self.spawn_asteroids()
        # Reset spinning trick tracking
        self.show_spinning_trick = False
        self.spinning_trick_timer = 0.0
        
        # Reset interstellar tracking
        self.show_interstellar = False
        self.interstellar_timer = 0.0
        
        # Reset god mode message tracking
        self.show_god_mode = False
        self.god_mode_timer = 0.0
        
        # Reset ludicrous speed message tracking
        self.show_ludicrous_speed = False
        self.ludicrous_speed_timer = 0.0
        self.ludicrous_speed_shown = False
        
        # Reset plaid message tracking
        self.show_plaid = False
        self.plaid_timer = 0.0
        self.plaid_shown = False
        
        # Reset score milestone message tracking
        self.show_250k_message = False
        self.show_500k_message = False
        self.show_1m_message = False
        self.message_250k_timer = 0.0
        self.message_500k_timer = 0.0
        self.message_1m_timer = 0.0
        
        # Reset ship achievement flags for new game
        if self.ship:
            self.ship.spinning_trick_shown = False
            self.ship.interstellar_shown = False
            self.ship.interstellar_threshold_crossed = False
            self.ship.total_rotations = 0.0
            self.ship.interstellar_timer = 0.0
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
    
    def on_score_submitted(self, success, message):
        """Callback for when score is submitted"""
        try:
            if success:
                print(f"Score submitted successfully: {message}")
                # Refresh scoreboard in background
                self.load_scoreboard_background()
            else:
                print(f"Score submission failed: {message}")
        except Exception as e:
            # print(f"[SCOREBOARD DEBUG] Error in score submission callback: {e}")
            pass
    
    def on_scores_loaded(self, scores):
        """Callback for when scores are loaded in background"""
        try:
            if scores is not None:
                self.scoreboard_scores = scores
                # print(f"[SCOREBOARD DEBUG] Background scores loaded: {len(scores)} scores")
            else:
                self.scoreboard_scores = []
                # print(f"[SCOREBOARD DEBUG] Background scores loaded: empty")
        except Exception as e:
            # print(f"[SCOREBOARD DEBUG] Error in scores loaded callback: {e}")
            self.scoreboard_scores = []
        finally:
            self.scoreboard_loading = False
    
    def load_scoreboard_background(self):
        """Load scoreboard scores in background without blocking"""
        if not self.scoreboard_available or not self.scoreboard:
            return
        if not self.scoreboard_loading:
            self.scoreboard_loading = True
            self.scoreboard.get_scores_async(self.on_scores_loaded)
            # print(f"[SCOREBOARD DEBUG] Started background scoreboard loading")
    
    def draw_debug_speed_display(self, surface):
        """Draw player speed and world speed in debug view, centered at bottom in white"""
        if not self.ship:
            return
        
        # Get current speeds
        player_speed = self.ship.velocity.magnitude()
        world_speed = self.time_dilation_factor * 100  # Convert to percentage
        
        # Format speed text with god mode status
        god_mode_text = " | GOD MODE" if self.god_mode else ""
        speed_text = f"Player Speed: {player_speed:.0f} | World Speed: {world_speed:.1f}%{god_mode_text}"
        
        # Create font
        font = pygame.font.Font(None, 24)
        
        # Render text in white
        text_surface = font.render(speed_text, True, WHITE)
        
        # Center the text horizontally at the bottom
        text_rect = text_surface.get_rect(center=(self.current_width // 2, self.current_height - 20))
        
        # Draw the text
        surface.blit(text_surface, text_rect)
    
    def draw_debug_rate_of_fire_display(self, surface):
        """Draw player rate of fire debug information in debug view"""
        if not self.ship:
            return
        
        # Get current rate of fire information
        current_interval = self.ship.shoot_interval
        asteroid_bonus = self.ship.asteroid_interval_bonus
        shots_per_second = 1.0 / current_interval if current_interval > 0 else 0
        
        # Format rate of fire text (simplified)
        rof_text = f"ROF: {shots_per_second:.1f} shots/sec"
        bonus_text = f"Asteroid Bonus: -{asteroid_bonus:.4f}s"
        
        # Create font
        font = pygame.font.Font(None, 20)
        
        # Render text in cyan
        rof_surface = font.render(rof_text, True, (0, 255, 255))
        bonus_surface = font.render(bonus_text, True, (0, 255, 255))
        
        # Position text at top-left
        start_x = 10
        start_y = 10
        line_height = 25
        
        # Draw the text
        surface.blit(rof_surface, (start_x, start_y))
        surface.blit(bonus_surface, (start_x, start_y + line_height))
    
    def draw_debug_controls_display(self, surface):
        """Draw debug controls information in debug view"""
        if not hasattr(self, 'debug_mode') or not self.debug_mode:
            return
        
        # Create debug font
        debug_font = pygame.font.Font(None, 20)
        
        # Debug controls text
        controls_text = [
            "DEBUG CONTROLS:",
            "F1 - Toggle Debug Mode",
            "G - Toggle God Mode",
            "1 - Add 100,000 points",
            "2 - Add 250,000 points", 
            "3 - Add 500,000 points",
            "4 - Spawn Boss",
            "5 - Advance Level"
        ]
        
        # Draw background on right side
        y_offset = self.current_height - 200  # Position at bottom
        for i, text in enumerate(controls_text):
            text_surface = debug_font.render(text, True, (255, 255, 255))
            # Semi-transparent background
            bg_rect = text_surface.get_rect()
            bg_rect.x = self.current_width - 200  # Position on right side
            bg_rect.y = y_offset + i * 20
            bg_rect.width += 10
            bg_rect.height += 2
            
            # Draw semi-transparent background
            bg_surface = pygame.Surface((bg_rect.width, bg_rect.height))
            bg_surface.set_alpha(128)
            bg_surface.fill((0, 0, 0))
            surface.blit(bg_surface, (bg_rect.x, bg_rect.y))
            
            # Draw text
            surface.blit(text_surface, (bg_rect.x + 5, bg_rect.y + 1))
    
    def draw_debug_cache_stats(self, surface):
        """Draw image cache performance statistics in debug view"""
        if not hasattr(self, 'debug_mode') or not self.debug_mode:
            return
        
        # Get cache statistics
        stats = image_cache.get_cache_stats()
        
        # Create debug font
        debug_font = pygame.font.Font(None, 24)
        
        # Cache statistics text
        cache_text = [
            f"Image Cache Stats:",
            f"Hits: {stats['hits']}",
            f"Misses: {stats['misses']}",
            f"Hit Rate: {stats['hit_rate']:.1f}%",
            f"Total Entries: {stats['total_entries']}"
        ]
        
        # Draw background
        y_offset = 50
        for i, text in enumerate(cache_text):
            text_surface = debug_font.render(text, True, (255, 255, 255))
            # Semi-transparent background
            bg_rect = text_surface.get_rect()
            bg_rect.x = 10
            bg_rect.y = y_offset + i * 25
            bg_rect.width += 10
            bg_rect.height += 5
            pygame.draw.rect(surface, (0, 0, 0, 128), bg_rect)
            surface.blit(text_surface, (15, y_offset + i * 25))
    
    def draw_debug_fps_display(self, surface):
        """Draw FPS information in debug view"""
        if not hasattr(self, 'debug_mode') or not self.debug_mode:
            return
        
        # Create debug font (200% bigger - from 20 to 60)
        debug_font = pygame.font.Font(None, 60)
        
        # FPS information text
        fps_text = f"FPS: {self.current_fps:.1f}"
        
        # Render main FPS text in green
        text_surface = debug_font.render(fps_text, True, (0, 255, 0))
        
        # Position at top-right corner
        text_rect = text_surface.get_rect()
        text_rect.x = self.current_width - text_rect.width - 10
        text_rect.y = 10
        
        # Draw semi-transparent background for main FPS
        bg_rect = text_rect.copy()
        bg_rect.width += 20
        bg_rect.height += 10
        bg_rect.x -= 10
        bg_rect.y -= 5
        pygame.draw.rect(surface, (0, 0, 0, 128), bg_rect)
        
        # Draw main FPS text
        surface.blit(text_surface, (text_rect.x, text_rect.y))
    
    def clear_image_cache(self):
        """Clear the image cache to free memory"""
        image_cache.clear_cache()
        # Image cache cleared (console output removed)
    
    def draw_debug_memory_display(self, surface):
        """Draw memory usage debug information"""
        if not hasattr(self, 'debug_mode') or not self.debug_mode:
            return
        
        import psutil
        import os
        
        # Get memory usage
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024  # Convert to MB
        
        # Count game objects
        asteroid_count = len([a for a in self.asteroids if a.active])
        ufo_count = len([u for u in self.ufos if u.active])
        bullet_count = len([b for b in self.bullets if b.active])
        ufo_bullet_count = len([b for b in self.ufo_bullets if b.active])
        boss_bullet_count = sum(len(b.weapon_bullets) for b in self.bosses if b.active)
        particle_count = len(self.explosions.particles) if hasattr(self, 'explosions') else 0
        
        # Calculate estimated memory usage by object type
        asteroid_memory = asteroid_count * 0.1  # Rough estimate in MB
        bullet_memory = (bullet_count + ufo_bullet_count + boss_bullet_count) * 0.01
        particle_memory = particle_count * 0.001
        
        # Create debug font
        debug_font = pygame.font.Font(None, 20)
        
        # Memory information text
        memory_text = [
            f"Memory Usage: {memory_mb:.1f} MB",
            f"Asteroids: {asteroid_count} ({asteroid_memory:.1f} MB)",
            f"UFOs: {ufo_count}",
            f"Bullets: {bullet_count + ufo_bullet_count + boss_bullet_count} ({bullet_memory:.1f} MB)",
            f"Particles: {particle_count} ({particle_memory:.1f} MB)"
        ]
        
        # Draw background and text
        y_offset = 100
        for i, text in enumerate(memory_text):
            text_surface = debug_font.render(text, True, (255, 255, 255))
            # Semi-transparent background
            bg_rect = text_surface.get_rect()
            bg_rect.x = 10
            bg_rect.y = y_offset + i * 22
            bg_rect.width += 10
            bg_rect.height += 2
            pygame.draw.rect(surface, (0, 0, 0, 128), bg_rect)
            surface.blit(text_surface, (15, y_offset + i * 22))
    
    def draw_debug_objects_display(self, surface):
        """Draw active object counts debug information"""
        if not hasattr(self, 'debug_mode') or not self.debug_mode:
            return
        
        # Count active objects
        asteroid_count = len([a for a in self.asteroids if a.active])
        ufo_count = len([u for u in self.ufos if u.active])
        bullet_count = len([b for b in self.bullets if b.active])
        ufo_bullet_count = len([b for b in self.ufo_bullets if b.active])
        boss_count = len([b for b in self.bosses if b.active])
        boss_bullet_count = sum(len(b.weapon_bullets) for b in self.bosses if b.active)
        particle_count = len(self.explosions.particles) if hasattr(self, 'explosions') else 0
        
        # Create debug font
        debug_font = pygame.font.Font(None, 20)
        
        # Object counts text
        objects_text = [
            "Active Objects:",
            f"Asteroids: {asteroid_count}",
            f"UFOs: {ufo_count}",
            f"Bosses: {boss_count}",
            f"Player Bullets: {bullet_count}",
            f"UFO Bullets: {ufo_bullet_count}",
            f"Boss Bullets: {boss_bullet_count}",
            f"Particles: {particle_count}"
        ]
        
        # Draw background and text
        y_offset = 250
        for i, text in enumerate(objects_text):
            text_surface = debug_font.render(text, True, (255, 255, 255))
            # Semi-transparent background
            bg_rect = text_surface.get_rect()
            bg_rect.x = 10
            bg_rect.y = y_offset + i * 22
            bg_rect.width += 10
            bg_rect.height += 2
            pygame.draw.rect(surface, (0, 0, 0, 128), bg_rect)
            surface.blit(text_surface, (15, y_offset + i * 22))
    
    def draw_debug_performance_display(self, surface):
        """Draw performance metrics debug information"""
        if not hasattr(self, 'debug_mode') or not self.debug_mode:
            return
        
        # Get performance metrics (these would need to be tracked in the main loop)
        frame_time = 1.0 / self.current_fps if self.current_fps > 0 else 0
        render_time = frame_time * 0.3  # Rough estimate
        collision_time = frame_time * 0.1  # Rough estimate
        collision_checks = len(self.asteroids) * len(self.bullets) + len(self.ufos) * len(self.bullets)  # Rough estimate
        particle_performance = len(self.explosions.particles) if hasattr(self, 'explosions') else 0
        
        # Create debug font
        debug_font = pygame.font.Font(None, 20)
        
        # Performance metrics text
        performance_text = [
            "Performance Metrics:",
            f"Frame Time: {frame_time*1000:.2f} ms",
            f"Render Time: {render_time*1000:.2f} ms",
            f"Collision Time: {collision_time*1000:.2f} ms",
            f"Collision Checks: {collision_checks}",
            f"Particle Count: {particle_performance}"
        ]
        
        # Draw background and text
        y_offset = 450
        for i, text in enumerate(performance_text):
            text_surface = debug_font.render(text, True, (255, 255, 255))
            # Semi-transparent background
            bg_rect = text_surface.get_rect()
            bg_rect.x = 10
            bg_rect.y = y_offset + i * 22
            bg_rect.width += 10
            bg_rect.height += 2
            pygame.draw.rect(surface, (0, 0, 0, 128), bg_rect)
            surface.blit(text_surface, (15, y_offset + i * 22))
    
    def draw_debug_ai_display(self, surface):
        """Draw AI debug information for UFOs"""
        if not hasattr(self, 'debug_mode') or not self.debug_mode:
            return
        
        # Create debug font
        debug_font = pygame.font.Font(None, 20)
        
        # AI information text
        ai_text = ["UFO AI Debug:"]
        
        # Add info for each active UFO
        for i, ufo in enumerate(self.ufos[:3]):  # Show max 3 UFOs
            if ufo.active and hasattr(ufo, 'current_state'):
                ai_text.extend([
                    f"UFO {i+1}: {ufo.current_state}",
                    f"  Threat: {getattr(ufo, 'threat_level', 0):.2f}",
                    f"  Opportunity: {getattr(ufo, 'opportunity_level', 0):.2f}",
                    f"  Target: {getattr(ufo, 'has_target', False)}"
                ])
        
        # Draw background and text
        y_offset = 600
        for i, text in enumerate(ai_text):
            text_surface = debug_font.render(text, True, (255, 255, 255))
            # Semi-transparent background
            bg_rect = text_surface.get_rect()
            bg_rect.x = 10
            bg_rect.y = y_offset + i * 22
            bg_rect.width += 10
            bg_rect.height += 2
            pygame.draw.rect(surface, (0, 0, 0, 128), bg_rect)
            surface.blit(text_surface, (15, y_offset + i * 22))

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
                # Draw hitbox at offset position (dim white)
                hitbox_center = asteroid.get_hitbox_center()
                self.draw_wrapped_hitbox(surface, hitbox_center, asteroid.radius, (200, 200, 200))
                # Draw asteroid size text
                font = pygame.font.Font(None, 20)
                size_text = f"Size {asteroid.size}"
                text_surface = font.render(size_text, True, (200, 200, 200))
                text_rect = text_surface.get_rect(center=(int(asteroid.position.x), int(asteroid.position.y) - asteroid.radius - 15))
                surface.blit(text_surface, text_rect)
        
        # Draw UFO hitboxes with wrapping
        for ufo in self.ufos:
            if ufo.active:
                self.draw_wrapped_hitbox(surface, ufo.get_hitbox_center(), ufo.radius, (255, 255, 0))
        
        # Draw boss hitboxes (no wrapping - bosses don't wrap around screen)
        for boss in self.bosses:
            if boss.active:
                # Draw polygon hitbox
                boss.draw_hitbox(surface)
        
        # Draw bullet hitboxes with wrapping
        for bullet in self.bullets:
            if bullet.active:
                self.draw_wrapped_hitbox(surface, bullet.position, bullet.radius, (0, 0, 255))
        
        for bullet in self.ufo_bullets:
            if bullet.active:
                self.draw_wrapped_hitbox(surface, bullet.position, bullet.radius, (255, 0, 255))
        
        # Draw boss weapon bullet hitboxes with wrapping
        for boss in self.bosses:
            if boss.active:
                for bullet in boss.weapon_bullets:
                    if bullet.active:
                        self.draw_wrapped_hitbox(surface, bullet.position, bullet.radius, (255, 165, 0))  # Orange color for boss shots
    
    def check_boss_spawn_collisions(self, boss):
        """Check for collisions when a boss spawns, including off-screen positions"""
        # Check collisions at the boss's spawn position and initial off-screen position
        positions_to_check = [
            (boss.position.x, boss.position.y)  # Current position
        ]
        
        # Also check the off-screen spawn position
        if boss.direction == "right":
            positions_to_check.append((-300, boss.position.y))
        else:  # left
            positions_to_check.append((self.current_width + 300, boss.position.y))
        
        for check_x, check_y in positions_to_check:
            # Temporarily set boss position for collision check
            original_x = boss.position.x
            original_y = boss.position.y
            boss.position.x = check_x
            boss.position.y = check_y
            
            # Check collision with all asteroids
            for asteroid in self.asteroids[:]:
                if not asteroid.active:
                    continue
                if boss.polygon_circle_collision_with_wrapping(asteroid.get_hitbox_center().x, asteroid.get_hitbox_center().y, asteroid.radius, self.current_width, self.current_height):
                    # Boss collision behavior based on asteroid size
                    if asteroid.size >= 3:  # Sizes 3-9: Split the asteroid
                        # Mark asteroid for destruction
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
                        # Size 3-4: No screen shake
                        
                        # Add explosion particles (with randomized lifetimes)
                        total_particles = int((20 + ((2 * asteroid.size) * 20)) * 0.5)  # 50% fewer particles
                        
                        # 40% Gray particles (75-125 range)
                        self.explosions.add_explosion(asteroid.position.x, asteroid.position.y, 
                                                    num_particles=int(total_particles * 0.40), 
                                                    color=(75, 75, 75), asteroid_size=asteroid.size)  # Gray
                        # 20% dark brown particles
                        self.explosions.add_explosion(asteroid.position.x, asteroid.position.y, 
                                                    num_particles=int(total_particles * 0.20), 
                                                    color=(34, 9, 1), asteroid_size=asteroid.size)  # Dark brown
                        # 15% red-brown particles
                        self.explosions.add_explosion(asteroid.position.x, asteroid.position.y, 
                                                    num_particles=int(total_particles * 0.15), 
                                                    color=(98, 23, 8), asteroid_size=asteroid.size)  # Red-brown
                        # 10% orange-red particles
                        self.explosions.add_explosion(asteroid.position.x, asteroid.position.y, 
                                                    num_particles=int(total_particles * 0.10), 
                                                    color=(148, 27, 12), asteroid_size=asteroid.size)  # Orange-red
                        # 8% orange particles
                        self.explosions.add_explosion(asteroid.position.x, asteroid.position.y, 
                                                    num_particles=int(total_particles * 0.08), 
                                                    color=(188, 57, 8), asteroid_size=asteroid.size)  # Orange
                        # 7% golden particles
                        self.explosions.add_explosion(asteroid.position.x, asteroid.position.y, 
                                                    num_particles=int(total_particles * 0.07), 
                                                    color=(246, 170, 28), asteroid_size=asteroid.size)  # Golden
                        
                        # Add score (size 3 = 33 points, size 4 = 44 points, etc.)
                        self.add_score(asteroid.size * 11, "asteroid collision")
                        
                        # Split asteroid with 2x boss velocity
                        boss_velocity_2x = Vector2D(boss.velocity.x * 2, boss.velocity.y * 2)
                        new_asteroids = asteroid.split(boss_velocity_2x, self.level)
                        self._add_asteroids_with_limit(new_asteroids)
                        
                        # Check if new asteroids are still colliding with boss and handle accordingly
                        self.check_new_asteroid_boss_collisions(new_asteroids, boss)
                    
                    # Sizes 1-2: Pass through boss unharmed (do nothing)
            
            # Restore original boss position
            boss.position.x = original_x
            boss.position.y = original_y
    
    def check_new_asteroid_boss_collisions(self, new_asteroids, boss):
        """Check if newly created asteroids are still colliding with the boss and handle accordingly"""
        for new_asteroid in new_asteroids[:]:  # Use slice to avoid modification during iteration
            if not new_asteroid.active:
                continue
                
            # Check if the new asteroid is still colliding with the boss
            if boss.polygon_circle_collision_with_wrapping(new_asteroid.get_hitbox_center().x, new_asteroid.get_hitbox_center().y, new_asteroid.radius, self.current_width, self.current_height):
                # Apply the same collision logic as the main game loop
                if new_asteroid.size >= 3:  # Sizes 3-9: Split the asteroid
                    # Mark asteroid for destruction
                    new_asteroid.active = False
                    
                    # Add screen shake for asteroid sizes 5+ only
                    if new_asteroid.size == 9:
                        self.trigger_screen_shake(12, 0.75)  # Large shake for size 9
                    elif new_asteroid.size == 8:
                        self.trigger_screen_shake(10, 0.5)  # Base shake for size 8
                    elif new_asteroid.size == 7:
                        self.trigger_screen_shake(8, 0.4)  # Medium shake for size 7
                    elif new_asteroid.size == 6:
                        self.trigger_screen_shake(6, 0.30)  # Medium shake for size 6
                    elif new_asteroid.size == 5:
                        self.trigger_screen_shake(5, 0.20)  # Small shake for size 5
                    # Size 3-4: No screen shake
                    
                    # Add explosion particles (with randomized lifetimes)
                    total_particles = int((20 + ((2 * new_asteroid.size) * 20)) * 0.5)  # 50% fewer particles
                    
                    # 40% Gray particles (75-125 range)
                    self.explosions.add_explosion(new_asteroid.position.x, new_asteroid.position.y, 
                                                num_particles=int(total_particles * 0.40), 
                                                color=(75, 75, 75), asteroid_size=new_asteroid.size)  # Gray
                    # 20% dark brown particles
                    self.explosions.add_explosion(new_asteroid.position.x, new_asteroid.position.y, 
                                                num_particles=int(total_particles * 0.20), 
                                                color=(34, 9, 1), asteroid_size=new_asteroid.size)  # Dark brown
                    # 15% red-brown particles
                    self.explosions.add_explosion(new_asteroid.position.x, new_asteroid.position.y, 
                                                num_particles=int(total_particles * 0.15), 
                                                color=(98, 23, 8), asteroid_size=new_asteroid.size)  # Red-brown
                    # 10% orange-red particles
                    self.explosions.add_explosion(new_asteroid.position.x, new_asteroid.position.y, 
                                                num_particles=int(total_particles * 0.10), 
                                                color=(148, 27, 12), asteroid_size=new_asteroid.size)  # Orange-red
                    # 8% orange particles
                    self.explosions.add_explosion(new_asteroid.position.x, new_asteroid.position.y, 
                                                num_particles=int(total_particles * 0.08), 
                                                color=(188, 57, 8), asteroid_size=new_asteroid.size)  # Orange
                    # 7% golden particles
                    self.explosions.add_explosion(new_asteroid.position.x, new_asteroid.position.y, 
                                                num_particles=int(total_particles * 0.07), 
                                                color=(246, 170, 28), asteroid_size=new_asteroid.size)  # Golden
                    
                    # Add score (size 3 = 33 points, size 4 = 44 points, etc.)
                    self.add_score(new_asteroid.size * 11, "asteroid shot")
                    
                    # Split asteroid with 2x boss velocity
                    boss_velocity_2x = Vector2D(boss.velocity.x * 2, boss.velocity.y * 2)
                    even_newer_asteroids = new_asteroid.split(boss_velocity_2x, self.level)
                    self._add_asteroids_with_limit(even_newer_asteroids)
                    
                    # Recursively check for further collisions
                    self.check_new_asteroid_boss_collisions(even_newer_asteroids, boss)
                
                # Sizes 1-2: Pass through boss unharmed (do nothing)
    
    def update_collision_fps(self, dt):
        """Update collision FPS based on object counts and gradually transition"""
        # Calculate object counts for thresholds
        asteroid_count = len([a for a in self.asteroids if a.active])
        ufo_bullet_count = len([b for b in self.ufo_bullets if b.active])
        bullet_asteroid_checks = len([b for b in self.bullets if b.active]) * asteroid_count
        ufo_bullet_asteroid_checks = ufo_bullet_count * asteroid_count
        
        # Update each collision type's FPS
        for collision_type, timer in self.collision_timers.items():
            normal_fps, reduced_fps, threshold = self.collision_fps_settings[collision_type]
            target_fps = normal_fps
            
            # Determine target FPS based on thresholds
            if threshold > 0:
                if collision_type == 'ship_asteroid' and asteroid_count > threshold:
                    target_fps = reduced_fps
                elif collision_type == 'ship_ufo_bullet' and ufo_bullet_count > threshold:
                    target_fps = reduced_fps
                elif collision_type == 'bullet_asteroid' and bullet_asteroid_checks > threshold:
                    target_fps = reduced_fps
                elif collision_type == 'ufo_bullet_asteroid' and ufo_bullet_asteroid_checks > threshold:
                    target_fps = reduced_fps
            
            # Gradually transition to target FPS
            current_fps = self.current_collision_fps[collision_type]
            if current_fps != target_fps:
                fps_diff = target_fps - current_fps
                fps_change = self.fps_transition_speed * dt
                
                if abs(fps_diff) <= fps_change:
                    self.current_collision_fps[collision_type] = target_fps
                else:
                    self.current_collision_fps[collision_type] += fps_change if fps_diff > 0 else -fps_change
    
    def should_check_collision(self, collision_type, dt):
        """Check if enough time has passed to run this collision type"""
        self.collision_timers[collision_type] += dt
        required_interval = 1.0 / self.current_collision_fps[collision_type]
        
        if self.collision_timers[collision_type] >= required_interval:
            self.collision_timers[collision_type] = 0.0
            return True
        return False
    
    def check_wrapped_collision(self, pos1, pos2, radius1, radius2):
        """Check collision between two objects with screen wrapping support"""
        width = self.current_width
        height = self.current_height
         
        # Use pre-allocated lists for better performance
        self.temp_positions_1.clear()
        self.temp_positions_2.clear()
        
        # Get wrapped positions using pre-allocated lists
        self.get_wrapped_positions_optimized(pos1, radius1, width, height, self.temp_positions_1)
        self.get_wrapped_positions_optimized(pos2, radius2, width, height, self.temp_positions_2)
        
        for p1 in self.temp_positions_1:
            for p2 in self.temp_positions_2:
                distance = math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)
                if distance < radius1 + radius2:
                    return True
        return False
    
    def get_wrapped_positions_optimized(self, position, radius, width, height, positions_list):
        """Get all possible wrapped positions for an object (optimized version)"""
        positions_list.append((position.x, position.y))
        
        # Horizontal wrapping
        if position.x < radius:
            positions_list.append((position.x + width, position.y))
        elif position.x > width - radius:
            positions_list.append((position.x - width, position.y))
        
        # Vertical wrapping
        if position.y < radius:
            positions_list.append((position.x, position.y + height))
        elif position.y > height - radius:
            positions_list.append((position.x, position.y - height))
        
        # Corner wrapping
        if (position.x < radius and position.y < radius):
            positions_list.append((position.x + width, position.y + height))
        elif (position.x > width - radius and position.y < radius):
            positions_list.append((position.x - width, position.y + height))
        elif (position.x < radius and position.y > height - radius):
            positions_list.append((position.x + width, position.y - height))
        elif (position.x > width - radius and position.y > height - radius):
            positions_list.append((position.x - width, position.y - height))
    
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
    
    def should_spawn_bosses(self):
        """Check if the current level should spawn bosses"""
        return self.level % 3 == 0
    
    def spawn_bosses_for_level(self):
        """Spawn bosses according to the new level-based system"""
        if self.level == 3:
            # Level 3: 1 boss (randomly from left or right, top or bottom), moving horizontally
            self.spawn_single_boss_random_side()
            
        elif self.level == 6:
            # Level 6: 2 bosses (1 from left top and 1 from right bottom) moving horizontally
            self.spawn_two_bosses_left_top_right_bottom()
            
        elif self.level == 9:
            # Level 9: 1 or 3 bosses (50% chance each) (randomly from left or right, top or bottom), moving horizontally
            if random.random() < 0.5:
                self.spawn_multiple_bosses_random_sides(3)
            else:
                self.spawn_single_boss_random_side()
                
        elif self.level >= 12:
            # Level 12+: Variable number based on probability
            chance = random.random()
            if chance < 0.33:
                # 33% chance: (current level/4 rounded down) bosses (randomly from left or right, top or bottom), moving horizontally
                num_bosses = max(1, self.level // 4)
                self.spawn_multiple_bosses_random_sides(num_bosses)
            elif chance < 0.66:
                # 33% chance: 4 corner bosses (1 each from left top, left bottom, right top and right bottom) moving horizontally
                self.spawn_four_corner_bosses()
            else:
                # 34% chance: 2 bosses (randomly from left or right, top or bottom), moving horizontally
                self.spawn_multiple_bosses_random_sides(2)
    
    def spawn_single_boss_random_side(self):
        """Spawn 1 boss on a random side of the screen"""
        direction = random.choice(["left_top", "right_top", "left_bottom", "right_bottom"])
        boss = BossEnemy(0, 0, direction, self.current_width, self.current_height, self.level)
        self.add_boss(boss)
        game_logger.log_boss_spawn(1, self.level)
        self.check_boss_spawn_collisions(boss)
    
    def spawn_two_bosses_left_top_right_bottom(self):
        """Spawn 2 bosses: 1 from left top and 1 from right bottom"""
        # First boss: left top
        boss1 = BossEnemy(0, 0, "left_top", self.current_width, self.current_height, self.level)
        self.add_boss(boss1)
        self.check_boss_spawn_collisions(boss1)
        
        # Second boss: right bottom
        boss2 = BossEnemy(0, 0, "right_bottom", self.current_width, self.current_height, self.level)
        self.add_boss(boss2)
        self.check_boss_spawn_collisions(boss2)
        
        # Log 2 bosses spawned
        game_logger.log_boss_spawn(2, self.level)
    
    def spawn_multiple_bosses_random_sides(self, num_bosses):
        """Spawn multiple bosses on random sides of the screen"""
        for _ in range(num_bosses):
            direction = random.choice(["left_top", "right_top", "left_bottom", "right_bottom"])
            boss = BossEnemy(0, 0, direction, self.current_width, self.current_height, self.level)
            self.add_boss(boss)
            self.check_boss_spawn_collisions(boss)
        
        # Log multiple bosses spawned
        game_logger.log_boss_spawn(num_bosses, self.level)
    
    def spawn_four_corner_bosses(self):
        """Spawn 4 bosses in the corners: left top, left bottom, right top, right bottom"""
        corners = ["left_top", "left_bottom", "right_top", "right_bottom"]
        for corner in corners:
            boss = BossEnemy(0, 0, corner, self.current_width, self.current_height, self.level)
            self.add_boss(boss)
            self.check_boss_spawn_collisions(boss)
        
        # Log 4 bosses spawned
        game_logger.log_boss_spawn(4, self.level)
    
    def run(self):
        self.running = True
        
        # Print welcome message on game start
        print("Welcome to c h u c k S T A R o i d s!")
        
        try:
            while self.running:
                dt = self.clock.tick(FPS) / 1000.0  # Convert to seconds
                
                # Calculate FPS for debug display
                if dt > 0:
                    current_fps = 1.0 / dt
                    self.fps_history.append(current_fps)
                    if len(self.fps_history) > 60:  # Keep last 60 frames
                        self.fps_history.pop(0)
                    self.current_fps = sum(self.fps_history) / len(self.fps_history)
                
                # Handle events
                try:
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            # Log current score before exiting
                            if hasattr(self, 'score') and self.score > 0:
                                game_logger.log_game_over(self.score, self.level)
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
                            try:
                                self.keys_pressed.add(event.key)
                            except Exception as e:
                                # print(f"[SCOREBOARD DEBUG] Error adding key to pressed set: {e}")
                                continue
                            
                            if event.key == pygame.K_SPACE and self.game_state == "waiting":
                                # Clean up title screen elements
                                self.cleanup_title_screen()
                                
                                # Clear any pressed keys from previous game state
                                self.keys_pressed.clear()
                                
                                # Clear high score file while preserving high scores when starting new game
                                game_logger.clear_gamelog_preserve_scores()
                                
                                # Start the game
                                self.game_state = "playing"
                                self.game_start_timer = 0.0  # Reset shooting prevention timer
                                
                                # Log game start
                                game_logger.log_game_start()
                                
                                self.init_ship()
                                self.spawn_asteroids()
                                self.spawn_ufo()  # Start with 1 UFO
                                # Start star explosion effect on game start
                                self.star_explosion_active = True
                                self.star_field.start_explosion(self.current_width, self.current_height)
                            elif (event.key == pygame.K_q or event.key == pygame.K_e or event.key == pygame.K_b) and self.game_state == "waiting":
                                # Generate ability particles on title screen
                                self.generate_title_ability_particles()
                            elif self.game_state == "waiting":
                                # Scoreboard controls on title screen
                                if event.key == pygame.K_TAB:
                                    # Toggle scoreboard display
                                    if self.scoreboard_available and self.scoreboard:
                                        self.show_scoreboard = not self.show_scoreboard
                                        if self.show_scoreboard:
                                            # Load scores in background
                                            self.load_scoreboard_background()
                                            # print(f"[SCOREBOARD DEBUG] TAB key pressed on title screen - toggled scoreboard")
                                    else:
                                        # Show message that scoreboard is unavailable
                                        print("Scoreboard is not available")
                                elif event.key == pygame.K_c:
                                    # Refresh scoreboard cache
                                    if self.scoreboard_available and self.scoreboard:
                                        self.scoreboard.force_refresh_cache()
                                        if self.show_scoreboard:
                                            # Load scores in background
                                            self.load_scoreboard_background()
                                    else:
                                        print("Scoreboard is not available")
                                    # print(f"[SCOREBOARD DEBUG] C key pressed on title screen - refreshed scoreboard cache")
                            elif event.key == pygame.K_r:
                                # R key restart - works when player is alive (playing state with lives > 0)
                                if self.game_state == "playing" and self.lives > 0:
                                    self.restart_game(log_current_score=True)
                                # R key also works in game_over state
                                elif self.game_state == "game_over":
                                    self.restart_game()
                            elif event.key == pygame.K_n:
                                # Press 'n' to go to title screen from any state
                                # Log current score if player is in the middle of a game
                                should_log_score = (self.game_state == "playing" and self.lives > 0)
                                self.return_to_title_screen(log_current_score=should_log_score)
                            elif self.game_state == "game_over":
                                # Only handle key events for game over state
                                if hasattr(event, 'key'):
                                    # Scoreboard controls
                                    if event.key == pygame.K_TAB:
                                        # Toggle scoreboard display
                                        if self.scoreboard_available and self.scoreboard:
                                            self.show_scoreboard = not self.show_scoreboard
                                            if self.show_scoreboard:
                                                # Load scores in background
                                                self.load_scoreboard_background()
                                        else:
                                            # Show message that scoreboard is unavailable
                                            print("Scoreboard is not available")
                                # S key removed - score submission is now automatic
                            elif event.key == pygame.K_p and self.game_state == "playing":
                                self.game_state = "paused"
                            elif event.key == pygame.K_p and self.game_state == "paused":
                                self.game_state = "playing"
                            # Handle name input first - highest priority when active
                            if self.name_input_active:
                                # Debug: Print when name input is active and key is pressed
                                print(f"Name input active, key pressed: {event.key}, unicode: {event.unicode}")
                                # When name input is active, handle all keys for input
                                try:
                                    if event.key == pygame.K_RETURN:
                                        # Submit the score
                                        try:
                                            if self.player_name_input and self.player_name_input.strip():
                                                # Limit name length to prevent API issues
                                                name = self.player_name_input.strip()[:50]  # Max 50 characters
                                                if self.scoreboard_available and self.scoreboard:
                                                    self.scoreboard.submit_score_async(
                                                        name, 
                                                        self.score,
                                                        self.on_score_submitted
                                                    )
                                                    # print(f"[SCOREBOARD DEBUG] Score submitted: {name} - {self.score}")
                                                else:
                                                    print("Scoreboard not available for score submission")
                                            else:
                                                # print(f"[SCOREBOARD DEBUG] Empty name, skipping submission")
                                                pass
                                        except Exception as e:
                                            # print(f"[SCOREBOARD DEBUG] Error submitting score: {e}")
                                            pass
                                        finally:
                                            self.name_input_active = False
                                            self.player_name_input = ""
                                    elif event.key == pygame.K_ESCAPE:
                                        # Cancel name input
                                        self.name_input_active = False
                                        self.player_name_input = ""
                                    elif event.key == pygame.K_BACKSPACE:
                                        # Safe backspace handling
                                        try:
                                            if self.player_name_input and len(self.player_name_input) > 0:
                                                self.player_name_input = self.player_name_input[:-1]
                                        except Exception as e:
                                            # print(f"[SCOREBOARD DEBUG] Error handling backspace: {e}")
                                            # Reset to empty string if there's an error
                                            self.player_name_input = ""
                                    elif event.unicode and event.unicode.isprintable():
                                        # Limit total input length and handle special characters safely
                                        try:
                                            # Ensure player_name_input is a string
                                            if not isinstance(self.player_name_input, str):
                                                self.player_name_input = str(self.player_name_input) if self.player_name_input else ""
                                            
                                            if len(self.player_name_input) < 50:  # Max 50 characters
                                                # Filter out problematic characters
                                                char = event.unicode
                                                if char and char.isprintable() and char not in ['\r', '\n', '\t']:
                                                    self.player_name_input += char
                                        except Exception as e:
                                            # print(f"[SCOREBOARD DEBUG] Error handling character input: {e}")
                                            # Reset to empty string if there's an error
                                            self.player_name_input = ""
                                except Exception as e:
                                    # print(f"[SCOREBOARD DEBUG] Critical error in name input handling: {e}")
                                    import traceback
                                    traceback.print_exc()
                                    # Reset to safe state
                                    self.name_input_active = False
                                    self.player_name_input = ""
                            elif self.game_state == "game_over":
                                # Only allow non-movement/action keys to restart from game over
                                excluded_keys = {
                                    pygame.K_w, pygame.K_a, pygame.K_s, pygame.K_d,  # WASD
                                    pygame.K_q, pygame.K_e, pygame.K_b,  # Q, E, B
                                    pygame.K_SPACE,  # Space
                                    pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT  # Arrow keys
                                }
                                if event.key not in excluded_keys:
                                    self.return_to_title_screen()
                                elif event.key == pygame.K_t:
                                    # Title effects are disabled
                                    pass
                                elif event.key == pygame.K_ESCAPE and not self.name_input_active:
                                    # ESC key behavior - only handle if not in name input
                                    # Log current score before exiting
                                    if hasattr(self, 'score') and self.score > 0:
                                        game_logger.log_game_over(self.score, self.level)
                                    # Otherwise, exit the game
                                    self.running = False
                        elif event.type == pygame.KEYUP:
                            if hasattr(event, 'key'):
                                self.keys_pressed.discard(event.key)
                except Exception as e:
                    # print(f"[SCOREBOARD DEBUG] Error in event handling: {e}")
                    import traceback
                    traceback.print_exc()
                    # Continue running despite event handling errors
                
                # Update and draw
                self.handle_input(dt)
                self.update(dt)
                self.draw(dt)
                
                # Periodic garbage collection for memory management
                if hasattr(self, 'gc_timer'):
                    self.gc_timer += dt
                    if self.gc_timer >= 5.0:  # Every 5 seconds
                        gc.collect()
                        self.gc_timer = 0.0
                else:
                    self.gc_timer = 0.0
                
                # Update the display
                pygame.display.flip()
                
        except Exception as e:
            # Game crashed - exit gracefully
            pygame.quit()
        finally:
            # Print footer message on game exit/termination/crash
            print("c h u c k S T A R o i d s  1.o  ~  September 7 - 12, 2025  ~  x o x")
            
            # Clean up music player
            if self.music_player:
                self.music_player.close()
    
    def draw_scoreboard(self, surface):
        """Draw the scoreboard"""
        try:
            # Semi-transparent background
            overlay = pygame.Surface((self.current_width, self.current_height))
            overlay.set_alpha(200)
            overlay.fill(BLACK)
            surface.blit(overlay, (0, 0))
            
            # Title
            font_large = pygame.font.Font(None, 48)
            if not self.scoreboard_available or not self.scoreboard:
                title_text = font_large.render("SCOREBOARD UNAVAILABLE", True, WHITE)
            else:
                title_text = font_large.render("TOP 10 SCORES", True, WHITE)
            title_rect = title_text.get_rect(center=(self.current_width // 2, 100))
            surface.blit(title_text, title_rect)
            
            # Scores - with error handling
            font = pygame.font.Font(None, 32)
            y_offset = 150
            
            # Ensure scoreboard_scores is valid
            if not hasattr(self, 'scoreboard_scores') or self.scoreboard_scores is None:
                self.scoreboard_scores = []
            
            # Get formatted scores with error handling
            try:
                if not self.scoreboard_available or not self.scoreboard:
                    formatted_scores = ["Scoreboard service unavailable"]
                elif self.scoreboard_loading:
                    formatted_scores = ["Loading scores..."]
                else:
                    formatted_scores = self.scoreboard.format_scores_display(self.scoreboard_scores)
            except Exception as e:
                # print(f"[SCOREBOARD DEBUG] Error formatting scores: {e}")
                formatted_scores = ["Error loading scores"]
            
            # Draw each score line
            for i, score_line in enumerate(formatted_scores):
                try:
                    score_text = font.render(score_line, True, WHITE)
                    score_rect = score_text.get_rect(center=(self.current_width // 2, y_offset + i * 35))
                    surface.blit(score_text, score_rect)
                except Exception as e:
                    # print(f"[SCOREBOARD DEBUG] Error rendering score line {i}: {e}")
                    # Draw error message for this line
                    error_text = font.render("Error displaying score", True, WHITE)
                    error_rect = error_text.get_rect(center=(self.current_width // 2, y_offset + i * 35))
                    surface.blit(error_text, error_rect)
            
            # Instructions
            font_small = pygame.font.Font(None, 24)
            inst_text = font_small.render("Press TAB to close scoreboard", True, WHITE)
            inst_rect = inst_text.get_rect(center=(self.current_width // 2, y_offset + 400))
            surface.blit(inst_text, inst_rect)
            
        except Exception as e:
            # print(f"[SCOREBOARD DEBUG] Critical error in draw_scoreboard: {e}")
            # Draw a simple error message
            try:
                error_font = pygame.font.Font(None, 36)
                error_text = error_font.render("Scoreboard Error", True, WHITE)
                error_rect = error_text.get_rect(center=(self.current_width // 2, self.current_height // 2))
                surface.blit(error_text, error_rect)
            except:
                pass  # If even this fails, just continue
    
    def draw_name_input(self, surface):
        """Draw name input dialog"""
        try:
            # Semi-transparent background
            overlay = pygame.Surface((self.current_width, self.current_height))
            overlay.set_alpha(150)
            overlay.fill(BLACK)
            surface.blit(overlay, (0, 0))
        
            # Dialog box
            dialog_width = 400
            dialog_height = 200
            dialog_x = (self.current_width - dialog_width) // 2
            dialog_y = (self.current_height - dialog_height) // 2
            
            pygame.draw.rect(surface, WHITE, (dialog_x, dialog_y, dialog_width, dialog_height))
            pygame.draw.rect(surface, BLACK, (dialog_x + 2, dialog_y + 2, dialog_width - 4, dialog_height - 4))
            
            # Text
            font = pygame.font.Font(None, 32)
            prompt_text = font.render("Enter your name:", True, WHITE)
            prompt_rect = prompt_text.get_rect(center=(self.current_width // 2, dialog_y + 50))
            surface.blit(prompt_text, prompt_rect)
            
            # Ensure player_name_input is valid
            if not hasattr(self, 'player_name_input') or self.player_name_input is None:
                self.player_name_input = ""
            
            # Safely render the name input with cursor
            try:
                # Filter out any problematic characters for rendering
                safe_input = str(self.player_name_input) if self.player_name_input else ""
                # Remove any non-printable characters that might cause rendering issues
                safe_input = ''.join(char for char in safe_input if char.isprintable() and char not in ['\r', '\n', '\t'])
                
                name_text = font.render(safe_input + "_", True, WHITE)
                name_rect = name_text.get_rect(center=(self.current_width // 2, dialog_y + 100))
                surface.blit(name_text, name_rect)
            except Exception as e:
                # print(f"[SCOREBOARD DEBUG] Error rendering name input: {e}")
                # Render a safe fallback
                try:
                    fallback_text = font.render("_", True, WHITE)
                    fallback_rect = fallback_text.get_rect(center=(self.current_width // 2, dialog_y + 100))
                    surface.blit(fallback_text, fallback_rect)
                except:
                    pass  # If even this fails, just continue
            
            # Instructions
            font_small = pygame.font.Font(None, 24)
            inst_text = font_small.render("Press ENTER to submit, ESC to cancel", True, WHITE)
            inst_rect = inst_text.get_rect(center=(self.current_width // 2, dialog_y + 150))
            surface.blit(inst_text, inst_rect)
            
        except Exception as e:
            # print(f"[SCOREBOARD DEBUG] Error in draw_name_input: {e}")
            # Draw a simple error message
            try:
                error_font = pygame.font.Font(None, 36)
                error_text = error_font.render("Name Input Error", True, WHITE)
                error_rect = error_text.get_rect(center=(self.current_width // 2, self.current_height // 2))
                surface.blit(error_text, error_rect)
            except:
                pass  # If even this fails, just continue

def main():
    
    game = Game()
    game.run()
    
    # Log final score before exiting
    if hasattr(game, 'score') and game.score > 0:
        game_logger.log_game_over(game.score, game.level)
    
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()