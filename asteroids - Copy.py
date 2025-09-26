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
        self.thrust_power = 140.625  # 25% increase from 112.5
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
        self.speed_decay_rate = 0.55  # Multiplier per second (45% decay per second)
        
        # Rotation tracking for "spinning trick" achievement
        self.total_rotations = 0.0
        self.last_angle = 0.0
        self.spinning_trick_shown = False
        self.is_spinning = False  # Track if currently spinning
        
        # Load ship image
        try:
            self.image = pygame.image.load("xwing.gif")
            self.image = pygame.transform.scale(self.image, (40, 40))
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
    
    def update(self, dt, screen_width=None, screen_height=None):
        super().update(dt, screen_width, screen_height)
        if self.invulnerable:
            self.invulnerable_time -= dt
            if self.invulnerable_time <= 0:
                self.invulnerable = False
        
        # Update shoot timer
        if self.shoot_timer > 0:
            self.shoot_timer -= dt
        
        # Update shield recharge
        if self.shield_hits < self.max_shield_hits:
            self.shield_recharge_time += dt
            if self.shield_recharge_time >= self.shield_recharge_duration:
                self.shield_hits += 1
                self.shield_recharge_time = 0
        
        # Update shield damage visual timer
        if self.shield_damage_timer > 0:
            self.shield_damage_timer -= dt
        
        # Apply speed decay
        if not self.thrusting:
            # Only decay when not thrusting
            self.velocity.x *= self.speed_decay_rate ** dt
            self.velocity.y *= self.speed_decay_rate ** dt
        
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
        
        # Draw shield (only when taking damage)
        # Draw shield circles with fade in/out based on shield status
        if self.shield_hits > 0:
            shield_radius = self.radius + 15
            
            # Calculate fade intensity based on shield status
            if self.shield_hits < self.max_shield_hits:
                # Fade in during recharge
                recharge_progress = self.shield_recharge_time / self.shield_recharge_duration
                fade_intensity = 0.3 + 0.7 * recharge_progress  # Fade from 30% to 100%
            else:
                # Completely invisible when at full shields (unless recently damaged)
                fade_intensity = 0.0  # Completely invisible when at full shields
            
            # Add pulsing effect if recently damaged
            if self.shield_damage_timer > 0:
                pulse = (self.shield_damage_duration - self.shield_damage_timer) / self.shield_damage_duration
                pulse_intensity = 0.5 + 0.5 * math.sin(pulse * math.pi * 8)  # Fast pulse
                fade_intensity = pulse_intensity  # Override fade when damaged
            
            # Only draw circles if they should be visible
            if fade_intensity > 0:
                # Draw circles for each shield hit (outline only, no fill)
                for i in range(self.shield_hits):
                    alpha = int(255 * fade_intensity)
                    color = (0, 100, 255, alpha)
                    pygame.draw.circle(screen, (0, 100, 255), 
                                    (int(self.position.x), int(self.position.y)), 
                                    shield_radius + i * 5, int(3 * fade_intensity))
        

class Bullet(GameObject):
    def __init__(self, x, y, vx, vy, is_ufo_bullet=False):
        super().__init__(x, y, vx, vy)
        self.radius = 4  # Increased for better hit detection with elongated bullets
        self.lifetime = 3.0  # seconds
        self.age = 0
        self.is_ufo_bullet = is_ufo_bullet
        # Calculate angle from velocity for rotation
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
            # New size hierarchy scaling (custom sizes)
            base_size = 100  # Base size for 100% scale
            scale_factors = {9: 7.5, 8: 6.0, 7: 4.5, 6: 3.0, 5: 1.5, 4: 1.0, 3: 0.75, 2: 0.5, 1: 0.25}
            scale = int(base_size * scale_factors.get(size, 1.0))
            self.image = pygame.transform.scale(self.image, (scale, scale))
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
    
    def update(self, dt, screen_width=None, screen_height=None, player_speed=0):
        super().update(dt, screen_width, screen_height)
        # Multiply rotation speed based on player speed
        speed_multiplier = 1.0 + (player_speed / 1000000000.0) * 4.0  # Scale with player speed (doubled)
        self.rotation_angle += self.rotation_speed * speed_multiplier * dt
    
    def draw(self, screen):
        if not self.active:
            return
        
        # Classic Asteroids Deluxe screen wrapping - no off-screen culling
        if self.image:
            # Draw asteroid using image
            rotated_asteroid = pygame.transform.rotate(self.image, -math.degrees(self.rotation_angle))
            asteroid_rect = rotated_asteroid.get_rect(center=(int(self.position.x), int(self.position.y)))
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
                # Translate
                rotated_points.append((rx + self.position.x, ry + self.position.y))
            
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

class UFO(GameObject):
    def __init__(self, x, y):
        super().__init__(x, y)
        self.radius = 26  # Half as big (52 * 0.5 = 26)
        self.speed = 100
        self.shoot_timer = 0
        self.shoot_interval = 1.0  # 2x faster shooting (was 2.0, now 1.0)
        self.direction = 1 if random.random() < 0.5 else -1
        self.velocity = Vector2D(self.direction * self.speed, 0)
        self.oscillation = 0
        self.oscillation_speed = 2
        
        # Load UFO image
        try:
            self.image = pygame.image.load("tie.gif")
            # Convert to 32-bit RGBA for smooth scaling compatibility
            self.image = self.image.convert_alpha()
            # Scale image to match the new UFO radius (77 * 2 = 154 pixels)
            image_size = int(self.radius * 2)
            self.image = pygame.transform.smoothscale(self.image, (image_size, image_size))  # Scale to match hitbox
        except Exception as e:
            print(f"Failed to load UFO image: {e}")  # Debug
            self.image = None
    
    def update(self, dt, ship_pos, screen_width=None, screen_height=None):
        super().update(dt, screen_width, screen_height)
        
        # Oscillate up and down
        self.oscillation += self.oscillation_speed * dt
        self.velocity.y = math.sin(self.oscillation) * 50
        
        # Shoot at ship
        self.shoot_timer += dt
        if self.shoot_timer >= self.shoot_interval:
            self.shoot_timer = 0
            return True  # Signal to create bullet
        return False
    
    def draw(self, screen):
        if not self.active:
            return
            
        if self.image:
            # Draw UFO using image
            ufo_rect = self.image.get_rect(center=(int(self.position.x), int(self.position.y)))
            screen.blit(self.image, ufo_rect)
        else:
            # Fallback to original UFO shape
            pygame.draw.ellipse(screen, WHITE, 
                              (self.position.x - self.radius, self.position.y - self.radius/2,
                               self.radius * 2, self.radius))
            pygame.draw.rect(screen, WHITE,
                            (self.position.x - self.radius/2, self.position.y - self.radius/4,
                             self.radius, self.radius/2))
        
        

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
        # Don't generate stars here - will be generated when screen size is known
    
    def generate_stars(self, screen_width, screen_height):
        self.stars = []
        for _ in range(self.num_stars):
            star = {
                'x': random.uniform(0, screen_width),
                'y': random.uniform(0, screen_height),
                'speed': random.uniform(0.5, 3.0),
                'brightness': random.uniform(0.3, 1.0),
                'size': random.uniform(0.5, 2.0)
            }
            self.stars.append(star)
    
    def update(self, ship_velocity, screen_width, screen_height):
        speed_factor = min(ship_velocity.magnitude() / 100.0, 5.0)  # Cap at 5x speed
        
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
            # Calculate brightness based on speed
            speed_factor = min(ship_velocity.magnitude() / 100.0, 5.0)
            brightness = int(255 * star['brightness'] * min(speed_factor, 2.0))
            # Clamp brightness to valid range
            brightness = max(0, min(255, brightness))
            color = (brightness, brightness, brightness)
            
            # Draw star with trail effect (only when going 42% of max speed)
            if speed_factor > 0.42:
                # Draw trail
                trail_length = min(speed_factor * 10, 30)
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
        
        # Spinning trick message
        self.spinning_trick_timer = 0.0
        self.show_spinning_trick = False
        
        # Screen shake variables
        self.screen_shake_intensity = 0
        self.screen_shake_duration = 0
        self.screen_shake_timer = 0
        self.game_over_timer = 0  # Timer for game over state
        
    def trigger_screen_shake(self, intensity, duration):
        """Trigger screen shake effect"""
        self.screen_shake_intensity = intensity
        self.screen_shake_duration = duration
        self.screen_shake_timer = duration
    
    def apply_shake_offset(self, x, y, shake_x, shake_y):
        """Apply screen shake offset to coordinates"""
        return x + shake_x, y + shake_y
    
    def init_ship(self):
        self.ship = Ship(self.current_width // 2, self.current_height // 2)
        self.ship.invulnerable = True
        self.ship.invulnerable_time = 3.0
    
    def spawn_asteroids(self, count=None):
        # New asteroid spawning system: level * ((1x random large) + 1 M asteroid)
        large_sizes = [9, 8, 7]  # XXXL, XXL, XL
        
        # Spawn level * ((1x random large) + 1 M asteroid)
        for _ in range(self.level):
            # Spawn 1 random large asteroid (XXXL, XXL, or XL) on edge
            random_large = random.choice(large_sizes)
            x, y = self.get_edge_position()
            self.asteroids.append(Asteroid(x, y, random_large))
            
            # Spawn 1 M asteroid on edge
            x, y = self.get_edge_position()
            self.asteroids.append(Asteroid(x, y, 5))
    
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
        
        self.ufos.append(UFO(x, y))
    
    def spawn_ufo_from_corner(self):
        # Pick a random corner
        corners = [
            (0, 0),  # Top-left
            (self.current_width, 0),  # Top-right
            (0, self.current_height),  # Bottom-left
            (self.current_width, self.current_height)  # Bottom-right
        ]
        x, y = random.choice(corners)
        self.ufos.append(UFO(x, y))
    
    def handle_input(self, dt):
        # R key restart works at any time
        if pygame.K_r in self.keys_pressed:
            self.restart_game()
            return
            
        if self.game_state != "playing":
            return
            
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
            bullet = Bullet(bullet_x, bullet_y, vx, vy, is_ufo_bullet=False)
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
            bullet = Bullet(bullet_x, bullet_y, vx, vy, is_ufo_bullet=False)
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
                    
                    # Add screen shake for size 9 asteroids
                    if asteroid.size == 9:
                        self.trigger_screen_shake(8, 0.5)  # Medium shake for 0.5 seconds
                    
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
                    
                    # Add explosion particles (75% electric blue, 20% firey, 5% white)
                    total_particles = int(40 * 1.5 * 1.5)  # 50% more particles (60 * 1.5 = 90)
                    
                    # 75% electric blue particles
                    self.explosions.add_explosion(ufo.position.x, ufo.position.y, 
                                                num_particles=int(total_particles * 0.75), 
                                                color=(0, 150, 255), is_ufo=True)  # Electric blue
                    # 20% firey particles
                    self.explosions.add_explosion(ufo.position.x, ufo.position.y, 
                                                num_particles=int(total_particles * 0.20), 
                                                color=(255, 50, 0), is_ufo=True)  # Firey red
                    # 5% white particles
                    self.explosions.add_explosion(ufo.position.x, ufo.position.y, 
                                                num_particles=int(total_particles * 0.05), 
                                                color=(255, 255, 255), is_ufo=True)  # White
                    
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
                        # Trigger screen shake for player death
                        self.trigger_screen_shake(15, 0.8)  # Strong shake for 0.8 seconds
                        self.ship.active = False
                        asteroid.active = False
                        self.lives -= 1
                        if self.lives <= 0:
                            self.game_state = "game_over"
                            self.game_over_timer = 0  # Start game over timer
                        else:
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
                        # Trigger screen shake for player death
                        self.trigger_screen_shake(15, 0.8)  # Strong shake for 0.8 seconds
                        self.ship.active = False
                        ufo.active = False
                        self.lives -= 1
                        if self.lives <= 0:
                            self.game_state = "game_over"
                            self.game_over_timer = 0  # Start game over timer
                        else:
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
                    else:
                        # No shield, ship destroyed
                        # Add rainbow explosion for dramatic death effect
                        self.explosions.add_rainbow_explosion(self.ship.position.x, self.ship.position.y, 200)
                        # Trigger screen shake for player death
                        self.trigger_screen_shake(15, 0.8)  # Strong shake for 0.8 seconds
                        self.ship.active = False
                        self.lives -= 1
                        if self.lives <= 0:
                            self.game_state = "game_over"
                            self.game_over_timer = 0  # Start game over timer
                        else:
                            self.init_ship()
                    break
    
    def update(self, dt):
        if self.game_state not in ["playing", "paused"]:
            return
            
        # Update ship
        if self.ship:
            self.ship.update(dt, self.current_width, self.current_height)
            # Update star field with ship velocity
            self.star_field.update(self.ship.velocity, self.current_width, self.current_height)
            
            # Check for spinning trick achievement
            if self.ship.spinning_trick_shown and not self.show_spinning_trick:
                self.show_spinning_trick = True
                self.spinning_trick_timer = 10.0  # Show for 10 seconds
        
        # Update explosion particles
        self.explosions.update(dt)
        
        # Update screen shake
        if self.screen_shake_timer > 0:
            self.screen_shake_timer -= dt
            if self.screen_shake_timer <= 0:
                self.screen_shake_intensity = 0
        
        # Update game over timer and stop screen shake after 1 second
        if self.game_state == "game_over":
            self.game_over_timer += dt
            if self.game_over_timer >= 1.0:  # After 1 second
                self.screen_shake_intensity = 0  # Stop screen shake
                self.screen_shake_timer = 0  # Also stop the timer
        
        # Update bullets
        for bullet in self.bullets[:]:
            bullet.update(dt, self.current_width, self.current_height)
            if not bullet.active:
                self.bullets.remove(bullet)
        
        # Update asteroids
        for asteroid in self.asteroids[:]:
            player_speed = self.ship.velocity.magnitude() if self.ship else 0
            asteroid.update(dt, self.current_width, self.current_height, player_speed)
            if not asteroid.active:
                self.asteroids.remove(asteroid)
        
        # Update UFOs
        for ufo in self.ufos[:]:
            should_shoot = ufo.update(dt, self.ship.position if self.ship else Vector2D(0, 0), self.current_width, self.current_height)
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
        
        # Update UFO bullets
        for bullet in self.ufo_bullets[:]:
            bullet.update(dt, self.current_width, self.current_height)
            if not bullet.active:
                self.ufo_bullets.remove(bullet)
        
        # Spawn UFOs with 5-second delay, then from random corner
        if self.initial_ufo_timer > 0:
            self.initial_ufo_timer -= dt
            if self.initial_ufo_timer <= 0:
                # Determine how many UFOs to spawn (1-3 randomly chosen x current level)
                self.ufos_to_spawn = random.randint(1, 3) * self.level
                self.ufo_spawn_delay = 0  # Start spawning immediately
        elif self.ufos_to_spawn > 0:
            # Spawn UFOs one per second from random corner
            self.ufo_spawn_delay += dt
            if self.ufo_spawn_delay >= 1.0:  # 1 second between spawns
                self.ufo_spawn_delay = 0
                self.spawn_ufo_from_corner()
                self.ufos_to_spawn -= 1
        
        # Check for level complete
        if len(self.asteroids) == 0:
            self.level += 1
            self.spawn_asteroids()
            # Spawn UFOs for new level (1-3 randomly chosen x current level) after 5 second delay
            self.initial_ufo_timer = 5.0  # 5 second delay for new level
            self.ufos_to_spawn = 0  # Will be set when timer expires
        
        # Check collisions
        self.check_collisions()
        
        # Update spinning trick message timer
        if self.show_spinning_trick and self.spinning_trick_timer > 0:
            self.spinning_trick_timer -= dt
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
            # Draw ship
            if self.ship:
                self.ship.draw(draw_surface)
            
            # Draw bullets
            for bullet in self.bullets:
                bullet.draw(draw_surface)
            
            # Draw asteroids
            for asteroid in self.asteroids:
                asteroid.draw(draw_surface)
            
            # Draw UFOs
            for ufo in self.ufos:
                ufo.draw(draw_surface)
            
            # Draw UFO bullets
            for bullet in self.ufo_bullets:
                bullet.draw(draw_surface)
        
        # Create font for UI elements
        font = pygame.font.Font(None, 36)
        
        # Draw UI (only during gameplay)
        if self.game_state == "playing":
            score_text = font.render(f"Score: {self.score}", True, WHITE)
            lives_text = font.render(f"Lives: {self.lives}", True, WHITE)
            level_text = font.render(f"Level: {self.level}", True, WHITE)
            
            draw_surface.blit(score_text, (10, 10))
            draw_surface.blit(lives_text, (10, 50))
            draw_surface.blit(level_text, (10, 90))
            
            # Draw shield info
            if self.ship:
                shield_text = font.render(f"Shield: {self.ship.shield_hits}/{self.ship.max_shield_hits}", True, (0, 100, 255))
                draw_surface.blit(shield_text, (10, 130))
        
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