#!/usr/bin/env python3
"""
Simple test to verify asteroid collision detection
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from chuckstaroidsv4 import Game, Asteroid, Ship
import pygame
import math

def test_simple_collision():
    """Test basic asteroid collision detection"""
    
    # Initialize pygame
    pygame.init()
    
    # Create a test game instance
    game = Game()
    game.current_width = 800
    game.current_height = 600
    
    # Initialize the ship
    game.ship = Ship(400, 300)
    game.ship.active = True
    
    # Clear existing asteroids
    game.asteroids.clear()
    
    # Create two asteroids that are definitely colliding
    asteroid1 = Asteroid(400, 300, 3, 1)  # Size 3 asteroid
    asteroid1.velocity.x = -50
    asteroid1.velocity.y = 0
    
    asteroid2 = Asteroid(420, 300, 3, 1)  # Size 3 asteroid - very close
    asteroid2.velocity.x = 50
    asteroid2.velocity.y = 0
    
    # Add asteroids to game
    game.asteroids.append(asteroid1)
    game.asteroids.append(asteroid2)
    
    print("Testing direct collision detection...")
    print(f"Asteroid 1 position: ({asteroid1.position.x}, {asteroid1.position.y})")
    print(f"Asteroid 2 position: ({asteroid2.position.x}, {asteroid2.position.y})")
    print(f"Asteroid 1 radius: {asteroid1.radius}")
    print(f"Asteroid 2 radius: {asteroid2.radius}")
    
    # Check if they're colliding
    distance = math.sqrt((asteroid1.position.x - asteroid2.position.x)**2 + (asteroid1.position.y - asteroid2.position.y)**2)
    print(f"Distance between asteroids: {distance}")
    print(f"Sum of radii: {asteroid1.radius + asteroid2.radius}")
    print(f"Should collide: {distance < asteroid1.radius + asteroid2.radius}")
    
    # Test wrapped collision detection
    collision = game.check_wrapped_collision(
        asteroid1.get_hitbox_center(), 
        asteroid2.get_hitbox_center(), 
        asteroid1.radius, 
        asteroid2.radius
    )
    print(f"Wrapped collision detection result: {collision}")
    
    print(f"Before collision - Asteroid 1 velocity: ({asteroid1.velocity.x}, {asteroid1.velocity.y})")
    print(f"Before collision - Asteroid 2 velocity: ({asteroid2.velocity.x}, {asteroid2.velocity.y})")
    
    # Run collision detection
    print("\nRunning collision detection...")
    game.check_collisions()
    
    print(f"After collision - Asteroid 1 velocity: ({asteroid1.velocity.x}, {asteroid1.velocity.y})")
    print(f"After collision - Asteroid 2 velocity: ({asteroid2.velocity.x}, {asteroid2.velocity.y})")
    
    pygame.quit()

if __name__ == "__main__":
    test_simple_collision()
