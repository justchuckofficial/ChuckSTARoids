# ChuckSTARoids UI Layout Diagram

## Gameplay UI Layout (Top to Bottom)

```
┌─────────────────────────────────────────────────────────────┐
│                    PROGRESS BARS (Top Layer)                │
│  Player Speed: [████████░░]  World Speed: [██████░░░░]      │
├─────────────────────────────────────────────────────────────┤
│                        LEVEL 5                              │
│                      (y=30, centered)                      │
├─────────────────────────────────────────────────────────────┤
│                        1,234,567                           │
│                      (y=60, centered)                      │
│                    (pulsing score)                         │
├─────────────────────────────────────────────────────────────┤
│                    [🚀] [🚀] [🚀] [🚀] [🚀]                │
│                  (y=90, life indicators)                   │
│                   (pulsing ship icons)                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│                    SPECIAL MESSAGES                         │
│                   (y=150, cascading)                       │
│                                                             │
│  Priority 1: Trick Messages                                │
│  "I'll try spinning, that's a good trick!"                 │
│                                                             │
│  Priority 2: Speed Messages                                │
│  "Interstellar!" / "Ludicrous speed... Go!"                │
│                                                             │
│  Priority 3: Score Milestones                              │
│  "250k Extra Life + Full Recharge!"                        │
│  "100k Ability Double Charged!"                            │
│  "25k Shields Recharged!"                                  │
│                                                             │
│  Priority 4: UFO Count Messages                            │
│  "90+ We've got incoming!"                                 │
│  "60+ This is where the fun begins."                       │
│  "30+ Stay on target… stay on target…"                     │
│  "20+ Launch fighters!"                                    │
│  "10+ All ships, fire at will!"                            │
│                                                             │
│  Priority 5: Multiplier Messages                           │
│  "5x Great, kid, don't get cocky."                         │
│  "4x The Force will be with you, always."                  │
│  "3x We've got them on the run!"                           │
│                                                             │
│  Priority 6: Combat Messages                               │
│  "Nice shot, kid!" (green text)                            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Title Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│                                                             │
│                    CHUCKSTAROIDS                            │
│                   (animated title)                         │
│                                                             │
│                                                             │
│                  PRESS SPACE TO START                       │
│                   (fade-in subtitle)                       │
│                                                             │
│                                                             │
│              TOP SCORES: Worldwide #1: 1,234,567           │
│                        Local: 987,654                       │
│                                                             │
│                                                             │
│        MOVE - w a s d + arrow keys  .  SHOOT - space       │
│        BLAST - q b shift  .  BRAKE - e ctrl                │
│                                                             │
│        SCORES - tab  .  RESTART - r  .  PAUSE - p          │
│        DATA - 0  .  EXIT - esc                             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Game Over Screen Layout

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│                                                             │
│                        SCORE: 1,234,567                    │
│                         LEVEL 5                             │
│                                                             │
│                                                             │
│                        GAME OVER                            │
│                    (large yellow text)                      │
│                                                             │
│                                                             │
│                    Press R to restart                       │
│                                                             │
│                                                             │
│        TAB = View Leaderboard  |  R = Restart  |  ESC = Exit│
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Message Priority System

```
Highest Priority (shows first)
    ↓
1. Trick Messages (spinning, etc.)
    ↓
2. Speed Messages (interstellar, ludicrous, plaid)
    ↓
3. Score Milestones (250k, 100k, 25k)
    ↓
4. UFO Count Messages (90+, 60+, 30+, 20+, 10+)
    ↓
5. Multiplier Messages (5x, 4x, 3x)
    ↓
6. Combat Messages (nice shot)
    ↓
Lowest Priority (shows last)
```

## Visual Effects

- **Skewed Text**: All special messages use 15-degree skew effect
- **Pulse Effects**: Score and life indicators pulse with sine waves
- **Fade Effects**: Title screen elements fade in over time
- **Scale Effects**: Score text scales up when multiplier increases
- **Color Coding**: 
  - White: Default text
  - Yellow: Special messages and titles
  - Green: Combat messages
  - Red: Score/level in game over
  - Gold: High scores
