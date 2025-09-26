import pygame
import math
import sys
import os

# Initialize Pygame
pygame.init()

# Constants
SCREEN_WIDTH = 1600
SCREEN_HEIGHT = 1000
FPS = 60

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE = (0, 100, 255)
PURPLE = (147, 20, 255)
HOT_PINK = (255, 20, 147)

def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class ShieldAbilityTest:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Shield & Ability Effects Test - All States")
        self.clock = pygame.time.Clock()
        
        # Load ship image
        try:
            self.ship_image = pygame.image.load(get_resource_path("xwing.gif")).convert_alpha()
        except:
            self.ship_image = None
        
        # Animation timer that resets every 8 seconds
        self.animation_timer = 0
        self.animation_duration = 8.0
        
        # Game constants (matching chuckstaroidsv2.py)
        self.shield_recharge_duration = 3.0
        self.ability_duration = 10.0
        self.first_charge_duration = 5.0
        self.shield_recharge_pulse_duration = 1.0
        self.ability_recharge_pulse_duration = 0.5
        self.ability_hold_duration = 1.0
        self.ability_fade_duration = 0.5
        
        # Ship positions in a grid
        self.ship_positions = [
            # Row 1: Shield states
            (200, 150),   # Shield 1 Charging
            (400, 150),   # Shield 1 Charged + Shield 2 Charging
            (600, 150),   # Shield 2 Charged + Shield 3 Charging
            (800, 150),   # All 3 Shields Charged
            (1000, 150),  # Shield Recharge Animation (1st)
            (1200, 150),  # Shield Recharge Animation (2nd)
            
            # Row 2: Ability states
            (200, 350),   # Ability 1 Charging
            (400, 350),   # Ability 1 Charged + Ability 2 Charging
            (600, 350),   # Both Abilities Charged
            (800, 350),   # Ability Recharge Animation (1st)
            (1000, 350),  # Ability Recharge Animation (2nd)
            
            # Row 3: Combined states
            (200, 550),   # Shield 1 + Ability 1 Charging
            (400, 550),   # Shield 2 + Ability 1 Charged
            (600, 550),   # All Shields + All Abilities
            (800, 550),   # Shield Recharge + Ability Recharge
        ]
        
        # Test descriptions
        self.test_names = [
            "Shield 1 Charging",
            "Shield 1 + Shield 2 Charging", 
            "Shield 2 + Shield 3 Charging",
            "All 3 Shields Charged",
            "Shield Recharge (1st)",
            "Shield Recharge (2nd)",
            "Ability 1 Charging",
            "Ability 1 + Ability 2 Charging",
            "Both Abilities Charged",
            "Ability Recharge (1st)",
            "Ability Recharge (2nd)",
            "Shield 1 + Ability 1 Charging",
            "Shield 2 + Ability 1 Charged",
            "All Shields + All Abilities",
            "Shield + Ability Recharge"
        ]
    
    def get_ship_state(self, index):
        """Get the state for a specific ship based on index and animation timer"""
        progress = (self.animation_timer % self.animation_duration) / self.animation_duration
        
        if index == 0:  # Shield 1 Charging
            return {
                'shield_hits': 0,
                'shield_recharge_time': progress * self.shield_recharge_duration,
                'ability_charges': 0,
                'ability_timer': 0,
                'shield_recharge_pulse_timer': 0,
                'ability_recharge_pulse_timer': 0
            }
        elif index == 1:  # Shield 1 + Shield 2 Charging
            return {
                'shield_hits': 1,
                'shield_recharge_time': progress * self.shield_recharge_duration,
                'ability_charges': 0,
                'ability_timer': 0,
                'shield_recharge_pulse_timer': 0,
                'ability_recharge_pulse_timer': 0
            }
        elif index == 2:  # Shield 2 + Shield 3 Charging
            return {
                'shield_hits': 2,
                'shield_recharge_time': progress * self.shield_recharge_duration,
                'ability_charges': 0,
                'ability_timer': 0,
                'shield_recharge_pulse_timer': 0,
                'ability_recharge_pulse_timer': 0
            }
        elif index == 3:  # All 3 Shields Charged
            return {
                'shield_hits': 3,
                'shield_recharge_time': 0,
                'ability_charges': 0,
                'ability_timer': 0,
                'shield_recharge_pulse_timer': 0,
                'ability_recharge_pulse_timer': 0
            }
        elif index == 4:  # Shield Recharge Animation (1st)
            return {
                'shield_hits': 0,
                'shield_recharge_time': 0,
                'ability_charges': 0,
                'ability_timer': 0,
                'shield_recharge_pulse_timer': max(0, self.shield_recharge_pulse_duration - progress * self.shield_recharge_pulse_duration),
                'ability_recharge_pulse_timer': 0
            }
        elif index == 5:  # Shield Recharge Animation (2nd)
            return {
                'shield_hits': 1,
                'shield_recharge_time': 0,
                'ability_charges': 0,
                'ability_timer': 0,
                'shield_recharge_pulse_timer': max(0, self.shield_recharge_pulse_duration - progress * self.shield_recharge_pulse_duration),
                'ability_recharge_pulse_timer': 0
            }
        elif index == 6:  # Ability 1 Charging
            return {
                'shield_hits': 3,
                'shield_recharge_time': 0,
                'ability_charges': 0,
                'ability_timer': progress * self.first_charge_duration,
                'shield_recharge_pulse_timer': 0,
                'ability_recharge_pulse_timer': 0
            }
        elif index == 7:  # Ability 1 + Ability 2 Charging
            return {
                'shield_hits': 3,
                'shield_recharge_time': 0,
                'ability_charges': 1,
                'ability_timer': progress * self.ability_duration,
                'shield_recharge_pulse_timer': 0,
                'ability_recharge_pulse_timer': 0
            }
        elif index == 8:  # Both Abilities Charged
            return {
                'shield_hits': 3,
                'shield_recharge_time': 0,
                'ability_charges': 2,
                'ability_timer': 0,
                'shield_recharge_pulse_timer': 0,
                'ability_recharge_pulse_timer': 0
            }
        elif index == 9:  # Ability Recharge Animation (1st)
            return {
                'shield_hits': 3,
                'shield_recharge_time': 0,
                'ability_charges': 0,
                'ability_timer': 0,
                'shield_recharge_pulse_timer': 0,
                'ability_recharge_pulse_timer': max(0, self.ability_recharge_pulse_duration - progress * self.ability_recharge_pulse_duration)
            }
        elif index == 10:  # Ability Recharge Animation (2nd)
            return {
                'shield_hits': 3,
                'shield_recharge_time': 0,
                'ability_charges': 1,
                'ability_timer': 0,
                'shield_recharge_pulse_timer': 0,
                'ability_recharge_pulse_timer': max(0, self.ability_recharge_pulse_duration - progress * self.ability_recharge_pulse_duration)
            }
        elif index == 11:  # Shield 1 + Ability 1 Charging
            return {
                'shield_hits': 0,
                'shield_recharge_time': progress * self.shield_recharge_duration,
                'ability_charges': 0,
                'ability_timer': progress * self.first_charge_duration,
                'shield_recharge_pulse_timer': 0,
                'ability_recharge_pulse_timer': 0
            }
        elif index == 12:  # Shield 2 + Ability 1 Charged
            return {
                'shield_hits': 2,
                'shield_recharge_time': 0,
                'ability_charges': 1,
                'ability_timer': 0,
                'shield_recharge_pulse_timer': 0,
                'ability_recharge_pulse_timer': 0
            }
        elif index == 13:  # All Shields + All Abilities
            return {
                'shield_hits': 3,
                'shield_recharge_time': 0,
                'ability_charges': 2,
                'ability_timer': 0,
                'shield_recharge_pulse_timer': 0,
                'ability_recharge_pulse_timer': 0
            }
        elif index == 14:  # Shield + Ability Recharge
            return {
                'shield_hits': 1,
                'shield_recharge_time': 0,
                'ability_charges': 0,
                'ability_timer': 0,
                'shield_recharge_pulse_timer': max(0, self.shield_recharge_pulse_duration - progress * self.shield_recharge_pulse_duration),
                'ability_recharge_pulse_timer': max(0, self.ability_recharge_pulse_duration - progress * self.ability_recharge_pulse_duration)
            }
    
    def draw_shield_rings(self, screen, pos, state):
        """Draw shield rings for a specific ship"""
        shield_radius = 20
        
        # Calculate pulse intensity
        pulse_intensity = 0.0
        if state['shield_recharge_pulse_timer'] > 0:
            # Flash effect when shield just recharged
            pulse = state['shield_recharge_pulse_timer'] / self.shield_recharge_pulse_duration
            flash_frequency = (state['shield_hits'] + 1) * 2
            pulse_intensity = 0.5 + 0.5 * math.sin(pulse * math.pi * flash_frequency)
        elif state['shield_hits'] < 3:
            # Charging phase - fade from 30% to 100%
            recharge_progress = state['shield_recharge_time'] / self.shield_recharge_duration
            pulse_intensity = 0.3 + 0.7 * recharge_progress  # Fade from 30% to 100%
        else:
            # Pulsing period
            pulse_intensity = 1.0
        
        # Draw circles for each shield hit
        if pulse_intensity > 0:
            for i in range(state['shield_hits']):
                # Add pulsing effect
                shield_phase = (self.animation_timer * 2) + (i * 0.10 * math.pi)
                shield_pulse = 0.5 + 0.5 * math.sin(shield_phase)
                
                # Calculate ring intensity
                if state['shield_hits'] == 1 and i == 0:
                    ring_intensity = 1.0  # Keep first shield at 100% opacity
                elif state['shield_hits'] < 3:
                    if state['shield_hits'] == 1 and i == 0:
                        ring_intensity = 1.0
                    elif state['shield_hits'] == 2:
                        # Pulse both rings like ability rings
                        pulse_cycle = (self.animation_timer * 1) % 1.0
                        ring_offset = i * 0.33
                        pulse_progress = (pulse_cycle + ring_offset) % 1.0
                        ring_intensity = 0.25 + 0.75 * (0.5 + 0.5 * math.sin(pulse_progress * 2 * math.pi))
                    else:
                        ring_intensity = pulse_intensity
                else:
                    # All 3 shields - use ability-style pulsing
                    pulse_cycle = (self.animation_timer * 1) % 1.0
                    ring_offset = i * 0.33
                    pulse_progress = (pulse_cycle + ring_offset) % 1.0
                    ring_intensity = 0.25 + 0.75 * (0.5 + 0.5 * math.sin(pulse_progress * 2 * math.pi))
                
                # Calculate alpha and width
                if state['shield_hits'] == 1 and i == 0:
                    alpha = int(255 * ring_intensity)
                    width = max(1, int(4 * ring_intensity))
                else:
                    alpha = int(255 * ring_intensity * shield_pulse)
                    width = max(1, int(4 * ring_intensity * shield_pulse))
                
                alpha = max(0, min(255, alpha))
                
                # Draw circle
                circle_radius = shield_radius + i * 5
                circle_surface = pygame.Surface((circle_radius * 2, circle_radius * 2), pygame.SRCALPHA)
                pygame.draw.circle(circle_surface, (0, 100, 255, alpha), 
                                (circle_radius, circle_radius), 
                                circle_radius, width)
                screen.blit(circle_surface, (int(pos[0] - circle_radius), int(pos[1] - circle_radius)))
    
    def draw_ability_rings(self, screen, pos, state):
        """Draw ability rings for a specific ship"""
        base_radius = 15
        
        # Only show ability rings when charging or during pulse effects
        if state['ability_charges'] < 2 or state['ability_recharge_pulse_timer'] > 0 or (state['ability_charges'] == 2):
            pulse_intensity = 0.0
            
            # Flash effect when ability just recharged
            if state['ability_recharge_pulse_timer'] > 0:
                pulse = state['ability_recharge_pulse_timer'] / self.ability_recharge_pulse_duration
                flash_frequency = 4  # 2 times for 1st charge, 3 times for 2nd charge
                pulse_intensity = 0.5 + 0.5 * math.sin(pulse * math.pi * flash_frequency)
            # Charging phase
            elif state['ability_charges'] < 2:
                charge_duration = self.first_charge_duration if state['ability_charges'] == 0 else self.ability_duration
                ability_progress = state['ability_timer'] / charge_duration
                
                # Opacity fade: 0% at 0% progress, 75% at 99% progress, 100% at 100% progress
                if ability_progress < 0.99:
                    opacity_progress = ability_progress / 0.99  # Scale 0-99% to 0-1
                    pulse_intensity = 0.75 * opacity_progress  # 0% to 75%
                else:
                    pulse_intensity = 0.75 + 0.25 * ((ability_progress - 0.99) / 0.01)  # 75% to 100% in last 1%
                
                # Add pulsing effect during recharge
                pulse = ability_progress * math.pi * 4  # 4 pulses during recharge
                pulse_intensity = pulse_intensity * (0.5 + 0.5 * math.sin(pulse))
            # Pulsing period
            elif state['ability_charges'] == 2:
                pulse_intensity = 1.0
            
            # Draw rings if visible
            if pulse_intensity > 0:
                for charge in range(2):
                    ability_radius = base_radius + (charge * 3)
                    is_ready = charge < state['ability_charges']
                    
                    if is_ready:
                        # Ready phase: full circle
                        if state['ability_charges'] == 1:
                            red, green, blue = 147, 20, 255  # Purple
                        else:
                            red, green, blue = 255, 20, 147  # Hot pink
                        
                        # Apply opacity based on charge state
                        if state['ability_charges'] == 1 and charge == 0:
                            base_opacity = 1.0
                        elif state['ability_charges'] == 2 and charge == 0:
                            base_opacity = 1.0
                        elif state['ability_charges'] == 2:
                            # Both charges at 100%: rhythmic pulse with 33% offset per ring
                            pulse_cycle = (self.animation_timer * 1) % 1.0
                            ring_offset = charge * 0.33
                            pulse_progress = (pulse_cycle + ring_offset) % 1.0
                            base_opacity = 0.25 + 0.75 * (0.5 + 0.5 * math.sin(pulse_progress * 2 * math.pi))
                        else:
                            base_opacity = 0.33 + 0.67 * pulse_intensity
                        
                        alpha = int(255 * base_opacity)
                        thickness = 1 + int(2 * pulse_intensity)
                        width = max(1, thickness)
                        
                        # Draw full circle
                        circle_surface = pygame.Surface((ability_radius * 2, ability_radius * 2), pygame.SRCALPHA)
                        pygame.draw.circle(circle_surface, (red, green, blue, alpha), 
                                        (ability_radius, ability_radius), 
                                        ability_radius, width)
                        screen.blit(circle_surface, (int(pos[0] - ability_radius), int(pos[1] - ability_radius)))
                    else:
                        # Charging phase: arc based on progress
                        if state['ability_charges'] < 2:
                            charge_duration = self.first_charge_duration if charge == 0 else self.ability_duration
                            ability_progress = state['ability_timer'] / charge_duration
                            
                            if ability_progress > 0:
                                # Draw arc based on progress (clockwise from 12 o'clock)
                                start_angle = -math.pi / 2
                                end_angle = start_angle + (ability_progress * 2 * math.pi)
                                
                                if ability_progress < 0.99:
                                    opacity_progress = ability_progress / 0.99
                                    color_intensity = 0.75 * opacity_progress
                                else:
                                    color_intensity = 0.75 + 0.25 * ((ability_progress - 0.99) / 0.01)
                                
                                pulse = ability_progress * math.pi * 4
                                color_intensity = color_intensity * (0.5 + 0.5 * math.sin(pulse))
                                
                                alpha = int(255 * color_intensity)
                                width = max(2, int(2.5 * ability_progress))
                                arc_rect = pygame.Rect(
                                    int(pos[0] - ability_radius), 
                                    int(pos[1] - ability_radius),
                                    ability_radius * 2, 
                                    ability_radius * 2
                                )
                                pygame.draw.arc(screen, (0, 150, 255), arc_rect, start_angle, end_angle, width)
    
    def draw_ship(self, screen, pos, state):
        """Draw a single ship with its effects"""
        # Draw ship using image or fallback to circle
        if self.ship_image:
            # Scale ship image to appropriate size
            ship_size = 30
            scaled_ship = pygame.transform.scale(self.ship_image, (ship_size, ship_size))
            ship_rect = scaled_ship.get_rect(center=(int(pos[0]), int(pos[1])))
            screen.blit(scaled_ship, ship_rect)
        else:
            # Fallback to circle
            pygame.draw.circle(screen, WHITE, (int(pos[0]), int(pos[1])), 15)
        
        # Draw shield rings
        self.draw_shield_rings(screen, pos, state)
        
        # Draw ability rings
        self.draw_ability_rings(screen, pos, state)
    
    def update(self, dt):
        """Update animation timer"""
        self.animation_timer += dt
    
    def get_timing_data(self, state, index):
        """Get detailed timing and opacity data for a state"""
        progress = (self.animation_timer % self.animation_duration) / self.animation_duration
        
        data = {
            'shield_hits': state['shield_hits'],
            'ability_charges': state['ability_charges'],
            'shield_recharge_progress': min(1.0, state['shield_recharge_time'] / self.shield_recharge_duration) if state['shield_hits'] < 3 else 1.0,
            'ability_recharge_progress': min(1.0, state['ability_timer'] / (self.first_charge_duration if state['ability_charges'] == 0 else self.ability_duration)) if state['ability_charges'] < 2 else 1.0,
            'shield_pulse_timer': state['shield_recharge_pulse_timer'],
            'ability_pulse_timer': state['ability_recharge_pulse_timer']
        }
        
        # Calculate shield ring opacities
        shield_opacities = []
        for i in range(3):
            if i < state['shield_hits']:
                if state['shield_hits'] == 1 and i == 0:
                    shield_opacities.append(1.0)  # First shield at 100%
                elif state['shield_hits'] == 2:
                    # Pulse both rings
                    pulse_cycle = (self.animation_timer * 1) % 1.0
                    ring_offset = i * 0.33
                    pulse_progress = (pulse_cycle + ring_offset) % 1.0
                    opacity = 0.25 + 0.75 * (0.5 + 0.5 * math.sin(pulse_progress * 2 * math.pi))
                    shield_opacities.append(opacity)
                elif state['shield_hits'] == 3:
                    # All 3 shields pulse
                    pulse_cycle = (self.animation_timer * 1) % 1.0
                    ring_offset = i * 0.33
                    pulse_progress = (pulse_cycle + ring_offset) % 1.0
                    opacity = 0.25 + 0.75 * (0.5 + 0.5 * math.sin(pulse_progress * 2 * math.pi))
                    shield_opacities.append(opacity)
                else:
                    shield_opacities.append(0.5)  # Charging
            else:
                shield_opacities.append(0.0)
        
        data['shield_opacities'] = shield_opacities
        
        # Calculate ability ring opacities
        ability_opacities = []
        for i in range(2):
            if i < state['ability_charges']:
                if state['ability_charges'] == 1 and i == 0:
                    ability_opacities.append(1.0)  # First ability at 100%
                elif state['ability_charges'] == 2:
                    # Both abilities pulse
                    pulse_cycle = (self.animation_timer * 1) % 1.0
                    ring_offset = i * 0.33
                    pulse_progress = (pulse_cycle + ring_offset) % 1.0
                    opacity = 0.25 + 0.75 * (0.5 + 0.5 * math.sin(pulse_progress * 2 * math.pi))
                    ability_opacities.append(opacity)
                else:
                    ability_opacities.append(0.5)  # Charging
            else:
                ability_opacities.append(0.0)
        
        data['ability_opacities'] = ability_opacities
        
        return data
    
    def draw(self, screen):
        """Draw everything"""
        screen.fill(BLACK)
        
        # Draw all ships
        for i, pos in enumerate(self.ship_positions):
            if i < len(self.test_names):
                state = self.get_ship_state(i)
                self.draw_ship(screen, pos, state)
                
                # Draw label
                font = pygame.font.Font(None, 20)
                text = font.render(self.test_names[i], True, WHITE)
                screen.blit(text, (pos[0] - 60, pos[1] + 40))
                
                # Draw detailed timing data
                timing_data = self.get_timing_data(state, i)
                y_offset = 60
                
                # Shield data
                font_small = pygame.font.Font(None, 16)
                shield_text = f"Shields: {timing_data['shield_hits']}/3 ({timing_data['shield_recharge_progress']:.2f})"
                text = font_small.render(shield_text, True, WHITE)
                screen.blit(text, (pos[0] - 60, pos[1] + y_offset))
                y_offset += 15
                
                # Shield ring opacities
                for j, opacity in enumerate(timing_data['shield_opacities']):
                    if opacity > 0:
                        ring_text = f"Ring {j+1}: {opacity:.2f}"
                        text = font_small.render(ring_text, True, WHITE)
                        screen.blit(text, (pos[0] - 60, pos[1] + y_offset))
                        y_offset += 12
                
                # Ability data
                ability_text = f"Abilities: {timing_data['ability_charges']}/2 ({timing_data['ability_recharge_progress']:.2f})"
                text = font_small.render(ability_text, True, WHITE)
                screen.blit(text, (pos[0] - 60, pos[1] + y_offset))
                y_offset += 15
                
                # Ability ring opacities
                for j, opacity in enumerate(timing_data['ability_opacities']):
                    if opacity > 0:
                        ring_text = f"Ability {j+1}: {opacity:.2f}"
                        text = font_small.render(ring_text, True, WHITE)
                        screen.blit(text, (pos[0] - 60, pos[1] + y_offset))
                        y_offset += 12
                
                # Pulse timers
                if timing_data['shield_pulse_timer'] > 0:
                    pulse_text = f"Shield Pulse: {timing_data['shield_pulse_timer']:.2f}s"
                    text = font_small.render(pulse_text, True, (255, 255, 0))
                    screen.blit(text, (pos[0] - 60, pos[1] + y_offset))
                    y_offset += 12
                
                if timing_data['ability_pulse_timer'] > 0:
                    pulse_text = f"Ability Pulse: {timing_data['ability_pulse_timer']:.2f}s"
                    text = font_small.render(pulse_text, True, (255, 255, 0))
                    screen.blit(text, (pos[0] - 60, pos[1] + y_offset))
                    y_offset += 12
        
        # Draw timer info
        font = pygame.font.Font(None, 36)
        timer_text = font.render(f"Animation Timer: {self.animation_timer:.1f}s (resets every {self.animation_duration}s)", True, WHITE)
        screen.blit(timer_text, (10, 10))
        
        # Draw instructions
        font_small = pygame.font.Font(None, 24)
        instructions = [
            "Press SPACE to reset animation",
            "Press ESC to exit",
            "Yellow text = Active pulse timers"
        ]
        for i, instruction in enumerate(instructions):
            text = font_small.render(instruction, True, WHITE)
            screen.blit(text, (10, 50 + i * 25))
    
    def run(self):
        """Main game loop"""
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_SPACE:
                        # Reset animation
                        self.animation_timer = 0
            
            self.update(dt)
            self.draw(self.screen)
            pygame.display.flip()
        
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    test = ShieldAbilityTest()
    test.run()
