#!/usr/bin/env python3
"""
演示如何整合 Pygame 和 luma.oled
Pygame 用于游戏逻辑，luma 用于显示
"""

import pygame
from PIL import Image
from drive.luma_ssd1305 import ssd1305
import time


class PygameLumaAdapter:
    """
    Pygame 和 Luma 的适配器
    将 Pygame Surface 转换为 PIL Image
    """
    def __init__(self, device, width=128, height=32):
        self.device = device
        self.width = width
        self.height = height

        # 初始化 Pygame（无窗口模式）
        pygame.init()
        pygame.display.set_mode((1, 1))  # 最小窗口

        # 创建虚拟表面
        self.surface = pygame.Surface((width, height))

    def surface_to_image(self, surface):
        """将 Pygame Surface 转换为 PIL Image"""
        # 获取像素数据
        raw_str = pygame.image.tostring(surface, 'RGB')

        # 创建 PIL Image
        pil_image = Image.frombytes('RGB', (self.width, self.height), raw_str)

        # 转换为单色模式
        pil_image = pil_image.convert('1')

        return pil_image

    def display(self, surface=None):
        """显示 Surface 到 OLED"""
        if surface is None:
            surface = self.surface

        image = self.surface_to_image(surface)
        self.device.display(image)


def example_1_basic_pygame(adapter):
    """示例1: Pygame 基本图形"""
    print("示例1: Pygame 绘图")

    # 清空表面
    adapter.surface.fill((0, 0, 0))

    # 使用 Pygame 绘制
    pygame.draw.rect(adapter.surface, (255, 255, 255), (10, 5, 40, 20), 1)  # 矩形
    pygame.draw.circle(adapter.surface, (255, 255, 255), (80, 15), 10, 1)   # 圆形
    pygame.draw.line(adapter.surface, (255, 255, 255), (10, 28), (118, 28), 1)  # 线

    # 显示到 OLED
    adapter.display()
    time.sleep(2)


def example_2_pygame_text(adapter):
    """示例2: Pygame 文字"""
    print("示例2: Pygame 文字")

    adapter.surface.fill((0, 0, 0))

    # 使用 Pygame 字体
    font = pygame.font.Font(None, 20)
    text = font.render("Pygame!", True, (255, 255, 255))

    # 居中显示
    text_rect = text.get_rect(center=(adapter.width//2, adapter.height//2))
    adapter.surface.blit(text, text_rect)

    adapter.display()
    time.sleep(2)


def example_3_bouncing_ball(adapter):
    """示例3: 弹跳小球动画"""
    print("示例3: 弹跳小球")

    # 小球参数
    ball_x, ball_y = 64, 16
    ball_dx, ball_dy = 2, 1
    ball_radius = 3

    for _ in range(100):
        # 清空
        adapter.surface.fill((0, 0, 0))

        # 绘制边框
        pygame.draw.rect(adapter.surface, (255, 255, 255),
                        (0, 0, adapter.width, adapter.height), 1)

        # 绘制小球
        pygame.draw.circle(adapter.surface, (255, 255, 255),
                          (int(ball_x), int(ball_y)), ball_radius)

        # 更新位置
        ball_x += ball_dx
        ball_y += ball_dy

        # 边界反弹
        if ball_x <= ball_radius or ball_x >= adapter.width - ball_radius:
            ball_dx = -ball_dx
        if ball_y <= ball_radius or ball_y >= adapter.height - ball_radius:
            ball_dy = -ball_dy

        # 显示
        adapter.display()
        time.sleep(0.03)


def example_4_game_scene(adapter):
    """示例4: 简单游戏场景"""
    print("示例4: 游戏场景")

    # 玩家参数
    player_x = 20
    player_y = 26
    player_width = 6
    player_height = 6

    # 障碍物
    obstacles = [
        {'x': 50, 'y': 26, 'w': 10, 'h': 6},
        {'x': 80, 'y': 26, 'w': 10, 'h': 6},
        {'x': 110, 'y': 26, 'w': 10, 'h': 6}
    ]

    # 移动玩家
    for i in range(100):
        adapter.surface.fill((0, 0, 0))

        # 绘制地面
        pygame.draw.line(adapter.surface, (255, 255, 255),
                        (0, 30), (adapter.width, 30), 1)

        # 绘制玩家（移动）
        player_x = (player_x + 1) % adapter.width
        pygame.draw.rect(adapter.surface, (255, 255, 255),
                        (player_x, player_y, player_width, player_height))

        # 绘制障碍物
        for obs in obstacles:
            pygame.draw.rect(adapter.surface, (255, 255, 255),
                           (obs['x'], obs['y'], obs['w'], obs['h']))

        # 绘制分数
        font = pygame.font.Font(None, 12)
        score_text = font.render(f"Score: {i}", True, (255, 255, 255))
        adapter.surface.blit(score_text, (2, 2))

        adapter.display()
        time.sleep(0.05)


def main():
    # 初始化设备
    device = ssd1305(rotate=2)

    # 创建适配器
    adapter = PygameLumaAdapter(device)

    print("Pygame + Luma 整合示例")
    print("=" * 40)

    try:
        example_1_basic_pygame(adapter)
        example_2_pygame_text(adapter)
        example_3_bouncing_ball(adapter)
        example_4_game_scene(adapter)

        print("\n所有示例完成！")

    except KeyboardInterrupt:
        print("\n用户中断")
    finally:
        device.clear()
        pygame.quit()


if __name__ == "__main__":
    main()
