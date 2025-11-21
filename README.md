# Muspi 🎵

> Muspi Entertainment with AI Agent - 基于树莓派的智能音乐播放器

```
          .~~.   .~~.
         '. \ ' ' / .'
          .~ .~~~..~.          __  ___                     _
         : .~.'~'.~. :        /  |/  /__  __ _____ ____   (_)
        ~ (   ) (   ) ~      / /|_/ // / / // ___// __ \ / /
       ( : '~'.~.'~' : )    / /  / // /_/ /(__  )/ /_/ // /
        ~ .~ (   ) ~. ~    /_/  /_/ \__,_//____// .___//_/
         (  : '~' :  )                         /_/
          '~ .~~~. ~'      Created by PuterJam
              '~'
```

## 项目简介

Muspi 是一个运行在树莓派上的智能音乐娱乐系统，集成了多种音乐播放源和 AI 语音助手功能。

### 主要特性

- 🎵 **多音源支持**
  - Roon 音乐服务集成
  - AirPlay 2 无线音频流（通过 shairport-sync）
  - CD 播放支持（使用优化的 cd-discid）
  - 流媒体播放

- 🤖 **AI 助手集成**
  - 小智语音助手支持
  - TTS（文本转语音）功能
  - MQTT 通信

- 📡 **网络优化**
  - WiFi 防掉线机制
  - 自动省电模式禁用
  - 连接保活监控

- 🖥️ **显示系统**
  - SSD1305 OLED 显示屏支持
  - 插件化界面系统
  - 滚动文本显示
  - 播放状态图标
  - 音量条可视化
  - Overlay 层支持

- ⌨️ **输入控制**
  - 物理按键支持
  - 自定义键盘映射
  - 设备热插拔监控（基于 watchdog）

## 硬件要求

- 树莓派（支持 GPIO、SPI、I2C）
- SSD1305 OLED 显示屏
- 输入设备（键盘/按键）
- 可选：CD 驱动器
- 可选：音频输出设备（用于 RoonBridge）

## 系统要求

- 树莓派 2 或更高版本（推荐树莓派 4）
- 树莓派 OS 64位（Debian Trixie 或更高版本）
- Python 3.11+（已测试 Python 3.13）
- 启用的 SPI 接口
- 启用的 I2C 接口（可选）
- WiFi 或有线网络连接

## 安装步骤

### 1. 克隆项目

```bash
git clone <repository-url>
cd muspi
```

### 2. 运行依赖安装脚本

```bash
chmod +x install_dependencies.sh
./install_dependencies.sh
```

> 注意：编译 shairport-sync 需要一些时间，请耐心等待。

### 3. 启用硬件接口

如果 SPI 接口未启用，需要手动配置：

```bash
sudo raspi-config
```

进入 `Interface Options`，启用：
- SPI


## 运行

```bash
./venv/bin/python main.py
```

或者激活虚拟环境后运行：

```bash
source venv/bin/activate
python main.py
```

## 项目结构

```
muspi/
├── main.py              # 主程序入口
├── drive/               # 硬件驱动
│   ├── SSD1305.py      # OLED 显示屏驱动
│   └── config.py       # 硬件配置
├── screen/              # 显示管理
│   ├── manager.py      # 显示管理器
│   ├── plugin.py       # 插件管理器
│   └── plugins/        # 显示插件
├── until/               # 工具模块
│   ├── device/         # 设备管理
│   └── log.py          # 日志工具
├── requirements.txt     # Python 依赖
└── install_dependencies.sh  # 依赖安装脚本
```

## 更新日志

### 最近更新 (2025-11-21)

- ✅ **CD 播放器优化**
  - 修复 mpv socket 连接问题（避免 socat 连接拒绝错误）
  - 修复重复播放问题（防止在 CD 读取时重复启动）
  - 修复长时间空闲后 CD 重载问题
  - 改进播放状态管理和错误处理
  - 添加 ALSA 音频输出支持

- ✅ **音量条显示优化**
  - 改进音量条的视觉表现
  - 修复 Overlay 层帧率问题

- ✅ **键盘映射系统**
  - 分离 keymap 配置到独立文件 (`config/keymap.json`)
  - 支持自定义按键映射
  - 改进输入设备热插拔支持

### 历史更新

- ✅ **新增 AirPlay 2 支持**（通过 shairport-sync）
- ✅ **WiFi 防掉线优化**（自动禁用省电模式 + 连接保活）
- ✅ **完善安装脚本**（自动编译依赖、配置服务）
- ✅ 迁移到 Python 3.13
- ✅ 用 `watchdog` 替换 `pyinotify`（解决 asyncore 兼容性问题）
- ✅ 添加 Overlay 层支持
- ✅ 使用 cd-discid 替代 libdiscid（性能优化）
- ✅ 优化 Roon 和小智的重连机制
- ✅ 兼容 TTS 的 stop 状态

详细更新历史请查看 `git log`。

## 故障排除

### shairport-sync 相关问题

**检查 shairport-sync 状态：**
```bash
sudo systemctl status shairport-sync
```

**重启 shairport-sync：**
```bash
sudo systemctl restart shairport-sync
```

**查看 shairport-sync 日志：**
```bash
journalctl -u shairport-sync -f
```

**测试 AirPlay 连接：**
在 iOS 设备上打开控制中心，点击 AirPlay 图标，应该能看到你的树莓派设备名称。

**配置音频输出：**
编辑配置文件 `/etc/shairport-sync.conf`，根据实际硬件调整音频输出设置。

### RoonBridge 连接问题

**手动安装 RoonBridge（64位系统）：**
```bash
curl -O https://download.roonlabs.net/builds/roonbridge-installer-linuxarmv8.sh
chmod +x roonbridge-installer-linuxarmv8.sh
sudo ./roonbridge-installer-linuxarmv8.sh
```

**32位系统请使用：**
```bash
curl -O https://download.roonlabs.net/builds/roonbridge-installer-linuxarmv7hf.sh
chmod +x roonbridge-installer-linuxarmv7hf.sh
sudo ./roonbridge-installer-linuxarmv7hf.sh
```

确保树莓派和 Roon Core 在同一网络中，并在 Roon 应用的 Settings → Audio 中可以看到 RoonBridge 设备。

## 许可证

MIT License

## 作者

PuterJam

---

**Enjoy your music with Muspi! 🎵**
