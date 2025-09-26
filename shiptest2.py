#!/usr/bin/env python3
"""
UFO Rotation Test - Display all UFOs and their rotation adjustments
Based on chuckstaroidsv2.py AdvancedUFO class
"""

import pygame
import math
import random
import sys
import os

# Add the current directory to the path to import from chuckstaroidsv2
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the necessary classes from the main game
from chuckstaroidsv2 import Vector2D, AdvancedUFO, get_resource_path

# Initialize Pygame
pygame.init()

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

class UFOTestDisplay:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("UFO Rotation Test - All Personalities")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 24)
        self.small_font = pygame.font.Font(None, 18)
        
        # Create UFOs with different personalities
        self.ufos = []
        self.ufo_personalities = ["aggressive", "defensive", "tactical", "swarm", "deadly"]
        self.ufo_colors = [RED, GREEN, BLUE, YELLOW, CYAN]
        
        # Spawn UFOs in a grid pattern
        for i, personality in enumerate(self.ufo_personalities):
            x = 200 + (i % 3) * 300
            y = 200 + (i // 3) * 200
            ufo = AdvancedUFO(x, y, personality)
            self.ufos.append(ufo)
        
        # Add some additional UFOs for variety
        for i in range(3):
            x = random.randint(100, SCREEN_WIDTH - 100)
            y = random.randint(100, SCREEN_HEIGHT - 100)
            personality = random.choice(self.ufo_personalities)
            ufo = AdvancedUFO(x, y, personality)
            self.ufos.append(ufo)
        
        # Player position (simulated)
        self.player_pos = Vector2D(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        
        # Debug info
        self.show_debug = True
        self.paused = False
        
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    self.paused = not self.paused
                elif event.key == pygame.K_d:
                    self.show_debug = not self.show_debug
                elif event.key == pygame.K_r:
                    # Reset UFOs
                    self.ufos = []
                    for i, personality in enumerate(self.ufo_personalities):
                        x = 200 + (i % 3) * 300
                        y = 200 + (i // 3) * 200
                        ufo = AdvancedUFO(x, y, personality)
                        self.ufos.append(ufo)
        return True
    
    def update(self, dt):
        if self.paused:
            return
        
        # Update each UFO
        for ufo in self.ufos:
            if ufo.active:
                # Update environmental awareness
                ufo.update_environmental_awareness(self.player_pos)
                
                # Calculate threat and opportunity levels
                threat_level = ufo.calculate_threat_level()
                opportunity_level = ufo.calculate_opportunity_level()
                
                # Update AI state
                ufo.update_ai_state(dt, threat_level, opportunity_level)
                
                # Update behavior weights
                ufo.update_behavior_weights()
                
                # Calculate movement vector (this updates the angle)
                ufo.calculate_movement_vector(dt)
                
                # Update position
                ufo.position += ufo.velocity * dt
                
                # Wrap around screen
                if ufo.position.x < 0:
                    ufo.position.x = SCREEN_WIDTH
                elif ufo.position.x > SCREEN_WIDTH:
                    ufo.position.x = 0
                if ufo.position.y < 0:
                    ufo.position.y = SCREEN_HEIGHT
                elif ufo.position.y > SCREEN_HEIGHT:
                    ufo.position.y = 0
    
    def draw_ufo(self, ufo, color):
        """Draw a UFO with rotation information"""
        if not ufo.active:
            return
        
        # Draw UFO using image if available, otherwise fallback to circle
        if ufo.image:
            # Rotate the UFO image (90 degrees clockwise offset like in main game)
            rotated_ufo = pygame.transform.rotate(ufo.image, -math.degrees(ufo.angle) - 90)
            ufo_rect = rotated_ufo.get_rect(center=(int(ufo.position.x), int(ufo.position.y)))
            self.screen.blit(rotated_ufo, ufo_rect)
        else:
            # Fallback to circle if no image
            pygame.draw.circle(self.screen, color, 
                              (int(ufo.position.x), int(ufo.position.y)), 
                              ufo.radius, 2)
        
        # Draw direction indicator (line showing current angle)
        end_x = ufo.position.x + math.cos(ufo.angle) * (ufo.radius + 20)
        end_y = ufo.position.y + math.sin(ufo.angle) * (ufo.radius + 20)
        pygame.draw.line(self.screen, WHITE, 
                        (int(ufo.position.x), int(ufo.position.y)),
                        (int(end_x), int(end_y)), 3)
        
        # Draw velocity vector
        if ufo.velocity.magnitude() > 0:
            vel_end_x = ufo.position.x + ufo.velocity.x * 0.5
            vel_end_y = ufo.position.y + ufo.velocity.y * 0.5
            pygame.draw.line(self.screen, YELLOW,
                           (int(ufo.position.x), int(ufo.position.y)),
                           (int(vel_end_x), int(vel_end_y)), 2)
        
        # Draw target velocity vector (AI calculated)
        if hasattr(ufo, 'target_velocity') and ufo.target_velocity.magnitude() > 0:
            target_end_x = ufo.position.x + ufo.target_velocity.x * 0.3
            target_end_y = ufo.position.y + ufo.target_velocity.y * 0.3
            pygame.draw.line(self.screen, ORANGE,
                           (int(ufo.position.x), int(ufo.position.y)),
                           (int(target_end_x), int(target_end_y)), 1)
    
    def draw_debug_info(self, ufo, x, y, color):
        """Draw debug information for a UFO"""
        if not self.show_debug:
            return
        
        # UFO ID and personality
        info_text = f"UFO {self.ufos.index(ufo)}: {ufo.personality}"
        text_surface = self.small_font.render(info_text, True, color)
        self.screen.blit(text_surface, (x, y))
        
        # Position
        pos_text = f"Pos: ({ufo.position.x:.1f}, {ufo.position.y:.1f})"
        text_surface = self.small_font.render(pos_text, True, WHITE)
        self.screen.blit(text_surface, (x, y + 15))
        
        # Angle information
        angle_deg = math.degrees(ufo.angle)
        angle_text = f"Angle: {angle_deg:.1f}°"
        text_surface = self.small_font.render(angle_text, True, WHITE)
        self.screen.blit(text_surface, (x, y + 30))
        
        # Velocity
        vel_text = f"Vel: ({ufo.velocity.x:.1f}, {ufo.velocity.y:.1f})"
        text_surface = self.small_font.render(vel_text, True, WHITE)
        self.screen.blit(text_surface, (x, y + 45))
        
        # Speed
        speed_text = f"Speed: {ufo.velocity.magnitude():.1f}"
        text_surface = self.small_font.render(speed_text, True, WHITE)
        self.screen.blit(text_surface, (x, y + 60))
        
        # Current state
        state_text = f"State: {ufo.current_state}"
        text_surface = self.small_font.render(state_text, True, WHITE)
        self.screen.blit(text_surface, (x, y + 75))
        
        # Behavior weights
        weights_text = f"Weights: S:{ufo.behavior_weights['seek']:.2f} F:{ufo.behavior_weights['flee']:.2f}"
        text_surface = self.small_font.render(weights_text, True, WHITE)
        self.screen.blit(text_surface, (x, y + 90))
        
        # Rotation speed
        rot_text = f"Rot Speed: {ufo.rotation_speed:.2f}"
        text_surface = self.small_font.render(rot_text, True, WHITE)
        self.screen.blit(text_surface, (x, y + 105))
        
        # Time dilation factor (if available)
        if hasattr(ufo, 'time_dilation_factor'):
            td_text = f"Time Dil: {ufo.time_dilation_factor:.2f}"
            text_surface = self.small_font.render(td_text, True, WHITE)
            self.screen.blit(text_surface, (x, y + 120))
        
        # Image file info
        if ufo.image:
            image_text = f"Image: Loaded"
            text_surface = self.small_font.render(image_text, True, GREEN)
            self.screen.blit(text_surface, (x, y + 135))
        else:
            image_text = f"Image: None (fallback)"
            text_surface = self.small_font.render(image_text, True, RED)
            self.screen.blit(text_surface, (x, y + 135))
    
    def draw(self):
        self.screen.fill(BLACK)
        
        # Draw player position
        pygame.draw.circle(self.screen, WHITE, 
                          (int(self.player_pos.x), int(self.player_pos.y)), 10, 2)
        pygame.draw.circle(self.screen, WHITE, 
                          (int(self.player_pos.x), int(self.player_pos.y)), 5)
        
        # Draw UFOs
        for i, ufo in enumerate(self.ufos):
            if ufo.active:
                color = self.ufo_colors[i % len(self.ufo_colors)]
                self.draw_ufo(ufo, color)
                
                # Draw debug info
                if self.show_debug:
                    debug_x = 10 + (i % 4) * 300
                    debug_y = 10 + (i // 4) * 150
                    self.draw_debug_info(ufo, debug_x, debug_y, color)
        
        # Draw instructions
        instructions = [
            "UFO Rotation Test - All Personalities",
            "SPACE: Pause/Resume",
            "D: Toggle Debug Info",
            "R: Reset UFOs",
            "ESC: Quit"
        ]
        
        for i, instruction in enumerate(instructions):
            color = WHITE if i == 0 else YELLOW
            text_surface = self.font.render(instruction, True, color)
            self.screen.blit(text_surface, (10, SCREEN_HEIGHT - 120 + i * 25))
        
        # Draw legend
        legend_y = SCREEN_HEIGHT - 200
        legend_items = [
            ("UFO Images", "Rotated based on movement"),
            ("White Line", "Current Direction"),
            ("Yellow Line", "Velocity Vector"),
            ("Orange Line", "Target Velocity"),
            ("White Circle", "Player Position")
        ]
        
        for i, (item, desc) in enumerate(legend_items):
            text_surface = self.small_font.render(f"{item}: {desc}", True, WHITE)
            self.screen.blit(text_surface, (SCREEN_WIDTH - 200, legend_y + i * 20))
        
        pygame.display.flip()
    
    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0  # Convert to seconds
            
            running = self.handle_events()
            self.update(dt)
            self.draw()
        
        pygame.quit()

def main():
    """Main function to run the UFO test"""
    try:
        test_display = UFOTestDisplay()
        test_display.run()
    except Exception as e:
        print(f"Error running UFO test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
