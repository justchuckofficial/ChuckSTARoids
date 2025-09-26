import pygame
import sys

# Initialize Pygame
pygame.init()

# Constants
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
GRAY = (128, 128, 128)
LIGHT_GRAY = (200, 200, 200)
YELLOW = (255, 255, 0)

class PolygonDrawer:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Boss Box Polygon Drawer")
        self.clock = pygame.time.Clock()
        
        # Polygon drawing state
        self.points = [(823, 430), (670, 394), (602, 335), (580, 237), (452, 245), 
                      (433, 316), (280, 367), (82, 372), (80, 400), (553, 510), (822, 447)]
        self.completed = True
        self.font = pygame.font.Font(None, 24)
        self.small_font = pygame.font.Font(None, 18)
        
        # UI layout
        self.drawing_area_width = SCREEN_WIDTH - 300
        self.sidebar_width = 300
        
        # Boss sprite
        self.boss_image = None
        self.boss_rect = None
        self.load_boss()
    
    def load_boss(self):
        """Load the boss sprite from stard.gif"""
        try:
            self.boss_image = pygame.image.load("stard.gif")
            # Scale the boss to 750x750 pixels
            self.boss_image = pygame.transform.scale(self.boss_image, (750, 750))
            
            # Position boss in center of drawing area
            self.boss_rect = self.boss_image.get_rect()
            self.boss_rect.center = (self.drawing_area_width // 2, SCREEN_HEIGHT // 2)
            print(f"Loaded boss sprite: stard.gif (scaled to 750x750)")
            
        except pygame.error as e:
            print(f"Error loading stard.gif: {e}")
            self.create_placeholder_boss()
    
    def create_placeholder_boss(self):
        """Create a simple placeholder boss if stard.gif is not found"""
        # Create a simple boss shape
        boss_surface = pygame.Surface((120, 80))
        boss_surface.set_colorkey(BLACK)
        
        # Draw a simple boss shape (rectangle with some details)
        pygame.draw.rect(boss_surface, RED, (10, 20, 100, 40))
        pygame.draw.rect(boss_surface, WHITE, (20, 25, 20, 10))
        pygame.draw.rect(boss_surface, WHITE, (60, 25, 20, 10))
        pygame.draw.rect(boss_surface, YELLOW, (45, 45, 10, 5))
        
        self.boss_image = boss_surface
        self.boss_rect = self.boss_image.get_rect()
        self.boss_rect.center = (self.drawing_area_width // 2, SCREEN_HEIGHT // 2)
        print("Created placeholder boss sprite")
        
    def add_point(self, pos):
        """Add a point to the polygon"""
        if not self.completed:
            self.points.append(pos)
            print(f"Added point {len(self.points)}: ({pos[0]}, {pos[1]})")
    
    def complete_polygon(self):
        """Complete the polygon"""
        if len(self.points) >= 3:
            self.completed = True
            print(f"Polygon completed with {len(self.points)} points!")
            self.print_points_list()
        else:
            print("Need at least 3 points to complete polygon!")
    
    def reset_polygon(self):
        """Reset the polygon"""
        self.points = []
        self.completed = False
        print("Polygon reset!")
    
    def print_points_list(self):
        """Print the points list in a format easy to copy"""
        print("\n" + "="*50)
        print("POLYGON POINTS:")
        print("="*50)
        for i, point in enumerate(self.points):
            print(f"Point {i+1}: ({point[0]}, {point[1]})")
        print("="*50)
        print("\nCopy-friendly format:")
        points_str = ", ".join([f"({p[0]}, {p[1]})" for p in self.points])
        print(f"[{points_str}]")
        print("="*50)
    
    def draw_ui(self):
        """Draw the UI elements"""
        # Draw sidebar background
        sidebar_rect = pygame.Rect(self.drawing_area_width, 0, self.sidebar_width, SCREEN_HEIGHT)
        pygame.draw.rect(self.screen, LIGHT_GRAY, sidebar_rect)
        pygame.draw.rect(self.screen, BLACK, sidebar_rect, 2)
        
        # Title
        title_text = self.font.render("Boss Box Polygon", True, BLACK)
        self.screen.blit(title_text, (self.drawing_area_width + 10, 20))
        
        # Instructions
        instructions = [
            "Instructions:",
            "• Click to add points",
            "• Press C to complete",
            "• Press R to reset",
            "• Press ESC to quit"
        ]
        
        y_offset = 60
        for instruction in instructions:
            text = self.small_font.render(instruction, True, BLACK)
            self.screen.blit(text, (self.drawing_area_width + 10, y_offset))
            y_offset += 25
        
        # Status
        y_offset += 20
        if self.completed:
            status_text = self.font.render("Status: COMPLETED", True, GREEN)
        else:
            status_text = self.font.render(f"Status: {len(self.points)} points", True, RED)
        self.screen.blit(status_text, (self.drawing_area_width + 10, y_offset))
        
        # Points list
        y_offset += 50
        points_title = self.font.render("Points:", True, BLACK)
        self.screen.blit(points_title, (self.drawing_area_width + 10, y_offset))
        y_offset += 30
        
        for i, point in enumerate(self.points):
            point_text = f"{i+1}. ({point[0]}, {point[1]})"
            text = self.small_font.render(point_text, True, BLACK)
            self.screen.blit(text, (self.drawing_area_width + 10, y_offset))
            y_offset += 20
    
    def draw_polygon(self):
        """Draw the current polygon"""
        if len(self.points) < 2:
            return
        
        # Draw lines between points
        for i in range(len(self.points) - 1):
            pygame.draw.line(self.screen, BLUE, self.points[i], self.points[i + 1], 2)
        
        # If completed, draw closing line and fill
        if self.completed and len(self.points) >= 3:
            pygame.draw.line(self.screen, BLUE, self.points[-1], self.points[0], 2)
            # Draw filled polygon (semi-transparent)
            if len(self.points) >= 3:
                overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
                overlay.set_alpha(50)
                pygame.draw.polygon(overlay, YELLOW, self.points)
                self.screen.blit(overlay, (0, 0))
        
        # Draw points
        for i, point in enumerate(self.points):
            color = GREEN if i == 0 else RED if i == len(self.points) - 1 else BLUE
            pygame.draw.circle(self.screen, color, point, 5)
            
            # Draw point numbers
            number_text = self.small_font.render(str(i + 1), True, BLACK)
            text_rect = number_text.get_rect(center=(point[0], point[1] - 20))
            self.screen.blit(number_text, text_rect)
    
    def run(self):
        """Main game loop"""
        running = True
        
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_c:
                        self.complete_polygon()
                    elif event.key == pygame.K_r:
                        self.reset_polygon()
                
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Left click
                        mouse_pos = event.pos
                        # Only add points if clicking in drawing area
                        if mouse_pos[0] < self.drawing_area_width:
                            self.add_point(mouse_pos)
            
            # Clear screen
            self.screen.fill(WHITE)
            
            # Draw drawing area border
            drawing_rect = pygame.Rect(0, 0, self.drawing_area_width, SCREEN_HEIGHT)
            pygame.draw.rect(self.screen, GRAY, drawing_rect, 2)
            
            # Draw boss sprite
            if self.boss_image and self.boss_rect:
                self.screen.blit(self.boss_image, self.boss_rect)
            
            # Draw polygon
            self.draw_polygon()
            
            # Draw UI
            self.draw_ui()
            
            # Update display
            pygame.display.flip()
            self.clock.tick(60)
        
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    drawer = PolygonDrawer()
    drawer.run()
