import pygame
import random
import numpy as np

class P300Test:

    def __init__(self, callback=None):
        pygame.init()
        
        self.total_tones = 300
        self.tone_duration_ms = 200
        self.interval_ms = 800
        self.tones_ratio = [0.8, 0.2]
        self.first_tone_frequency = 1200
        self.second_tone_frequency = 1000
        self.callback = callback

        pygame.mixer.init()

    def start_test(self):
        tones = [self.first_tone_frequency] * int(self.total_tones * self.tones_ratio[0])
        tones += [self.second_tone_frequency] * int(self.total_tones * self.tones_ratio[1])
        random.shuffle(tones)

        for i in range(1, len(tones)):
            if tones[i] == self.second_tone_frequency and tones[i - 1] == self.second_tone_frequency:
                tones[i], tones[i + 1] = tones[i + 1], tones[i]

        for frequency in tones:
            if self.callback:  # If there's a callback function provided, use it.
                self.callback(frequency)

            sample_rate = 44100
            t = np.arange(0, self.tone_duration_ms / 1000.0, 1.0 / sample_rate)
            audio_waveform = np.sin(2 * np.pi * frequency * t)
            audio_waveform = (audio_waveform * 32767.0).astype(np.int16)
            audio_waveform = np.column_stack((audio_waveform, audio_waveform))
            sound = pygame.sndarray.make_sound(audio_waveform)
            sound.play()

            pygame.time.delay(self.tone_duration_ms)
            pygame.time.delay(self.interval_ms)

        pygame.quit()