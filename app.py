import asyncio
import tkinter as tk
from tkinter import ttk
from pupil_labs.realtime_api import Device, Network
from DeviceHandler import DeviceHandler
import time
import json
# Data loging
import csv
import os
from datetime import datetime
# LSL
from pylsl import StreamInfo, StreamOutlet, local_clock
# P300
from p300 import P300Test
from fakeP300 import FakeP300Test
import concurrent.futures
# Transition beep 
from TransitionBeep import TransitionBeep
# BLUE BALLS 
from jamie import Talker

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
        info = StreamInfo('TABARNAK V3', 'Markers', 1, 0, 'string', '80085')
        self.outlet = StreamOutlet(info)

        # Create a frame for the navbar
        # PUPIL LAB DEVICES SETUP 
        self.navbar_frame = tk.Frame(self.root)
        self.navbar_frame.pack(fill=tk.X)

        self.discover_button = tk.Button(self.navbar_frame, text="Discover Devices", 
                                        command=self.discover_devices_threadsafe)
        self.discover_button.pack(side=tk.LEFT)  

        self.start_all_button = tk.Button(self.navbar_frame, text="Start Recording All", 
                                        command=self.toggle_recording_all)
        self.start_all_button.pack(side=tk.LEFT)  
        

        # LOAD SECTION DATA
        f = open('vectors.json')
        self.sections = json.load(f)
        # Init current section index and load sections
        self.current_section_index = 0
        self.section_state = "STOPPED"
        self.sections = list(self.sections.values())

        # CUSTOM MESSAGE WITH TIME 
        self.custom_frame = tk.Frame(self.root)  
        self.custom_frame.pack(fill=tk.X) 
        # Add timers next to custom input
        self.start_time = time.time()
        self.button_timer = None

        self.total_time_label = tk.Label(self.custom_frame, text="HH:MM:SS")
        self.total_time_label.pack(side=tk.LEFT)
        self.custom_input = tk.Entry(self.custom_frame)
        self.custom_input.pack(side=tk.LEFT)
        
        # Create a button to send message
        def send_and_clear(): # Send message and clear the input
            self.send_message_all(self.custom_input.get())
            self.custom_input.delete(0, 'end')

        self.custom_button = tk.Button(self.custom_frame, text="SEND", command=send_and_clear)
        self.custom_button.pack(side=tk.LEFT)  
        self.custom_input.bind('<Return>', lambda _: send_and_clear()) # Bind the enter key to the send button
        

        # TIMER AND SECTION NAVBAR
        self.vector_frame = tk.Frame(self.root)  
        self.vector_frame.pack(fill=tk.X) 
        self.sound_time_label = tk.Label(self.vector_frame, text="MM:SS")
        self.sound_time_label.pack(side=tk.LEFT)
         # Create a StringVar for the dropdown menu
        self.vector_var = tk.StringVar(self.root)
        self.vector_var.set(f'VECTOR {self.sections[self.current_section_index]["vector"]}')  # default value

        # Dropdown menu for selecting the vector
        self.vector_dropdown = tk.OptionMenu(self.vector_frame, self.vector_var, 
                                     *(f'VECTOR {section["vector"]}' for section in self.sections), 
                                     command=self.on_vector_select)
        
        self.vector_dropdown.pack(side=tk.LEFT, padx=10)

        self.toggle_section_button = tk.Button(self.vector_frame, text="Start", 
                                               command=self.toggle_section)
        self.toggle_section_button.pack(side=tk.LEFT)

        self.name_label = tk.Label(self.vector_frame, text=self.sections[self.current_section_index]["name"])
        self.name_label.pack(side=tk.LEFT, padx= 2)
        
        # AUDIO RELATED NAVBAR
        self.sound_frame = tk.Frame(self.root)
        self.sound_frame.pack(fill=tk.X)

        # P300
        self.p300 = P300Test(tone_callback=self.on_tone_played)
        self.p300_test_button = tk.Button(self.sound_frame, text="Start P300 Test", command=self.toggle_p300_test)
        self.p300_test_button.pack(side=tk.LEFT)

        # Fake P300
        self.fake_p300 = FakeP300Test(tone_callback=self.on_fake_tone_played)
        self.fake_p300_test_button = tk.Button(self.sound_frame, text="Start Fake P300 Test", command=self.toggle_fake_p300_test)
        self.fake_p300_test_button.pack(side=tk.LEFT)

        # Transition Beep
        self.transition_beep = TransitionBeep(beep_callback=self.on_beep_played, sequence_complete_callback=self.on_transition_complete)
        self.transition_beep_button = tk.Button(self.sound_frame, text="Start Transition Beep", 
                                                command=self.toggle_transition_beep)
        self.transition_beep_button.pack(side=tk.LEFT)

        # Start the heartbeat function
        self.heartbeat()
        self.tasks = []  # List of tasks to cancel on close
        
        # Start timers
        self.update_timers()

    # ==== SECTION ====
    def on_vector_select(self, choice):
        # Extract the vector label from the choice
        vector_label = choice.replace('VECTOR ', '')  # This assumes choice is like "VECTOR 5.2"
        # Find the index of the section with the selected vector label
        self.current_section_index = next((index for index, section in enumerate(self.sections) 
                                        if str(section["vector"]) == vector_label), 0)
        # Update the name label and any other UI components as necessary
        current_section = self.sections[self.current_section_index]
        self.name_label.config(text=current_section["name"])
        
    def toggle_section(self):
        current_section = self.sections[self.current_section_index]

        if self.section_state == "STOPPED":
            # If the section requires a transition, play the beep first
            if current_section["transition"]:
                # Start the transition beep and delay starting the timer until it completes
                self.transition_beep.sequence_complete_callback = self.on_transition_complete  # Set the beep callback
                self.loop.run_in_executor(concurrent.futures.ThreadPoolExecutor(), self.transition_beep.start)
            else:
                # If no transition is needed, start the section timer immediately
                self.start_section_logic()
        else:
            # Stop the section
            self.stop_section_logic()

    def start_section_logic(self):
        current_section = self.sections[self.current_section_index]

        # Logic to start the section timer goes here
        self.section_state = "STARTED"
        message = f"VECTOR_{current_section['vector']} STARTED"
        self.send_message_all(message)
        self.vector_var.set(f'VECTOR {current_section["vector"]}')  # Update dropdown
        self.name_label.config(text=current_section["name"])
        self.toggle_section_button.config(text='Stop')
        self.button_timer = time.time()
        
        # Schedule the section to automatically stop after the specified duration
        duration_ms = self.sections[self.current_section_index]["duration"]
        if duration_ms != "open":
            self.root.after(duration_ms, self.auto_stop_section)
    
    def stop_section_logic(self):
        current_section = self.sections[self.current_section_index]
        
        self.section_state = "STOPPED"
        message = f'VECTOR {current_section["vector"]} STOPPED'
        self.send_message_all(message)
        # Increase the current section index (with wrap-around)
        self.current_section_index = (self.current_section_index + 1) % len(self.sections)
        current_section = self.sections[self.current_section_index]
        self.name_label.config(text=current_section["name"])
        self.toggle_section_button.config(text="START")
        self.button_timer = None
        # ... Other logic related to stopping the section

    def auto_stop_section(self):
        if self.section_state == "STARTED":  # Check to make sure the section is still running
            self.stop_section_logic()    

    # ==== TRANSITION BEEP ====
    def toggle_transition_beep(self):
        if self.transition_beep_button.cget("text") == "Start Transition Beep":
            # Run the TransitionBeep start function in a thread pool
            self.loop.run_in_executor(concurrent.futures.ThreadPoolExecutor(), self.transition_beep.start)
            self.transition_beep_button.config(text="Stop Transition Beep")
        else:
            self.transition_beep.stop()
            self.transition_beep_button.config(text="Start Transition Beep")

    def on_beep_played(self, frequency):
        # Callback function when we have a new beep
        message = f"TRANS:{frequency}"
        self.send_message_all(message)

    def on_transition_complete(self, status):
        if status == "complete":
            # Once the transition is complete, start the section timer
            self.start_section_logic()

    # ==== FAKE P300 TEST ====
    def toggle_fake_p300_test(self):
        if self.fake_p300_test_button.cget("text") == "Start Fake P300 Test":
            # Run the P300 start function in a thread pool
            self.loop.run_in_executor(concurrent.futures.ThreadPoolExecutor(), self.fake_p300.start)
            self.fake_p300_test_button.config(text="Stop Fake P300 Test")
            self.button_timer = time.time()
        else:
            self.fake_p300.stop()
            self.fake_p300_test_button.config(text="Start Fake P300 Test")
            self.button_timer = None

    def on_fake_tone_played(self, frequency):
        # Call back function when we have a new beep
        message = f"FAKE:{frequency}"
        self.send_message_all(message)

    # ==== P300 TEST ====
    def toggle_p300_test(self):
        if self.p300_test_button.cget("text") == "Start P300 Test":
            # Run the P300 start function in a thread pool
            self.loop.run_in_executor(concurrent.futures.ThreadPoolExecutor(), self.p300.start)
            self.p300_test_button.config(text="Stop P300 Test")
            self.button_timer = time.time()
        else:
            self.p300.stop()
            self.p300_test_button.config(text="Start P300 Test")
            self.button_timer = None

    def on_tone_played(self, frequency):
        # Call back function when we have a new beep
        message = f"P300:{frequency}"
        self.send_message_all(message)

    # ==== TIMER ====
    def update_timers(self):
        # Update the total time since program started
        elapsed_total = time.time() - self.start_time
        hours, remainder = divmod(elapsed_total, 3600)
        minutes, seconds = divmod(remainder, 60)
        self.total_time_label.config(text="{:02}:{:02}:{:02}".format(int(hours), int(minutes), int(seconds)))

        # Update the time since the sound button was pressed
        if self.button_timer:
            elapsed_sound = time.time() - self.button_timer
            minutes, seconds = divmod(elapsed_sound, 60)
            self.sound_time_label.config(text="{:02}:{:02}".format(int(minutes), int(seconds)))

        # Call this method again after 1000ms (1 second)
        self.root.after(1000, self.update_timers)

    #==== SENDING MESSAGE ====
    def send_message_all(self, message):
        # Default message setup
        lsl_time = local_clock()
        u_time = time.time_ns()

        # Convert nanoseconds to seconds
        u_time_s = u_time / 1e9
        dt_object = datetime.fromtimestamp(u_time_s) # Convert unix time to human readable time 
        human_time = dt_object.strftime('%H:%M:%S:%f')     

        formatted_message = f"{message} T:{u_time} LSL:{lsl_time} HT:{human_time}" # Add LSL time and unix time to the message

        print(formatted_message)
        
        for handler in self.handlers:
            task = asyncio.run_coroutine_threadsafe(handler.send_message(formatted_message, u_time), self.loop)
            self.tasks.append(task)

        # Send message through LSL
        self.outlet.push_sample([formatted_message])
        # BLUE BALLS 
        # blue_balls = Talker()
        # blue_balls.send(f'log("{formatted_message}")')
        # blue_balls.close()

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
            # loop to search for devices
            while True:
                try:
                    dev_info = await asyncio.wait_for(network.wait_for_new_device(), timeout=5)
                    # Check if device already exists in handlers list using the name

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
        self.p300.stop()
        self.fake_p300.stop()
        self.transition_beep.stop()
        # Cancel the heartbeat function
        self.root.after_cancel(self.heartbeat_id)
        # Cancel all tasks
        for task in self.tasks:
            task.cancel()

        # Then destroy the window
        self.root.destroy()


