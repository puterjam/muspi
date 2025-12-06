import time
from screen.base import DisplayPlugin
from ui.component import draw_scroll_text


class clock(DisplayPlugin):
    def __init__(self, manager, width, height):
        self.name = "clock"
        super().__init__(manager, width, height)
        self.last_blink_time = 0
        self.show_colon = True

    def render(self):
        draw = self.canvas
        current_time = time.time()

        # handle the colon blinking
        if current_time - self.last_blink_time >= 0.5:
            self.show_colon = not self.show_colon
            self.last_blink_time = current_time

        # display time (large font)
        if self.show_colon:
            time_str = time.strftime("%H:%M:%S")
        else:
            time_str = time.strftime("%H %M %S")

        # 计算垂直居中位置
        # 日期高度 (font8) + 时间高度 (font16) + 间距
        date_height = 8  # font8 的高度
        time_height = 16  # font16 的高度
        spacing = 4  # 日期和时间之间的间距
        total_height = date_height + spacing + time_height

        # 垂直居中起始位置
        start_y = (self.height - total_height) // 2

        # display date (small font, top center)
        current_date = time.strftime("%Y年%m月%d日")
        draw_scroll_text(
            draw,
            "" + current_date,
            (0, start_y),
            width=self.width,
            font=self.font8,
            align="center",
        )

        # display time (large font, centered)
        draw_scroll_text(
            draw, time_str, (2, start_y + date_height + spacing), width=self.width, font=self.font16, align="center"
        )
