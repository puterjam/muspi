"""
覆盖层基类
所有覆盖层的基础实现
"""

import time
from PIL import Image, ImageDraw
from ui.animation import Animation, Operator
from ui.fonts import Fonts


class Overlay:
    """单个覆盖层基类"""

    def __init__(self, width, height, duration=3.0):
        """
        初始化覆盖层

        Args:
            width: 覆盖层宽度
            height: 覆盖层高度
            duration: 显示持续时间（秒）
        """
        self.width = width
        self.height = height
        self.duration = duration
        self.image = Image.new("1", (width, height), 0)
        self.draw = ImageDraw.Draw(self.image)
        self.fonts = Fonts()

        # 动画相关
        self.y_offset = -height  # 初始位置在屏幕上方
        self.anim = Animation(duration=0.3)
        self.anim.reset("slide", current=self.y_offset)

        # 状态管理
        self.create_time = time.time()
        self.is_showing = False
        self.is_hiding = False
        self.is_expired = False

    def show(self):
        """显示覆盖层（从上方滑入）"""
        self.is_showing = True
        self.is_hiding = False
        self.create_time = time.time()
        # 从上方滑入到顶部 (y=0)
        self.anim.reset("slide", current=self.y_offset)

    def hide(self):
        """隐藏覆盖层（向上方滑出）"""
        self.is_hiding = True
        self.is_showing = False
        # 向上方滑出
        self.anim.reset("slide", current=self.y_offset)

    def update(self):
        """更新覆盖层状态"""
        # 检查是否过期
        if not self.is_hiding and time.time() - self.create_time > self.duration:
            self.hide()

        # 更新动画
        if self.is_showing:
            self.y_offset = round(self.anim.run("slide", 0, duration=0.3, operator=Operator.ease_out_cubic))
            if not self.anim.is_running("slide"):
                self.is_showing = False

        elif self.is_hiding:
            self.y_offset = round(self.anim.run("slide", -self.height, duration=0.3, operator=Operator.ease_in_cubic))
            if not self.anim.is_running("slide"):
                self.is_hiding = False
                self.is_expired = True

    def render(self):
        """渲染覆盖层内容（子类需要重写此方法）"""
        pass

    def get_image(self):
        """获取当前覆盖层图像"""
        self.image = Image.new("1", (self.width, self.height), 0)
        self.draw = ImageDraw.Draw(self.image)
        self.render()
        return self.image

    def get_y_offset(self):
        """获取当前 Y 轴偏移量"""
        return self.y_offset
