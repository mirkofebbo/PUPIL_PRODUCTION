# device_handler.py
import asyncio
from pupil_labs.realtime_api import Device, StatusUpdateNotifier
import time

class DeviceHandler:

    def __init__(self, dev_info):
        self.dev_info = dev_info
        self.device = None
        self.status = None

    async def init_device(self):
        self.device = Device.from_discovered_device(self.dev_info)
        self.status = await self.device.get_status()

    async def get_info(self):
        name = self.status.phone.device_name
        ip = self.status.phone.ip
        battery = self.status.phone.battery_level
        glass = self.status.hardware.glasses_serial
        return [name, ip, battery, glass]
    
    async def start_recording(self):
        # Create notifier to get update when recording is fully started
        notifier = StatusUpdateNotifier(self.device, callbacks=[self.print_recording])

        # Start receiving updates
        await notifier.receive_updates_start()

        # Start recording
        recording_id = await self.device.recording_start()
        print(f"Initiated recording with id {recording_id}")

    async def stop_recording(self):
        print("Stopping recording")
        await self.device.recording_stop_and_save()
        await asyncio.sleep(2)  # wait for confirmation via auto-update

    async def send_message(self, message, u_time):
        # Send a message
        try:
            estimate = self.device.estimate_time_offset()
            u_time_offset = estimate.time_offset_ms.mean *1000000  # Convert MS to NS 
            newtime = u_time - u_time_offset
            event = self.device.send_event(f'{message} o:{u_time_offset} t:{u_time}', event_timestamp_unix_ns=newtime)
            # print(event)
        except:
            print('Not found')

    @staticmethod
    def print_recording(status):
        print("Recording: ", status.recording.is_recording)
