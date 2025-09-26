import pygame
import math
import random
import sys

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
        
        
        # Deceleration tracking for time dilation
        self.last_velocity = Vector2D(0, 0)  # Previous frame velocity
        self.deceleration_rate = 0.0  # Current deceleration rate
        
        # Shield recharge pulse effect
        self.shield_recharge_pulse_timer = 0.0  # Timer for shield recharge pulse effect
        self.shield_recharge_pulse_duration = 1.0  # Duration of pulse effect
        
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
                self.shield_hits += 1
                self.shield_recharge_time = 0
        
        # Update shield damage visual timer (affected by time dilation)
        if self.shield_damage_timer > 0:
            self.shield_damage_timer -= dt
        
        # Update shield recharge pulse timer (affected by time dilation)
        if self.shield_recharge_pulse_timer > 0:
            self.shield_recharge_pulse_timer -= dt
        
        # Apply speed decay
        if not self.thrusting:
            # Only decay when not thrusting
            current_speed = self.velocity.magnitude()
            speed_percent = current_speed / 1000.0 * 100  # Convert to percentage
            
            # Use faster decay when speed is below 10%
            if speed_percent < 10.0:
                # Twice as fast decay (square the decay rate)
                decay_rate = self.speed_decay_rate ** 2
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
    
    def draw(self, screen):
        if not self.active:
            return
            
        # Draw ship using image or fallback to triangle
        if self.image:
            # Rotate the ship image 90 degrees clockwise from default orientation
            rotated_ship = pygame.transform.rotate(self.image, -math.degrees(self.angle) - 90)
            ship_rect = rotated_ship.get_rect(center=(int(self.position.x), int(self.position.y)))
            
            # Draw ship
            if self.invulnerable and int(self.invulnerable_time * 10) % 2:
                # Flash effect when invulnerable - create a red tinted version
                red_ship = self.image.copy()
                red_ship.fill((255, 0, 0, 128), special_flags=pygame.BLEND_MULT)
                red_ship = pygame.transform.rotate(red_ship, -math.degrees(self.angle) - 90)
                screen.blit(red_ship, ship_rect)
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
            if self.invulnerable and int(self.invulnerable_time * 10) % 2:
                color = RED
            pygame.draw.polygon(screen, color, points)
        
        
        # Draw thrust flame
        if self.thrusting:
            # Position flame behind the rocket (opposite direction of movement)
            flame_angle = self.angle + math.pi
            flame_x = self.position.x + math.cos(flame_angle) * 40
            flame_y = self.position.y + math.sin(flame_angle) * 40
            
            try:
                # Try fire.gif image with rotation
                flame_image = pygame.image.load("fire.gif")
                flame_image = pygame.transform.scale(flame_image, (30, 15))  # 25% shorter (40->30 width, 20->15 height)
                # Rotate the flame 180 degrees and match ship rotation
                rotated_flame = pygame.transform.rotate(flame_image, -math.degrees(self.angle) - 90 + 90 + 180)
                flame_rect = rotated_flame.get_rect(center=(int(flame_x), int(flame_y)))
                screen.blit(rotated_flame, flame_rect)
            except:
                # Fallback to triangle flame
                flame_points = []
                for i in range(3):
                    angle = self.angle + math.pi + i * (2 * math.pi / 3)
                    x = self.position.x + math.cos(angle) * self.radius * 0.7
                    y = self.position.y + math.sin(angle) * self.radius * 0.7
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
                    alpha = int(255 * pulse_intensity)
                    color = (0, 100, 255, alpha)
                    # Draw outline circle (width parameter makes it outline only)
                    # Ensure minimum width of 1 to avoid filled circles
                    width = max(1, int(3 * pulse_intensity))
                    pygame.draw.circle(screen, (0, 100, 255), 
                                    (int(self.position.x), int(self.position.y)), 
                                    shield_radius + i * 5, width)
        

class Bullet(GameObject):
    def __init__(self, x, y, vx, vy, is_ufo_bullet=False, angle=None):
        super().__init__(x, y, vx, vy)
        self.radius = 4  # Increased for better hit detection with elongated bullets
        self.lifetime = 3.0  # seconds
        self.age = 0
        self.is_ufo_bullet = is_ufo_bullet
        # Use provided angle or calculate from velocity for rotation
        if angle is not None:
            self.angle = angle
        else:
            self.angle = math.atan2(vy, vx)
        
        # Load bullet image
        try:
            if is_ufo_bullet:
                self.image = pygame.image.load("tieshot.gif")
            else:
                self.image = pygame.image.load("shot.gif")
            # Make bullets 100% longer (double width)
            self.image = pygame.transform.scale(self.image, (16, 8))  # Double width
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
                # Fallback to circle - make it more visible
                color = RED if self.is_ufo_bullet else WHITE
                radius = 4 if self.is_ufo_bullet else 3
                pygame.draw.circle(screen, color, (int(self.position.x), int(self.position.y)), radius)
            
            

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
    
    def draw(self, screen):
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
        
        # Debug text: Show UFO state and personality
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
    
    def update(self, dt):
        for particle in self.particles[:]:
            particle.update(dt)
            if not particle.active:
                self.particles.remove(particle)
    
    def draw(self, screen):
        for particle in self.particles:
            particle.draw(screen)

class StarField:
    def __init__(self, num_stars=200):
        self.stars = []
        self.num_stars = num_stars
        self.last_speed_factor = 0.0  # For smoothing
        # Don't generate stars here - will be generated when screen size is known
    
    def generate_stars(self, screen_width, screen_height):
        self.stars = []
        for _ in range(self.num_stars):
            star = {
                'x': random.uniform(0, screen_width),
                'y': random.uniform(0, screen_height),
                'speed': random.uniform(0.5, 3.0),
                'brightness': random.uniform(0.3, 1.0),
                'size': random.uniform(0.5, 2.0),
                'stationary_brightness': random.randint(20, 150)  # Pre-calculated stationary brightness
            }
            self.stars.append(star)
    
    def update(self, ship_velocity, screen_width, screen_height):
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
            
            # Draw star with trail effect (only when going 42% of max speed)
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
        
        # Window resizing
        self.current_width = SCREEN_WIDTH
        self.current_height = SCREEN_HEIGHT
        
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
        
        # Screen shake variables
        self.screen_shake_intensity = 0
        self.screen_shake_duration = 0
        self.screen_shake_timer = 0
        self.game_over_timer = 0  # Timer for game over state
        
        # Time dilation system (Superhot-style)
        self.time_dilation_factor = 1.0  # 1.0 = normal time, 0.01 = 100x slower
        
    def trigger_screen_shake(self, intensity, duration):
        """Trigger screen shake effect"""
        # Don't trigger screen shake during game over state (except for player death)
        if self.game_state == "game_over" and self.game_over_timer > 0.1:
            return
        self.screen_shake_intensity = intensity
        self.screen_shake_duration = duration
        self.screen_shake_timer = duration
    
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
            
            # Use faster decay when speed is below 10%
            if speed_percent < 10.0:
                # Twice as fast decay (square the decay rate)
                decay_rate = self.ship.speed_decay_rate ** 2
            else:
                decay_rate = self.ship.speed_decay_rate
            
            self.time_dilation_factor *= decay_rate ** dt
        
        # Clamp to valid range (0.01x to 1.0x)
        self.time_dilation_factor = max(0.01, min(1.0, self.time_dilation_factor))
    
    def apply_shake_offset(self, x, y, shake_x, shake_y):
        """Apply screen shake offset to coordinates"""
        return x + shake_x, y + shake_y
    
    def init_ship(self):
        self.ship = Ship(self.current_width // 2, self.current_height // 2)
        self.ship.invulnerable = True
        self.ship.invulnerable_time = 3.0
    
    def spawn_asteroids(self, count=None):
        # New asteroid spawning system: 1 Large + 1 Medium + ((level-1) * random size 1-9)
        large_sizes = [9, 8, 7]  # XXXL, XXL, XL
        all_sizes = [1, 2, 3, 4, 5, 6, 7, 8, 9]  # All sizes for random spawning
        
        # Spawn 1 random large asteroid (XXXL, XXL, or XL) on edge
        random_large = random.choice(large_sizes)
        x, y = self.get_edge_position()
        self.asteroids.append(Asteroid(x, y, random_large))
        
        # Spawn 1 M asteroid on edge
        x, y = self.get_edge_position()
        self.asteroids.append(Asteroid(x, y, 5))
        
        # Spawn (level - 1) random asteroids of any size
        for _ in range(self.level - 1):
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
        if pygame.K_LEFT in self.keys_pressed:
            self.ship.rotate_left(dt)
            self.ship.is_spinning = True
        elif pygame.K_RIGHT in self.keys_pressed:
            self.ship.rotate_right(dt)
            self.ship.is_spinning = True
        else:
            self.ship.is_spinning = False
        if pygame.K_UP in self.keys_pressed:
            self.ship.thrust(dt)
        elif pygame.K_DOWN in self.keys_pressed:
            self.ship.reverse_thrust(dt)
        else:
            self.ship.stop_thrust()
        if pygame.K_SPACE in self.keys_pressed:
            self.shoot_continuous()
    
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
            
    
    def check_collisions(self):
        # Bullet vs Asteroid
        for bullet in self.bullets[:]:
            if not bullet.active:
                continue
            for asteroid in self.asteroids[:]:
                if not asteroid.active:
                    continue
                distance = (bullet.position - asteroid.position).magnitude()
                if distance < asteroid.radius:
                    # Hit!
                    bullet.active = False
                    asteroid.active = False
                    
                    # Add screen shake for all asteroid sizes (scaled)
                    # Size 8 = base shake (10 intensity, 0.5 duration)
                    # Size 9 = scaled up (12 intensity, 0.75 duration)
                    # Size 1 = very brief (1 intensity, 0.01 duration)
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
                    elif asteroid.size == 4:
                        self.trigger_screen_shake(4, 0.15)  # Small shake for size 4
                    elif asteroid.size == 3:
                        self.trigger_screen_shake(3, 0.10)  # Very small shake for size 3
                    elif asteroid.size == 2:
                        self.trigger_screen_shake(2, 0.05)  # Very small shake for size 2
                    elif asteroid.size == 1:
                        self.trigger_screen_shake(1, 0.01)  # Very brief shake for size 1
                    
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
        
        # Bullet vs UFO
        for bullet in self.bullets[:]:
            if not bullet.active:
                continue
            for ufo in self.ufos[:]:
                if not ufo.active:
                    continue
                distance = (bullet.position - ufo.position).magnitude()
                if distance < ufo.radius:
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
        
        # Ship vs Asteroid
        if self.ship.active and not self.ship.invulnerable:
            for asteroid in self.asteroids:
                if not asteroid.active:
                    continue
                distance = (self.ship.position - asteroid.position).magnitude()
                if distance < self.ship.radius + asteroid.radius:
                    # Collision!
                    if self.ship.shield_hits > 0:
                        # Shield absorbs hit
                        self.ship.shield_hits -= 1
                        self.ship.shield_recharge_time = 0  # Reset recharge timer
                        self.ship.shield_damage_timer = self.ship.shield_damage_duration  # Show shield visual
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
                        self.explosions.add_rainbow_explosion(self.ship.position.x, self.ship.position.y, 200)
                        self.ship.active = False
                        asteroid.active = False
                        self.lives -= 1
                        if self.lives <= 0:
                            # Game over - no screen shake
                            self.game_state = "game_over"
                            self.game_over_timer = 0  # Start game over timer
                        else:
                            # Still alive - trigger screen shake
                            self.trigger_screen_shake(7, 0.6)  # Level 7 shake for player death
                            self.init_ship()
                    break
        
        # Ship vs UFO
        if self.ship.active and not self.ship.invulnerable:
            for ufo in self.ufos:
                if not ufo.active:
                    continue
                distance = (self.ship.position - ufo.position).magnitude()
                if distance < self.ship.radius + ufo.radius:
                    # Collision!
                    if self.ship.shield_hits > 0:
                        # Shield absorbs hit
                        self.ship.shield_hits -= 1
                        self.ship.shield_recharge_time = 0  # Reset recharge timer
                        self.ship.shield_damage_timer = self.ship.shield_damage_duration  # Show shield visual
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
                        self.explosions.add_rainbow_explosion(self.ship.position.x, self.ship.position.y, 200)
                        self.ship.active = False
                        ufo.active = False
                        self.lives -= 1
                        if self.lives <= 0:
                            # Game over - no screen shake
                            self.game_state = "game_over"
                            self.game_over_timer = 0  # Start game over timer
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
                distance = (self.ship.position - bullet.position).magnitude()
                if distance < self.ship.radius + bullet.radius:
                    # Hit!
                    bullet.active = False
                    if self.ship.shield_hits > 0:
                        # Shield absorbs hit
                        self.ship.shield_hits -= 1
                        self.ship.shield_recharge_time = 0  # Reset recharge timer
                        self.ship.shield_damage_timer = self.ship.shield_damage_duration  # Show shield visual
                        
                        # Add shield hit particles
                        self.explosions.add_explosion(self.ship.position.x, self.ship.position.y, 
                                                    num_particles=25, 
                                                    color=(0, 100, 255))  # Blue shield hit explosion
                    else:
                        # No shield, ship destroyed
                        # Add rainbow explosion for dramatic death effect
                        self.explosions.add_rainbow_explosion(self.ship.position.x, self.ship.position.y, 200)
                        self.ship.active = False
                        self.lives -= 1
                        if self.lives <= 0:
                            # Game over - no screen shake
                            self.game_state = "game_over"
                            self.game_over_timer = 0  # Start game over timer
                        else:
                            # Still alive - trigger screen shake
                            self.trigger_screen_shake(7, 0.6)  # Level 7 shake for player death
                            self.init_ship()
                    break
    
    def update(self, dt):
        if self.game_state not in ["playing", "paused"]:
            return
        
        # Calculate time dilation based on player movement (Superhot-style)
        self.calculate_time_dilation(dt)
        
        # Calculate dilated time for non-player objects
        dilated_dt = dt * self.time_dilation_factor
            
        # Update ship (affected by time dilation like everything else)
        if self.ship:
            self.ship.update(dilated_dt, self.current_width, self.current_height, 1.0)
            # Update star field with ship velocity (affected by time dilation)
            self.star_field.update(self.ship.velocity, self.current_width, self.current_height)
            
            # Check for spinning trick achievement
            if self.ship.spinning_trick_shown and not self.show_spinning_trick:
                self.show_spinning_trick = True
                self.spinning_trick_timer = 10.0  # Show for 10 seconds
        
        # Update explosion particles (affected by time dilation)
        self.explosions.update(dilated_dt)
        
        # Update screen shake (NOT affected by time dilation - always normal speed)
        if self.screen_shake_timer > 0:
            self.screen_shake_timer -= dt
            if self.screen_shake_timer <= 0:
                self.screen_shake_intensity = 0
        
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
            self.level += 1
            self.spawn_asteroids()
            # Spawn UFOs for new level (1-3 randomly chosen x current level) after 5 second delay
            self.initial_ufo_timer = 5.0  # 5 second delay for new level
            self.ufos_to_spawn = 0  # Will be set when timer expires
        
        # Check collisions (affected by time dilation)
        self.check_collisions()
        
        # Update spinning trick message timer (affected by time dilation)
        if self.show_spinning_trick and self.spinning_trick_timer > 0:
            self.spinning_trick_timer -= dilated_dt
            if self.spinning_trick_timer <= 0:
                self.show_spinning_trick = False
    
    def draw(self):
        # Create a temporary surface for screen shake
        if self.screen_shake_intensity > 0:
            shake_x = random.uniform(-self.screen_shake_intensity, self.screen_shake_intensity)
            shake_y = random.uniform(-self.screen_shake_intensity, self.screen_shake_intensity)
            temp_surface = pygame.Surface((self.current_width, self.current_height))
            temp_surface.fill(BLACK)
            draw_surface = temp_surface
        else:
            shake_x = 0
            shake_y = 0
            draw_surface = self.screen
            self.screen.fill(BLACK)
        
        # Draw star field background
        if self.ship:
            self.star_field.draw(draw_surface, self.ship.velocity)
        
        if self.game_state == "playing":
            # Draw asteroids (background layer)
            for asteroid in self.asteroids:
                asteroid.draw(draw_surface, self.current_width, self.current_height)
            
            # Draw UFOs (middle layer)
            for ufo in self.ufos:
                ufo.draw(draw_surface)
            
            # Draw ship (player always visible on top of asteroids and UFOs)
            if self.ship:
                self.ship.draw(draw_surface)
            
            # Draw all bullets on top (player bullets + UFO bullets)
            for bullet in self.bullets:
                bullet.draw(draw_surface)
            for bullet in self.ufo_bullets:
                bullet.draw(draw_surface)
        
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
        
        # Draw spinning trick message
        if self.show_spinning_trick:
            spinning_font = pygame.font.Font(None, 48)
            spinning_text = spinning_font.render("I'll try spinning, that's a good trick!", True, YELLOW)
            text_rect = spinning_text.get_rect(center=(self.current_width//2, 50))
            draw_surface.blit(spinning_text, text_rect)
            
        
        
        if self.game_state == "waiting":
            # Title - yellow, bold, larger (44pt instead of 36pt)
            title_font = pygame.font.Font(None, 44)
            title_font.set_bold(True)
            title_text = title_font.render("C H U C K S T A R O I D S", True, YELLOW)
            title_rect = title_text.get_rect(center=(self.current_width//2, self.current_height//2 - 100))
            draw_surface.blit(title_text, title_rect)
            
            # Start text - centered
            start_text = font.render("Press SPACE to start", True, YELLOW)
            start_rect = start_text.get_rect(center=(self.current_width//2, self.current_height//2 - 50))
            draw_surface.blit(start_text, start_rect)
            
            # Controls - centered, smaller font (18pt instead of 36pt)
            controls_font = pygame.font.Font(None, 18)
            controls_text = controls_font.render("Arrow Keys: Move | Space: Shoot | P: Pause | ESC: Quit", True, (200, 200, 200))
            controls_rect = controls_text.get_rect(center=(self.current_width//2, self.current_height//2 + 20))
            draw_surface.blit(controls_text, controls_rect)
        elif self.game_state == "game_over":
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
        # Reset UFO spawn timer for new game
        self.initial_ufo_timer = 5.0  # 5 second delay before first UFOs
        self.game_over_timer = 0  # Reset game over timer
        # Reset time dilation
        self.time_dilation_factor = 1.0
    
    def run(self):
        self.running = True
        
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

def main():
    print("Asteroids Deluxe")
    print("Controls:")
    print("  Arrow Keys: Rotate & Thrust")
    print("  Space: Shoot")
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