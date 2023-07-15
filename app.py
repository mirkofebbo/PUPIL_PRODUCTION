import asyncio
import tkinter as tk
from pupil_labs.realtime_api import Device, Network
from DeviceHandler import DeviceHandler
import threading

class App:
    
    def __init__(self, root, loop):
        self.root = root
        self.handlers = []
        self.loop = loop
        self.device_frame = tk.Frame(self.root)
        self.device_frame.pack()

        # Discover button
        self.discover_button = tk.Button(self.root, text="Discover Devices", 
                                         command=self.discover_devices_threadsafe)
        self.discover_button.pack()

    def toggle_recording(self, handler, button):
        if handler.is_recording:
            asyncio.run_coroutine_threadsafe(handler.stop_recording(), self.loop)
            handler.is_recording = False
            button.config(text="Start Recording")
        else:
            asyncio.run_coroutine_threadsafe(handler.start_recording(), self.loop)
            handler.is_recording = True
            button.config(text="Stop Recording")

    def send_message(self, handler, message, u_time):
        asyncio.run_coroutine_threadsafe(handler.send_message(message, u_time), self.loop)

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

    async def get_device_info(self):
        return [await handler.get_info() for handler in self.handlers]

    def display_devices(self, devices_info):
        # Clear previous device labels
        for widget in self.device_frame.winfo_children():
            widget.destroy()

        # Display current list of devices
        for i, device_info in enumerate(devices_info):
            device_label = tk.Label(self.device_frame, text=device_info)
            device_label.pack()

            # Creating a new function here creates a closure that keeps the values of `handler` and `record_button` 
            def make_button(handler):
                record_button = tk.Button(self.device_frame, text="Start Recording",
                                          command=lambda: self.toggle_recording(handler, record_button))
                record_button.pack()
                return record_button

            make_button(self.handlers[i])

            # Placeholder for message and u_time values
            message = "Placeholder"
            u_time = 1234567890
            send_button = tk.Button(self.device_frame, text="Send Message",
                                    command=lambda handler=self.handlers[i]: self.send_message(handler, message, u_time))
            send_button.pack()


if __name__ == "__main__":
    root = tk.Tk()
    loop = asyncio.get_event_loop()
    app = App(root, loop)
    threading.Thread(target=loop.run_forever, daemon=True).start()
    root.mainloop()
