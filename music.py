import pygame
import time
import threading
import math
import numpy as np
from typing import List, Tuple

class EnhancedMusicPlayer:
    """Enhanced music player with dual channels, reverb, and speed control."""
    
    def __init__(self, sample_rate: int = 44100):
        """Initialize the enhanced music player."""
        pygame.mixer.pre_init(frequency=sample_rate, size=-16, channels=2, buffer=1024)
        pygame.mixer.init()
        self.sample_rate = sample_rate
        self.is_playing = False
        self.current_thread = None
        
    def apply_reverb(self, wave: np.ndarray, reverb_amount: float = 0.3, delay_samples: int = 2205) -> np.ndarray:
        """Apply enhanced reverb effect with multiple delays and feedback."""
        if reverb_amount <= 0:
            return wave
        
        result = wave.copy()
        
        # Multiple reverb delays for richer effect
        delays = [delay_samples, delay_samples * 2, delay_samples * 3, delay_samples * 4]
        feedbacks = [reverb_amount, reverb_amount * 0.7, reverb_amount * 0.5, reverb_amount * 0.3]
        
        for delay, feedback in zip(delays, feedbacks):
            if len(wave) > delay:
                delayed = np.zeros_like(wave)
                delayed[delay:] = wave[:-delay] * feedback
                result += delayed
        
        # Add some high-frequency rolloff for more realistic reverb
        # Simple low-pass filter effect
        if len(result) > 1:
            for i in range(1, len(result)):
                result[i] = result[i] * 0.9 + result[i-1] * 0.1
        
        return result
    
    def generate_tone(self, frequency: float, duration: float, volume: float = 0.5, 
                     wave_type: str = "sine", harmonics: List[float] = None, 
                     reverb_amount: float = 0.0) -> pygame.mixer.Sound:
        """Generate a tone with different wave types, harmonics, and reverb."""
        # Extend duration to allow reverb to fully decay
        extended_duration = duration + (reverb_amount * 0.2)  # Add reverb tail time
        frames = int(extended_duration * self.sample_rate)
        
        # Create time array
        t = np.linspace(0, extended_duration, frames, False)
        
        # Generate base wave
        if wave_type == "sine":
            wave = np.sin(2 * np.pi * frequency * t)
        elif wave_type == "square":
            wave = np.sign(np.sin(2 * np.pi * frequency * t))
        elif wave_type == "sawtooth":
            wave = 2 * (frequency * t - np.floor(frequency * t + 0.5))
        elif wave_type == "triangle":
            wave = 2 * np.abs(2 * (frequency * t - np.floor(frequency * t + 0.5))) - 1
        else:
            wave = np.sin(2 * np.pi * frequency * t)
        
        # Add harmonics if specified
        if harmonics:
            for i, harmonic_amp in enumerate(harmonics, 1):
                if wave_type == "sine":
                    wave += harmonic_amp * np.sin(2 * np.pi * frequency * i * t)
                elif wave_type == "triangle":
                    wave += harmonic_amp * (2 * np.abs(2 * (frequency * i * t - np.floor(frequency * i * t + 0.5))) - 1)
                elif wave_type == "square":
                    wave += harmonic_amp * np.sign(np.sin(2 * np.pi * frequency * i * t))
                elif wave_type == "sawtooth":
                    wave += harmonic_amp * 2 * (frequency * i * t - np.floor(frequency * i * t + 0.5))
        
        # Apply advanced envelope to avoid clicks and add musical character
        envelope = np.ones(frames)
        # Fade in
        fade_frames = int(0.01 * self.sample_rate)  # 10ms fade in
        if fade_frames > 0:
            envelope[:fade_frames] = np.linspace(0, 1, fade_frames)
        
        # Main note envelope - ends at original duration
        main_note_frames = int(duration * self.sample_rate)
        if main_note_frames < frames:
            # Advanced fade out with multiple stages
            fade_out_frames = int(0.05 * self.sample_rate)  # 50ms fade out
            if fade_out_frames > 0 and main_note_frames > fade_out_frames:
                # Create smooth exponential fade out
                fade_curve = np.linspace(1, 0, fade_out_frames)
                fade_curve = np.power(fade_curve, 2)  # Exponential curve for smoother fade
                envelope[main_note_frames - fade_out_frames:main_note_frames] = fade_curve
                envelope[main_note_frames:] = 0  # Silence after main note
            else:
                envelope[main_note_frames:] = 0
        else:
            # Fade out at the end with exponential curve
            if fade_frames > 0:
                fade_curve = np.linspace(1, 0, fade_frames)
                fade_curve = np.power(fade_curve, 2)  # Exponential curve
                envelope[-fade_frames:] = fade_curve
        
        wave *= envelope
        
        # Apply reverb
        if reverb_amount > 0:
            wave = self.apply_reverb(wave, reverb_amount)
        
        # Normalize and apply volume
        max_amplitude = np.max(np.abs(wave))
        if max_amplitude > 0:
            wave = wave / max_amplitude * volume
        else:
            wave = wave * volume
        
        # Convert to 16-bit stereo with proper dual-channel processing
        wave_16bit = (wave * 32767).astype(np.int16)
        stereo_wave = np.column_stack((wave_16bit, wave_16bit))
        
        return pygame.sndarray.make_sound(stereo_wave)
    
    def play_dual_channel_sequence(self, left_sequence: List[Tuple], right_sequence: List[Tuple], 
                                 tempo: float = 120.0):
        """Play two sequences simultaneously on left and right channels."""
        self.is_playing = True
        
        def play_thread():
            beat_duration = 60.0 / tempo
            
            # Create combined sequence with both channels
            max_length = max(len(left_sequence), len(right_sequence))
            
            for i in range(max_length):
                if not self.is_playing:
                    break
                
                # Get events from both channels (or silence if one is shorter)
                left_event = left_sequence[i] if i < len(left_sequence) else (0, 0.1, 0.0)
                right_event = right_sequence[i] if i < len(right_sequence) else (0, 0.1, 0.0)
                
                # Process left channel
                if len(left_event) >= 3:
                    freq_l, dur_l, vol_l = left_event[:3]
                    wave_type_l = left_event[3] if len(left_event) > 3 else "sine"
                    harmonics_l = left_event[4] if len(left_event) > 4 else None
                    reverb_l = left_event[5] if len(left_event) > 5 else 0.0
                else:
                    freq_l, dur_l, vol_l = left_event[0], left_event[1], 0.0
                    wave_type_l, harmonics_l, reverb_l = "sine", None, 0.0
                
                # Process right channel
                if len(right_event) >= 3:
                    freq_r, dur_r, vol_r = right_event[:3]
                    wave_type_r = right_event[3] if len(right_event) > 3 else "sine"
                    harmonics_r = right_event[4] if len(right_event) > 4 else None
                    reverb_r = right_event[5] if len(right_event) > 5 else 0.0
                else:
                    freq_r, dur_r, vol_r = right_event[0], right_event[1], 0.0
                    wave_type_r, harmonics_r, reverb_r = "sine", None, 0.0
                
                # Use the longer duration
                note_duration = max(dur_l, dur_r) * beat_duration
                
                # Calculate extended duration for reverb
                max_reverb = max(reverb_l, reverb_r)
                extended_duration = note_duration + (max_reverb * 0.2)
                
                # Generate sounds for both channels
                if freq_l > 0:
                    sound_l = self.generate_tone(freq_l, note_duration, vol_l, wave_type_l, harmonics_l, reverb_l)
                    sound_l.play()
                
                if freq_r > 0:
                    sound_r = self.generate_tone(freq_r, note_duration, vol_r, wave_type_r, harmonics_r, reverb_r)
                    sound_r.play()
                
                time.sleep(extended_duration)
            
            self.is_playing = False
        
        self.current_thread = threading.Thread(target=play_thread)
        self.current_thread.start()
    
    def stop(self):
        """Stop the current playback."""
        self.is_playing = False
        try:
            pygame.mixer.stop()
        except pygame.error:
            # Mixer not initialized, ignore
            pass
        if self.current_thread:
            self.current_thread.join()
    
    def close(self):
        """Close the player and cleanup resources."""
        self.stop()
        try:
            pygame.mixer.quit()
        except:
            pass  # Ignore if mixer already quit
    
    def __del__(self):
        """Cleanup when the object is destroyed."""
        try:
            self.close()
        except:
            pass  # Ignore cleanup errors


class EnhancedAAGACAStyles:
    """Enhanced AAGACA styles with dual channels and effects."""
    
    # Musical note frequencies (Hz)
    NOTES = {
        'A': 440.00,  # A4
        'B': 493.88,  # B4
        'C': 523.25,  # C5
        'D': 587.33,  # D5
        'E': 659.25,  # E5
        'F': 698.46,  # F5
        'G': 391.99,  # G4 (down one octave)
    }
    
    @classmethod
    def get_note_frequency(cls, note_name: str) -> float:
        """Get frequency for a note name."""
        return cls.NOTES.get(note_name.upper(), 440.00)
    
    @classmethod
    def get_base_sequence(cls) -> List[Tuple]:
        """Get the base AAGACA sequence timing."""
        return [
            # A - full beat
            (cls.get_note_frequency('A'), 1.0, 0.1),
            # Quarter beat rest
            (0, 0.25, 0.0),
            # A - full beat
            (cls.get_note_frequency('A'), 1.0, 0.1),
            # Quarter beat rest
            (0, 0.25, 0.0),
            # G - half beat
            (cls.get_note_frequency('G'), 0.5, 0.1),
            # Quarter beat rest
            (0, 0.25, 0.0),
            # A - half beat
            (cls.get_note_frequency('A'), 0.5, 0.1),
            # Quarter beat rest
            (0, 0.25, 0.0),
            # Quarter beat rest (before C)
            (0, 0.25, 0.0),
            # C - 2 beats
            (cls.get_note_frequency('C'), 2.0, 0.1),
            # A - 1.5 beats
            (cls.get_note_frequency('A'), 1.5, 0.1),
        ]
    
    @classmethod
    def get_crystal_style(cls) -> List[Tuple]:
        """Crystal style - triangle waves with crystal-like harmonics and moderate reverb."""
        sequence = cls.get_base_sequence()
        return [(freq, dur, vol * 0.6, "triangle", [0.2, 0.15, 0.1, 0.05, 0.03], 0.3) if freq > 0 else (freq, dur, vol) 
                for freq, dur, vol in sequence]
    
    @classmethod
    def get_ambient_style(cls) -> List[Tuple]:
        """Ambient style - very soft, pure sine waves with moderate reverb."""
        sequence = cls.get_base_sequence()
        return [(freq, dur, vol * 0.6, "sine", None, 0.4) if freq > 0 else (freq, dur, vol) 
                for freq, dur, vol in sequence]
    
    @classmethod
    def get_dual_crystal_ambient(cls) -> Tuple[List[Tuple], List[Tuple]]:
        """Get Crystal and Ambient styles for dual-channel playback."""
        crystal = cls.get_crystal_style()
        ambient = cls.get_ambient_style()
        return crystal, ambient


def main():
    """Main function to play the enhanced dual-channel AAGACA sequence."""
    print("Enhanced AAGACA Music Player")
    print("=" * 35)
    print("🎵 Crystal + Ambient Dual Channel")
    print("⚡ 50% Faster Tempo")
    print("🌊 With Advanced Reverb Effects")
    print("🎼 Complex Harmonic Generation")
    print("🔊 Dual-Channel Stereo Processing")
    print("📈 Advanced Envelope Shaping")
    print()
    
    # Initialize pygame
    pygame.init()
    
    # Create enhanced player
    player = EnhancedMusicPlayer()
    
    print("🎼 Playing enhanced AAGACA sequence...")
    print("Press Ctrl+C to stop")
    print()
    
    try:
        # Get the dual-channel sequences
        crystal_seq, ambient_seq = EnhancedAAGACAStyles.get_dual_crystal_ambient()
        
        # Play at 180 BPM (50% faster than 120 BPM)
        player.play_dual_channel_sequence(crystal_seq, ambient_seq, tempo=180)
        
        # Wait for playback to complete
        while player.is_playing:
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\n🛑 Stopping playback...")
        player.stop()
    
    finally:
        player.close()
        pygame.quit()
        print("✨ Done! Enhanced Crystal and Ambient styles with advanced features!")


if __name__ == "__main__":
    main()