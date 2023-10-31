import asyncio
import tkinter as tk
from tkinter import ttk
from pupil_labs.realtime_api import Device, Network
from DeviceHandler import DeviceHandler
import time
# Data loging
import csv
import os
from datetime import datetime
# LSL
from pylsl import StreamInfo, StreamOutlet, local_clock
# P300
from p300 import P300Test
import concurrent.futures
import pygame
import random
import numpy as np

file_name = 'TEST_'
class App:

    def __init__(self, root, loop):
    
        self.root = root
        self.handlers = []
        self.loop = loop
        self.device_frame = tk.Frame(self.root)
        self.device_frame.pack(fill=tk.X)
        self.is_any_recording = False 

        # Data logging
        self.init_csv_writer()

        # Create LSL stream
        info = StreamInfo('TABARNAK V3', 'Markers', 1, 0, 'string', 'myuidw43536')
        self.outlet = StreamOutlet(info)

        # Create a frame for the navbar
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
        
        # Create a button to send message
        def send_and_clear(): # Send message and clear the input
            self.send_message_all(self.custom_input.get())
            self.custom_input.delete(0, 'end')

        self.custom_button = tk.Button(self.custom_frame, text="SEND", command=send_and_clear)
        self.custom_button.pack(side=tk.LEFT)  

        self.custom_input.bind('<Return>', lambda _: send_and_clear()) # Bind the enter key to the send button
        # Start the heartbeat function
        self.heartbeat()
        self.tasks = [] # List of tasks to cancel on close

        # P300 
        self.p300 = P300Test()
        self.p300_test_button = tk.Button(self.navbar_frame, text="Start P300 Test", command=self.toggle_p300_test)
        self.p300_test_button.pack(side=tk.LEFT)

    # ==== P300 TEST ====
    def toggle_p300_test(self):
        if self.p300_test_button.cget("text") == "Start P300 Test":
            # Run the P300 start function in a thread pool
            self.loop.run_in_executor(concurrent.futures.ThreadPoolExecutor(), self.p300.start)
            self.p300_test_button.config(text="Stop P300 Test")
        else:
            self.p300.stop()
            self.p300_test_button.config(text="Start P300 Test")

   
    #==== SENDING MESSAGE ====
    def send_message_all(self, message):
        # Default message setup
        lsl_time = local_clock()
        u_time = time.time_ns()

        # Convert nanoseconds to seconds
        u_time_s = u_time / 1e9
        dt_object = datetime.fromtimestamp(u_time_s) # Convert unix time to human readable time 
        human_time = dt_object.strftime('%H:%M:%S:%f')     

        formatted_message = f"{message}_t:{u_time}_lsl:{lsl_time}_ht:{human_time}" # Add LSL time and unix time to the message

        print(formatted_message)

        for handler in self.handlers:
            task = asyncio.run_coroutine_threadsafe(handler.send_message(formatted_message, u_time), self.loop)
            self.tasks.append(task)

        # Send message through LSL
        self.outlet.push_sample([formatted_message])
        self.write_to_csv(u_time, lsl_time, human_time, message)

    def heartbeat(self):
        # This function sends a heartbeat message to all devices every 10 seconds
        self.send_message_all("H")
        # Schedule the next heartbeat for 10 seconds from now
        self.heartbeat_id = self.root.after(10000, self.heartbeat)        # Note that because it is using the Tkinter event loop to schedule the heartbeat function, 
        # the function itself doesn't need to be threadsafe. 
        # The after method is the standard way to schedule recurring events in Tkinter.
        # self.write_to_csv(lsl_time, "H", "STAGE TEST")

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
                print("No devices found within the timeout period!")

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

    # ==== DATA LOGGING ====
    def init_csv_writer(self):
        # Initializes a CSV writer with a new file name based on the current time
        data_dir = './data/'
        os.makedirs(data_dir, exist_ok=True)
        now = datetime.now()
        filename = f'{data_dir}{file_name}{self.get_next_file_number()}_{now.strftime("%H-%M-%S-%f_%d-%m-%Y")}.csv'
        self.csv_file = open(filename, 'w', newline='')
        self.csv_writer = csv.writer(self.csv_file)
        self.csv_writer.writerow(['U_TIME', 'LSL_TIME', 'HUMAN_TIME', 'MESSAGE'])
        self.csv_file_is_open = True

    def get_next_file_number(self):
        # Returns the next performance number based on the existing files in the current directory
        data_dir = './data'
        os.makedirs(data_dir, exist_ok=True)
        files = [f for f in os.listdir(data_dir) if os.path.isfile(os.path.join(data_dir, f))]
        perfo_files = [f for f in files if f.startswith(file_name)]
        return len(perfo_files)

    def write_to_csv(self, u_time, lsl_time, human_time, message):
        # Check if file is open before writing
        if self.csv_file_is_open:
            self.csv_writer.writerow([u_time, lsl_time, human_time, message])

    def close_csv(self):
        if self.csv_file_is_open:
            self.csv_file.close()
            self.csv_file_is_open = False
  
    def close(self):
        # Cancel the heartbeat function
        self.root.after_cancel(self.heartbeat_id)
        # Cancel all tasks
        for task in self.tasks:
            task.cancel()

        # Then destroy the window
        self.root.destroy()


