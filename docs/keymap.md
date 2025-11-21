# 按键映射配置说明

## 概述

Muspi 使用全局按键映射系统，允许您自定义键盘、手柄等输入设备的按键功能。所有插件共享相同的按键配置，确保操作的一致性。

## 配置文件位置

**配置文件**: `config/keymap.json`

**代码实现**: `until/keymap.py`

## 配置文件结构

```json
{
    "settings": {
        "longpress_threshold": 3.0  // 长按触发时间（秒）
    },
    "keymap": {
        "navigation": { ... },      // 导航键配置
        "action": { ... },          // 功能键配置
        "media": { ... }            // 媒体键配置
    },
    "available_keys": { ... }       // 可用按键参考列表
}
```

## 按键分类

### 1. 导航键 (navigation)
- `up`: 上方向键
- `down`: 下方向键
- `left`: 左方向键
- `right`: 右方向键

### 2. 功能键 (action)
- `select`: **确定键** - 播放/暂停、确认操作、跳跃等（默认: `KEY_ENTER`）
- `cancel`: **取消键** - 下一曲、取消操作、切换视图等（默认: `KEY_SPACE`）
- `menu`: **菜单键** - 切换插件、打开菜单等（默认: `KEY_M`）
- `next_screen`: **下一个插件** - 快速切换（默认: `KEY_PAGEDOWN`）
- `previous_screen`: **上一个插件** - 快速切换（默认: `KEY_PAGEUP`）

### 3. 媒体控制键 (media)
- `play_pause`: 播放/暂停
- `next`: 下一曲
- `previous`: 上一曲
- `stop`: 停止
- `volume_up`: 音量增加
- `volume_down`: 音量减少
- `mute`: 静音

## 默认按键配置

当前默认配置：

| 功能 | 默认按键 | 说明 |
|------|---------|------|
| 确定 | `KEY_ENTER` | 确认、播放/暂停 |
| 取消 | `KEY_SPACE` | 取消、下一曲 |
| 下一个插件 | `KEY_PAGEDOWN`, `KEY_RIGHT` | 切换插件 |
| 上一个插件 | `KEY_PAGEUP`, `KEY_LEFT` | 切换插件 |
| 播放/暂停 | `KEY_PLAYPAUSE`| 媒体控制 |
| 下一曲 | `KEY_NEXTSONG` | 媒体控制 |
| 上一曲 | `KEY_PREVIOUSSONG` | 媒体控制 |
| 音量+ | `KEY_VOLUMEUP`, `KEY_UP` | 音量控制 |
| 音量- | `KEY_VOLUMEDOWN`, `KEY_DOWN` | 音量控制 |

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

### 示例 1：将确定键改为空格键

```json
{
    "keymap": {
        "action": {
            "select": ["KEY_SPACE"]
        }
    }
}
```

### 示例 2：一个功能绑定多个按键

```json
{
    "keymap": {
        "action": {
            "select": ["KEY_ENTER", "KEY_KP1", "KEY_SPACE"]
        }
    }
}
```

### 示例 3：添加手柄支持

```json
{
    "keymap": {
        "action": {
            "select": ["KEY_ENTER", "KEY_KP1", "BTN_A"],
            "cancel": ["KEY_SPACE", "KEY_KP2", "BTN_B"],
            "menu": ["KEY_M", "BTN_START"]
        }
    }
}
```

### 示例 4：修改长按阈值

```json
{
    "settings": {
        "longpress_threshold": 2.0
    }
}
```

## 可用按键代码参考

### 完整按键列表
参考: [Linux Input Event Codes](https://github.com/torvalds/linux/blob/master/include/uapi/linux/input-event-codes.h)
