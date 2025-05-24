import pytest
import numpy as np
import pygame
from unittest.mock import patch, MagicMock
import timeit
import os
from datetime import datetime
import csv

file_name = 'TEST_'
data_dir = './data/test/'

class SectionState:
    STOPPED = 0
    RUNNING = 1

class Talker:
    def send(self, _):
        return "mocked_reply"
    def close(self):
        pass

class DummyClass:
    def __init__(self):
        self.vector_state = SectionState.STOPPED
        self.sections = [{'id': 1, 'name': 'A', 'people': 3}]
        self.current_section_index = 0
        self.tone_duration_ms = 100
        self.init_csv_writer()

    def write_to_csv(self, u_time, lsl_time, human_time, message, vector_num=None, vector_name=None, performer=None):
        if hasattr(self, 'csv_writer') and not self.csv_file.closed:
            self.csv_writer.writerow([u_time, lsl_time, human_time, message, vector_num, vector_name, performer])
            self.csv_file.flush()

    def init_csv_writer(self):
        os.makedirs(data_dir, exist_ok=True)
        now = datetime.now()
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        filename = f'{data_dir}{file_name}.csv'
        self.csv_file = open(filename, 'w', newline='')
        self.csv_writer = csv.writer(self.csv_file)
        self.csv_writer.writerow(['U_TIME', 'LSL_TIME', 'HUMAN_TIME', 'MESSAGE', "VECTOR_NUM", "VECTOR_NAME", "PERFORMER"])

def function_under_test(self, formatted_message, u_time, lsl_time, human_time, message, frequency=440):
    try:
        blue_balls = Talker()
        _ = blue_balls.send(f'log("{formatted_message}")')
        blue_balls.close()
    except:
        pass

    if self.vector_state == SectionState.STOPPED:
        self.write_to_csv(u_time, lsl_time, human_time, message)
    else:
        current_vector = self.sections[self.current_section_index]
        self.write_to_csv(u_time, lsl_time, human_time, message, current_vector['id'], current_vector['name'], current_vector['people'])

    sample_rate = 44100
    t = np.arange(0, self.tone_duration_ms / 1000.0, 1.0 / sample_rate)
    audio_waveform = np.sin(2 * np.pi * frequency * t)
    audio_waveform = (audio_waveform * 32767.0).astype(np.int16)
    audio_waveform = np.column_stack((audio_waveform, audio_waveform))
    sound = pygame.sndarray.make_sound(audio_waveform)
    return sound

def test_all_branches_and_audio_with_mocks():
    dummy = DummyClass()

    with patch.object(Talker, 'send', return_value="mocked_reply") as mock_send, \
         patch.object(Talker, 'close') as mock_close, \
         patch.object(dummy, 'write_to_csv') as mock_write, \
         patch('pygame.sndarray.make_sound', return_value="mocked_sound") as mock_sound:

        dummy.vector_state = SectionState.STOPPED
        sound1 = function_under_test(dummy, "msg", 1, 2, 3, "msg")
        assert sound1 == "mocked_sound"
        assert mock_write.called
        assert mock_send.called
        assert mock_close.called

        dummy.vector_state = SectionState.RUNNING
        sound2 = function_under_test(dummy, "msg", 1, 2, 3, "msg")
        assert sound2 == "mocked_sound"

#==== TEST FUCNTION =========================================================
def timeit_function():
    dummy = DummyClass()
    with patch.object(Talker, 'send', return_value="mocked_reply"), \
         patch.object(Talker, 'close'), \
         patch.object(dummy, 'write_to_csv'), \
         patch('pygame.sndarray.make_sound', return_value="mocked_sound"):
        function_under_test(dummy, "msg", 1, 2, 3, "msg", frequency=440)

if __name__ == "__main__":
    print("Timing full function with mocks:")
    print(timeit.timeit(timeit_function))
