"""
音量通知覆盖层
显示音量调节的视觉反馈
"""

from ui.overlays.base import Overlay


class VolumeOverlay(Overlay):
    """音量通知覆盖层"""

    def __init__(self, width, height, volume_percent, duration=3.0):
        """
        初始化音量通知

        Args:
            width: 覆盖层宽度
            height: 覆盖层高度
            volume_percent: 音量百分比 (0-100)
            duration: 显示持续时间（秒）
        """
        super().__init__(width, height, duration)
        self.volume_percent = max(0, min(100, volume_percent))

    def set_volume(self, volume_percent):
        """更新音量值并重置显示时间"""
        self.volume_percent = max(0, min(100, volume_percent))
        self.create_time = time.time()
        self.is_expired = False
        if self.is_hiding:
            self.show()

    def render(self):
        """渲染音量通知"""
        # 覆盖层高度约 20 像素
        overlay_height = 6 

        # 音量条整体尺寸:
        bar_total_width = 32
        bar_total_height = 7

        # 居中定位
        bar_x = (self.width - bar_total_width)
        bar_y = (overlay_height - bar_total_height) // 2

        # 注意：不绘制黑底，保持背景为黑色（0），用作透明 mask
        # 只绘制白色部分（框和填充条），这样黑色区域会透明

        # 1. 绘制音量框白框 (居中)
        frame_width = bar_total_width - 2
        frame_height = bar_total_height -2
        frame_x = bar_x + (bar_total_width - frame_width)
        frame_y = bar_y + (bar_total_height - frame_height) // 2

        self.draw.rectangle(
            [(frame_x, frame_y), (frame_x + frame_width - 1, frame_y + frame_height - 1)],
            outline=255,
            width=1,
            fill=0
        )

        # 3. 绘制音量条填充 (居中于音量框)
        fill_max_width = frame_width - 2
        fill_height = 1
        fill_x = frame_x + (frame_width - fill_max_width)
        fill_y = frame_y + (frame_height - fill_height) // 2

        # 根据音量百分比计算填充宽度
        fill_width = int(fill_max_width * self.volume_percent / 100)
        if fill_width > 0:
            self.draw.rectangle(
                [(fill_x, fill_y), (fill_x + fill_width - 3, fill_y + fill_height - 1)],
                fill=255
            )


# 需要导入 time 用于 set_volume 方法
import time
