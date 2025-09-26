# All Hitboxes Test

This script (`allhitboxestest.py`) reads hitbox information from `chuckstaroidsv2.py` and displays all UFOs and Boss enemies with their hitboxes and data for testing and visualization purposes.

## Features

- **UFO Display**: Shows 15 UFOs with different AI personalities (aggressive, defensive, tactical, swarm, deadly)
- **Boss Display**: Shows 2 Boss enemies with different movement patterns
- **Actual Game Images**: Uses the real in-game sprites at their proper sizes
- **Stationary Analysis**: All objects are stationary for precise hitbox analysis
- **Hitbox Visualization**: Circular hitboxes with different colors for each object type
- **Data Display**: Shows detailed information about each object including position, radius, speed, and type-specific properties
- **Velocity Vectors**: Visual arrows showing movement direction and speed (zero for stationary objects)
- **Interactive Controls**: Toggle various display options in real-time

## Hitbox Information

### UFOs
- **Radius**: 26 pixels
- **Hitbox Color**: Yellow
- **Collision Detection**: Uses `check_wrapped_collision()` for screen wrapping
- **Personalities**: Each UFO has different AI behavior patterns

### Boss Enemies
- **Radius**: 250 pixels (for 500px image)
- **Hitbox Color**: Orange
- **Collision Detection**: Standard circular collision (no screen wrapping)
- **Movement**: Sine wave pattern with configurable amplitude and frequency

## Controls

- **H** - Toggle hitbox display
- **D** - Toggle data display
- **V** - Toggle velocity vectors
- **R** - Reset/regenerate all objects
- **ESC** - Exit application

## Image Display

- **UFOs**: Uses actual game UFO sprites with proper rotation and scaling
- **Bosses**: Uses actual game boss sprites at 500x500 pixel size
- **Fallback**: Simple geometric shapes if images fail to load

## Usage

```bash
python allhitboxestest.py
```

## Technical Details

The script imports the game classes directly from `chuckstaroidsv2.py`:
- `AdvancedUFO` - For UFO objects with AI personalities
- `BossEnemy` - For boss enemy objects
- `Vector2D` - For position and velocity calculations
- `get_resource_path` - For resource loading

## Display Information

Each object shows:
- **Position**: Current x,y coordinates
- **Radius**: Hitbox radius in pixels
- **Active Status**: Whether the object is currently active
- **Type-specific Data**:
  - UFOs: Personality, speed, max speed, acceleration, angle
  - Bosses: Direction, speed, amplitude, frequency

## Purpose

This test tool is useful for:
- Verifying hitbox accuracy and positioning
- Testing collision detection systems
- Debugging object behavior and movement
- Visualizing game object properties
- Performance testing with multiple objects
