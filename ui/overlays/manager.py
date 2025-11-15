"""
覆盖层管理器
管理和渲染所有活跃的覆盖层
"""

from ui.overlays.volume import VolumeOverlay


class OverlayManager:
    """覆盖层管理器"""

    def __init__(self, width, height):
        """
        初始化覆盖层管理器

        Args:
            width: 屏幕宽度
            height: 屏幕高度
        """
        self.width = width
        self.height = height
        self.overlays = []  # 当前活跃的覆盖层列表
        
    def add_overlay(self, overlay):
        """
        添加覆盖层

        Args:
            overlay: Overlay 实例
        """
        # 如果是音量通知，检查是否已存在
        if isinstance(overlay, VolumeOverlay):
            for existing in self.overlays:
                if isinstance(existing, VolumeOverlay):
                    # 更新现有音量通知
                    existing.set_volume(overlay.volume_percent)
                    return

        overlay.show()
        self.overlays.append(overlay)

    def update(self):
        """更新所有覆盖层"""
        for overlay in self.overlays:
            overlay.update()

        # 移除已过期的覆盖层
        self.overlays = [o for o in self.overlays if not o.is_expired]

    def render(self, base_image):
        """
        渲染所有覆盖层到基础图像上

        Args:
            base_image: PIL Image 对象，主屏幕图像

        Returns:
            PIL Image: 合成后的图像
        """
        if not self.overlays:
            return base_image

        # 创建副本避免修改原图像
        result = base_image.copy()

        for overlay in self.overlays:
            overlay_image = overlay.get_image()
            y_offset = overlay.get_y_offset()

            # 只渲染可见区域
            if y_offset < self.height and y_offset + overlay.height > 0:
                # 计算粘贴位置 - 居右显示
                paste_x = self.width - overlay.width
                paste_y = max(0, y_offset)

                # 计算源图像的裁剪区域
                crop_top = max(0, -y_offset)
                crop_bottom = min(overlay.height, self.height - y_offset)

                if crop_top < crop_bottom:
                    cropped = overlay_image.crop((0, crop_top, overlay.width, crop_bottom))
                    # 使用图像本身作为 mask：白色像素=不透明，黑色像素=透明
                    # 在单色模式下，白色（1）会覆盖，黑色（0）保持原样
                    result.paste(cropped, (paste_x, paste_y))

        return result

    def has_active_overlays(self):
        """检查是否有活跃的覆盖层"""
        return len(self.overlays) > 0


    # 音量通知 overlay
    def show_volume(self, volume_percent):
        """
        显示音量通知

        Args:
            volume_percent: 音量百分比 (0-100)
        """
        self.add_overlay(VolumeOverlay(24, 7, volume_percent))