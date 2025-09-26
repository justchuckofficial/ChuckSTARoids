# Player Speed / Time Speed Table

## Overview
This table shows the relationship between player speed and time dilation in Chucksteroids. The time dilation system creates a Superhot-style effect where time slows down when the player moves faster.

## Time Dilation Formula

The time dilation is calculated based on **total movement**, which includes:
- **Player Speed**: Actual velocity magnitude
- **Shooting Movement**: Progressive bonus (200, 300, 400, 500+ units)
- **Turning Movement**: 0.01 units per degree per second of turning

### Time Dilation Ranges

| Total Movement Range | Time Dilation | Description |
|---------------------|---------------|-------------|
| 0 - 1,000 units | 0.01x - 1.0x | Nearly frozen to normal speed |
| 1,000 - 2,000 units | 1.0x - 5.0x | Normal speed to 5x speed |
| 2,000 - 10,000 units | 5.0x - 0.1x | 5x speed to very slow |
| 10,000+ units | 0.1x | Very slow (capped) |

## Detailed Speed Table

### Low Speed Range (0 - 1,000 units)
| Player Speed | Shooting Bonus | Total Movement | Time Dilation | Time Speed | Description |
|-------------|----------------|----------------|---------------|------------|-------------|
| 0 | 0 | 0 | 0.01x | 1% | Nearly frozen |
| 100 | 0 | 100 | 0.11x | 11% | Very slow |
| 200 | 0 | 200 | 0.21x | 21% | Slow |
| 300 | 0 | 300 | 0.31x | 31% | Slow |
| 400 | 0 | 400 | 0.41x | 41% | Slow |
| 500 | 0 | 500 | 0.51x | 51% | Half speed |
| 600 | 0 | 600 | 0.61x | 61% | Slow |
| 700 | 0 | 700 | 0.71x | 71% | Slow |
| 800 | 0 | 800 | 0.81x | 81% | Slow |
| 900 | 0 | 900 | 0.91x | 91% | Nearly normal |
| 1000 | 0 | 1000 | 1.0x | 100% | Normal speed |

### Medium Speed Range (1,000 - 2,000 units)
| Player Speed | Shooting Bonus | Total Movement | Time Dilation | Time Speed | Description |
|-------------|----------------|----------------|---------------|------------|-------------|
| 1000 | 0 | 1000 | 1.0x | 100% | Normal speed |
| 1100 | 0 | 1100 | 1.4x | 140% | Fast |
| 1200 | 0 | 1200 | 1.8x | 180% | Fast |
| 1300 | 0 | 1300 | 2.2x | 220% | Very fast |
| 1400 | 0 | 1400 | 2.6x | 260% | Very fast |
| 1500 | 0 | 1500 | 3.0x | 300% | 3x speed |
| 1600 | 0 | 1600 | 3.4x | 340% | 3.4x speed |
| 1700 | 0 | 1700 | 3.8x | 380% | 3.8x speed |
| 1800 | 0 | 1800 | 4.2x | 420% | 4.2x speed |
| 1900 | 0 | 1900 | 4.6x | 460% | 4.6x speed |
| 2000 | 0 | 2000 | 5.0x | 500% | 5x speed |

### High Speed Range (2,000 - 10,000 units)
| Player Speed | Shooting Bonus | Total Movement | Time Dilation | Time Speed | Description |
|-------------|----------------|----------------|---------------|------------|-------------|
| 2000 | 0 | 2000 | 5.0x | 500% | 5x speed |
| 3000 | 0 | 3000 | 2.5x | 250% | 2.5x speed |
| 4000 | 0 | 4000 | 0.75x | 75% | Slow |
| 5000 | 0 | 5000 | 0.5x | 50% | Half speed |
| 6000 | 0 | 6000 | 0.4x | 40% | Slow |
| 7000 | 0 | 7000 | 0.3x | 30% | Very slow |
| 8000 | 0 | 8000 | 0.2x | 20% | Very slow |
| 9000 | 0 | 9000 | 0.1x | 10% | Very slow |
| 10000+ | 0 | 10000+ | 0.01x | 1% | Nearly frozen (capped) |

### Shooting Bonus Effects

#### 1st Shot (200 units bonus)
| Player Speed | Total Movement | Time Dilation | Time Speed | Effect |
|-------------|----------------|---------------|------------|---------|
| 0 | 200 | 0.21x | 21% | Slow |
| 500 | 700 | 0.71x | 71% | Slow |
| 800 | 1000 | 1.0x | 100% | Normal |
| 1000 | 1200 | 1.8x | 180% | Fast |

#### 2nd Shot (300 units bonus)
| Player Speed | Total Movement | Time Dilation | Time Speed | Effect |
|-------------|----------------|---------------|------------|---------|
| 0 | 300 | 0.31x | 31% | Slow |
| 500 | 800 | 0.81x | 81% | Slow |
| 700 | 1000 | 1.0x | 100% | Normal |
| 900 | 1200 | 1.8x | 180% | Fast |

#### 3rd Shot (400 units bonus)
| Player Speed | Total Movement | Time Dilation | Time Speed | Effect |
|-------------|----------------|---------------|------------|---------|
| 0 | 400 | 0.41x | 41% | Slow |
| 500 | 900 | 0.91x | 91% | Nearly normal |
| 600 | 1000 | 1.0x | 100% | Normal |
| 800 | 1200 | 1.8x | 180% | Fast |

#### 4th+ Shot (500 units bonus)
| Player Speed | Total Movement | Time Dilation | Time Speed | Effect |
|-------------|----------------|---------------|------------|---------|
| 0 | 500 | 0.51x | 51% | Half speed |
| 500 | 1000 | 1.0x | 100% | Normal |
| 700 | 1200 | 1.8x | 180% | Fast |
| 900 | 1400 | 2.6x | 260% | Very fast |

## Progress Bar Width Scaling

The left progress bar width scales based on player speed:

| Player Speed | Width Multiplier | Visual Effect |
|-------------|------------------|---------------|
| 0 | 1.0x | Normal width |
| 1000 | 1.0x | Normal width |
| 2000 | 1.5x | 50% wider |
| 10000 | 3.0x | 3x wider |

## Key Insights

1. **Sweet Spot**: The optimal speed range is 1,000-2,000 units for maximum time speed (1x-5x)
2. **Shooting Power**: Shooting provides significant movement bonus, especially for slower players
3. **Diminishing Returns**: Speeds above 2,000 units actually slow down time
4. **Visual Feedback**: Progress bar width provides immediate visual feedback of speed
5. **Strategic Depth**: Players must balance speed for time control vs. maneuverability

## Debug Commands

- **F1**: Toggle debug mode
- **G**: Toggle god mode (no damage) - only works in debug mode
- **Debug Display**: Shows current player speed, world speed, and god mode status
