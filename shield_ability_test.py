import pygame
import math
import sys

# Initialize Pygame
pygame.init()

# Constants
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800
FPS = 60

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE = (0, 100, 255)
PURPLE = (147, 20, 255)
HOT_PINK = (255, 20, 147)

class ShieldAbilityTest:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Shield & Ability Effects Test - All States")
        self.clock = pygame.time.Clock()
        
        # Ship properties
        self.radius = 20
        self.positions = [
            pygame.Vector2(200, 200),   # Shield 1 Charging
            pygame.Vector2(400, 200),   # Shield 1 Charged + Shield 2 Charging
            pygame.Vector2(600, 200),   # Shield 2 Charged + Shield 3 Charging
            pygame.Vector2(800, 200),   # All 3 Shields Charged
            pygame.Vector2(200, 400),   # Ability 1 Charging
            pygame.Vector2(400, 400),   # Ability 1 Charged + Ability 2 Charging
            pygame.Vector2(600, 400),   # Both Abilities Charged
            pygame.Vector2(800, 400),   # Shield Recharge Animation (1st)
            pygame.Vector2(200, 600),   # Shield Recharge Animation (2nd)
            pygame.Vector2(400, 600),   # Shield Recharge Animation (3rd)
            pygame.Vector2(600, 600),   # Ability Recharge Animation (1st)
            pygame.Vector2(800, 600),   # Ability Recharge Animation (2nd)
        ]
        
        # Create multiple ship instances for each state
        self.ships = []
        for i, pos in enumerate(self.positions):
            ship = {
                'position': pos,
                'radius': 15,
                'shield_hits': 0,
                'shield_recharge_time': 0,
                'shield_recharge_duration': 3.0,
                'shield_recharge_pulse_timer': 0,
                'shield_recharge_pulse_duration': 0.5,
                'shield_pulse_timer': 0,
                'shield_full_flash_timer': 0,
                'shield_full_flash_duration': 0.3,
                'shield_full_hold_timer': 0,
                'shield_full_hold_duration': 1.0,
                'shield_full_fade_timer': 0,
                'shield_full_fade_duration': 0.5,
                'ring_pulse_timer': 0,
                'ability_charges': 0,
                'ability_timer': 0,
                'ability_duration': 4.0,
                'first_charge_duration': 2.0,
                'ability_recharge_pulse_timer': 0,
                'ability_recharge_pulse_duration': 0.5,
                'ability_flash_count': 2,
                'ability_hold_timer': 0,
                'ability_hold_duration': 0.5,
                'ability_fade_timer': 0,
                'ability_fade_duration': 1.0,
                'ability_fully_charged_pulse_timer': 0,
                'is_first_game': True,
                'max_shield_hits': 3,
                'max_ability_charges': 2
            }
            self.ships.append(ship)
        
        # Test descriptions
        self.tests = [
            "Shield 1 Charging",
            "Shield 1 Charged + Shield 2 Charging", 
            "Shield 2 Charged + Shield 3 Charging",
            "All 3 Shields Charged",
            "Ability 1 Charging",
            "Ability 1 Charged + Ability 2 Charging",
            "Both Abilities Charged",
            "Shield Recharge Animation (1st)",
            "Shield Recharge Animation (2nd)",
            "Shield Recharge Animation (3rd)",
            "Ability Recharge Animation (1st)",
            "Ability Recharge Animation (2nd)"
        ]
        
        self.setup_all_tests()
    
    def setup_all_tests(self):
        """Setup all test scenarios simultaneously"""
        # Shield 1 Charging
        self.ships[0]['shield_hits'] = 0
        self.ships[0]['shield_recharge_time'] = 0
        self.ships[0]['ability_charges'] = 0
        self.ships[0]['ability_timer'] = 0
        
        # Shield 1 Charged + Shield 2 Charging
        self.ships[1]['shield_hits'] = 1
        self.ships[1]['shield_recharge_time'] = 0
        self.ships[1]['ability_charges'] = 0
        self.ships[1]['ability_timer'] = 0
        
        # Shield 2 Charged + Shield 3 Charging
        self.ships[2]['shield_hits'] = 2
        self.ships[2]['shield_recharge_time'] = 0
        self.ships[2]['ability_charges'] = 0
        self.ships[2]['ability_timer'] = 0
        
        # All 3 Shields Charged
        self.ships[3]['shield_hits'] = 3
        self.ships[3]['shield_recharge_time'] = 0
        self.ships[3]['ability_charges'] = 0
        self.ships[3]['ability_timer'] = 0
        
        # Ability 1 Charging
        self.ships[4]['shield_hits'] = 3
        self.ships[4]['shield_recharge_time'] = 0
        self.ships[4]['ability_charges'] = 0
        self.ships[4]['ability_timer'] = 0
        
        # Ability 1 Charged + Ability 2 Charging
        self.ships[5]['shield_hits'] = 3
        self.ships[5]['shield_recharge_time'] = 0
        self.ships[5]['ability_charges'] = 1
        self.ships[5]['ability_timer'] = 0
        
        # Both Abilities Charged
        self.ships[6]['shield_hits'] = 3
        self.ships[6]['shield_recharge_time'] = 0
        self.ships[6]['ability_charges'] = 2
        self.ships[6]['ability_timer'] = 0
        
        # Shield Recharge Animation (1st)
        self.ships[7]['shield_hits'] = 0
        self.ships[7]['shield_recharge_time'] = 0
        self.ships[7]['shield_recharge_pulse_timer'] = self.ships[7]['shield_recharge_pulse_duration']
        self.ships[7]['ability_charges'] = 0
        self.ships[7]['ability_timer'] = 0
        
        # Shield Recharge Animation (2nd)
        self.ships[8]['shield_hits'] = 1
        self.ships[8]['shield_recharge_time'] = 0
        self.ships[8]['shield_recharge_pulse_timer'] = self.ships[8]['shield_recharge_pulse_duration']
        self.ships[8]['ability_charges'] = 0
        self.ships[8]['ability_timer'] = 0
        
        # Shield Recharge Animation (3rd)
        self.ships[9]['shield_hits'] = 2
        self.ships[9]['shield_recharge_time'] = 0
        self.ships[9]['shield_recharge_pulse_timer'] = self.ships[9]['shield_recharge_pulse_duration']
        self.ships[9]['ability_charges'] = 0
        self.ships[9]['ability_timer'] = 0
        
        # Ability Recharge Animation (1st)
        self.ships[10]['shield_hits'] = 3
        self.ships[10]['shield_recharge_time'] = 0
        self.ships[10]['ability_charges'] = 0
        self.ships[10]['ability_timer'] = 0
        self.ships[10]['ability_recharge_pulse_timer'] = self.ships[10]['ability_recharge_pulse_duration']
        
        # Ability Recharge Animation (2nd)
        self.ships[11]['shield_hits'] = 3
        self.ships[11]['shield_recharge_time'] = 0
        self.ships[11]['ability_charges'] = 1
        self.ships[11]['ability_timer'] = 0
        self.ships[11]['ability_recharge_pulse_timer'] = self.ships[11]['ability_recharge_pulse_duration']
    
    def update(self, dt):
        """Update all timers and states for all ships"""
        # Update each ship individually
        for ship in self.ships:
            # Update shield recharge
            if ship['shield_hits'] < ship['max_shield_hits']:
                ship['shield_recharge_time'] += dt
                if ship['shield_recharge_time'] >= ship['shield_recharge_duration']:
                    ship['shield_hits'] += 1
                    ship['shield_recharge_time'] = 0
                    # Trigger recharge pulse animation
                    ship['shield_recharge_pulse_timer'] = ship['shield_recharge_pulse_duration']
            
            # Update ability recharge
            if ship['ability_charges'] < ship['max_ability_charges']:
                ship['ability_timer'] += dt
                charge_duration = ship['first_charge_duration'] if (ship['ability_charges'] == 0 and ship['is_first_game']) else ship['ability_duration']
                if ship['ability_timer'] >= charge_duration:
                    ship['ability_charges'] += 1
                    ship['ability_timer'] = 0
                    # Trigger recharge pulse animation
                    ship['ability_recharge_pulse_timer'] = ship['ability_recharge_pulse_duration']
                    # Start hold timer
                    ship['ability_hold_timer'] = ship['ability_hold_duration']
            
            # Update timers
            if ship['shield_recharge_pulse_timer'] > 0:
                ship['shield_recharge_pulse_timer'] -= dt
            if ship['shield_pulse_timer'] > 0:
                ship['shield_pulse_timer'] -= dt
            if ship['shield_full_flash_timer'] > 0:
                ship['shield_full_flash_timer'] -= dt
            if ship['shield_full_hold_timer'] > 0:
                ship['shield_full_hold_timer'] -= dt
            if ship['shield_full_fade_timer'] > 0:
                ship['shield_full_fade_timer'] -= dt
            if ship['ability_recharge_pulse_timer'] > 0:
                ship['ability_recharge_pulse_timer'] -= dt
            if ship['ability_hold_timer'] > 0:
                ship['ability_hold_timer'] -= dt
            if ship['ability_fade_timer'] > 0:
                ship['ability_fade_timer'] -= dt
            
            # Continuous pulse timers
            ship['ring_pulse_timer'] += dt
            ship['ability_fully_charged_pulse_timer'] += dt
            
            # Handle shield full animation sequence
            if ship['shield_hits'] == ship['max_shield_hits'] and ship['shield_recharge_pulse_timer'] <= 0:
                if ship['shield_full_flash_timer'] <= 0 and ship['shield_full_hold_timer'] <= 0 and ship['shield_full_fade_timer'] <= 0:
                    # Start the full shield animation sequence
                    ship['shield_full_flash_timer'] = ship['shield_full_flash_duration']
            
            # Handle ability fade sequence
            if ship['ability_charges'] == ship['max_ability_charges'] and ship['ability_hold_timer'] <= 0 and ship['ability_fade_timer'] <= 0:
                ship['ability_fade_timer'] = ship['ability_fade_duration']
    
    def draw_shield_rings(self, screen, ship):
        """Draw shield rings exactly like in the game"""
        shield_radius = ship['radius'] + 15
        
        # Calculate pulse intensity
        pulse_intensity = 0.0
        if ship['shield_recharge_pulse_timer'] > 0:
            # Flash effect when shield just recharged
            pulse = (ship['shield_recharge_pulse_duration'] - ship['shield_recharge_pulse_timer']) / ship['shield_recharge_pulse_duration']
            # Flash 0% to 100% opacity (2 times for 1st charge, 3 times for 2nd charge in 0.5 seconds)
            flash_frequency = (ship['shield_hits'] + 1) * 2  # 2 for 1st, 4 for 2nd, 6 for 3rd
            pulse_intensity = 0.5 + 0.5 * math.sin(pulse * math.pi * flash_frequency)  # 0% to 100%
        elif ship['shield_hits'] < ship['max_shield_hits']:
            # Charging phase
            recharge_progress = ship['shield_recharge_time'] / ship['shield_recharge_duration']
            # Opacity fade: 0% at 0% progress, 75% at 99% progress, 100% at 100% progress
            if recharge_progress < 0.99:
                opacity_progress = recharge_progress / 0.99  # Scale 0-99% to 0-1
                pulse_intensity = 0.75 * opacity_progress  # 0% to 75%
            else:
                pulse_intensity = 0.75 + 0.25 * ((recharge_progress - 0.99) / 0.01)  # 75% to 100% in last 1%
            
            # Add pulsing effect during recharge
            pulse = recharge_progress * math.pi * 4  # 4 pulses during recharge
            pulse_intensity = pulse_intensity * (0.5 + 0.5 * math.sin(pulse))
        elif ship['shield_full_flash_timer'] > 0:
            # Flash effect when all shields are fully charged
            flash_progress = (ship['shield_full_flash_duration'] - ship['shield_full_flash_timer']) / ship['shield_full_flash_duration']
            # Flash 0% to 100% opacity (3 times in 0.3 seconds)
            pulse_intensity = 0.5 + 0.5 * math.sin(flash_progress * math.pi * 6)  # 0% to 100%
        elif ship['shield_full_hold_timer'] > 0:
            # Hold period - 100% opacity
            pulse_intensity = 1.0  # Full opacity during hold
        elif ship['shield_full_fade_timer'] > 0:
            # Fade period - fade from 100% to 33% opacity (smooth animation)
            fade_progress = ship['shield_full_fade_timer'] / ship['shield_full_fade_duration']
            # Smooth fade using ease-out curve
            smooth_fade = fade_progress * fade_progress  # Quadratic ease-out
            pulse_intensity = 0.33 + 0.67 * smooth_fade  # 100% to 33%
        else:
            # Pulsing period - pulse between 25% and 100% opacity with 33% offset per ring
            pulse_intensity = 1.0  # Base intensity, will be modified per ring
        
        # Only draw circles if they should be visible
        if pulse_intensity > 0:
            # Draw circles for each shield hit (outline only, no fill)
            for i in range(ship['shield_hits']):
                # Add 10% offset between shield rings for pulsing effect
                shield_phase = (ship['shield_pulse_timer'] * 2) + (i * 0.10 * math.pi)  # 1 pulse per second, 10% offset
                shield_pulse = 0.5 + 0.5 * math.sin(shield_phase)  # 0.5 to 1.0 multiplier
                
                # During celebration animation (recharge pulse), show only current shield level
                if ship['shield_recharge_pulse_timer'] > 0:
                    # Show only rings up to current shield level during celebration
                    if i < ship['shield_hits']:
                        # Enhanced ripple effect with better oscillation for 2nd recharge
                        if ship['shield_hits'] == 2:
                            # Special oscillation for 2 rings - create wave that moves between them
                            wave_phase = (ship['shield_pulse_timer'] * 4) + (i * 0.5 * math.pi)  # 4x speed, 50% offset
                            # Create alternating pattern: ring 0 bright when ring 1 dim, and vice versa
                            oscillation = 0.2 + 0.8 * math.sin(wave_phase)  # 20%-100% range
                            ring_intensity = pulse_intensity * oscillation
                        else:
                            # Standard ripple for 1st and 3rd recharge
                            ripple_phase = (ship['shield_pulse_timer'] * 3) + (i * 0.3 * math.pi)  # 3x faster, 30% offset
                            ripple_pulse = 0.3 + 0.7 * math.sin(ripple_phase)  # 30%-100% range
                            ring_intensity = pulse_intensity * ripple_pulse
                    else:
                        continue  # Skip drawing rings beyond current level
                # For charging shields, only the charging ring fades, others pulse
                elif ship['shield_hits'] < ship['max_shield_hits'] and i == ship['shield_hits'] - 1:
                    # This is the charging ring - use fade intensity
                    ring_intensity = pulse_intensity
                elif ship['shield_hits'] < ship['max_shield_hits']:
                    # Handle different shield charging states
                    if ship['shield_hits'] == 1:
                        # 1st shield fully charged, 2nd charging - keep 1st at 100% opacity
                        if i == 0:  # First ring (fully charged)
                            ring_intensity = 1.0  # 100% opacity
                        else:  # Second ring (charging)
                            ring_intensity = pulse_intensity  # Use charging intensity
                    elif ship['shield_hits'] == 2:
                        # 2nd shield fully charged, 3rd charging - pulse both rings like ability rings
                        pulse_cycle = (ship['ring_pulse_timer'] * 1) % 1.0  # 1-second cycle
                        # Add 33% offset per ring (0%, 33% for 2 rings)
                        ring_offset = i * 0.33
                        pulse_progress = (pulse_cycle + ring_offset) % 1.0
                        # Pulse from 25% to 100% opacity
                        ring_intensity = 0.25 + 0.75 * (0.5 + 0.5 * math.sin(pulse_progress * 2 * math.pi))
                    elif ship['shield_hits'] == 3:
                        # All 3 shields fully charged - use ability-style pulsing for all rings
                        pulse_cycle = (ship['ring_pulse_timer'] * 1) % 1.0  # 1-second cycle
                        # Add 33% offset per ring (0%, 33%, 66% for 3 rings)
                        ring_offset = i * 0.33
                        pulse_progress = (pulse_cycle + ring_offset) % 1.0
                        # Pulse from 25% to 100% opacity
                        ring_intensity = 0.25 + 0.75 * (0.5 + 0.5 * math.sin(pulse_progress * 2 * math.pi))
                    else:
                        # Other rings - pulse 2 cycles per 0.5s (game time affected)
                        pulse_cycle = (ship['shield_pulse_timer'] * 4) % 0.5  # 0.5 second cycle with 2 pulses
                        pulse_progress = pulse_cycle / 0.5
                        ring_intensity = 0.1 + 0.9 * (0.5 + 0.5 * math.sin(pulse_progress * 4 * math.pi))  # 10%-100%
                else:
                    # Full shields - use main pulse intensity with 10% delay per ring
                    if ship['shield_full_fade_timer'] > 0:
                        # Calculate individual ring fade with 10% delay per ring
                        # Inside ring (i=0) fades first, outside ring (i=2) fades last
                        ring_delay = i * 0.1  # 10% delay per ring (0%, 10%, 20%)
                        ring_fade_progress = max(0, min(1, (fade_progress - ring_delay) / (1 - ring_delay)))
                        ring_intensity = ring_fade_progress * ring_fade_progress  # Quadratic ease-out
                    else:
                        ring_intensity = pulse_intensity
                
                # For 1st shield fully charged, don't apply shield_pulse to keep it at 100% opacity
                if ship['shield_hits'] == 1 and i == 0:
                    alpha = int(255 * ring_intensity)  # No shield_pulse multiplier
                else:
                    alpha = int(255 * ring_intensity * shield_pulse)
                alpha = max(0, min(255, alpha))  # Clamp alpha to valid range
                color = (0, 100, 255, alpha)
                # Draw outline circle (width parameter makes it outline only)
                # Ensure minimum width of 1 to avoid filled circles
                # For 1st shield fully charged, don't apply shield_pulse to width either
                if ship['shield_hits'] == 1 and i == 0:
                    width = max(1, int(4 * ring_intensity))  # 2x thickness, no shield_pulse multiplier
                else:
                    width = max(1, int(4 * ring_intensity * shield_pulse))  # 2x thickness as ability rings
                
                # Create surface with alpha for transparency (like ability rings)
                circle_radius = shield_radius + i * 5
                circle_surface = pygame.Surface((circle_radius * 2, circle_radius * 2), pygame.SRCALPHA)
                pygame.draw.circle(circle_surface, (0, 100, 255, alpha), 
                                (circle_radius, circle_radius), 
                                circle_radius, width)
                screen.blit(circle_surface, (int(ship['position'].x - circle_radius), int(ship['position'].y - circle_radius)))
    
    def draw_ability_rings(self, screen, ship):
        """Draw ability rings exactly like in the game"""
        base_radius = ship['radius'] + 10  # Inside the smallest shield
        
        # Only show ability rings when charging or during pulse effects
        if ship['ability_charges'] < ship['max_ability_charges'] or ship['ability_recharge_pulse_timer'] > 0 or ship['ability_hold_timer'] > 0 or ship['ability_fade_timer'] > 0 or (ship['ability_charges'] == ship['max_ability_charges'] and ship['ability_fade_timer'] <= 0):
            pulse_intensity = 0.0  # Start invisible
            
            # Flash effect when ability just recharged
            if self.ability_recharge_pulse_timer > 0:
                pulse = (self.ability_recharge_pulse_duration - self.ability_recharge_pulse_timer) / self.ability_recharge_pulse_duration
                # Flash 0% to 100% opacity (2 times for 1st charge, 3 times for 2nd charge in 0.5 seconds)
                flash_frequency = self.ability_flash_count * 2  # 4 for 1st charge, 6 for 2nd charge
                pulse_intensity = 0.5 + 0.5 * math.sin(pulse * math.pi * flash_frequency)  # 0% to 100%
            # Charging phase
            elif self.ability_charges < self.max_ability_charges:
                # Calculate progress for current charge
                if self.ability_charges == 0:
                    charge_duration = self.first_charge_duration if self.is_first_game else self.ability_duration
                    ability_progress = self.ability_timer / charge_duration
                else:
                    ability_progress = self.ability_timer / self.ability_duration
                
                # Opacity fade: 0% at 0% progress, 75% at 99% progress, 100% at 100% progress
                if ability_progress < 0.99:
                    opacity_progress = ability_progress / 0.99  # Scale 0-99% to 0-1
                    pulse_intensity = 0.75 * opacity_progress  # 0% to 75%
                else:
                    pulse_intensity = 0.75 + 0.25 * ((ability_progress - 0.99) / 0.01)  # 75% to 100% in last 1%
                
                # Add pulsing effect during recharge
                pulse = ability_progress * math.pi * 4  # 4 pulses during recharge
                pulse_intensity = pulse_intensity * (0.5 + 0.5 * math.sin(pulse))
            # Hold period - 100% opacity
            elif self.ability_hold_timer > 0:
                pulse_intensity = 1.0  # Full opacity during hold
            # Fade period - fade from 100% to 33% opacity (smooth animation)
            elif self.ability_fade_timer > 0:
                fade_progress = self.ability_fade_timer / self.ability_fade_duration
                # Smooth fade using ease-out curve
                smooth_fade = fade_progress * fade_progress  # Quadratic ease-out
                pulse_intensity = 0.33 + 0.67 * smooth_fade  # 100% to 33%
            # Pulsing period - pulse between 25% and 100% opacity with 33% offset per ring
            elif self.ability_charges == self.max_ability_charges:
                # This will be calculated per ring in the drawing loop below
                pulse_intensity = 1.0  # Base intensity, will be modified per ring
            # Otherwise - invisible
            
            # Only draw rings if they should be visible
            if pulse_intensity > 0:
                # Draw rings for each charge
                for charge in range(self.max_ability_charges):
                    ability_radius = base_radius + (charge * 3)  # 3 pixel separation
                    
                    # Determine if this charge is ready
                    is_ready = charge < self.ability_charges
                    
                    if is_ready:
                        # Ready phase: full circle
                        # Color based on number of charges
                        if self.ability_charges == 1:  # 1 charge = purple (ready state)
                            red = 147
                            green = 20
                            blue = 255
                        else:  # 2 charges = hot pink
                            red = 255
                            green = 20
                            blue = 147
                        
                        # Apply opacity based on charge state
                        if self.ability_charges == 1 and charge == 0:
                            # First ring after charging: keep at 100% opacity
                            base_opacity = 1.0
                        elif self.ability_charges == 2 and charge == 0:
                            # First ring when second is charging: keep at 100% opacity
                            base_opacity = 1.0
                        elif self.ability_charges == self.max_ability_charges:
                            # Both charges at 100%: rhythmic pulse with 33% offset per ring
                            pulse_cycle = (self.ability_fully_charged_pulse_timer * 1) % 1.0  # 1-second cycle
                            # Add 33% offset per ring (0%, 33%, 66% for 3 rings)
                            ring_offset = charge * 0.33
                            pulse_progress = (pulse_cycle + ring_offset) % 1.0
                            # Pulse from 25% to 100% opacity
                            base_opacity = 0.25 + 0.75 * (0.5 + 0.5 * math.sin(pulse_progress * 2 * math.pi))
                        else:
                            # Normal pulsing: 33%-100% opacity range
                            base_opacity = 0.33 + 0.67 * pulse_intensity
                        alpha = int(255 * base_opacity)
                        color = (red, green, blue, alpha)
                        
                        # Draw full circle with shield-like thickness
                        # Thickness varies from 1 to 3 based on pulse intensity
                        thickness = 1 + int(2 * pulse_intensity)  # 1 to 3 thickness
                        width = max(1, thickness)
                        
                        # Create surface with alpha for transparency
                        circle_surface = pygame.Surface((ability_radius * 2, ability_radius * 2), pygame.SRCALPHA)
                        pygame.draw.circle(circle_surface, (red, green, blue, alpha), 
                                        (ability_radius, ability_radius), 
                                        ability_radius, width)
                        screen.blit(circle_surface, (int(self.position.x - ability_radius), int(self.position.y - ability_radius)))
                    else:
                        # Charging phase: arc based on progress
                        if self.ability_charges < self.max_ability_charges:  # Show progress if not fully charged
                            # Calculate progress for this specific ring
                            if charge == 0:
                                # First ring: use first charge duration for first game, otherwise normal
                                charge_duration = self.first_charge_duration if self.is_first_game else self.ability_duration
                                ability_progress = self.ability_timer / charge_duration
                            else:
                                # Second ring: only show progress if first ring is charged
                                if self.ability_charges > 0:
                                    ability_progress = self.ability_timer / self.ability_duration
                                else:
                                    ability_progress = 0.0
                            
                            if ability_progress > 0:
                                # Draw arc based on progress (clockwise from 12 o'clock)
                                start_angle = -math.pi / 2  # 12 o'clock
                                end_angle = start_angle + (ability_progress * 2 * math.pi)
                                
                                # Opacity fade: 0% at 0% progress, 75% at 99% progress, 100% at 100% progress
                                if ability_progress < 0.99:
                                    opacity_progress = ability_progress / 0.99  # Scale 0-99% to 0-1
                                    color_intensity = 0.75 * opacity_progress  # 0% to 75%
                                else:
                                    color_intensity = 0.75 + 0.25 * ((ability_progress - 0.99) / 0.01)  # 75% to 100% in last 1%
                                
                                # Add pulsing effect during recharge
                                pulse = ability_progress * math.pi * 4  # 4 pulses during recharge
                                color_intensity = color_intensity * (0.5 + 0.5 * math.sin(pulse))
                                
                                alpha = int(255 * color_intensity)
                                color = (0, 150, 255)  # Slightly brighter blue for recharge indicator
                                
                                # Draw the arc with a thick line to make it visible (50% thinner)
                                width = max(2, int(2.5 * ability_progress))
                                arc_rect = pygame.Rect(
                                    int(self.position.x - ability_radius), 
                                    int(self.position.y - ability_radius),
                                    ability_radius * 2, 
                                    ability_radius * 2
                                )
                                pygame.draw.arc(screen, color, arc_rect, start_angle, end_angle, width)
    
    def draw(self, screen):
        """Draw everything"""
        screen.fill(BLACK)
        
        # Draw ship (simple circle)
        pygame.draw.circle(screen, WHITE, (int(self.position.x), int(self.position.y)), self.radius)
        
        # Draw shield rings
        self.draw_shield_rings(screen)
        
        # Draw ability rings
        self.draw_ability_rings(screen)
        
        # Draw test info
        font = pygame.font.Font(None, 36)
        test_text = font.render(f"Test {self.current_test + 1}/{len(self.tests)}: {self.tests[self.current_test]}", True, WHITE)
        screen.blit(test_text, (10, 10))
        
        # Draw state info
        state_text = font.render(f"Shields: {self.shield_hits}/{self.max_shield_hits} | Abilities: {self.ability_charges}/{self.max_ability_charges}", True, WHITE)
        screen.blit(state_text, (10, 50))
        
        # Draw timer info
        timer_text = font.render(f"Time: {self.test_timer:.1f}s / {self.test_duration:.1f}s", True, WHITE)
        screen.blit(timer_text, (10, 90))
        
        # Draw instructions
        font_small = pygame.font.Font(None, 24)
        instructions = [
            "Press SPACE to advance to next test",
            "Press R to restart current test",
            "Press ESC to exit"
        ]
        for i, instruction in enumerate(instructions):
            text = font_small.render(instruction, True, WHITE)
            screen.blit(text, (10, 130 + i * 25))
    
    def run(self):
        """Main game loop"""
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0  # Convert to seconds
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_SPACE:
                        # Advance to next test
                        next_test = (self.current_test + 1) % len(self.tests)
                        self.setup_test(next_test)
                    elif event.key == pygame.K_r:
                        # Restart current test
                        self.setup_test(self.current_test)
            
            self.update(dt)
            self.draw(self.screen)
            pygame.display.flip()
        
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    test = ShieldAbilityTest()
    test.run()
