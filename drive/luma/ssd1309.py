from luma.core.interface.serial import spi
from luma.oled.device import ssd1309 as _ssd1309
import RPi.GPIO as GPIO

# 定义 SSD1309 引脚 waveshare 128x64
PORT = 0
DEVICE = 0
GPIO_DC = 25
GPIO_RST = 27
IPS_SPEED_HZ = 10000000


def ssd1309(width=128, height=64, rotate=0, **kwargs):
    """
    创建 ssd1309 设备实例

    Args:
        width: 显示宽度，默认 128
        height: 显示高度，默认 64
        rotate: 旋转角度（0, 1, 2, 3），默认 0
        **kwargs: 其他参数传递给设备

    Returns:
        ssd1309 设备实例
    """
    # 设置 GPIO 模式
    GPIO.setmode(GPIO.BCM)

    # 创建 SPI 接口
    serial = SPISerial(
        bus=0,
        device=DEVICE,        
        gpio_DC=GPIO_DC,
        gpio_RST=GPIO_RST,
        spi_speed_hz=IPS_SPEED_HZ,
        gpio=GPIO
    )
    
    # 创建并返回设备实例
    return _ssd1309(serial, width=width, height=height, rotate=rotate, **kwargs)


class SPISerial:
    """
    自定义 SPI 串口类,支持任意频率

    兼容 luma.core.interface.serial.spi 接口,但绕过频率限制
    """
    def __init__(self, bus=0, device=0, gpio_DC=25, gpio_RST=27, spi_speed_hz=10000000, gpio=None):
        import spidev

        self._spi = spidev.SpiDev()
        self._spi.open(bus, device)
        self._spi.max_speed_hz = spi_speed_hz  # 直接设置任意频率!
        self._spi.mode = 0

        self._gpio = gpio
        self._DC = gpio_DC
        self._RST = gpio_RST

        # 设置 GPIO 引脚
        if self._gpio:
            self._gpio.setup(self._DC, self._gpio.OUT)
            self._gpio.setup(self._RST, self._gpio.OUT)

            # 复位 OLED
            self._gpio.output(self._RST, self._gpio.LOW)
            import time
            time.sleep(0.01)
            self._gpio.output(self._RST, self._gpio.HIGH)

            # 等待复位稳定
            time.sleep(0.1)

    def command(self, *cmd):
        """发送命令到 OLED"""
        if self._gpio:
            self._gpio.output(self._DC, self._gpio.LOW)  # 命令模式
        self._spi.writebytes(list(cmd))

    def data(self, data):
        """发送数据到 OLED"""
        if self._gpio:
            self._gpio.output(self._DC, self._gpio.HIGH)  # 数据模式

        # 转换数据格式
        if isinstance(data, (list, tuple)):
            self._spi.writebytes(list(data))
        else:
            self._spi.writebytes(list(data))

    def cleanup(self):
        """清理资源"""
        self._spi.close()

