#!/usr/bin/env python3
"""
测试 luma.oled 驱动 SSD1306 屏幕
屏幕尺寸: 128x32
绘制一个矩形框: (0,0) 到 (127,31)
"""

from luma.core.interface.serial import spi
from luma.core.render import canvas
from luma.oled.device import ssd1306
from PIL import ImageFont
import time


class ssd1305(ssd1306):
    """
    SSD1305 驱动类，继承自 ssd1306
    重写 display 方法来处理列地址偏移
    封装 SPI 接口初始化，使用更简洁
    """
    def __init__(self, port=0, device=0, gpio_DC=24, gpio_RST=25, width=128, height=32, rotate=0, **kwargs):
        # 创建 SPI 接口
        serial_interface = spi(port=port, device=device, gpio_DC=gpio_DC, gpio_RST=gpio_RST)
        # 调用父类初始化
        super(ssd1305, self).__init__(serial_interface, width=width, height=height, rotate=rotate, **kwargs)
        # 128x32 pixel specific initialization.
        # 设置 COM Pins Hardware Configuration，解决垂直显示偏移
        self.command(0xDA)  # Set COM Pins Hardware Configuration
        self.command(0x12)  # 配置值：0x12 for 128x32

        
    def display(self, image):
        """
        Takes a 1-bit :py:mod:`PIL.Image` and dumps it to the OLED
        display.

        重写以支持列地址偏移（4像素偏移）

        :param image: Image to display.
        :type image: :py:mod:`PIL.Image`
        """
        assert image.mode == self.mode
        assert image.size == self.size

        image = self.preprocess(image)

        # self.command(
        #     # Column start/end address
        #     self._const.COLUMNADDR, self._colstart, self._colend - 1,
        #     # Page start/end address
        #     self._const.PAGEADDR, 0x00, self._pages - 1)
        
        # 准备图像数据
        buf = bytearray(self._w * self._pages)
        off = self._offsets
        mask = self._mask

        idx = 0
        for pix in image.getdata():
            if pix > 0:
                buf[off[idx]] |= mask[idx]
            idx += 1

        # 逐页写入数据，每页都设置列地址偏移
        # 对于 128x32 屏幕：self._pages = 4 (32÷8=4)
        # Page 0: 0-7行, Page 1: 8-15行, Page 2: 16-23行, Page 3: 24-31行
        set_page_address = 0xB0

        for page in range(self._pages):
            # 设置页地址 (0xB0 | page)
            self.command(set_page_address | page)
            # 设置列地址起始位置（带4像素偏移）
            # 对应 drive/SSD1305.py:121-125
            self.command(0x04)  # 列地址低4位（4像素偏移）
            self.command(0x10)  # 列地址高4位

            # 发送当前页的数据 (128字节)
            page_data = buf[page * self._w:(page + 1) * self._w]
            self.data(list(page_data))


def main():
    # 直接初始化 SSD1305 设备，内部自动创建 SPI 接口
    # 默认参数：port=0, device=0, gpio_DC=24, gpio_RST=25
    device = ssd1305(rotate=2)

    print("SSD1305 OLED 测试 (基于 luma.oled)")
    print(f"屏幕尺寸: {device.width}x{device.height}")

    # 绘制矩形框和文字
    with canvas(device) as draw:
        # 绘制从 (0,0) 到 (127,31) 的矩形框
        draw.rectangle([(0, 0), (127, 31)], outline="white", fill=None)

        # 在屏幕中间绘制 "Hello World"
        text = "Hello World"
        # 使用默认字体
        font = ImageFont.load_default()
        # 获取文本边界框来计算居中位置
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        # 计算居中位置
        x = (device.width - text_width) // 2
        y = (device.height - text_height) // 2
        # 绘制文字
        draw.text((x, y), text, font=font, fill="white")

    print("已绘制矩形框和 'Hello World' 文字")
    print("按 Ctrl+C 退出...")

    try:
        # 保持显示
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n退出程序")
        # 清空屏幕
        device.clear()


if __name__ == "__main__":
    main()
