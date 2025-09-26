import pygame
import math
import sys
import os

def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

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
GRAY = (128, 128, 128)
DARK_GRAY = (64, 64, 64)

class UFOSizer:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("UFO Sizer - Press 1-5 to select, Up/Down to resize, P to print data")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 24)
        self.small_font = pygame.font.Font(None, 18)
        
        # UFO data based on the game's UFO class - using exact game values
        self.ufo_types = {
            "aggressive": {
                "name": "Aggressive",
                "image_file": "tie.gif",
                "base_radius": 26,  # From game: self.radius = 26
                "base_image_size": 52,  # From game: int(self.radius * 2) = 52
                "current_scale": 1.000,  # From game hitbox data
                "hitbox_offset_x": 0,  # From game hitbox data
                "hitbox_offset_y": 0,  # From game hitbox data
                "color": (200, 200, 200)  # Dim white
            },
            "defensive": {
                "name": "Defensive", 
                "image_file": "tieb.gif",
                "base_radius": 26,
                "base_image_size": 52,
                "current_scale": 1.103,  # From game hitbox data
                "hitbox_offset_x": 0,  # From game hitbox data
                "hitbox_offset_y": 1,  # From game hitbox data
                "color": (200, 200, 200)  # Dim white
            },
            "tactical": {
                "name": "Tactical",
                "image_file": "tiea.gif", 
                "base_radius": 26,
                "base_image_size": 52,
                "current_scale": 1.050,  # From game hitbox data
                "hitbox_offset_x": 0,  # From game hitbox data
                "hitbox_offset_y": 0,  # From game hitbox data
                "color": (200, 200, 200)  # Dim white
            },
            "swarm": {
                "name": "Swarm",
                "image_file": "tiefo.gif",
                "base_radius": 26,
                "base_image_size": 48,  # From game: swarm gets 48px instead of 52px
                "current_scale": 1.158,  # From game hitbox data
                "hitbox_offset_x": 1,  # From game hitbox data
                "hitbox_offset_y": 2,  # From game hitbox data
                "color": (200, 200, 200)  # Dim white
            },
            "deadly": {
                "name": "Deadly",
                "image_file": "tiei.gif",
                "base_radius": 26,
                "base_image_size": 52,
                "current_scale": 1.340,  # From game hitbox data
                "hitbox_offset_x": -1,  # From game hitbox data
                "hitbox_offset_y": 10,  # From game hitbox data
                "color": (200, 200, 200)  # Dim white
            }
        }
        
        # Load UFO images
        self.load_ufo_images()
        
        # Selection state
        self.selected_ufo = 0  # Index into ufo_types list
        self.ufo_keys = list(self.ufo_types.keys())
        
        # Display positions
        self.ufo_spacing = 200
        self.start_x = 150
        self.start_y = 200
        self.second_row_y = 500  # Second row position
        self.third_row_y = 600  # Third row position
        
    def load_ufo_images(self):
        """Load and process UFO images with the same transformations as the game"""
        for ufo_type, data in self.ufo_types.items():
            try:
                # Load the image
                image = pygame.image.load(get_resource_path(data["image_file"]))
                image = image.convert_alpha()
                
                # Apply the same transformations as in the game
                if ufo_type == "aggressive":
                    # Flip tie.gif horizontally then rotate 90 degrees clockwise then rotate 180 degrees
                    image = pygame.transform.flip(image, True, False)
                    image = pygame.transform.rotate(image, -90)
                    image = pygame.transform.rotate(image, 180)
                elif ufo_type == "deadly":
                    # Rotate tiei.gif 90 degrees counter-clockwise, flip horizontally, flip vertically, and rotate 180 degrees
                    image = pygame.transform.rotate(image, 90)
                    image = pygame.transform.flip(image, True, False)
                    image = pygame.transform.flip(image, False, True)
                    image = pygame.transform.rotate(image, 180)
                elif ufo_type in ["defensive", "tactical", "swarm"]:
                    # Flip horizontally then rotate 90 degrees counter-clockwise
                    image = pygame.transform.flip(image, True, False)
                    image = pygame.transform.rotate(image, 90)
                
                # Store the processed image
                data["original_image"] = image
                data["scaled_image"] = image  # Will be updated when scaling
                
            except Exception as e:
                print(f"Error loading {data['image_file']}: {e}")
                # Create a fallback colored circle
                data["original_image"] = None
                data["scaled_image"] = None
    
    def scale_ufo_image(self, ufo_type):
        """Scale the UFO image based on current scale"""
        data = self.ufo_types[ufo_type]
        if data["original_image"]:
            # Calculate new size
            new_size = int(data["base_image_size"] * data["current_scale"])
            data["scaled_image"] = pygame.transform.smoothscale(data["original_image"], (new_size, new_size))
        else:
            data["scaled_image"] = None
    
    def update_all_scaled_images(self):
        """Update all UFO scaled images"""
        for ufo_type in self.ufo_types:
            self.scale_ufo_image(ufo_type)
    
    def draw_ufo(self, ufo_type, x, y, is_selected=False):
        """Draw a UFO at the specified position"""
        data = self.ufo_types[ufo_type]
        
        # Calculate hitbox position (offset by hitbox_offset_x and hitbox_offset_y)
        hitbox_x = x + data["hitbox_offset_x"]
        hitbox_y = y + data["hitbox_offset_y"]
        
        # Draw UFO image or fallback
        if data["scaled_image"]:
            rect = data["scaled_image"].get_rect(center=(x, y))
            self.screen.blit(data["scaled_image"], rect)
        else:
            # Fallback: draw dim white circle
            radius = int(data["base_radius"] * data["current_scale"])
            pygame.draw.circle(self.screen, (200, 200, 200), (x, y), radius)
            pygame.draw.circle(self.screen, (200, 200, 200), (x, y), radius, 2)
        
        # Draw selection highlight circle at hitbox position (26px radius)
        if is_selected:
            highlight_radius = 26  # Fixed 26px radius
            pygame.draw.circle(self.screen, (200, 200, 200), (hitbox_x, hitbox_y), highlight_radius, 1)
    
    def draw_size_info(self, ufo_type, x, y):
        """Draw size information for a UFO"""
        data = self.ufo_types[ufo_type]
        
        # Calculate current values
        current_radius = data["base_radius"] * data["current_scale"]
        current_image_size = data["base_image_size"] * data["current_scale"]
        
        # Position text below the UFO
        text_y = y + 80
        
        # UFO name
        name_text = self.font.render(f"{data['name']} ({ufo_type})", True, data["color"])
        name_rect = name_text.get_rect(centerx=x, y=text_y)
        self.screen.blit(name_text, name_rect)
        
        # Scale factor
        scale_text = self.small_font.render(f"Scale: {data['current_scale']:.2f}x", True, WHITE)
        scale_rect = scale_text.get_rect(centerx=x, y=text_y + 25)
        self.screen.blit(scale_text, scale_rect)
        
        # Radius info
        radius_text = self.small_font.render(f"Radius: {current_radius:.1f}px", True, WHITE)
        radius_rect = radius_text.get_rect(centerx=x, y=text_y + 45)
        self.screen.blit(radius_text, radius_rect)
        
        # Image size info
        image_text = self.small_font.render(f"Image: {current_image_size:.0f}px", True, WHITE)
        image_rect = image_text.get_rect(centerx=x, y=text_y + 65)
        self.screen.blit(image_text, image_rect)
        
        # Hitbox offset info
        offset_text = self.small_font.render(f"Hitbox: ({data['hitbox_offset_x']:+d}, {data['hitbox_offset_y']:+d})px", True, WHITE)
        offset_rect = offset_text.get_rect(centerx=x, y=text_y + 85)
        self.screen.blit(offset_text, offset_rect)
    
    def draw_instructions(self):
        """Draw control instructions"""
        instructions = [
            "Controls:",
            "1-5: Select UFO type",
            "W/S: Scale UFO by 5%",
            "Arrow Keys: Move hitbox",
            "P: Print all size data to console",
            "ESC: Exit"
        ]
        
        y_offset = 50
        for instruction in instructions:
            text = self.font.render(instruction, True, WHITE)
            self.screen.blit(text, (20, y_offset))
            y_offset += 30
    
    def print_size_data(self):
        """Print all UFO size data to console"""
        print("\n" + "="*60)
        print("UFO SIZE DATA")
        print("="*60)
        
        for ufo_type, data in self.ufo_types.items():
            current_radius = data["base_radius"] * data["current_scale"]
            current_image_size = data["base_image_size"] * data["current_scale"]
            
            print(f"\n{data['name']} ({ufo_type}):")
            print(f"  Base radius: {data['base_radius']}px")
            print(f"  Base image size: {data['base_image_size']}px")
            print(f"  Current scale: {data['current_scale']:.3f}x")
            print(f"  Current radius: {current_radius:.1f}px")
            print(f"  Current image size: {current_image_size:.0f}px")
            print(f"  Hitbox offset: ({data['hitbox_offset_x']:+d}, {data['hitbox_offset_y']:+d})px")
        
        print("\n" + "="*60)
    
    def handle_events(self):
        """Handle pygame events"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
                elif event.key == pygame.K_p:
                    self.print_size_data()
                elif event.key >= pygame.K_1 and event.key <= pygame.K_5:
                    # Select UFO type (1-5)
                    self.selected_ufo = event.key - pygame.K_1
                    if self.selected_ufo < len(self.ufo_keys):
                        print(f"Selected: {self.ufo_types[self.ufo_keys[self.selected_ufo]]['name']}")
                elif event.key == pygame.K_w:
                    # Increase size by 5%
                    if self.selected_ufo < len(self.ufo_keys):
                        ufo_type = self.ufo_keys[self.selected_ufo]
                        self.ufo_types[ufo_type]["current_scale"] *= 1.05
                        self.scale_ufo_image(ufo_type)
                        print(f"Increased {self.ufo_types[ufo_type]['name']} scale to {self.ufo_types[ufo_type]['current_scale']:.3f}x")
                elif event.key == pygame.K_s:
                    # Decrease size by 5%
                    if self.selected_ufo < len(self.ufo_keys):
                        ufo_type = self.ufo_keys[self.selected_ufo]
                        self.ufo_types[ufo_type]["current_scale"] = max(0.1, self.ufo_types[ufo_type]["current_scale"] / 1.05)
                        self.scale_ufo_image(ufo_type)
                        print(f"Decreased {self.ufo_types[ufo_type]['name']} scale to {self.ufo_types[ufo_type]['current_scale']:.3f}x")
                elif event.key == pygame.K_UP:
                    # Move hitbox up
                    if self.selected_ufo < len(self.ufo_keys):
                        ufo_type = self.ufo_keys[self.selected_ufo]
                        self.ufo_types[ufo_type]["hitbox_offset_y"] -= 1
                        print(f"Moved {self.ufo_types[ufo_type]['name']} hitbox up to {self.ufo_types[ufo_type]['hitbox_offset_y']:+d}px")
                elif event.key == pygame.K_DOWN:
                    # Move hitbox down
                    if self.selected_ufo < len(self.ufo_keys):
                        ufo_type = self.ufo_keys[self.selected_ufo]
                        self.ufo_types[ufo_type]["hitbox_offset_y"] += 1
                        print(f"Moved {self.ufo_types[ufo_type]['name']} hitbox down to {self.ufo_types[ufo_type]['hitbox_offset_y']:+d}px")
                elif event.key == pygame.K_LEFT:
                    # Move hitbox left
                    if self.selected_ufo < len(self.ufo_keys):
                        ufo_type = self.ufo_keys[self.selected_ufo]
                        self.ufo_types[ufo_type]["hitbox_offset_x"] -= 1
                        print(f"Moved {self.ufo_types[ufo_type]['name']} hitbox left to {self.ufo_types[ufo_type]['hitbox_offset_x']:+d}px")
                elif event.key == pygame.K_RIGHT:
                    # Move hitbox right
                    if self.selected_ufo < len(self.ufo_keys):
                        ufo_type = self.ufo_keys[self.selected_ufo]
                        self.ufo_types[ufo_type]["hitbox_offset_x"] += 1
                        print(f"Moved {self.ufo_types[ufo_type]['name']} hitbox right to {self.ufo_types[ufo_type]['hitbox_offset_x']:+d}px")
        
        return True
    
    def draw(self):
        """Draw everything"""
        self.screen.fill(BLACK)
        
        # Draw instructions
        self.draw_instructions()
        
        # Draw UFOs - First row (spaced out)
        for i, ufo_type in enumerate(self.ufo_keys):
            x = self.start_x + (i * self.ufo_spacing)
            y = self.start_y
            is_selected = (i == self.selected_ufo)
            
            self.draw_ufo(ufo_type, x, y, is_selected)
            self.draw_size_info(ufo_type, x, y)
        
        # Draw UFOs - Second row (100px spacing)
        second_row_spacing = 100
        second_row_start_x = 150
        for i, ufo_type in enumerate(self.ufo_keys):
            x = second_row_start_x + (i * second_row_spacing)
            y = self.second_row_y
            is_selected = (i == self.selected_ufo)
            
            self.draw_ufo(ufo_type, x, y, is_selected)
        
        # Draw UFOs - Third row (60px spacing)
        third_row_spacing = 60
        third_row_start_x = 150
        for i, ufo_type in enumerate(self.ufo_keys):
            x = third_row_start_x + (i * third_row_spacing)
            y = self.third_row_y
            is_selected = (i == self.selected_ufo)
            
            self.draw_ufo(ufo_type, x, y, is_selected)
        
        # Draw selection indicator
        if self.selected_ufo < len(self.ufo_keys):
            selected_name = self.ufo_types[self.ufo_keys[self.selected_ufo]]["name"]
            selection_text = self.font.render(f"Selected: {selected_name}", True, YELLOW)
            self.screen.blit(selection_text, (20, SCREEN_HEIGHT - 50))
        
        pygame.display.flip()
    
    def run(self):
        """Main game loop"""
        print("UFO Sizer started!")
        print("Controls: 1-5 to select, W/S to scale, Arrow keys to move hitbox, P to print data, ESC to exit")
        
        # Initial scale update
        self.update_all_scaled_images()
        
        running = True
        while running:
            running = self.handle_events()
            self.draw()
            self.clock.tick(FPS)
        
        pygame.quit()

if __name__ == "__main__":
    ufo_sizer = UFOSizer()
    ufo_sizer.run()
