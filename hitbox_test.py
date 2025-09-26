import pygame
import math
import random
import os
import sys

# Initialize Pygame
pygame.init()

# Constants
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 900  # Increased height for scrollable content
FPS = 60

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
CYAN = (0, 255, 255)
DIM_GREEN = (0, 150, 0)  # Dim green for hitboxes

def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

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

class Asteroid(GameObject):
    def __init__(self, x, y, size=3):
        super().__init__(x, y)
        self.size = size  # 9=XXXL, 8=XXL, 7=XL, 6=L, 5=M, 4=S, 3=XS, 2=XXS, 1=XXS
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
            self.image = None
        
        # Create classic irregular shape (fallback)
        self.points = self.create_shape()
    
    def get_hitbox_center(self):
        """Get the actual hitbox center position (asteroid position + offset)"""
        return Vector2D(
            self.position.x + self.hitbox_offset_x,
            self.position.y + self.hitbox_offset_y
        )
    
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
    
    def draw_hitbox(self, screen):
        """Draw the hitbox visualization"""
        if not self.active:
            return
        
        # Get hitbox center
        hitbox_center = self.get_hitbox_center()
        
        # Draw hitbox circle at the actual hitbox center
        pygame.draw.circle(screen, DIM_GREEN, (int(hitbox_center.x), int(hitbox_center.y)), self.radius, 2)
        
        # Draw line from asteroid center to hitbox center
        pygame.draw.line(screen, YELLOW, 
                        (int(self.position.x), int(self.position.y)), 
                        (int(hitbox_center.x), int(hitbox_center.y)), 2)
        
        # Draw size and radius text
        font = pygame.font.Font(None, 24)
        size_text = font.render(f"Size {self.size}", True, WHITE)
        size_rect = size_text.get_rect(center=(self.position.x, self.position.y - self.radius - 30))
        screen.blit(size_text, size_rect)
        
        radius_text = font.render(f"R: {self.radius}", True, WHITE)
        radius_rect = radius_text.get_rect(center=(self.position.x, self.position.y + self.radius + 30))
        screen.blit(radius_text, radius_rect)
        
        # Draw offset text
        offset_text = font.render(f"Offset: ({self.hitbox_offset_x:.1f}, {self.hitbox_offset_y:.1f})", True, CYAN)
        offset_rect = offset_text.get_rect(center=(self.position.x, self.position.y + self.radius + 60))
        screen.blit(offset_text, offset_rect)

def main():
    # Create screen
    global SCREEN_WIDTH, SCREEN_HEIGHT
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)
    pygame.display.set_caption("Asteroid Hitbox Test - Exact chuckstaroidsv2.py Code")
    clock = pygame.time.Clock()
    
    # Scroll offset
    scroll_y = 0
    scroll_speed = 5
    
    # Create asteroids for all 9 sizes
    asteroids = []
    
    # Top row: sizes 1-5
    top_y = SCREEN_HEIGHT // 3
    top_spacing = SCREEN_WIDTH // 6  # 5 asteroids across
    top_start_x = SCREEN_WIDTH // 6  # Start position for top row
    
    for size in range(1, 6):  # Sizes 1-5
        x = top_start_x + (size - 1) * top_spacing
        asteroid = Asteroid(x, top_y, size)
        asteroid.velocity = Vector2D(0, 0)  # Stop movement for testing
        asteroids.append(asteroid)
    
    # Bottom row: sizes 6-9 (200px below top row, 100px spacing between 7,8,9)
    bottom_y = top_y + 300  # 200px between rows (300 for visual spacing)
    bottom_spacing = 350  # 100px spacing between asteroids 6-9
    bottom_start_x = SCREEN_WIDTH // 2 - (3 * bottom_spacing) // 2  # Center the 4 asteroids
    
    for size in range(6, 10):  # Sizes 6-9
        x = bottom_start_x + (size - 6) * bottom_spacing
        asteroid = Asteroid(x, bottom_y, size)
        asteroid.velocity = Vector2D(0, 0)  # Stop movement for testing
        asteroids.append(asteroid)
    
    # Main game loop
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_UP:
                    scroll_y += scroll_speed
                elif event.key == pygame.K_DOWN:
                    scroll_y -= scroll_speed
            elif event.type == pygame.VIDEORESIZE:
                # Handle window resize
                SCREEN_WIDTH, SCREEN_HEIGHT = event.w, event.h
        
        # Update asteroids
        for asteroid in asteroids:
            asteroid.update(0.016)  # Fixed dt for consistent rotation
        
        # Draw everything
        screen.fill(BLACK)
        
        # Apply scroll offset
        scroll_offset = Vector2D(0, scroll_y)
        
        # Draw title
        title_font = pygame.font.Font(None, 48)
        title_text = title_font.render("Asteroid Hitbox Test - Exact chuckstaroidsv2.py Code", True, WHITE)
        title_rect = title_text.get_rect(center=(SCREEN_WIDTH // 2, 50 + scroll_y))
        screen.blit(title_text, title_rect)
        
        # Draw instructions
        instruction_font = pygame.font.Font(None, 24)
        instruction_text = instruction_font.render("Dim green circles = hitboxes, Yellow lines = offset from center, Press ESC to exit", True, WHITE)
        instruction_rect = instruction_text.get_rect(center=(SCREEN_WIDTH // 2, 80 + scroll_y))
        screen.blit(instruction_text, instruction_rect)
        
        # Draw scroll instructions
        scroll_instruction = instruction_font.render("Use UP/DOWN arrows to scroll", True, CYAN)
        scroll_rect = scroll_instruction.get_rect(center=(SCREEN_WIDTH // 2, 110 + scroll_y))
        screen.blit(scroll_instruction, scroll_rect)
        
        # Draw asteroids with hitboxes
        for asteroid in asteroids:
            # Create a temporary asteroid with scroll offset
            temp_asteroid = Asteroid(asteroid.position.x, asteroid.position.y + scroll_y, asteroid.size)
            temp_asteroid.image = asteroid.image
            temp_asteroid.rotation_angle = asteroid.rotation_angle
            temp_asteroid.radius = asteroid.radius
            temp_asteroid.hitbox_offset_x = asteroid.hitbox_offset_x
            temp_asteroid.hitbox_offset_y = asteroid.hitbox_offset_y
            temp_asteroid.points = asteroid.points
            
            temp_asteroid.draw(screen)
            temp_asteroid.draw_hitbox(screen)
        
        # Draw legend
        legend_y = SCREEN_HEIGHT - 50 + scroll_y
        legend_font = pygame.font.Font(None, 20)
        legend_text = legend_font.render("Top: Sizes 1-5 | Bottom: Sizes 6-9 | Using exact game code and hitbox calculations", True, WHITE)
        legend_rect = legend_text.get_rect(center=(SCREEN_WIDTH // 2, legend_y))
        screen.blit(legend_text, legend_rect)
        
        pygame.display.flip()
        clock.tick(FPS)
    
    pygame.quit()

if __name__ == "__main__":
    main()