"""
Hello World 插件示例

这是一个简单的插件示例，展示了如何创建一个 Muspi 显示插件。
它在屏幕中央显示 "Hello World" 文本。

插件接口说明：
    所有插件都必须继承 DisplayPlugin 基类，并实现必需的接口方法。
"""

from screen.base import DisplayPlugin
from ui.component import draw_scroll_text


class hello(DisplayPlugin):
    """
    Hello World 插件类

    这个插件在屏幕中央显示 "Hello World" 文本，
    是学习插件开发的最简单示例。

    继承自 DisplayPlugin，需要实现的核心方法：
        - __init__: 初始化插件
        - update: 更新显示内容（必需）
        - event_listener: 监听外部事件（可选）
    """

    def __init__(self, manager, width, height):
        """
        初始化插件

        参数:
            manager (DisplayManager): 显示管理器实例，用于控制屏幕和插件切换
            width (int): 屏幕宽度（像素），通常为 128
            height (int): 屏幕高度（像素），通常为 32

        说明:
            在初始化中需要：
            1. 设置插件名称 (self.name)
            2. 调用父类初始化 (super().__init__)
            3. 初始化插件特定的状态变量

        注意:
            - 避免在 __init__ 中执行耗时操作（如网络请求）
            - 重操作应该放到后台线程或延迟到实际使用时
        """
        # 设置插件名称（必需，用于日志和插件识别）
        self.name = "hello"

        # 调用父类初始化（必需）
        # 这会初始化：
        #   - self.image: PIL Image 对象，插件的画布
        #   - draw: PIL ImageDraw 对象，用于绘制
        #   - self.font8, self.font10, self.font12, self.font16: 预设字体
        #   - self.is_active: 插件是否激活状态
        super().__init__(manager, width, height)

        # 插件特定的状态变量（可选）
        self.message = "Hello World"
        self.counter = 0  # 示例：更新计数器
        
        self.framerate = 20.0 # 帧率

    def render(self):
        """
        更新显示内容（必需实现）

        这个方法会被 DisplayManager 定期调用（默认每秒 8 次）。
        在这里实现插件的渲染逻辑。

        典型流程：
            1. 清空画布 (self.clear())
            2. 绘制新内容 (使用 draw 或辅助函数)
            3. 返回（DisplayManager 会自动将 self.image 显示到屏幕）

        绘图工具：
            - draw: PIL ImageDraw 对象
                - draw.text(): 绘制文本
                - draw.rectangle(): 绘制矩形
                - draw.line(): 绘制线条
                - draw.ellipse(): 绘制圆形/椭圆

            - 辅助函数（from ui.component import ...）:
                - draw_scroll_text(): 绘制可滚动文本
                - draw_text_with_shadow(): 绘制带阴影的文本

        注意:
            - 坐标原点 (0, 0) 在左上角
            - 填充值: 0 = 黑色（关闭像素），255 = 白色（点亮像素）
            - 对于 OLED 屏幕，白色像素会发光
        """
        draw = self.canvas

        # 1. 绘制主要内容
        # 使用 draw_scroll_text 在屏幕中央显示文本
        # 参数说明:
        #   - draw: 绘图对象
        #   - self.message: 要显示的文本
        #   - (0, 12): 文本位置 (x, y)，y=12 使文本垂直居中
        #   - width=128: 文本区域宽度
        #   - font=self.font12: 使用 12 号字体
        #   - align="center": 水平居中对齐
        draw_scroll_text(
            draw,
            self.message,
            (0, 12),           # 位置: (x, y) - y=12 使 12px 字体在 32px 高度中垂直居中
            width=self.width,  # 使用全屏宽度
            font=self.font12,  # 12 号字体（推荐用于主要文本）
            align="center"     # 水平居中
        )

        # 2. 可选：在顶部显示额外信息（示例）
        # 显示更新次数
        self.counter += 1
        info_text = f"Updates: {self.counter}"

        draw_scroll_text(
            draw,
            info_text,
            (0, 3),            # 顶部位置
            width=self.width,
            font=self.font8,   # 小字体用于次要信息
            align="center"
        )

        # 3. 可选：绘制装饰边框
        # 在屏幕周围画一个矩形框
        draw.rectangle(
            (0, 0, self.width - 1, self.height - 1),  # (left, top, right, bottom)
            outline=255,  # 白色边框
            fill=None     # 不填充内部
        )

        # 注意：不需要返回任何值
        # DisplayManager 会自动获取 self.image 并显示到屏幕

    def event_listener(self):
        """
        监听外部事件（可选实现）

        用于监听外部事件，如：
            - 按键输入
            - 网络消息
            - 系统通知
            - 传感器数据

        示例用途：
            - 播放器插件：监听音乐播放状态
            - 通知插件：监听系统通知
            - 游戏插件：监听按键输入

        注意:
            - 这个方法通常在单独的线程中运行
            - 需要处理线程安全问题
            - 避免阻塞操作，使用队列或回调机制
        """
        # Hello World 插件不需要监听事件
        # 实际插件可以在这里实现事件监听逻辑
        pass

    def is_playing(self):
        """
        检查插件是否正在播放（可选实现）

        返回:
            bool: True 表示插件正在活动/播放，False 表示空闲

        用途:
            用于 auto_hide 功能。当插件标记为 auto_hide=True 时：
            - is_playing() 返回 True: 插件保持显示
            - is_playing() 返回 False: 插件自动隐藏，切换到其他插件

        典型场景：
            - 音乐播放器：当音乐播放时返回 True，暂停/停止时返回 False
            - 通知插件：有新通知时返回 True，无通知时返回 False
            - 游戏插件：游戏进行中返回 True，游戏结束返回 False
        """
        # Hello World 插件不使用 auto_hide 功能
        # 返回 None 或不实现此方法
        return None
