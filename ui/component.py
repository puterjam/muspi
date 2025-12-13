import random
import time
from PIL import Image, ImageDraw

SCROLL_START_TIME = time.time()
SCROLL_SPEED = 0.2  # speed parameter, 1.0, means 1 unit per second
STOP_FRAMES = 32  # 停顿的帧数

# VU 动画相关
VU_FPS = 12  # VU 动画更新频率
VU_FRAME_INTERVAL = 1.0 / VU_FPS  # 每帧间隔时间
_last_vu_update_time = 0
_cached_vu_heights = [0, 0, 0]  # 缓存的柱状图高度

# 绘制左侧 VU 效果（32x32 区域）
def draw_vu(draw, volume_level = 0.5, offset_x=0, center_y=14):
    global _last_vu_update_time, _cached_vu_heights

    bar_width = 1
    spacing = 3
    num_bars = 3   # 增加到4个柱状图
    max_height = 12

    # 每个柱状图的高度系数，让它们有明显差异
    bar_coefficients = [0.5, 0.8, 0.65]

    current_time = time.time()

    # 检查是否需要更新 VU 高度（8fps 控制）
    if current_time - _last_vu_update_time >= VU_FRAME_INTERVAL:
        _last_vu_update_time = current_time

        # 更新缓存的柱状图高度
        for i in range(num_bars):
            # 根据当前音量级别和柱状图索引计算高度
            bar_height = int(max_height * min(0.8, volume_level) * bar_coefficients[i])

            # 添加非常小的随机变化使显示更平滑
            if bar_height > 0:
                bar_height = max(2, min(max_height,
                                  bar_height + random.randint(-3, 3)))

            _cached_vu_heights[i] = bar_height

    # 使用缓存的高度绘制柱状图
    for i in range(num_bars):
        bar_height = _cached_vu_heights[i]
        
        x = 4 + i * (bar_width + spacing) + offset_x
        
        # 绘制上半部分
        draw.rectangle((x, center_y - bar_height, 
                       x + bar_width, center_y), fill=255)
        
        # 绘制下半部分
        draw.rectangle((x, center_y, 
                       x + bar_width, center_y + bar_height), fill=255)

def _get_step_time():
    """get the current step time, adjust according to the speed parameter"""
    elapsed = time.time() - SCROLL_START_TIME
    return int(elapsed * SCROLL_SPEED * 1000 / 16)  # 16ms is a unit


# 右侧文字滚动
def draw_scroll_text(draw, text, position=(32, 0), width=None, font=None, align="left"):
    x, y = position
    text = f"{text} "
    bbox = font.getbbox(text)
    
    # 计算文字尺寸
    text_width = bbox[2]
    text_height = bbox[3]
    # print(f"text: {text}, text_width: {text_width}, visible_width: {visible_width}")
    
    if width is None:
        visible_width = text_width
    else:
        visible_width = width
    
    bitmap = Image.new('1', (visible_width, text_height))
    draw_bitmap = ImageDraw.Draw(bitmap)
    
    if text_width <= visible_width:
        # 文字不需要滚动，直接显示
        if align=="center":
            draw_bitmap.text(((visible_width - text_width) / 2, 0), text, font=font, fill=255)
        elif align=="right":
            draw_bitmap.text((visible_width - text_width, 0), text, font=font, fill=255)
        else:
            draw_bitmap.text((0, 0), text, font=font, fill=255)
    else:
        # 文字需要滚动
        # 计算最大滚动距离
        max_scroll = text_width - visible_width
        
        # 计算完整的来回滚动周期（包括停顿时间）
        full_cycle = max_scroll * 2 + STOP_FRAMES * 2  # 来回滚动的总距离加上停顿时间
        step = _get_step_time()
        current_pos = step % full_cycle
        
        # 确定滚动方向和位置
        if current_pos <= max_scroll:
            # 向左滚动
            scroll_x = current_pos
        elif current_pos <= max_scroll + STOP_FRAMES:
            # 在左端停顿
            scroll_x = max_scroll
        elif current_pos <= max_scroll * 2 + STOP_FRAMES:
            # 向右滚动
            scroll_x = max_scroll - (current_pos - max_scroll - STOP_FRAMES)
        else:
            # 在右端停顿
            scroll_x = 0
        
        # 绘制文字
        
        draw_bitmap.text((-scroll_x, 0), text, font=font, fill=255)

    # draw_bitmap.rectangle((0, 0, visible_width-1, text_height-1), outline=255)
    draw.bitmap((x, y), bitmap, fill=255)
