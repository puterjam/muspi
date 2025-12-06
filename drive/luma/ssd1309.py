from luma.core.interface.serial import spi
from luma.oled.device import ssd1309 as _ssd1309
import RPi.GPIO as GPIO

# 定义 SSD1309 引脚 waveshare 128x64
PORT = 0
DEVICE = 0
GPIO_DC = 25
GPIO_RST = 27
IPS_SPEED_HZ = 8000000


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
    serial = spi(
        port=PORT,
        device=DEVICE,
        gpio_DC=GPIO_DC,
        gpio_RST=GPIO_RST,
        gpio=GPIO,
        bus_speed_hz=IPS_SPEED_HZ
    )

    # 创建并返回设备实例
    return _ssd1309(serial, width=width, height=height, rotate=rotate, **kwargs)
