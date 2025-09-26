#!/usr/bin/env python3
"""
Test script to verify asteroid collision detection with screen wrapping
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from chuckstaroidsv4 import Game, Asteroid
import pygame
import math

def test_asteroid_collision_wrapping():
    """Test asteroid collision detection when asteroids are wrapping across screen edges"""
    
    # Initialize pygame
    pygame.init()
    
    # Create a test game instance
    game = Game()
    game.current_width = 800
    game.current_height = 600
    
    # Initialize the ship to avoid None errors
    from chuckstaroidsv4 import Ship
    game.ship = Ship(400, 300)  # Center of screen
    game.ship.active = True
    
    # Clear existing asteroids
    game.asteroids.clear()
    
    # Create two asteroids that will wrap around the screen
    # Asteroid 1: positioned near left edge, moving left (will wrap to right)
    asteroid1 = Asteroid(50, 300, 3, 1)  # Size 3 asteroid
    asteroid1.velocity.x = -100  # Moving left
    asteroid1.velocity.y = 0
    
    # Asteroid 2: positioned near right edge, moving right (will wrap to left)  
    asteroid2 = Asteroid(750, 300, 3, 1)  # Size 3 asteroid
    asteroid2.velocity.x = 100  # Moving right
    asteroid2.velocity.y = 0
    
    # Add asteroids to game
    game.asteroids.append(asteroid1)
    game.asteroids.append(asteroid2)
    
    print("Initial positions:")
    print(f"Asteroid 1: ({asteroid1.position.x}, {asteroid1.position.y})")
    print(f"Asteroid 2: ({asteroid2.position.x}, {asteroid2.position.y})")
    print(f"Asteroid 1 velocity: ({asteroid1.velocity.x}, {asteroid1.velocity.y})")
    print(f"Asteroid 2 velocity: ({asteroid2.velocity.x}, {asteroid2.velocity.y})")
    
    # Test collision detection before wrapping
    collision_before = game.check_wrapped_collision(
        asteroid1.get_hitbox_center(), 
        asteroid2.get_hitbox_center(), 
        asteroid1.radius, 
        asteroid2.radius
    )
    print(f"Collision detected before wrapping: {collision_before}")
    
    # Simulate a few frames of movement
    dt = 0.016  # ~60 FPS
    for frame in range(10):
        # Update asteroid positions
        asteroid1.position.x += asteroid1.velocity.x * dt
        asteroid2.position.x += asteroid2.velocity.x * dt
        
        # Apply screen wrapping
        if asteroid1.position.x < -asteroid1.radius:
            asteroid1.position.x = game.current_width + asteroid1.radius
        elif asteroid1.position.x > game.current_width + asteroid1.radius:
            asteroid1.position.x = -asteroid1.radius
            
        if asteroid2.position.x < -asteroid2.radius:
            asteroid2.position.x = game.current_width + asteroid2.radius
        elif asteroid2.position.x > game.current_width + asteroid2.radius:
            asteroid2.position.x = -asteroid2.radius
        
        # Check collision
        collision = game.check_wrapped_collision(
            asteroid1.get_hitbox_center(), 
            asteroid2.get_hitbox_center(), 
            asteroid1.radius, 
            asteroid2.radius
        )
        
        print(f"Frame {frame + 1}: Asteroid 1: ({asteroid1.position.x:.1f}, {asteroid1.position.y:.1f}), "
              f"Asteroid 2: ({asteroid2.position.x:.1f}, {asteroid2.position.y:.1f}), "
              f"Collision: {collision}")
        
        if collision:
            print("✓ Collision detected with screen wrapping!")
            break
    
    # Test the actual collision resolution
    print("\nTesting collision resolution...")
    
    # Reset positions to simulate collision - put them very close together
    asteroid1.position.x = 400
    asteroid1.position.y = 300
    asteroid1.velocity.x = -50
    asteroid1.velocity.y = 0
    
    asteroid2.position.x = 420  # Very close - should definitely collide
    asteroid2.position.y = 300
    asteroid2.velocity.x = 50
    asteroid2.velocity.y = 0
    
    print(f"Before collision - Asteroid 1 velocity: ({asteroid1.velocity.x}, {asteroid1.velocity.y})")
    print(f"Before collision - Asteroid 2 velocity: ({asteroid2.velocity.x}, {asteroid2.velocity.y})")
    
    # Run collision detection (this should trigger collision resolution)
    game.check_collisions()
    
    print(f"After collision - Asteroid 1 velocity: ({asteroid1.velocity.x}, {asteroid1.velocity.y})")
    print(f"After collision - Asteroid 2 velocity: ({asteroid2.velocity.x}, {asteroid2.velocity.y})")
    
    print("\n✓ Asteroid collision detection with screen wrapping test completed!")
    
    pygame.quit()

if __name__ == "__main__":
    test_asteroid_collision_wrapping()
