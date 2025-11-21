#!/usr/bin/env python3
"""
luma.oled canvas 使用示例
展示各种绘图操作
"""

from luma.core.render import canvas
from drive.luma_ssd1305 import ssd1305
from PIL import ImageFont
import time


def example_1_basic_shapes(device):
    """示例1: 基本图形"""
    print("示例1: 绘制基本图形")
    with canvas(device) as draw:
        # 矩形
        draw.rectangle((10, 5, 50, 15), outline="white", fill=None)
        # 实心矩形
        draw.rectangle((60, 5, 100, 15), outline="white", fill="white")
        # 线条
        draw.line((10, 20, 100, 20), fill="white", width=1)
        # 圆形
        draw.ellipse((10, 22, 30, 30), outline="white")
    time.sleep(2)


def example_2_text(device):
    """示例2: 文字显示"""
    print("示例2: 显示文字")
    with canvas(device) as draw:
        # 默认字体
        draw.text((10, 5), "Default Font", fill="white")

        # 不同位置的文字
        draw.text((10, 15), "Line 2", fill="white")
        draw.text((10, 25), "Line 3", fill="white")
    time.sleep(2)


def example_3_centered_text(device):
    """示例3: 居中文字"""
    print("示例3: 居中显示文字")
    with canvas(device) as draw:
        text = "Centered!"
        font = ImageFont.load_default()

        # 计算文字尺寸
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # 居中位置
        x = (device.width - text_width) // 2
        y = (device.height - text_height) // 2

        # 绘制边框和文字
        draw.rectangle((0, 0, device.width-1, device.height-1), outline="white")
        draw.text((x, y), text, font=font, fill="white")
    time.sleep(2)


def example_4_animation(device):
    """示例4: 简单动画"""
    print("示例4: 移动的方块")
    for i in range(0, 100, 5):
        with canvas(device) as draw:
            # 移动的方块
            draw.rectangle((i, 10, i+20, 22), outline="white", fill="white")
            draw.text((50, 0), f"X: {i}", fill="white")
        time.sleep(0.05)


def example_5_progress_bar(device):
    """示例5: 进度条"""
    print("示例5: 进度条")
    for progress in range(0, 101, 5):
        with canvas(device) as draw:
            # 进度条背景
            draw.rectangle((10, 10, 118, 22), outline="white")

            # 进度条填充
            if progress > 0:
                bar_width = int((108 * progress) / 100)
                draw.rectangle((11, 11, 11+bar_width, 21), fill="white")

            # 百分比文字
            text = f"{progress}%"
            bbox = draw.textbbox((0, 0), text)
            text_width = bbox[2] - bbox[0]
            x = (device.width - text_width) // 2
            draw.text((x, 24), text, fill="white")
        time.sleep(0.1)


def example_6_dashboard(device):
    """示例6: 仪表盘样式"""
    print("示例6: 仪表盘")
    with canvas(device) as draw:
        # 标题
        draw.text((30, 0), "Dashboard", fill="white")
        draw.line((0, 9, 127, 9), fill="white")

        # CPU
        draw.text((5, 12), "CPU:", fill="white")
        draw.rectangle((35, 12, 120, 19), outline="white")
        draw.rectangle((36, 13, 90, 18), fill="white")  # 75%

        # RAM
        draw.text((5, 22), "RAM:", fill="white")
        draw.rectangle((35, 22, 120, 29), outline="white")
        draw.rectangle((36, 23, 65, 28), fill="white")  # 50%
    time.sleep(3)


def main():
    # 初始化设备
    device = ssd1305(rotate=2)

    print("Canvas 使用示例")
    print("=" * 40)

    try:
        # 运行所有示例
        example_1_basic_shapes(device)
        example_2_text(device)
        example_3_centered_text(device)
        example_4_animation(device)
        example_5_progress_bar(device)
        example_6_dashboard(device)

        print("\n所有示例完成！")

    except KeyboardInterrupt:
        print("\n用户中断")
    finally:
        device.clear()


if __name__ == "__main__":
    main()
