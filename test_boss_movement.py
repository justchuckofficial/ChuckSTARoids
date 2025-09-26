import pygame
import sys
import math

# Initialize Pygame
pygame.init()

# Constants
SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 750
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
MAGENTA = (255, 0, 255)
YELLOW = (255, 255, 0)

class Vector2D:
    def __init__(self, x=0, y=0):
        self.x = x
        self.y = y

class BossTester:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Boss Movement Test")
        self.clock = pygame.time.Clock()
        
        # Load boss image
        try:
            self.boss_image = pygame.image.load("stard.gif")
            self.boss_image = pygame.transform.scale(self.boss_image, (500, 500))
            print(f"Loaded boss sprite: 500x500")
        except pygame.error as e:
            print(f"Error loading stard.gif: {e}")
            self.boss_image = None
        
        # Boss properties (copied from the game)
        self.position = Vector2D(500, 300)  # Start in middle
        self.speed = 60
        self.amplitude = 10
        self.frequency = 0.1
        self.sine_timer = 0.0
        self.center_y = 300
        self.flip_horizontal = False
        
        # Hitbox points (adjusted coordinates - shifted -50 more left)
        self.hitbox_points = [
            (-52, 270), (-154, 246), (-199, 207), (-214, 142), (-299, 147),
            (-311, 194), (-413, 228), (-545, 232), (-546, 250), (-232, 323), (-52, 281)
        ]
        
        self.font = pygame.font.Font(None, 24)
        self.show_hitbox = True
        
    def update_boss(self, dt):
        # Update sine wave timer
        self.sine_timer += dt
        
        # Calculate sine wave Y offset
        sine_offset = self.amplitude * math.sin(self.frequency * self.sine_timer * 2 * math.pi)
        
        # Update position (moving horizontally, sine wave vertically)
        self.position.x += self.speed * dt
        self.position.y = self.center_y + sine_offset
        
        # Wrap around screen
        if self.position.x > SCREEN_WIDTH + 300:
            self.position.x = -300
    
    def draw_boss(self):
        if self.boss_image:
            # Draw boss at position, offset by -250 to center the 500x500 image
            x = self.position.x - 250
            y = self.position.y - 250
            self.screen.blit(self.boss_image, (x, y))
            
            # Draw boss center point
            pygame.draw.circle(self.screen, RED, (int(self.position.x), int(self.position.y)), 5)
    
    def draw_hitbox(self):
        if not self.show_hitbox or len(self.hitbox_points) < 3:
            return
            
        # Convert local hitbox points to world coordinates
        # Boss sprite is drawn at (position.x - 250, position.y - 250) to center the 500x500 image
        world_points = []
        for point in self.hitbox_points:
            world_x = self.position.x - 250 + (point[0] if not self.flip_horizontal else -point[0])
            world_y = self.position.y - 250 + point[1]
            world_points.append((world_x, world_y))
        
        # Draw polygon
        pygame.draw.polygon(self.screen, MAGENTA, world_points, 2)
        
        # Draw vertices
        for point in world_points:
            pygame.draw.circle(self.screen, YELLOW, (int(point[0]), int(point[1])), 3)
    
    def run(self):
        running = True
        
        while running:
            dt = self.clock.tick(60) / 1000.0  # Convert to seconds
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        self.show_hitbox = not self.show_hitbox
                    elif event.key == pygame.K_ESCAPE:
                        running = False
            
            # Update boss
            self.update_boss(dt)
            
            # Clear screen
            self.screen.fill(WHITE)
            
            # Draw boss and hitbox
            self.draw_boss()
            self.draw_hitbox()
            
            # Draw info
            info_lines = [
                f"Position: ({self.position.x:.1f}, {self.position.y:.1f})",
                f"Sine Timer: {self.sine_timer:.1f}",
                f"Sine Offset: {self.amplitude * math.sin(self.frequency * self.sine_timer * 2 * math.pi):.1f}",
                f"Hitbox: {'ON' if self.show_hitbox else 'OFF'}",
                "",
                "SPACE: Toggle hitbox",
                "ESC: Quit"
            ]
            
            y_offset = 10
            for line in info_lines:
                text = self.font.render(line, True, RED)
                self.screen.blit(text, (10, y_offset))
                y_offset += 25
            
            # Update display
            pygame.display.flip()
        
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    tester = BossTester()
    tester.run()
