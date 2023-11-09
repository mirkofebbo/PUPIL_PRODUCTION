import pygame
import random
import numpy as np
#30 sec beep -> 40 sec gap -> 1m beep -> 30 sec gap-> beep until stoped
class FakeP300Test:
    def __init__(self, tone_callback=None):
        pygame.init()

        # Constants
        self.tone_duration_ms = 200
        self.interval_ms = 800
        self.first_tone_frequency = 1200
        self.running = False
        self.tone_callback = tone_callback

        # Calculate total tones within 30 seconds
        single_tone_time = self.tone_duration_ms + self.interval_ms
        self.total_tones = int(30000 / single_tone_time) 
        
        self.setup_tones()


    def setup_tones(self):
        # Create a list of tones that consist only of the first tone frequency
        self.tones = [self.first_tone_frequency] * self.total_tones

    def play_tone(self, frequency):
        # push the frequency to the callback function to be sent to all devices
        if self.tone_callback:
            self.tone_callback(frequency)

        # Create the audio waveform using numpy
        sample_rate = 44100  # Adjust as needed
        t = np.arange(0, self.tone_duration_ms / 1000.0, 1.0 / sample_rate)
        audio_waveform = np.sin(2 * np.pi * frequency * t)

        audio_waveform *= 0.35  # This reduces the waveform amplitude by half
        # Convert to 16-bit signed integers
        audio_waveform = (audio_waveform * 32767.0).astype(np.int16)

        # Make it 2-dimensional (mono)
        audio_waveform = np.column_stack((audio_waveform, audio_waveform))

        # Create a Pygame sound object
        sound = pygame.sndarray.make_sound(audio_waveform)

        # Play the sound
        sound.play()

        # Wait for the tone to finish playing
        pygame.time.delay(self.tone_duration_ms)

        # Wait for the interval (800 milliseconds) before the next tone
        pygame.time.delay(self.interval_ms)

    def start(self):
        # Initialize Pygame mixer
        pygame.mixer.init()
        self.running = True
        self.run()

    def stop(self):
        self.running = False

    def run(self):
        while self.running:
            # 30 seconds of beeping
            start_time = pygame.time.get_ticks()
            while pygame.time.get_ticks() - start_time < 30000 and self.running:
                self.play_tone(self.first_tone_frequency)
            
            if not self.running:
                break
            
            # 40 seconds gap
            pygame.time.delay(40000)
            
            # 1 minute of beeping
            start_time = pygame.time.get_ticks()
            while pygame.time.get_ticks() - start_time < 60000 and self.running:
                self.play_tone(self.first_tone_frequency)
            
            if not self.running:
                break
            
            # 30 seconds gap
            pygame.time.delay(30000)
            
            # Beep continuously until stopped
            while self.running:
                self.play_tone(self.first_tone_frequency)

        # Quit Pygame
        pygame.quit()