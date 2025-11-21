# Muspi 插件开发规范

本文档描述如何为 Muspi 系统开发自定义显示插件。

## 目录

- [插件架构](#插件架构)
- [基础插件开发](#基础插件开发)
- [插件生命周期](#插件生命周期)
- [API 参考](#api-参考)
- [最佳实践](#最佳实践)
- [示例插件](#示例插件)

---

## 插件架构

### 系统概述

Muspi 使用插件系统来管理不同的显示内容。每个插件负责：
- 在 OLED 屏幕上渲染特定的内容
- 处理用户输入（按键事件）
- 管理自身的激活/停用状态
- 控制帧率和更新频率

### 插件加载机制

1. 插件文件位于 `screen/plugins/` 目录
2. 插件配置在 `config/plugins.json` 中管理
3. 系统通过动态导入加载启用的插件
4. 插件类名必须与文件名一致（小写）

---

## 基础插件开发

### 1. 创建插件文件

在 `screen/plugins/` 目录下创建新的 Python 文件，例如 `myplugin.py`。

### 2. 导入基类

```python
from screen.base import DisplayPlugin
```

### 3. 定义插件类

插件类名必须与文件名一致（小写）：

```python
class myplugin(DisplayPlugin):
    def __init__(self, manager, width, height):
        # 设置插件名称（必须在调用 super().__init__ 之前）
        self.name = "myplugin"

        # 调用父类构造函数
        super().__init__(manager, width, height)

        # 初始化插件特定的属性
        self.counter = 0

    def update(self):
        """更新显示内容（必须实现）"""
        # 清空画布
        self.clear()

        # 绘制内容
        self.draw.text((10, 10), f"Counter: {self.counter}", fill=1, font=self.font12)
        self.counter += 1
```

### 4. 配置插件

在 `config/plugins.json` 中添加插件配置：

```json
{
    "plugins": [
        {
            "name": "myplugin",
            "enabled": true,
            "auto_hide": false,
            "config": {}
        }
    ]
}
```

**配置参数说明：**
- `name`: 插件名称（必须与类名和文件名一致）
- `enabled`: 是否启用插件
- `auto_hide`: 是否在没有活动时自动隐藏
- `config`: 插件特定的配置参数（可选）

---

## 插件生命周期

### 生命周期方法

```python
class myplugin(DisplayPlugin):
    def __init__(self, manager, width, height):
        """插件初始化"""
        self.name = "myplugin"
        super().__init__(manager, width, height)

    def update(self):
        """每帧调用，用于更新显示内容（必须实现）"""
        pass

    def event_listener(self):
        """每帧调用，用于监听和处理事件（可选）"""
        pass

    def set_active(self, active):
        """激活/停用插件时调用"""
        super().set_active(active)

        if active:
            # 插件被激活时的处理
            self.manager.key_listener.on(self.key_callback)
        else:
            # 插件被停用时的处理
            self.manager.key_listener.off(self.key_callback)

    def key_callback(self, device_name, evt):
        """按键事件回调（如果需要处理输入）"""
        pass

    def is_playing(self):
        """返回插件是否正在播放（可选）"""
        return False

    def get_frame_time(self):
        """返回帧时间（秒），控制更新频率"""
        return 1.0 / 8.0  # 默认 8 FPS
```

---

## API 参考

### 父类属性

插件继承 `DisplayPlugin` 后可使用以下属性：

#### 管理器和尺寸
- `self.manager`: 显示管理器实例
- `self.width`: 显示宽度（通常为 128）
- `self.height`: 显示高度（通常为 32）

#### 绘图对象
- `self.image`: PIL Image 对象
- `self.draw`: PIL ImageDraw 对象，用于绘制图形

#### 字体
- `self.font_status`: 5px 字体（状态栏）
- `self.font8`: 8px 字体
- `self.font10`: 10px 字体
- `self.font12`: 12px 字体
- `self.font16`: 16px 字体

#### 状态
- `self.name`: 插件名称
- `self.is_active`: 插件是否处于激活状态

### 管理器方法

通过 `self.manager` 访问：

```python
# 屏幕管理
self.manager.turn_on_screen()      # 唤醒屏幕
self.manager.reset_sleep_timer()   # 重置睡眠定时器

# 输入监听
self.manager.key_listener.on(callback)   # 注册按键回调
# 移除按键回调
self.manager.key_listener.off(callback)

# 状态查询
self.manager.sleep                 # 屏幕是否休眠
self.manager.active_id             # 当前激活插件的 ID
self.manager.last_active           # 上一个激活的插件
```

### 绘图方法

```python
# 基础绘图（使用 PIL ImageDraw）
self.draw.rectangle((x1, y1, x2, y2), fill=1)  # 矩形
self.draw.ellipse((x1, y1, x2, y2), fill=1)    # 椭圆
self.draw.line((x1, y1, x2, y2), fill=1)       # 线条
self.draw.text((x, y), "Text", fill=1, font=self.font12)  # 文本

# 清空画布
self.clear()

# 使用 UI 组件
from ui.component import draw_scroll_text, draw_vu

# 滚动文本
draw_scroll_text(
    self.draw,
    "长文本内容",
    (x, y),
    width=100,
    font=self.font10,
    align="center"
)

# 音量条
draw_vu(self.draw, volume_level=0.8)
```

### 按键处理

```python
from until.keymap import get_keymap

class myplugin(DisplayPlugin):
    def __init__(self, manager, width, height):
        self.name = "myplugin"
        super().__init__(manager, width, height)
        self.keymap = get_keymap()

    def set_active(self, active):
        super().set_active(active)
        if active:
            self.manager.key_listener.on(self.key_callback)
        else:
            self.manager.key_listener.off(self.key_callback)

    def key_callback(self, device_name, evt):
        # 获取标准按键
        key_select = self.keymap.get_action_select()  # 确认/选择键
        key_cancel = self.keymap.get_action_cancel()  # 取消/返回键

        # evt.value: 0=释放, 1=按下, 2=长按
        if evt.value == 1:  # 按下
            if self.keymap.is_key_match(evt.code, key_select):
                # 处理选择键
                pass

            if self.keymap.is_key_match(evt.code, key_cancel):
                # 处理取消键
                pass

        if evt.value == 2:  # 长按
            if self.keymap.is_key_match(evt.code, key_select):
                # 处理长按选择键
                pass
```

---

## 最佳实践

### 1. 性能优化

**控制帧率：**
```python
def get_frame_time(self):
    # 静态内容使用低帧率
    return 1.0 / 2.0  # 2 FPS

    # 游戏或动画使用高帧率
    return 1.0 / 30.0  # 30 FPS
```

**避免重复计算：**
```python
def __init__(self, manager, width, height):
    self.name = "myplugin"
    super().__init__(manager, width, height)

    # 预计算固定值
    self.center_x = self.width // 2
    self.center_y = self.height // 2
```

### 2. 激活管理

**自动激活插件：**
```python
def event_listener(self):
    # 检测到特定事件时激活
    if self.should_activate():
        self.set_active(True)
```

**自动停用插件：**
```python
def event_listener(self):
    # 超时或条件不满足时停用
    if not self.is_still_relevant():
        self.set_active(False)
```

### 3. 资源清理

**及时释放资源：**
```python
def set_active(self, active):
    super().set_active(active)

    if active:
        # 获取资源
        self.resource = self.acquire_resource()
    else:
        # 释放资源
        if hasattr(self, 'resource'):
            self.resource.close()
            del self.resource
```

### 4. 错误处理

**捕获异常：**
```python
def update(self):
    try:
        self.clear()
        # 绘制逻辑
        self.draw_content()
    except Exception as e:
        LOGGER.error(f"[{self.name}] Update error: {e}")
        # 显示错误信息
        self.draw.text((10, 10), "Error!", fill=1, font=self.font10)
```

### 5. 日志记录

```python
from until.log import LOGGER

class myplugin(DisplayPlugin):
    def __init__(self, manager, width, height):
        self.name = "myplugin"
        super().__init__(manager, width, height)
        LOGGER.info(f"[{self.name}] Custom initialization complete")

    def some_method(self):
        LOGGER.debug(f"[{self.name}] Debug message")
        LOGGER.info(f"[{self.name}] Info message")
        LOGGER.warning(f"[{self.name}] Warning message")
        LOGGER.error(f"[{self.name}] Error message")
```

---

## 示例插件

### 示例 1: 简单时钟插件

```python
import time
from screen.base import DisplayPlugin
from ui.component import draw_scroll_text

class clock(DisplayPlugin):
    def __init__(self, manager, width, height):
        self.name = "clock"
        super().__init__(manager, width, height)
        self.last_blink_time = 0
        self.show_colon = True

    def update(self):
        self.clear()
        current_time = time.time()

        # 处理冒号闪烁
        if current_time - self.last_blink_time >= 0.5:
            self.show_colon = not self.show_colon
            self.last_blink_time = current_time

        # 显示时间
        if self.show_colon:
            time_str = time.strftime("%H:%M:%S")
        else:
            time_str = time.strftime("%H %M %S")

        draw_scroll_text(
            self.draw, time_str, (2, 12),
            width=128, font=self.font16, align="center"
        )

        # 显示日期
        current_date = time.strftime("%Y年%m月%d日")
        draw_scroll_text(
            self.draw, current_date, (0, 2),
            width=128, font=self.font8, align="center"
        )
```

### 示例 2: 交互式游戏插件

```python
import random
from screen.base import DisplayPlugin
from until.keymap import get_keymap

class life(DisplayPlugin):
    def __init__(self, manager, width, height):
        self.name = "life"
        super().__init__(manager, width, height)
        self.cell_size = 2
        self.grid_width = self.width // self.cell_size
        self.grid_height = self.height // self.cell_size
        self.grid = [[0 for _ in range(self.grid_width)]
                     for _ in range(self.grid_height)]
        self.keymap = get_keymap()
        self.initialize_grid()

    def initialize_grid(self):
        """随机初始化网格"""
        for y in range(self.grid_height):
            for x in range(self.grid_width):
                self.grid[y][x] = random.randint(0, 1)

    def count_neighbors(self, x, y):
        """计算邻居数量"""
        count = 0
        for dy in [-1, 0, 1]:
            for dx in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue
                nx = (x + dx) % self.grid_width
                ny = (y + dy) % self.grid_height
                count += self.grid[ny][nx]
        return count

    def update(self):
        """更新游戏状态并渲染"""
        self.clear()

        # 计算下一代
        new_grid = [[0 for _ in range(self.grid_width)]
                    for _ in range(self.grid_height)]
        for y in range(self.grid_height):
            for x in range(self.grid_width):
                neighbors = self.count_neighbors(x, y)
                if self.grid[y][x] == 1:
                    # 存活细胞：2-3个邻居存活
                    new_grid[y][x] = 1 if 2 <= neighbors <= 3 else 0
                else:
                    # 死亡细胞：3个邻居复活
                    new_grid[y][x] = 1 if neighbors == 3 else 0
        self.grid = new_grid

        # 渲染当前状态
        for y in range(self.grid_height):
            for x in range(self.grid_width):
                if self.grid[y][x] == 1:
                    self.draw.rectangle([
                        x * self.cell_size,
                        y * self.cell_size,
                        (x + 1) * self.cell_size - 1,
                        (y + 1) * self.cell_size - 1
                    ], fill=1)

    def get_frame_time(self):
        """游戏帧率"""
        return 1.0 / 30.0  # 30 FPS

    def set_active(self, active):
        """激活/停用处理"""
        super().set_active(active)
        if active:
            self.initialize_grid()
            self.manager.key_listener.on(self.key_callback)
        else:
            self.manager.key_listener.off(self.key_callback)

    def key_callback(self, device_name, evt):
        """按键处理"""
        key_select = self.keymap.get_action_select()
        key_cancel = self.keymap.get_action_cancel()

        if evt.value == 1:  # 按下
            if (self.keymap.is_key_match(evt.code, key_select) or
                self.keymap.is_key_match(evt.code, key_cancel)):
                self.initialize_grid()  # 重新初始化
```

### 示例 3: 音乐播放器插件框架

```python
import threading
import time
from screen.base import DisplayPlugin
from ui.component import draw_scroll_text, draw_vu
from until.keymap import get_keymap
from until.log import LOGGER

class musicplayer(DisplayPlugin):
    def __init__(self, manager, width, height):
        self.name = "musicplayer"
        super().__init__(manager, width, height)

        # 播放状态
        self.is_running = False
        self.play_state = "stopped"  # stopped, playing, paused

        # 元数据
        self.current_artist = "Unknown Artist"
        self.current_title = "Unknown Title"
        self.current_album = "Unknown Album"

        # 按键映射
        self.keymap = get_keymap()

        # 监控线程
        self.monitor_thread = None
        self.stop_monitor = False

    def update(self):
        """更新显示"""
        self.clear()

        if self.is_running:
            # 显示歌曲信息
            draw_scroll_text(
                self.draw, self.current_title,
                (0, 10), width=128, font=self.font10, align="center"
            )
            draw_scroll_text(
                self.draw, f"{self.current_artist} - {self.current_album}",
                (0, 24), width=128, font=self.font8, align="center"
            )

            # 显示播放状态
            if self.play_state == "playing":
                draw_vu(self.draw, volume_level=0.8)
                self.draw.text((0, 0), "⏵", fill=1, font=self.font_status)
            elif self.play_state == "paused":
                draw_vu(self.draw, volume_level=0.0)
                self.draw.text((0, 0), "⏸", fill=1, font=self.font_status)
        else:
            # 显示待机信息
            draw_scroll_text(
                self.draw, "Music Player Ready",
                (0, 12), width=128, font=self.font10, align="center"
            )

    def event_listener(self):
        """事件监听"""
        # 检测播放状态并自动激活
        if self.is_running and not self.is_active:
            self.set_active(True)

        # 播放停止后自动停用
        if not self.is_running and self.is_active:
            self.set_active(False)

    def set_active(self, active):
        """激活/停用"""
        super().set_active(active)

        if active:
            self.manager.key_listener.on(self.key_callback)
            self.start_monitor()
        else:
            self.manager.key_listener.off(self.key_callback)
            self.stop_monitor_thread()

    def key_callback(self, device_name, evt):
        """按键处理"""
        key_select = self.keymap.get_action_select()
        key_cancel = self.keymap.get_action_cancel()

        if evt.value == 1:  # 按下
            if self.keymap.is_key_match(evt.code, key_select):
                self.toggle_play_pause()

            if self.keymap.is_key_match(evt.code, key_cancel):
                self.next_track()

        if evt.value == 2:  # 长按
            if self.keymap.is_key_match(evt.code, key_select):
                self.stop()

    def toggle_play_pause(self):
        """播放/暂停切换"""
        if self.play_state == "playing":
            self.pause()
        else:
            self.play()

    def play(self):
        """开始播放"""
        LOGGER.info(f"[{self.name}] Playing")
        self.is_running = True
        self.play_state = "playing"
        # TODO: 实现实际的播放逻辑

    def pause(self):
        """暂停"""
        LOGGER.info(f"[{self.name}] Paused")
        self.play_state = "paused"
        # TODO: 实现实际的暂停逻辑

    def stop(self):
        """停止"""
        LOGGER.info(f"[{self.name}] Stopped")
        self.is_running = False
        self.play_state = "stopped"
        # TODO: 实现实际的停止逻辑

    def next_track(self):
        """下一曲"""
        LOGGER.info(f"[{self.name}] Next track")
        # TODO: 实现实际的切换逻辑

    def start_monitor(self):
        """启动监控线程"""
        if self.monitor_thread is None:
            self.stop_monitor = False
            self.monitor_thread = threading.Thread(
                target=self._monitor_loop,
                daemon=True
            )
            self.monitor_thread.start()

    def stop_monitor_thread(self):
        """停止监控线程"""
        self.stop_monitor = True
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1)
            self.monitor_thread = None

    def _monitor_loop(self):
        """监控循环"""
        while not self.stop_monitor:
            # TODO: 更新播放状态和元数据
            time.sleep(1)
```

---

## 插件调试

### 查看日志

```bash
# 运行程序并查看日志
./venv/bin/python main.py

# 或者如果安装了服务
sudo journalctl -u muspi.service -f
```

### 常见问题

**1. 插件未加载**
- 检查文件名、类名是否一致（小写）
- 检查 `config/plugins.json` 中是否启用
- 查看日志中的错误信息

**2. 显示不正常**
- 确保调用了 `self.clear()` 清空画布
- 检查坐标是否在显示范围内（0-128, 0-32）
- 确认 `fill=1` 用于白色，`fill=0` 用于黑色

**3. 按键不响应**
- 确保在 `set_active(True)` 时注册了回调
- 确保在 `set_active(False)` 时移除了回调
- 检查按键映射配置

**4. 性能问题**
- 降低帧率 `get_frame_time()`
- 避免在 `update()` 中进行重复计算
- 使用缓存存储计算结果

---

## 进阶主题

### 线程安全

如果插件使用多线程，注意线程安全：

```python
import threading

class myplugin(DisplayPlugin):
    def __init__(self, manager, width, height):
        self.name = "myplugin"
        super().__init__(manager, width, height)
        self.lock = threading.Lock()
        self.data = {}

    def update(self):
        self.clear()
        with self.lock:
            # 访问共享数据
            text = self.data.get('text', 'No data')
        self.draw.text((10, 10), text, fill=1, font=self.font10)

    def background_task(self):
        with self.lock:
            # 修改共享数据
            self.data['text'] = "Updated"
```

### 配置文件使用

从配置中读取参数：

```python
class myplugin(DisplayPlugin):
    def __init__(self, manager, width, height):
        self.name = "myplugin"
        super().__init__(manager, width, height)

        # 从配置中读取参数
        config = self.manager.get_plugin_config(self.name)
        self.refresh_interval = config.get('refresh_interval', 60)
        self.api_url = config.get('api_url', 'http://default.url')
```

配置文件 `config/plugins.json`:
```json
{
    "plugins": [
        {
            "name": "myplugin",
            "enabled": true,
            "auto_hide": false,
            "config": {
                "refresh_interval": 30,
                "api_url": "http://api.example.com"
            }
        }
    ]
}
```

---

## 参考资源

- **PIL 文档**: https://pillow.readthedocs.io/
- **示例插件**: `screen/plugins/clock.py`, `screen/plugins/life.py`
- **基类源码**: `screen/base.py`
- **UI 组件**: `ui/component.py`

---

**Happy Coding! 🎵**
