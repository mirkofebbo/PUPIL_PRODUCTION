# Pupil Labs Device Manager with LSL Integration
This project provides an interface to discover and control Pupil Labs devices using their Realtime API. It is built with Python's Tkinter for the user interface, asyncio for managing the asynchronous communication with the devices, and LSL for streaming timestamps and messages to EEG systems.

## Features
- Discover Pupil Labs devices on the network
- Start/Stop recording on each individual device
- Start/Stop recording on all devices simultaneously
- Send a message to all devices
- Stream timestamps and messages to EEG systems via LSL
- Each new start of the programe create a new files to log the message sent
- Save all messages in the following columns: U_TIME, LSL_TIME, HUMAN_TIME, MESSAGE
    - U_TIME: unix in nanosecond using time.time_ns() 
    - LSL_TIME: lsl time using local_clock()
    - HUMAN_TIME: human readable time in the following format: %H:%M:%S:%f
    - MESSAGE: only the message string like H or the custom text 
## Getting Started
These instructions will get you a copy of the project up and running on your local machine.

### Prerequisites
- Python 3.10+
- Pupil Labs Realtime API package (pip install pupil_labs)
- pylsl (`pip install pylsl`)

## Usage
- Start the application and click on the "Discover Devices" button to discover the Pupil Labs devices in the network.
- The discovered devices are displayed with their name, IP, battery level, and glasses serial number.
- Use the "Start Recording" button next to each device to start/stop recording on that specific device.
- Use the "Start Recording All" button to start/stop recording on all devices simultaneously.
- Use the custom input field to send a message to all devices.
- Messages and timestamps are also streamed to EEG systems via LSL.

## LSL Integration
The project uses the Lab Streaming Layer (LSL) to stream messages and timestamps to EEG systems. The LSL stream is initialized in the `App` class constructor, and messages are sent via LSL in the `send_message_all` method.

## Contributing
Please read CONTRIBUTING.md for details on our code of conduct, and the process for submitting pull requests to us.
## License
This project is licensed under the MIT License - see the LICENSE.md file for details.

## Acknowledgments
- Thanks to Pupil Labs for providing the Realtime API
- Thanks to the LSL community for providing the Lab Streaming Layer

# Explaining the App Class

The `App` class is the main class that drives the functionality of the GUI application. The `App` class makes use of several other components such as `Tkinter` for the GUI, `asyncio` for asynchronous operations, and the `DeviceHandler` class for handling device-related functionalities.

Below is an explanation of each part of the `App` class:

## 1. `__init__(self, root, loop)`: 

This is the constructor for the `App` class. It initializes the main Tkinter root widget, an asyncio event loop, a list to hold `DeviceHandler` instances, and a frame within the main root widget to hold the device information. It also creates and packs a 'Discover Devices' button into the Tkinter root widget.
In addition to the existing initializations, an LSL stream is also created here. The LSL stream is used to send messages and timestamps to EEG systems.
## 2. `toggle_recording(self, handler, button)`: 

This function controls the recording state of a device. It takes in two arguments: a `DeviceHandler` instance and a Tkinter button. Depending on the current recording state of the device, it will either start or stop the recording and update the text on the button accordingly.

## 3. `send_message(self, handler, message, u_time)`: 

This function is responsible for sending a message to a device. It uses `asyncio` to run the `send_message` coroutine in the `DeviceHandler` class in a threadsafe manner.
This function has been updated to send messages not only to the Pupil Labs devices but also to EEG systems via LSL. The LSL stream is used to push samples, which include the message and the timestamp.

## 4. `discover_devices_threadsafe(self)`: 

This function is used to start the discovery of devices in a threadsafe way.

## 5. `async discover_devices(self)`: 

This coroutine uses the Pupil Labs API to discover devices. It will continue to find devices until it times out. It also checks if a device is already in the handlers list before adding it, thereby preventing duplicate devices. Each discovered device is initialized and its recording state is set to `False`.

## 6. `async get_device_info(self)`: 

This coroutine returns a list of device information for each `DeviceHandler` in the handlers list.

## 7. `display_devices(self, devices_info)`: 

This function displays the information of all discovered devices. It first clears the device frame of any previously displayed information. For each device, it creates a label with the device information, a button to start/stop recording, and a button to send a message. It uses closures to bind each button to its specific handler and to maintain the current state of the recording button.

## 8. `if __name__ == "__main__"`: 

This is the entry point of the application when it's run as a script. It creates the main Tkinter root widget and asyncio event loop, then instantiates the `App` class. It also creates and starts a new thread to run the asyncio event loop so that it can run in parallel with the Tkinter mainloop. 

This entire application functions as a simple graphical user interface to interact with Pupil Labs devices. It provides functionalities to discover devices, display device information, start and stop recording on a device, and send a message to a device.
