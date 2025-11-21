#!/usr/bin/env python3
"""
分析 luma.oled 参数与硬件配置的关系
特别是与 COM Pins (0xDA, 0x12) 相关的参数
"""

from luma.core.interface.serial import spi
from luma.oled.device import ssd1306

# ============================================
# 与 COM Pins 配置直接相关的参数
# ============================================

"""
COM Pins Hardware Configuration (0xDA)
命令格式: 0xDA, config_byte

config_byte 的位含义:
- Bit 4 (0x10): Sequential (0) or Alternative (1) COM pin configuration
- Bit 5 (0x20): Disable (0) or Enable (1) COM Left/Right remap

常见配置值:
- 0x02: Sequential, no remap (128x32 常用)
- 0x12: Alternative, no remap (128x32/128x64 常用) ✅ 你在用的
- 0x22: Sequential, remap
- 0x32: Alternative, remap

对于 128x32 屏幕:
- 0x02 或 0x12 都可能工作
- 具体取决于硬件接线
"""

def analyze_com_pins_config():
    """分析 COM Pins 配置"""
    print("=" * 60)
    print("COM Pins 配置 (0xDA) 分析")
    print("=" * 60)
    print()

    configs = {
        0x02: "Sequential COM pins, no remap",
        0x12: "Alternative COM pins, no remap (你在用的)",
        0x22: "Sequential COM pins, with remap",
        0x32: "Alternative COM pins, with remap"
    }

    for value, desc in configs.items():
        print(f"0x{value:02X}: {desc}")
    print()


# ============================================
# luma.oled 可调参数分析
# ============================================

def analyze_luma_spi_params():
    """
    分析 luma SPI 参数
    这些参数影响通信，但不直接影响 COM Pins
    """
    print("=" * 60)
    print("luma SPI 参数（影响通信性能）")
    print("=" * 60)
    print()

    print("--spi-port          SPI 端口号 (0 或 1)")
    print("--spi-device        SPI 设备 (0 或 1)")
    print("--spi-bus-speed     SPI 总线速度 (Hz)")
    print("  默认: 8000000 (8 MHz)")
    print("  可调: 1000000 - 32000000")
    print("  影响: 刷新速度，太高可能不稳定")
    print()
    print("--spi-transfer-size SPI 最大传输单元 (bytes)")
    print("  默认: 4096")
    print("  影响: 每次传输的数据块大小")
    print()
    print("--spi-mode          SPI 模式 (0-3)")
    print("  默认: 0")
    print("  说明: 时钟极性和相位")
    print()


def analyze_luma_gpio_params():
    """
    分析 luma GPIO 参数
    这些参数影响引脚配置
    """
    print("=" * 60)
    print("luma GPIO 参数（影响引脚配置）")
    print("=" * 60)
    print()

    print("--gpio-data-command GPIO pin for D/C (默认: 24)")
    print("  你在用: GPIO 24 ✅")
    print()
    print("--gpio-reset        GPIO pin for RESET (默认: 25)")
    print("  你在用: GPIO 25 ✅")
    print()
    print("--gpio-reset-hold-time")
    print("  复位线保持活动的时间 (秒)")
    print("  默认: 0")
    print("  可能有用: 0.001 - 0.1 (如果启动不稳定)")
    print()
    print("--gpio-reset-release-time")
    print("  复位后等待时间 (秒)")
    print("  默认: 0")
    print("  可能有用: 0.001 - 0.1 (如果启动不稳定)")
    print()


def analyze_display_params():
    """
    分析显示相关参数
    这些参数可能影响显示效果
    """
    print("=" * 60)
    print("显示相关参数（可能影响显示效果）")
    print("=" * 60)
    print()

    print("rotate              屏幕旋转")
    print("  0: 不旋转")
    print("  1: 90° (顺时针)")
    print("  2: 180° ✅ 你在用的")
    print("  3: 270° (顺时针)")
    print()
    print("h-offset            水平偏移 (像素)")
    print("  对应你的列地址偏移 (0x04)")
    print("  但 SSD1306 可能不支持这个参数")
    print()
    print("v-offset            垂直偏移 (像素)")
    print("  可能影响显示位置")
    print()


# ============================================
# 可以在 ssd1305 类中调整的参数
# ============================================

def adjustable_in_ssd1305_class():
    """
    可以在你的 ssd1305 类中调整的参数
    """
    print("=" * 60)
    print("ssd1305 类中可调整的硬件参数")
    print("=" * 60)
    print()

    params = [
        {
            "name": "COM Pins Configuration (0xDA)",
            "current": "0x12",
            "alternatives": ["0x02", "0x22", "0x32"],
            "effect": "改变 COM 引脚映射方式",
            "test": "如果显示上下颠倒或错位"
        },
        {
            "name": "Display Offset (0xD3)",
            "current": "未设置（默认0x00）",
            "alternatives": ["0x00 - 0x3F (0-63)"],
            "effect": "垂直偏移显示内容",
            "test": "如果显示有垂直偏移"
        },
        {
            "name": "Contrast (0x81)",
            "current": "默认（父类设置）",
            "alternatives": ["0x00 - 0xFF (0-255)"],
            "effect": "调整显示亮度/对比度",
            "test": "如果显示太亮或太暗"
        },
        {
            "name": "Column Address Offset",
            "current": "0x04 (4 像素)",
            "alternatives": ["0x00 - 0x0F (0-15)"],
            "effect": "水平偏移显示内容",
            "test": "如果显示有水平偏移"
        },
        {
            "name": "Segment Remap (0xA0/0xA1)",
            "current": "默认",
            "alternatives": ["0xA0 (正常)", "0xA1 (左右翻转)"],
            "effect": "左右翻转显示",
            "test": "如果显示左右镜像"
        },
        {
            "name": "COM Output Scan (0xC0/0xC8)",
            "current": "默认",
            "alternatives": ["0xC0 (正常)", "0xC8 (上下翻转)"],
            "effect": "上下翻转显示",
            "test": "如果显示上下颠倒"
        },
        {
            "name": "Multiplex Ratio (0xA8)",
            "current": "默认 (31 for 32-line)",
            "alternatives": ["15-63"],
            "effect": "设置实际显示行数",
            "test": "如果显示不完整"
        },
        {
            "name": "Clock Divide Ratio (0xD5)",
            "current": "默认",
            "alternatives": ["0x00-0xFF"],
            "effect": "调整刷新率和振荡频率",
            "test": "如果显示闪烁或不稳定"
        }
    ]

    for i, param in enumerate(params, 1):
        print(f"{i}. {param['name']}")
        print(f"   当前值: {param['current']}")
        print(f"   可选值: {', '.join(param['alternatives'])}")
        print(f"   影响: {param['effect']}")
        print(f"   何时调整: {param['test']}")
        print()


# ============================================
# 示例：可配置的 ssd1305 类
# ============================================

def example_configurable_ssd1305():
    """展示可配置的 ssd1305 类"""
    print("=" * 60)
    print("可配置的 ssd1305 类示例")
    print("=" * 60)
    print()

    code = '''
class ssd1305(ssd1306):
    def __init__(self,
                 port=0, device=0,
                 gpio_DC=24, gpio_RST=25,
                 width=128, height=32, rotate=0,
                 # 新增可配置参数
                 col_offset=4,           # 列偏移
                 com_pins_config=0x12,   # COM Pins 配置
                 contrast=0xCF,          # 对比度
                 display_offset=0x00,    # 显示偏移
                 **kwargs):

        serial_interface = spi(port=port, device=device,
                              gpio_DC=gpio_DC, gpio_RST=gpio_RST)
        super().__init__(serial_interface, width=width,
                        height=height, rotate=rotate, **kwargs)

        # 应用自定义配置
        self.command(0xDA)  # COM Pins
        self.command(com_pins_config)

        self.command(0xD3)  # Display Offset
        self.command(display_offset)

        self.command(0x81)  # Contrast
        self.command(contrast)

        self._col_offset = col_offset

# 使用示例:
device = ssd1305(
    rotate=2,
    col_offset=4,
    com_pins_config=0x12,  # 如果显示不对，试试 0x02
    contrast=200,           # 调整亮度
    display_offset=0        # 如果有垂直偏移，调整这个
)
'''
    print(code)


# ============================================
# 调试建议
# ============================================

def debugging_tips():
    """调试建议"""
    print("=" * 60)
    print("调试建议")
    print("=" * 60)
    print()

    tips = [
        ("显示上下颠倒", "试试 COM Pins: 0x02 而不是 0x12"),
        ("显示左右翻转", "添加 self.command(0xA1) 启用 Segment Remap"),
        ("显示位置偏移（垂直）", "调整 Display Offset (0xD3)"),
        ("显示位置偏移（水平）", "调整 col_offset 参数"),
        ("显示太暗", "增加 contrast 值 (默认 ~0xCF)"),
        ("显示闪烁", "降低 SPI 总线速度"),
        ("启动不稳定", "增加 reset hold/release 时间"),
        ("显示不完整", "检查 Multiplex Ratio (0xA8) 设置")
    ]

    for issue, solution in tips:
        print(f"问题: {issue}")
        print(f"解决: {solution}")
        print()


def main():
    analyze_com_pins_config()
    analyze_luma_spi_params()
    analyze_luma_gpio_params()
    analyze_display_params()
    adjustable_in_ssd1305_class()
    example_configurable_ssd1305()
    debugging_tips()

    print("=" * 60)
    print("总结")
    print("=" * 60)
    print("""
与 COM Pins (0xDA, 0x12) 直接相关的参数:

1. ❌ luma SPI 参数 (--spi-*)
   - 只影响通信速度，不影响显示配置

2. ❌ luma GPIO 参数 (--gpio-*)
   - 只影响引脚映射，不影响显示配置

3. ✅ 在 ssd1305.__init__() 中设置
   - self.command(0xDA, 0x12)  # 这就是你在做的

4. ✅ 可添加的可配置参数:
   - com_pins_config: 控制 0xDA 的值
   - display_offset: 控制垂直偏移 (0xD3)
   - contrast: 控制亮度 (0x81)
   - col_offset: 控制水平偏移

建议: 如果显示正常，保持 0x12 不变。
      如果有问题，在 ssd1305 类中添加可配置参数来调试。
    """)


if __name__ == "__main__":
    main()
