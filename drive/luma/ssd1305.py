from luma.core.interface.serial import spi
from luma.oled.device import ssd1306

# 定义 SSD1305 引脚
PORT= 0
DEVICE= 0
GPIO_DC= 24
GPIO_RST= 25

class ssd1305(ssd1306):
    """
    SSD1305 驱动类，继承自 ssd1306
    重写 display 方法来处理列地址偏移
    """
    def __init__(self, width=128, height=32, rotate=0, **kwargs):
        # 创建 SPI 接口
        serial = spi(port=PORT, device=DEVICE, gpio_DC=GPIO_DC, gpio_RST=GPIO_RST)
        
        # 调用父类初始化
        super(ssd1305, self).__init__(serial, width=width, height=height, rotate=rotate, **kwargs)
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
