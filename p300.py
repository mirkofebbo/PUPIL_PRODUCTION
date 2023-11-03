import pygame
import random
import numpy as np

class P300Test:
    def __init__(self, tone_callback=None):
        pygame.init()

        # Constants
        self.total_tones = 360
        self.tone_duration_ms = 200
        self.interval_ms = 800
        self.tones_ratio = [0.8, 0.2]
        self.first_tone_frequency = 1200
        self.second_tone_frequency = 1000
        self.running = False
        self.tone_callback = tone_callback
        
        self.setup_tones()


    def setup_tones(self):
        # Create a list of tones based on the ratio
        self.tones = [self.first_tone_frequency] * int(self.total_tones * self.tones_ratio[0])
        self.tones += [self.second_tone_frequency] * int(self.total_tones * self.tones_ratio[1])

        # Shuffle the list of tones randomly
        random.shuffle(self.tones)

        # Ensure that two consecutive 1000Hz tones are avoided
        for i in range(1, len(self.tones)):
            if self.tones[i] == self.second_tone_frequency and self.tones[i - 1] == self.second_tone_frequency:
                # Swap the tone with the next one to break the sequence
                self.tones[i], self.tones[i + 1] = self.tones[i + 1], self.tones[i]

    def play_tone(self, frequency):
        # push the frequency to the callback function to be sent to all devices
        if self.tone_callback:
            self.tone_callback(frequency)

        # Create the audio waveform using numpy
        sample_rate = 44100  # Adjust as needed
        t = np.arange(0, self.tone_duration_ms / 1000.0, 1.0 / sample_rate)
        audio_waveform = np.sin(2 * np.pi * frequency * t)

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
        for frequency in self.tones:
            if not self.running:  # Stop the test if running flag is False
                break
            self.play_tone(frequency)

        # Quit Pygame
        pygame.quit()