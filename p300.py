import pygame
import random
import time
import numpy as np
from pylsl import StreamInfo, StreamOutlet, local_clock

# Initialize Pygame
pygame.init()

# Constants
total_tones = 300
tone_duration_ms = 200
interval_ms = 800
tones_ratio = [0.8, 0.2]
first_tone_frequency = 1200
second_tone_frequency = 1000

# Create a list of tones based on the ratio
tones = [first_tone_frequency] * int(total_tones * tones_ratio[0])
tones += [second_tone_frequency] * int(total_tones * tones_ratio[1])

# Shuffle the list of tones randomly
random.shuffle(tones)

# Ensure that two consecutive 1000Hz tones are avoided
for i in range(1, len(tones)):
    if tones[i] == second_tone_frequency and tones[i - 1] == second_tone_frequency:
        # Swap the tone with the next one to break the sequence
        tones[i], tones[i + 1] = tones[i + 1], tones[i]

# Initialize Pygame mixer
pygame.mixer.init()

# Create an LSL outlet for sending triggers
#info = StreamInfo('ToneTriggers', 'Markers', 2, 0, 'string', 'myuidw43536')
info = StreamInfo('ToneTriggers1', 'Markers', 1, 0, 'string', 'laura_p300')

outlet = StreamOutlet(info)

# # Create a function to play a tone and send a trigger
# def play_tone_with_trigger(frequency):
#     # Send a trigger with a value corresponding to the frequency
#     if frequency == first_tone_frequency:
#         trigger_value = 1
#     else:
#         trigger_value = 2
#     #outlet.push_sample([trigger_value])

#     # Create the audio waveform using numpy
#     sample_rate = 44100  # Adjust as needed
#     t = np.arange(0, tone_duration_ms / 1000.0, 1.0 / sample_rate)
#     audio_waveform = np.sin(2 * np.pi * frequency * t)

#     # Play the tone
#     pygame.mixer.music.set
    
# Play the tones
for frequency in tones:
    # Push the LSL trigger with the tone frequency
    #outlet.push_sample([str(frequency), str(local_clock())])
    msg=f'{{ freq: {frequency}, time: {local_clock()} }}'
    outlet.push_sample([msg]) 
    print(msg)
    #outlet.push_sample(["f:{}".format(frequency)])

    #outlet.push_chunk([frequency], local_clock)
    
    # Create the audio waveform using numpy
    sample_rate = 44100  # Adjust as needed
    t = np.arange(0, tone_duration_ms / 1000.0, 1.0 / sample_rate)
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
    pygame.time.delay(tone_duration_ms)

    # Wait for the interval (800 milliseconds) before the next tone
    pygame.time.delay(interval_ms)

# Quit Pygame
pygame.quit()






