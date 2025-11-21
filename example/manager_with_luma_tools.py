"""
演示如何在 manager.py 中使用 luma 生态工具
"""

from PIL import Image, ImageDraw
from luma.core.sprite_system import framerate_regulator


class DisplayManagerWithLumaTools:
    """
    展示如何在 DisplayManager 中使用 luma 生态工具
    """

    def __init__(self, device):
        self.disp = device
        self.main_screen = Image.new("1", (self.disp.width, self.disp.height), 0)

        # 使用 luma 的帧率调节器
        self.regulator = framerate_regulator(fps=60)

    def run_with_regulator(self):
        """使用 luma 的帧率调节器"""

        x = 0
        while x < 100:
            # 使用帧率调节器
            with self.regulator:
                # 清空
                self.main_screen = Image.new("1", (self.disp.width, self.disp.height), 0)
                draw = ImageDraw.Draw(self.main_screen)

                # 绘制移动的方块
                draw.rectangle((x, 10, x+10, 20), outline=255, fill=255)

                # 显示
                self.disp.display(self.main_screen)

                x += 1


# 方案1: 保持当前的 PIL Image 方式（推荐）
def current_approach():
    """
    当前 manager.py 的方式（最灵活）
    - 使用 PIL Image 作为缓冲区
    - 手动控制所有渲染细节
    - 最佳性能
    """
    image = Image.new("1", (128, 32), 0)
    draw = ImageDraw.Draw(image)

    # 完全控制
    draw.rectangle((0, 0, 127, 31), outline=255)
    # device.display(image)


# 方案2: 使用 luma 工具辅助（可选）
def luma_tools_approach():
    """
    使用 luma 生态工具辅助
    - framerate_regulator: 帧率控制
    - viewport: 虚拟视口（大画布滚动）
    """
    from luma.core.sprite_system import framerate_regulator

    regulator = framerate_regulator(fps=30)

    with regulator:
        # 你的渲染代码
        pass


# 方案3: Pygame 整合（游戏插件用）
def pygame_approach():
    """
    Pygame 整合方式（适合游戏插件）
    - 使用 Pygame 处理游戏逻辑
    - 转换为 PIL Image 显示
    """
    import pygame

    surface = pygame.Surface((128, 32))
    # Pygame 绘制...

    # 转换为 PIL Image
    raw = pygame.image.tostring(surface, 'RGB')
    image = Image.frombytes('RGB', (128, 32), raw).convert('1')
    # device.display(image)


"""
推荐方案：

1. manager.py 主循环：保持当前的 PIL Image 方式
   - 性能最好
   - 完全可控
   - 简单直接

2. 特定插件可以使用：
   - Pygame：游戏类插件
   - luma.core.virtual.viewport：大画布滚动
   - luma.core.sprite_system：精灵系统

3. 静态页面可以使用：
   - canvas：简化代码
"""
