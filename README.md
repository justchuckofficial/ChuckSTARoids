# Asteroids Deluxe

A faithful reproduction of the classic arcade game Asteroids Deluxe, built with Python and Pygame.

## Features

- **Complete Gameplay**: All original game mechanics including ship movement, rotation, thrust, and shooting
- **Asteroid System**: Multiple asteroid sizes that split when destroyed
- **UFO Enemies**: AI-controlled UFOs that shoot at the player
- **Collision Detection**: Accurate collision detection between all game objects
- **Scoring System**: Points for destroying asteroids and UFOs
- **Lives System**: Multiple lives with invulnerability periods
- **Level Progression**: Advance to next level when all asteroids are destroyed
- **Windows GUI**: Clean interface with control instructions

## Installation

1. Install Python 3.7 or higher
2. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Game

```bash
python asteroids_deluxe.py
```

## Controls

- **Arrow Keys**: Rotate ship left/right and thrust forward
- **Spacebar**: Shoot bullets
- **R**: Restart game (when game over)
- **P**: Pause game

## Gameplay

- Destroy all asteroids to advance to the next level
- Avoid collisions with asteroids and UFOs
- UFOs will shoot at your ship - avoid their bullets!
- Each level has more asteroids than the previous one
- You have 3 lives - use them wisely!

## Scoring

- Large Asteroid: 100 points
- Medium Asteroid: 50 points  
- Small Asteroid: 25 points
- UFO: 200 points

## Technical Details

- Built with Python 3 and Pygame
- 60 FPS gameplay
- Vector-based physics
- Screen wrapping for seamless movement
- Threaded game loop for smooth GUI integration

Enjoy the classic arcade experience!
