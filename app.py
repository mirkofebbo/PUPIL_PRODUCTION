import asyncio
import tkinter as tk
from tkinter import ttk
from pupil_labs.realtime_api import Device, Network
from DeviceHandler import DeviceHandler
import time
# Data loging
import csv
from datetime import datetime
import os
import json
from datetime import datetime
from pylsl import StreamInfo, StreamOutlet
from P300Test import P300Test
import concurrent.futures
import pygame
import random
import numpy as np

class App:

    def __init__(self, root, loop):
        self.root = root
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.handlers = []
        self.loop = loop
        self.device_frame = tk.Frame(self.root)
        self.device_frame.pack(fill=tk.X)
        self.is_any_recording = False 

        # Create LSL stream
        info = StreamInfo('TABARNAK V3', 'Markers', 1, 0, 'string', 'myuidw43536')
        self.outlet = StreamOutlet(info)

        # Button and functionality
        self.navbar_frame = tk.Frame(self.root)
        self.navbar_frame.pack(fill=tk.X)

        self.discover_button = tk.Button(self.navbar_frame, text="Discover Devices", 
                                        command=self.discover_devices_threadsafe)
        self.discover_button.pack(side=tk.LEFT)  

        self.start_all_button = tk.Button(self.navbar_frame, text="Start Recording All", 
                                        command=self.toggle_recording_all)
        self.start_all_button.pack(side=tk.LEFT)  
        
        self.custom_frame = tk.Frame(self.root)  
        self.custom_frame.pack(fill=tk.X) 

        self.custom_input = tk.Entry(self.custom_frame)
        self.custom_input.pack(side=tk.LEFT)

        def send_and_clear():
            self.send_message_all(self.custom_input.get(), time.time_ns())
            self.custom_input.delete(0, 'end')

        self.custom_button = tk.Button(self.custom_frame, text="SEND", command=send_and_clear)
        self.custom_button.pack(side=tk.LEFT)

        self.custom_input.bind('<Return>', lambda _: send_and_clear())
        
        #Start heartbeat and log on the threads 
        self.heartbeat()
        self.tasks = [] # log the current threads

        # P300 
          
        self.p300_test_button = tk.Button(self.navbar_frame, text="Start P300 Test", command=self.trigger_p300_test)
        self.p300_test_button.pack(side=tk.LEFT)
        self.is_p300_running = False

    # 
    async def run_p300_test(self):
        # Use default loop's ThreadPoolExecutor.
        loop = asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor() as pool:
            await loop.run_in_executor(pool, self.p300_sound_play)

    async def start_p300_test(self):
        await self.run_p300_test()

    def stop_p300_test(self):
        self.is_p300_running = False

    def trigger_p300_test(self):
        if self.p300_test_button.cget("text") == "Start P300 Test":
            self.is_p300_running = True 
            asyncio.run_coroutine_threadsafe(self.start_p300_test(), self.loop)
            self.p300_test_button.config(text="Stop P300 Test")
        else:
            self.is_p300_running = False  
            self.stop_p300_test()
            self.p300_test_button.config(text="Start P300 Test")


    #==== P300 ====
    def p300_sound_play(self):
        
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

        # Play the tones
        for frequency in tones:
            if not self.is_p300_running:
                break
            message = f"freq: {frequency}"
            u_time = time.time_ns()
            self.send_message_all(message, u_time)
            # Push the LSL trigger with the tone frequency
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
        
    #==== SENDING MESSAGE ====
    def send_message_all(self, message, u_time):
        # Default message
        formatted_message = f"{message}"
        print(message)
        # Send message through LSL
        self.outlet.push_sample([formatted_message])

        for handler in self.handlers:
            task = asyncio.run_coroutine_threadsafe(handler.send_message(formatted_message, u_time), self.loop)
            self.tasks.append(task)

    def heartbeat(self):
        u_time = time.time_ns()
        # This function sends a heartbeat message to all devices every 10 seconds
        self.send_message_all("H", u_time)
        # Schedule the next heartbeat for 10 seconds from now
        self.heartbeat_id = self.root.after(10000, self.heartbeat)        # Note that because it is using the Tkinter event loop to schedule the heartbeat function, 
        # the function itself doesn't need to be threadsafe. 
        # The after method is the standard way to schedule recurring events in Tkinter.
        # self.write_to_csv(u_time, "H", "STAGE TEST")

    # ==== RECORDING ====
    def toggle_recording_all(self):
        if self.is_any_recording:
            # If any recording is in progress, stop all
            for handler in self.handlers:
                if handler.is_recording:
                    self.toggle_recording(handler, handler.record_button)
            self.start_all_button.config(text="Start Recording All")
            self.is_any_recording = False
        else:
            # If no recording is in progress, start all
            for handler in self.handlers:
                if not handler.is_recording:
                    self.toggle_recording(handler, handler.record_button)
            self.start_all_button.config(text="Stop Recording All")
            self.is_any_recording = True

    def toggle_recording(self, handler, button):
        if handler.is_recording:
            asyncio.run_coroutine_threadsafe(handler.stop_recording(), self.loop)
            handler.is_recording = False
            button.config(text="Start Recording")
        else:
            asyncio.run_coroutine_threadsafe(handler.start_recording(), self.loop)
            handler.is_recording = True
            button.config(text="Stop Recording")

    # ==== DEVICE DISCOVERY ====
    def discover_devices_threadsafe(self):
        # Schedule discover_devices() coroutine to run on the asyncio event loop
        asyncio.run_coroutine_threadsafe(self.discover_devices(), self.loop)
    
    async def discover_devices(self):
        # Use Pupil Labs API to discover devices
        async with Network() as network:
            # loop to search for devices
            while True:
                try:
                    dev_info = await asyncio.wait_for(network.wait_for_new_device(), timeout=5)
                    # Check if device already exists in handlers list using the name
                    print(dev_info.name)

                    if not any(handler.dev_info.name == dev_info.name for handler in self.handlers):
                        handler = DeviceHandler(dev_info)
                        await handler.init_device()  # Initialize the device
                        handler.is_recording = False  # Add a state variable to handler
                        self.handlers.append(handler)

                except asyncio.TimeoutError:
                    # no more devices to be found, break the loop
                    break

        # If no devices found, create a label and return
        if not self.handlers:
            print("No devices could be found! Abort")
            no_device_label = tk.Label(self.device_frame, text="No devices found.")
            no_device_label.pack()
            return

        # If devices found, schedule the display_devices coroutine
        devices_info = await self.get_device_info()  # Get the updated info
        self.root.after(0, self.display_devices, devices_info)  # Schedule on the Tkinter event loop

    # ==== DEVICE DISPLAY ====
    async def get_device_info(self):
        return [await handler.get_info() for handler in sorted(self.handlers, key=lambda handler: handler.dev_info.name)]

    def display_devices(self, devices_info):
        # Clear previous device labels
        for widget in self.device_frame.winfo_children():
            widget.destroy()

        # Sort the device handlers by device name before displaying
        self.handlers.sort(key=lambda handler: handler.dev_info.name)

        # Display current list of devices
        for i, device_info in enumerate(devices_info):

            # Creating a new function here creates a closure that keeps the values of `handler` and `record_button` 
            def make_button(handler):
                record_button = tk.Button(self.device_frame, text="Start Recording",
                                command=lambda: self.toggle_recording(self.handlers[i], record_button))
                record_button.grid(row=i, column=0)  # put the button on the left

                self.handlers[i].record_button = record_button

                return record_button

            make_button(self.handlers[i])

            device_label = tk.Label(self.device_frame, text=device_info)
            device_label.grid(row=i, column=1)  # put the text on the right

            
    def close(self):
        self.is_running = False
        # Cancel the heartbeat function
        self.root.after_cancel(self.heartbeat_id)

        # Cancel all tasks
        for task in self.tasks:
            task.cancel()

        # Then destroy the window
        self.root.destroy()


