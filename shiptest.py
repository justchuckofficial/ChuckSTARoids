import pygame
import math
import sys
import os
import random

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
BLUE = (0, 0, 255)

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

class Bullet(GameObject):
    def __init__(self, x, y, vx, vy, angle=None):
        super().__init__(x, y, vx, vy)
        self.angle = angle if angle is not None else math.atan2(vy, vx)
        self.lifetime = 3.0  # 3 seconds lifetime
        self.max_lifetime = 3.0
        
    def update(self, dt, screen_width, screen_height):
        if not self.active:
            return
            
        # Update position
        self.position.x += self.velocity.x * dt
        self.position.y += self.velocity.y * dt
        
        # Screen wrapping
        if self.position.x < 0:
            self.position.x = screen_width
        elif self.position.x > screen_width:
            self.position.x = 0
        if self.position.y < 0:
            self.position.y = screen_height
        elif self.position.y > screen_height:
            self.position.y = 0
            
        # Update lifetime
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.active = False
    
    def draw(self, screen):
        if not self.active:
            return
            
        # Draw bullet as a small circle
        pygame.draw.circle(screen, RED, (int(self.position.x), int(self.position.y)), 3)

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
        
        # Draw particle (ensure minimum size of 1 pixel)
        radius = max(1, int(self.size))
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), radius)

class ExplosionSystem:
    def __init__(self):
        self.particles = []
    
    def add_explosion(self, x, y, num_particles=50, color=(255, 255, 0), asteroid_size=None, is_ufo=False):
        for _ in range(int(num_particles)):
            # Random spawn position within diameter based on asteroid size
            if asteroid_size is not None:
                # All asteroid sizes: spawn within diameter radius
                spawn_radius = asteroid_size * 8  # Diameter increases with asteroid size
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
                elif asteroid_size == 2:
                    base_speed = 75
                else:  # size 3
                    base_speed = 100
                speed = random.uniform(base_speed * 0.5, base_speed * 1.5)
            else:
                # UFO or other explosion
                speed = random.uniform(50, 200)
            
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            
            # Random size
            if asteroid_size is not None:
                size = random.uniform(1.0, 3.0)
            else:
                size = random.uniform(1.0, 4.0)
            
            # Random lifetime
            lifetime = random.uniform(0.5, 2.0)
            
            # Create particle
            particle = Particle(spawn_x, spawn_y, vx, vy, color, lifetime, size)
            self.particles.append(particle)
    
    def update(self, dt, screen_width=None, screen_height=None):
        # Use list comprehension for more efficient cleanup
        self.particles = [p for p in self.particles if p.active]
        for particle in self.particles:
            particle.update(dt, screen_width, screen_height)
    
    def draw(self, screen):
        for particle in self.particles:
            particle.draw(screen)

class AdvancedUFO(GameObject):
    def __init__(self, x, y, ai_personality="aggressive"):
        super().__init__(x, y)
        
        # Basic properties
        self.radius = 26  # Half as big (52 * 0.5 = 26)
        self.speed = 100
        self.max_speed = 150
        self.acceleration = 50
        self.rotation_speed = 2.0  # Base rotation speed for UFOs
        
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
        self.individual_accuracy_multiplier = random.uniform(0.8, 1.1)  # Individual UFO accuracy variation
        self.aggression_level = 1.0
        self.bullets_fired = 0  # Track bullets fired by this UFO
        self.max_bullets = 5  # Will be set based on level
        
        # Set accuracy modifiers based on personality
        if ai_personality in ["defensive", "aggressive"]:
            self.accuracy_modifier = 0.75  # 75% accuracy for these types
        elif ai_personality in ["tactical", "swarm", "deadly"]:
            self.accuracy_modifier = 1.0  # Perfect accuracy for predictive types
        
        # Deadly AI enhancements
        if ai_personality == "deadly":
            self.speed = 120  # 20% faster
            self.max_speed = 180  # 20% faster max speed
            self.shoot_interval = 0.7  # 30% faster shooting
            self.accuracy_modifier = 1.5  # 50% more accurate (overrides above)
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
        self.spinout_duration = random.uniform(0.5, 1.5)  # Random duration 0.5-1.5 seconds
        self.spinout_flame_scale = 0.0  # 0% to 100% scaling over 1 second
        self.spinout_flame_scale_timer = 0.0
        self.spinout_flame_scale_duration = 1.0  # 1 second to scale up
        self.spinout_spark_timer = 0.0
        self.spinout_spark_interval = 1.0 / random.uniform(20, 42)  # 20-42 sparks per second
        self.spinout_movement_type = None  # "straight" or "spiral"
        self.spinout_spiral_angle = 0.0
        self.spinout_spiral_radius = 0.0
        self.spinout_spiral_center = Vector2D(0, 0)
        self.spinout_rotation_speed_multiplier = 1.0  # Will be set to random 1x-10x
        self.spinout_target_rotation_speed = 0.0
        self.spinout_original_max_speed = self.max_speed
        self.spinout_collision_delay_timer = 0.0
        self.spinout_collision_delay = 0.5  # 0.5 second delay before collision damage
        
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
            
            # Set image size based on personality (swarm gets 48px, others get 52px)
            if self.personality == "swarm":
                image_size = 48
            else:
                image_size = int(self.radius * 2)  # 52px for others
                
            self.image = pygame.transform.smoothscale(self.image, (image_size, image_size))
            
            # Apply image-specific transformations
            if self.personality == "aggressive":
                # Flip tie.gif horizontally then rotate 90 degrees clockwise then rotate 180 degrees
                self.image = pygame.transform.flip(self.image, True, False)
                self.image = pygame.transform.rotate(self.image, -90)
                self.image = pygame.transform.rotate(self.image, 180)
            elif self.personality == "deadly":
                # Rotate tiei.gif 90 degrees counter-clockwise and flip horizontally
                self.image = pygame.transform.rotate(self.image, 90)
                self.image = pygame.transform.flip(self.image, True, False)
            elif self.personality in ["defensive", "tactical", "swarm"]:
                # Flip tieb.gif, tiea.gif, and tiefo.gif horizontally then rotate 90 degrees counter-clockwise
                self.image = pygame.transform.flip(self.image, True, False)
                self.image = pygame.transform.rotate(self.image, 90)
        except Exception as e:
            print(f"Failed to load UFO image for {self.personality}: {e}")
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
            print(f"Failed to load spinout flame image: {e}")
            self.spinout_flame_image = None
    
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
            self.update_spinout(dt, explosion_system)
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
    
    def draw(self, screen, debug_mode=False, shake_x=0, shake_y=0):
        if not self.active:
            return
        
        # Draw spinout flame effect first (behind UFO)
        if self.spinout_active:
            self.draw_spinout(screen, shake_x, shake_y)
            
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
        """Update AI state based on personality and current situation"""
        self.state_timer += dt
        
        # Simple state machine for testing - just move forward
        if self.personality == "aggressive":
            self.current_state = "seek"
        elif self.personality == "defensive":
            self.current_state = "flee"
        elif self.personality == "tactical":
            self.current_state = "flank"
        elif self.personality == "swarm":
            self.current_state = "swarm"
        elif self.personality == "deadly":
            self.current_state = "intercept"
        else:
            self.current_state = "patrol"
    
    def update_behavior_weights(self):
        """Update behavior weights based on current state"""
        # Reset all weights
        for key in self.behavior_weights:
            self.behavior_weights[key] = 0.0
        
        # Set weights based on current state
        if self.current_state == "seek":
            self.behavior_weights["seek"] = 1.0
        elif self.current_state == "flee":
            self.behavior_weights["flee"] = 1.0
        elif self.current_state == "flank":
            self.behavior_weights["flank"] = 1.0
        elif self.current_state == "swarm":
            self.behavior_weights["swarm"] = 1.0
        elif self.current_state == "intercept":
            self.behavior_weights["intercept"] = 1.0
        else:
            self.behavior_weights["patrol"] = 1.0
    
    def calculate_movement_vector(self, dt):
        """Calculate movement vector based on behavior weights"""
        # For testing, just move forward at constant speed
        self.velocity = Vector2D(self.speed, 0)
        self.angle = math.atan2(self.velocity.y, self.velocity.x)
    
    def update_shooting_behavior(self, dt):
        """Update shooting behavior and return whether to shoot"""
        self.shoot_timer += dt
        
        if self.shoot_timer >= self.shoot_interval:
            self.shoot_timer = 0.0
            return True
        return False
    
    def shoot(self):
        """Shoot a bullet forward"""
        # Calculate bullet velocity (forward direction)
        bullet_speed = 300
        bullet_vx = math.cos(self.angle) * bullet_speed
        bullet_vy = math.sin(self.angle) * bullet_speed
        
        # Create bullet slightly in front of UFO
        offset_distance = self.radius + 10
        bullet_x = self.position.x + math.cos(self.angle) * offset_distance
        bullet_y = self.position.y + math.sin(self.angle) * offset_distance
        
        return Bullet(bullet_x, bullet_y, bullet_vx, bullet_vy, self.angle)
    
    def trigger_spinout(self):
        """Trigger the spinout 'Burst into Flames' effect"""
        try:
            self.spinout_active = True
            self.spinout_timer = 0.0
            self.spinout_duration = random.uniform(0.5, 1.5)  # Random duration
            self.spinout_flame_scale = 0.0
            self.spinout_flame_scale_timer = 0.0
            self.spinout_spark_timer = 0.0
            self.spinout_spark_interval = 1.0 / random.uniform(20, 42)  # 20-42 sparks per second
            self.spinout_collision_delay_timer = 0.0
            
            # Set movement type (50% straight, 50% spiral)
            self.spinout_movement_type = "straight" if random.random() < 0.5 else "spiral"
            
            # Set rotation speed multiplier (1x to 10x)
            self.spinout_rotation_speed_multiplier = random.uniform(1.0, 10.0)
            self.spinout_target_rotation_speed = self.rotation_speed * self.spinout_rotation_speed_multiplier
            
            # Set up movement
            # Random speed multiplier between 3x and 5x
            self.spinout_speed_multiplier = random.uniform(3.0, 5.0)
            
            if self.spinout_movement_type == "straight":
                # Random direction
                angle = random.uniform(0, 2 * math.pi)
                self.velocity = Vector2D(math.cos(angle), math.sin(angle)) * (self.max_speed * self.spinout_speed_multiplier)
            else:
                # Spiral outward - set up spiral parameters
                self.spinout_spiral_center = Vector2D(self.position.x, self.position.y)
                self.spinout_spiral_angle = 0.0
                self.spinout_spiral_radius = 0.0
                # Start with current velocity direction for spiral
                current_angle = math.atan2(self.velocity.y, self.velocity.x)
                self.velocity = Vector2D(math.cos(current_angle), math.sin(current_angle)) * (self.max_speed * self.spinout_speed_multiplier)
            
            # Add 350 speed units to current velocity when entering spinout
            current_speed = self.velocity.magnitude()
            if current_speed > 0:
                # Normalize current velocity and add 350 speed units
                velocity_direction = Vector2D(self.velocity.x / current_speed, self.velocity.y / current_speed)
                additional_velocity = velocity_direction * 350
                self.velocity = self.velocity + additional_velocity
        except Exception as e:
            print(f"Error in trigger_spinout: {e}")
            print(f"UFO position: {self.position}")
            print(f"UFO velocity: {self.velocity}")
            print(f"UFO max_speed: {self.max_speed}")
            print(f"UFO rotation_speed: {self.rotation_speed}")
            raise
    
    def update_spinout(self, dt, explosion_system, game_instance=None):
        """Update spinout effect"""
        if not self.spinout_active:
            return
        
        self.spinout_timer += dt
        self.spinout_collision_delay_timer += dt
        
        # Update flame scaling (0% to 100% over 1 second)
        self.spinout_flame_scale_timer += dt
        if self.spinout_flame_scale_timer < self.spinout_flame_scale_duration:
            self.spinout_flame_scale = self.spinout_flame_scale_timer / self.spinout_flame_scale_duration
        else:
            self.spinout_flame_scale = 1.0
        
        # Update movement
        if self.spinout_movement_type == "spiral":
            # Logarithmic spiral movement
            self.spinout_spiral_angle += dt * 3.0  # Spiral speed
            self.spinout_spiral_radius += dt * 100  # Spiral expansion rate
            
            # Logarithmic spiral: r = a * e^(b * θ)
            a = 10  # Scale factor
            b = 0.1  # Growth rate
            r = a * math.exp(b * self.spinout_spiral_angle)
            
            # Convert to cartesian
            x = self.spinout_spiral_center.x + r * math.cos(self.spinout_spiral_angle)
            y = self.spinout_spiral_center.y + r * math.sin(self.spinout_spiral_angle)
            
            # Update velocity to move towards spiral position
            target_pos = Vector2D(x, y)
            direction = target_pos - self.position
            if direction.magnitude() > 0:
                direction = direction.normalize()
                self.velocity = direction * (self.max_speed * self.spinout_speed_multiplier)
        
        # Update rotation speed gradually
        current_rotation_speed = self.rotation_speed
        target_rotation_speed = self.spinout_target_rotation_speed
        if current_rotation_speed < target_rotation_speed:
            self.rotation_speed = min(target_rotation_speed, current_rotation_speed + dt * 5.0)
        
        # Generate sparks
        self.spinout_spark_timer += dt
        if self.spinout_spark_timer >= self.spinout_spark_interval:
            self.spinout_spark_timer = 0.0
            self.spinout_spark_interval = 1.0 / random.uniform(20, 42)  # New random interval
            
            # Generate 1-20 sparks per burst
            num_sparks = random.randint(1, 20)
            for _ in range(num_sparks):
                # 66% firey, 34% electric
                if random.random() < 0.66:
                    # Firey colors (red/orange/yellow)
                    colors = [(255, 100, 0), (255, 150, 0), (255, 200, 0), (255, 50, 0)]
                    color = random.choice(colors)
                else:
                    # Electric colors (blue/white)
                    colors = [(0, 150, 255), (100, 200, 255), (255, 255, 255), (0, 100, 255)]
                    color = random.choice(colors)
                
                # Random velocity and direction
                angle = random.uniform(0, 2 * math.pi)
                speed = random.uniform(50, 200)
                vx = math.cos(angle) * speed
                vy = math.sin(angle) * speed
                
                # Random size
                size = random.uniform(1.0, 3.0)
                
                # Add particle
                explosion_system.add_explosion(
                    self.position.x + random.uniform(-10, 10),
                    self.position.y + random.uniform(-10, 10),
                    num_particles=1,
                    color=color
                )
        
        # Check if spinout duration is over
        if self.spinout_timer >= self.spinout_duration:
            self.spinout_active = False
            self.active = False  # UFO dies after spinout
            
            # Add final explosion and score when spinout ends
            explosion_system.add_explosion(self.position.x, self.position.y, 
                                        num_particles=90, 
                                        color=(0, 150, 255), is_ufo=True)  # Electric blue
            explosion_system.add_explosion(self.position.x, self.position.y, 
                                        num_particles=10, 
                                        color=(255, 255, 255), is_ufo=True)  # Bright white
    
    def draw_spinout(self, screen, shake_x=0, shake_y=0):
        """Draw spinout flame effect"""
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
                # Rotate the flame to point behind the UFO (180 degrees from UFO's facing direction) + 90 degrees counter-clockwise
                rotated_flame = pygame.transform.rotate(scaled_flame, -math.degrees(self.angle) + 180 + 90)
                # Apply screen shake offset to flame position to match UFO
                flame_x = int(self.position.x + shake_x)
                flame_y = int(self.position.y + shake_y)
                flame_rect = rotated_flame.get_rect(center=(flame_x, flame_y))
                screen.blit(rotated_flame, flame_rect)

def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def main():
    # Create screen
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("UFO Test - Full Mechanics with Spinout Animation")
    clock = pygame.time.Clock()
    
    # Create explosion system
    explosion_system = ExplosionSystem()
    
    # Create UFOs for each personality
    ufos = []
    personalities = ["aggressive", "defensive", "deadly", "tactical", "swarm"]
    
    # Position UFOs in a grid
    start_x = 150
    start_y = 200
    spacing_x = 200
    spacing_y = 150
    
    for i, personality in enumerate(personalities):
        x = start_x + (i % 3) * spacing_x
        y = start_y + (i // 3) * spacing_y
        ufo = AdvancedUFO(x, y, personality)
        ufos.append(ufo)
    
    # Create bullets list
    bullets = []
    
    # Font for labels
    font = pygame.font.Font(None, 36)
    small_font = pygame.font.Font(None, 24)
    
    # Mock ship position for UFO AI
    ship_pos = Vector2D(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
    
    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0  # Convert to seconds
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    # Trigger spinout for all UFOs
                    for ufo in ufos:
                        if ufo.active and not ufo.spinout_active:
                            ufo.trigger_spinout()
                elif event.key == pygame.K_r:
                    # Reset all UFOs
                    for i, ufo in enumerate(ufos):
                        x = start_x + (i % 3) * spacing_x
                        y = start_y + (i // 3) * spacing_y
                        ufo.position = Vector2D(x, y)
                        ufo.active = True
                        ufo.spinout_active = False
                        ufo.velocity = Vector2D(ufo.speed, 0)
                        ufo.angle = 0
        
        # Clear screen
        screen.fill(BLACK)
        
        # Update explosion system
        explosion_system.update(dt, SCREEN_WIDTH, SCREEN_HEIGHT)
        
        # Update UFOs and handle shooting
        for ufo in ufos[:]:  # Use slice to avoid modification during iteration
            if ufo.active:
                should_shoot = ufo.update(dt, ship_pos, SCREEN_WIDTH, SCREEN_HEIGHT, 1.0, explosion_system)
                
                # Try to shoot if not in spinout
                if should_shoot and not ufo.spinout_active:
                    bullet = ufo.shoot()
                    if bullet:
                        bullets.append(bullet)
            else:
                # Remove inactive UFOs
                ufos.remove(ufo)
        
        # Update bullets
        for bullet in bullets[:]:  # Use slice to avoid modification during iteration
            bullet.update(dt, SCREEN_WIDTH, SCREEN_HEIGHT)
            if not bullet.active:
                bullets.remove(bullet)
        
        # Draw explosion system
        explosion_system.draw(screen)
        
        # Draw bullets
        for bullet in bullets:
            bullet.draw(screen)
        
        # Draw UFOs
        for i, ufo in enumerate(ufos):
            if ufo.active:
                ufo.draw(screen, debug_mode=True)
                
                # Draw hitbox circle
                pygame.draw.circle(screen, GREEN, 
                                (int(ufo.position.x), int(ufo.position.y)), 
                                ufo.radius, 2)
                
                # Draw center point
                pygame.draw.circle(screen, RED, 
                                (int(ufo.position.x), int(ufo.position.y)), 
                                3)
                
                # Draw movement indicator (small line showing forward movement)
                direction_length = 30
                end_x = ufo.position.x + math.cos(ufo.angle) * direction_length
                end_y = ufo.position.y + math.sin(ufo.angle) * direction_length
                pygame.draw.line(screen, YELLOW, 
                               (int(ufo.position.x), int(ufo.position.y)),
                               (int(end_x), int(end_y)), 3)
                
                # Draw personality label
                label_text = f"{ufo.personality.capitalize()}"
                label_surface = font.render(label_text, True, WHITE)
                label_rect = label_surface.get_rect()
                label_rect.centerx = ufo.position.x
                label_rect.y = ufo.position.y + 60
                screen.blit(label_surface, label_rect)
                
                # Draw state info
                state_text = f"State: {ufo.current_state}"
                state_surface = small_font.render(state_text, True, CYAN)
                state_rect = state_surface.get_rect()
                state_rect.centerx = ufo.position.x
                state_rect.y = ufo.position.y + 85
                screen.blit(state_surface, state_rect)
                
                # Draw spinout info if active
                if ufo.spinout_active:
                    spinout_text = f"SPINOUT: {ufo.spinout_movement_type}"
                    spinout_surface = small_font.render(spinout_text, True, (255, 100, 0))
                    spinout_rect = spinout_surface.get_rect()
                    spinout_rect.centerx = ufo.position.x
                    spinout_rect.y = ufo.position.y + 105
                    screen.blit(spinout_surface, spinout_rect)
        
        # Draw title
        title_text = "UFO Test - Full Mechanics with Spinout Animation"
        title_surface = font.render(title_text, True, WHITE)
        title_rect = title_surface.get_rect()
        title_rect.centerx = SCREEN_WIDTH // 2
        title_rect.y = 50
        screen.blit(title_surface, title_rect)
        
        # Draw legend
        legend_y = SCREEN_HEIGHT - 140
        legend_items = [
            ("Green Circle", "Hitbox (collision detection)"),
            ("Red Dot", "Center point"),
            ("Yellow Line", "Movement direction"),
            ("Red Circles", "Bullets"),
            ("SPACE", "Trigger spinout for all UFOs"),
            ("R", "Reset all UFOs"),
            ("ESC", "Exit")
        ]
        
        for i, (item, description) in enumerate(legend_items):
            if i < 4:
                color = GREEN if i == 0 else RED if i == 1 else YELLOW if i == 2 else RED
            else:
                color = WHITE
            item_surface = small_font.render(f"{item}: {description}", True, color)
            screen.blit(item_surface, (50, legend_y + i * 20))
        
        # Instructions
        instructions = [
            "UFOs move forward and fire bullets",
            "Each personality has different behavior",
            "Spinout shows full flame animation",
            "Particles and explosions included"
        ]
        
        for i, instruction in enumerate(instructions):
            inst_surface = small_font.render(instruction, True, WHITE)
            screen.blit(inst_surface, (SCREEN_WIDTH - 400, legend_y + i * 20))
        
        pygame.display.flip()
        clock.tick(FPS)
    
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
