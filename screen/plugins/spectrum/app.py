"""
Matrix 数字雨插件

模拟《黑客帝国》中的绿色数字雨效果。
适配单色 OLED 屏幕（128x32），使用灰度级别模拟颜色渐变。
"""

from screen.base import DisplayPlugin
from random import randint, gauss

FPS = 25.0


class spectrum(DisplayPlugin):
    """Matrix 数字雨插件"""

    def __init__(self, manager, width, height):
        self.name = "spectrum"
        super().__init__(manager, width, height)

        self.framerate = FPS

        # 初始化 matrix 数据
        self._init_matrix()

    def _init_matrix(self):
        """
        初始化 Matrix 数据结构

        将 RGB 颜色转换为单色灰度值（0-255）
        用于在单色屏幕上模拟渐变效果
        """
        # 原版 RGB 颜色 → 转换为灰度值
        # 使用绿色通道的值作为灰度（因为原版是绿色主题）
        wrd_rgb = [
            (154, 173, 154),  # 灰绿色
            (0, 255, 0),      # 最亮绿
            (0, 235, 0),
            (0, 220, 0),
            (0, 185, 0),
            (0, 165, 0),
            (0, 128, 0),
            (0, 0, 0),        # 黑色
            (154, 173, 154),
            (0, 145, 0),
            (0, 125, 0),
            (0, 100, 0),
            (0, 80, 0),
            (0, 60, 0),
            (0, 40, 0),
            (0, 0, 0)         # 黑色
        ]

        # 转换为单色灰度值（取绿色通道值）
        self.gray_levels = [rgb[1] for rgb in wrd_rgb]

        self.clock = 0
        self.blue_pilled_population = []
        self.max_population = self.width * 8

    def increase_population(self):
        """
        增加一个新的雨滴

        参数：[x位置, y位置, 速度]
        """
        x = randint(0, self.width - 1)
        y = 0
        speed = gauss(1, 0.4)

        # 限制速度范围
        speed = max(0.3, min(speed, 3.0))

        self.blue_pilled_population.append([x, y, speed])

    def render(self):
        """
        渲染 Matrix 数字雨效果

        算法：
        1. 遍历所有雨滴
        2. 对每个雨滴，绘制渐变尾巴（使用灰度级别）
        3. 更新雨滴位置
        4. 定期生成新雨滴
        5. 清理超出屏幕的雨滴
        """
        draw = self.canvas
        self.clock += 1

        # 绘制所有雨滴
        for person in self.blue_pilled_population:
            x, y, speed = person

            # 绘制渐变尾巴
            for i, gray in enumerate(self.gray_levels):
                tail_y = int(y - i)  # 尾巴向上延伸

                # 只绘制屏幕范围内的点
                if 0 <= tail_y < self.height:
                    # 单色屏幕灰度模拟：使用概率抖动
                    if gray == 255:
                        # 最亮：100% 点亮
                        draw.point((x, tail_y), fill=255)
                    elif gray > 128:
                        # 较亮：75% 概率
                        if randint(0, 3) < 3:
                            draw.point((x, tail_y), fill=255)
                    elif gray > 64:
                        # 中等：50% 概率
                        if randint(0, 1) == 1:
                            draw.point((x, tail_y), fill=255)
                    elif gray > 32:
                        # 较暗：25% 概率
                        if randint(0, 3) == 0:
                            draw.point((x, tail_y), fill=255)
                    # gray == 0: 黑色，不绘制

            # 更新雨滴位置
            person[1] += speed

        # 定期增加新雨滴
        if self.clock % 5 == 0 or self.clock % 3 == 0:
            self.increase_population()

        # 移除超出屏幕的雨滴
        tail_length = len(self.gray_levels)
        self.blue_pilled_population = [
            person for person in self.blue_pilled_population
            if person[1] < self.height + tail_length
        ]

        # 限制最大雨滴数量
        while len(self.blue_pilled_population) > self.max_population:
            self.blue_pilled_population.pop(0)
      
