# 按键映射配置说明

## 概述

Muspi 使用全局按键映射系统，允许您自定义键盘、手柄等输入设备的按键功能。所有插件共享相同的按键配置，确保操作的一致性。

## 配置文件位置

`config/keymap.json`

## 按键分类

### 1. 导航键 (navigation)
- `up`: 上方向键
- `down`: 下方向键
- `left`: 左方向键
- `right`: 右方向键

### 2. 功能键 (action)
- `select`: **确定键** - 播放/暂停、确认操作、跳跃等
- `cancel`: **取消键** - 下一曲、取消操作、切换视图等
- `menu`: **菜单键** - 切换插件、打开菜单等

### 3. 媒体控制键 (media)
- `play_pause`: 播放/暂停
- `next`: 下一曲
- `previous`: 上一曲
- `stop`: 停止
- `volume_up`: 音量增加
- `volume_down`: 音量减少
- `mute`: 静音

## 各插件按键功能映射

### 全局 (DisplayManager)
- **菜单键 (menu)**: 切换插件
- **菜单键长按**: 关闭屏幕
- **音量键 (volume_up/down)**: 调节音量

### CD 播放器 (cdplayer)
- **确定键 (select) 短按**: 播放/暂停
- **确定键 (select) 长按**: 停止播放并重置
- **取消键 (cancel) 短按**: 下一曲
- **取消键 (cancel) 长按**: 弹出 CD

### Roon 音乐播放器 (roon)
- **确定键 (select) 或 播放/暂停键**: 播放/暂停
- **取消键 (cancel) 或 下一曲键**: 下一曲
- **上一曲键 (previous)**: 上一曲

### 小智 AI (xiaozhi)
- **确定键 (select) 按下**: 开始语音输入
- **确定键 (select) 释放**: 停止语音输入
- **取消键 (cancel)**: 切换聊天框显示

### 恐龙游戏 (dino)
- **确定键 (select) 或 取消键 (cancel)**: 跳跃 / 开始游戏

### 生命游戏 (life)
- **确定键 (select) 或 取消键 (cancel)**: 重新初始化

## 修改按键映射

编辑 `config/keymap.json` 文件，修改对应的按键代码。

### 示例：将确定键改为空格键

```json
{
    "keymap": {
        "action": {
            "select": ["KEY_SPACE", "KEY_KP1"]
        }
    }
}
```

### 示例：添加手柄支持

```json
{
    "keymap": {
        "action": {
            "select": ["KEY_ENTER", "KEY_KP1", "BTN_A"],
            "cancel": ["KEY_ESC", "KEY_KP2", "BTN_B"],
            "menu": ["KEY_FORWARD", "KEY_M", "BTN_START"]
        }
    }
}
```

## 可用按键代码参考

### 键盘按键
- 数字键: `KEY_KP0` ~ `KEY_KP9`
- 方向键: `KEY_UP`, `KEY_DOWN`, `KEY_LEFT`, `KEY_RIGHT`
- 功能键: `KEY_F1` ~ `KEY_F12`
- 常用键: `KEY_ENTER`, `KEY_ESC`, `KEY_SPACE`

### 媒体键
- `KEY_PLAYPAUSE`, `KEY_PLAY`, `KEY_PAUSE`, `KEY_STOP`
- `KEY_NEXTSONG`, `KEY_PREVIOUSSONG`
- `KEY_VOLUMEUP`, `KEY_VOLUMEDOWN`, `KEY_MUTE`
- `KEY_FORWARD`, `KEY_REWIND`

### 手柄按键
- `BTN_A`, `BTN_B`, `BTN_X`, `BTN_Y`
- `BTN_TL`, `BTN_TR` (L/R 肩键)
- `BTN_SELECT`, `BTN_START`

### 完整按键列表
参考: [Linux Input Event Codes](https://github.com/torvalds/linux/blob/master/include/uapi/linux/input-event-codes.h)

## 热重载

修改配置文件后，可以调用 `KeyMap.reload_config()` 进行热重载，无需重启程序。

## 测试按键映射

运行测试脚本：

```bash
python3 until/keymap.py
```

这将打印当前的按键映射配置，并测试按键匹配功能。

## 注意事项

1. **按键冲突**: 避免将相同的按键分配给不同的功能
2. **多按键支持**: 每个功能可以绑定多个按键（数组形式）
3. **大小写敏感**: 按键代码必须全大写（如 `KEY_ENTER`）
4. **长按检测**: 长按阈值可在 `settings.longpress_threshold` 中配置（默认 3.0 秒）

## 故障排除

### 按键不响应
1. 检查设备是否被正确识别: `ls /dev/input/event*`
2. 检查按键代码是否正确: 使用 `evtest` 工具测试
3. 查看日志输出: `until/log.py` 会记录按键事件

### 配置文件错误
如果配置文件格式错误，系统将自动使用默认配置，并在日志中输出错误信息。
