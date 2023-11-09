import pygame
import random
import numpy as np

class TransitionBeep:
    
    def __init__(self, beep_callback=None, sequence_complete_callback=None):
        pygame.init()
        self.beep_callback = beep_callback
        self.sequence_complete_callback = sequence_complete_callback  # Callback for when the sequence is completed
        self.first_tone_frequency = 1600  # Quick beep frequency
        self.second_tone_frequency = 900  # Long beep frequency
        self.running = False

    def special_sequence(self):
        for _ in range(4):
            if not self.running:
                break
            self.play_tone_special(self.first_tone_frequency, 200)  # Quick beep
            pygame.time.delay(1000)  # 1-second delay
        if self.running:
            self.play_tone_special(self.second_tone_frequency, 1000)  # Longer beep
            if self.sequence_complete_callback:  # Check if a callback function has been provided
                self.sequence_complete_callback('complete')  # Invoke the callback

    def play_tone_special(self, frequency, duration_ms):
        # Push the frequency to the callback function to be sent to all devices
        if self.beep_callback:
            self.beep_callback(frequency)

        # Create the audio waveform using numpy
        sample_rate = 44100  # Adjust as needed
        t = np.arange(0, duration_ms / 1000.0, 1.0 / sample_rate)
        audio_waveform = np.sin(2 * np.pi * frequency * t)

        audio_waveform *= 0.8  # This reduces the waveform amplitude by half
        # Convert to 16-bit signed integers
        audio_waveform = (audio_waveform * 32767.0).astype(np.int16)

        # Make it 2-dimensional (mono)
        audio_waveform = np.column_stack((audio_waveform, audio_waveform))

        # Create a Pygame sound object
        sound = pygame.sndarray.make_sound(audio_waveform)

        # Play the sound
        sound.play()

        # Wait for the tone to finish playing
        pygame.time.delay(duration_ms)

    def start(self):
        # Initialize Pygame mixer
        pygame.mixer.init()
        self.running = True
        self.special_sequence()

    def stop(self):
        self.running = False
        pygame.mixer.quit()
