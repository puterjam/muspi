import threading
from evdev import InputDevice, ecodes, list_devices
import select
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from until.log import LOGGER

ecodes = ecodes

class DeviceChangeHandler(FileSystemEventHandler):
    """Handler for device change events"""
    def __init__(self, key_listener):
        super().__init__()
        self.key_listener = key_listener

    def on_created(self, event):
        """Handle device creation"""
        if not event.is_directory and '/dev/input/event' in event.src_path:
            LOGGER.debug(f"Device created: {event.src_path}")
            self.key_listener.rescan_devices()

    def on_deleted(self, event):
        """Handle device deletion"""
        if not event.is_directory and '/dev/input/event' in event.src_path:
            LOGGER.debug(f"Device deleted: {event.src_path}")
            self.key_listener.rescan_devices()

class KeyListener(threading.Thread):
    def __init__(self):
        super().__init__()
        self.daemon = True  # set as daemon thread, exit when main program exits
        self.running = True
        self.devices = []
        self.callbacks = []
        self.observer = Observer()  # 创建 Observer
        self.event_handler = DeviceChangeHandler(self)  # 创建事件处理器
        
    def on(self, callback):
        """add callback function"""
        if callback not in self.callbacks:
            self.callbacks.append(callback)
            LOGGER.debug(f"add keyboardCallback: {callback.__name__}")

    def off(self, callback):
        """remove callback function"""
        if callback in self.callbacks:
            self.callbacks.remove(callback)
            LOGGER.debug(f"remove keyboardCallback: {callback.__name__}")

    def scan(self):
        """scan all available input devices"""
        devices = []
        for device_path in list_devices():
            try:
                dev = InputDevice(device_path)
                devices.append(dev)
                LOGGER.debug(f"scan device: {dev.name}")
            except Exception as e:
                LOGGER.error(f"cannot open device {device_path}: {e}")
        return devices

    def rescan_devices(self):
        """rescan devices and update device list"""
        self.devices = self.scan()

    def run(self):
        """线程主函数"""
        # 设置 watchdog 监听 /dev/input 目录
        self.observer.schedule(self.event_handler, '/dev/input', recursive=False)
        self.observer.start()

        # 扫描设备
        self.devices = self.scan()
        if not self.devices:
            LOGGER.error("no input device found")
            return

        while self.running:
            try:
                r, w, x = select.select(self.devices, [], [], 0.1)
                for device in r:
                    for event in device.read():
                        if event.type == ecodes.EV_KEY:
                            key_name = ecodes.KEY[event.code]
                            LOGGER.debug(f"{device.name} - key down {key_name}")

                            # call all registered callbacks
                            for callback in self.callbacks:
                                try:
                                    callback(device.name, event)
                                except Exception as e:
                                    LOGGER.error(f"execute callback {callback.__name__} error: {e}")

                            LOGGER.debug(f"Event: type={event.type}, code={event.code}, value={event.value}")
            except Exception as e:
                LOGGER.info("read device error, rescanning...")
                LOGGER.error(f"read device error: {e}")
                time.sleep(1)  # 出错后等待1秒再重试
                self.devices = self.scan()

    def stop(self):
        """stop listening"""
        self.running = False
        if self.observer.is_alive():
            self.observer.stop()
            self.observer.join()