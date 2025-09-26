#!/usr/bin/env python3
"""
All Hitboxes Test - Displays all UFOs and Boss enemies with their hitboxes and data
Reads hitbox information from chuckstaroidsv2.py and creates a visual test display
"""

import pygame
import math
import random
import sys
import os
from typing import List, Tuple

# Add the current directory to the path to import from chuckstaroidsv2
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the game classes
from chuckstaroidsv2 import AdvancedUFO, BossEnemy, Vector2D, get_resource_path

# Constants
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800
FPS = 60

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
CYAN = (0, 255, 255)
MAGENTA = (255, 0, 255)
ORANGE = (255, 165, 0)
PURPLE = (128, 0, 128)

class HitboxTestDisplay:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("All Hitboxes Test - UFOs and Boss Enemies")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 24)
        self.small_font = pygame.font.Font(None, 18)
        
        # Display settings
        self.show_hitboxes = True
        self.show_data = True
        self.show_velocity_vectors = False  # Disable velocity vectors
        self.scale_factor = 3.0  # 300% scale
        
        # Create test objects
        self.ufos = []
        self.bosses = []
        self.create_test_objects()
        
    def create_test_objects(self):
        """Create one of each UFO personality type and one boss for testing"""
        
        # Create one UFO of each personality type - scaled positions
        personalities = ["aggressive", "defensive", "tactical", "swarm", "deadly"]
        ufo_positions = [
            (200, 200), (400, 200), (600, 200), (800, 200), (1000, 200)
        ]
        
        for i, (x, y) in enumerate(ufo_positions):
            personality = personalities[i]
            ufo = AdvancedUFO(x, y, personality)
            # Set velocity to zero for stationary display
            ufo.velocity = Vector2D(0, 0)
            # Scale the radius for display
            ufo.display_radius = ufo.radius * self.scale_factor
            
            # Print image dimensions for debugging
            if hasattr(ufo, 'image') and ufo.image:
                print(f"UFO {personality}: Image size = {ufo.image.get_width()}x{ufo.image.get_height()}")
            else:
                print(f"UFO {personality}: No image loaded")
            
            self.ufos.append(ufo)
        
        # Create one Boss enemy - centered
        boss = BossEnemy(600, 500, "right", SCREEN_WIDTH, SCREEN_HEIGHT)
        # Set velocity to zero for stationary display
        boss.velocity = Vector2D(0, 0)
        # Scale the radius for display
        boss.display_radius = boss.radius * self.scale_factor
        
        # Print boss image dimensions for debugging
        if hasattr(boss, 'image') and boss.image:
            print(f"Boss: Image size = {boss.image.get_width()}x{boss.image.get_height()}")
        else:
            print(f"Boss: No image loaded")
        
        self.bosses = [boss]
    
    def handle_events(self):
        """Handle pygame events"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
                elif event.key == pygame.K_h:
                    self.show_hitboxes = not self.show_hitboxes
                elif event.key == pygame.K_d:
                    self.show_data = not self.show_data
                elif event.key == pygame.K_r:
                    # Reset/regenerate objects
                    self.ufos.clear()
                    self.bosses.clear()
                    self.create_test_objects()
        return True
    
    def update_objects(self, dt):
        """Update all objects if not paused - everything is stationary for analysis"""
        # All objects are stationary for hitbox analysis
        # No movement updates needed
        pass
    
    def draw_hitbox(self, surface, position, radius, color, thickness=2):
        """Draw a circular hitbox"""
        pygame.draw.circle(surface, color, 
                         (int(position.x), int(position.y)), 
                         int(radius), thickness)
    
    def draw_velocity_vector(self, surface, position, velocity, color, scale=0.1):
        """Draw velocity vector as an arrow"""
        if velocity.magnitude() < 0.1:
            return
            
        # Calculate arrow end point
        end_x = position.x + velocity.x * scale
        end_y = position.y + velocity.y * scale
        
        # Draw main line
        pygame.draw.line(surface, color, 
                        (int(position.x), int(position.y)),
                        (int(end_x), int(end_y)), 2)
        
        # Draw arrowhead
        if velocity.magnitude() > 5:  # Only draw arrowhead for significant velocity
            angle = math.atan2(velocity.y, velocity.x)
            arrow_length = 10
            arrow_angle = math.pi / 6  # 30 degrees
            
            # Calculate arrowhead points
            head1_x = end_x - arrow_length * math.cos(angle - arrow_angle)
            head1_y = end_y - arrow_length * math.sin(angle - arrow_angle)
            head2_x = end_x - arrow_length * math.cos(angle + arrow_angle)
            head2_y = end_y - arrow_length * math.sin(angle + arrow_angle)
            
            pygame.draw.line(surface, color, 
                           (int(end_x), int(end_y)),
                           (int(head1_x), int(head1_y)), 2)
            pygame.draw.line(surface, color, 
                           (int(end_x), int(end_y)),
                           (int(head2_x), int(head2_y)), 2)
    
    def draw_object_data(self, surface, obj, obj_type, color, y_offset=0):
        """Draw object data text"""
        if not self.show_data:
            return
            
        # Object type and basic info
        info_lines = [
            f"{obj_type}",
            f"Pos: ({obj.position.x:.1f}, {obj.position.y:.1f})",
            f"Radius: {obj.radius} (scaled: {getattr(obj, 'display_radius', obj.radius):.1f})",
            f"Active: {obj.active}"
        ]
        
        # Add type-specific info
        if obj_type == "UFO":
            info_lines.extend([
                f"Personality: {getattr(obj, 'ai_personality', 'unknown')}",
                f"Speed: {obj.speed:.1f}",
                f"Max Speed: {obj.max_speed:.1f}",
                f"Acceleration: {obj.acceleration:.1f}",
                f"Angle: {math.degrees(obj.angle):.1f}°"
            ])
        elif obj_type == "Boss":
            info_lines.extend([
                f"Direction: {getattr(obj, 'direction', 'unknown')}",
                f"Speed: {obj.speed:.1f}",
                f"Amplitude: {getattr(obj, 'amplitude', 0)}",
                f"Frequency: {getattr(obj, 'frequency', 0):.2f}"
            ])
        
        # Draw background rectangle
        text_height = len(info_lines) * 20 + 10
        text_width = 200
        rect = pygame.Rect(obj.position.x - text_width//2, 
                          obj.position.y - obj.radius - text_height - 10 + y_offset,
                          text_width, text_height)
        pygame.draw.rect(surface, (0, 0, 0, 128), rect)
        pygame.draw.rect(surface, color, rect, 2)
        
        # Draw text
        for i, line in enumerate(info_lines):
            text_surface = self.small_font.render(line, True, WHITE)
            text_rect = text_surface.get_rect()
            text_rect.centerx = rect.centerx
            text_rect.y = rect.y + 5 + i * 20
            surface.blit(text_surface, text_rect)
    
    def draw_instructions(self, surface):
        """Draw control instructions"""
        instructions = [
            "Hitbox Analysis Tool:",
            "5 UFOs + 1 Boss (300% scale)",
            "",
            "H - Toggle hitboxes",
            "D - Toggle data display", 
            "R - Reset objects",
            "ESC - Exit",
            "",
            "All objects stationary"
        ]
        
        y = 10
        for instruction in instructions:
            text_surface = self.font.render(instruction, True, WHITE)
            surface.blit(text_surface, (10, y))
            y += 25
    
    def draw_status(self, surface):
        """Draw status information"""
        status_lines = [
            f"UFOs: {len([u for u in self.ufos if u.active])}/{len(self.ufos)} (5 personalities)",
            f"Bosses: {len([b for b in self.bosses if b.active])}/{len(self.bosses)}",
            f"Scale: {self.scale_factor}x",
            f"Hitboxes: {self.show_hitboxes}",
            f"Data: {self.show_data}",
            "",
            "Stationary Analysis Mode"
        ]
        
        y = SCREEN_HEIGHT - len(status_lines) * 25 - 10
        for line in status_lines:
            text_surface = self.font.render(line, True, WHITE)
            surface.blit(text_surface, (SCREEN_WIDTH - 200, y))
            y += 25
    
    def draw_ufo_image(self, surface, ufo):
        """Draw UFO using actual game image scaled up"""
        if hasattr(ufo, 'image') and ufo.image:
            # Scale the UFO image by 300%
            scaled_ufo = pygame.transform.scale(ufo.image, 
                (int(ufo.image.get_width() * self.scale_factor), 
                 int(ufo.image.get_height() * self.scale_factor)))
            # Draw UFO using scaled image with rotation (90 degrees clockwise offset)
            rotated_ufo = pygame.transform.rotate(scaled_ufo, -math.degrees(ufo.angle) - 90)
            ufo_rect = rotated_ufo.get_rect(center=(int(ufo.position.x), int(ufo.position.y)))
            surface.blit(rotated_ufo, ufo_rect)
        else:
            # Fallback to original UFO shape if image not available - scaled
            scaled_radius = ufo.radius * self.scale_factor
            pygame.draw.ellipse(surface, CYAN, 
                              (ufo.position.x - scaled_radius, ufo.position.y - scaled_radius//2,
                               scaled_radius * 2, scaled_radius))
            pygame.draw.rect(surface, CYAN,
                            (ufo.position.x - scaled_radius/2, ufo.position.y - scaled_radius/4,
                             scaled_radius, scaled_radius//2))
    
    def draw_boss_image(self, surface, boss):
        """Draw Boss using actual game image scaled up"""
        if hasattr(boss, 'image') and boss.image:
            # Scale the boss image by 300%
            scaled_boss = pygame.transform.scale(boss.image, 
                (int(boss.image.get_width() * self.scale_factor), 
                 int(boss.image.get_height() * self.scale_factor)))
            # Draw the scaled boss image centered
            x = int(boss.position.x - scaled_boss.get_width() // 2)
            y = int(boss.position.y - scaled_boss.get_height() // 2)
            surface.blit(scaled_boss, (x, y))
        else:
            # Fallback to rectangle if image not available - scaled
            scaled_radius = boss.radius * self.scale_factor
            pygame.draw.rect(surface, ORANGE,
                           (boss.position.x - scaled_radius, boss.position.y - scaled_radius,
                            scaled_radius * 2, scaled_radius * 2))

    def draw(self):
        """Main draw method"""
        self.screen.fill(BLACK)
        
        # Draw UFOs
        for i, ufo in enumerate(self.ufos):
            if not ufo.active:
                continue
                
            # Draw UFO using actual game image (scaled)
            self.draw_ufo_image(self.screen, ufo)
            
            # Draw hitbox (scaled)
            if self.show_hitboxes:
                self.draw_hitbox(self.screen, ufo.position, ufo.display_radius, YELLOW, 3)
            
            # Draw data
            self.draw_object_data(self.screen, ufo, "UFO", YELLOW, -50)
        
        # Draw Bosses
        for i, boss in enumerate(self.bosses):
            if not boss.active:
                continue
                
            # Draw Boss using actual game image (scaled)
            self.draw_boss_image(self.screen, boss)
            
            # Draw hitbox (scaled)
            if self.show_hitboxes:
                self.draw_hitbox(self.screen, boss.position, boss.display_radius, ORANGE, 4)
            
            # Draw data
            self.draw_object_data(self.screen, boss, "Boss", ORANGE, -100)
        
        # Draw instructions and status
        self.draw_instructions(self.screen)
        self.draw_status(self.screen)
        
        pygame.display.flip()
    
    def run(self):
        """Main game loop"""
        running = True
        dt = 0.016  # Fixed timestep for consistent behavior
        
        print("All Hitboxes Test Started - Stationary Analysis Mode")
        print("Displaying: 5 UFOs (one of each personality) + 1 Boss at 300% scale")
        print()
        print("Controls:")
        print("  H - Toggle hitboxes")
        print("  D - Toggle data display")
        print("  R - Reset objects")
        print("  ESC - Exit")
        print()
        print("Hitbox Information:")
        print(f"  UFO Radius: {self.ufos[0].radius if self.ufos else 'N/A'} (scaled: {self.ufos[0].display_radius if self.ufos else 'N/A'})")
        print(f"  Boss Radius: {self.bosses[0].radius if self.bosses else 'N/A'} (scaled: {self.bosses[0].display_radius if self.bosses else 'N/A'})")
        print()
        print("UFO Personalities: aggressive, defensive, tactical, swarm, deadly")
        print("All objects are stationary for hitbox analysis")
        print("Everything scaled up by 300% for better visibility")
        print()
        
        while running:
            running = self.handle_events()
            self.update_objects(dt)
            self.draw()
            self.clock.tick(FPS)
        
        pygame.quit()
        print("All Hitboxes Test Ended")

def main():
    """Main entry point"""
    try:
        display = HitboxTestDisplay()
        display.run()
    except Exception as e:
        print(f"Error running hitbox test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
