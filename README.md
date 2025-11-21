# Muspi 🎵

> Muspi Entertainment with AI Agent - 基于树莓派的智能音乐播放器

![Muspi](https://i.imgur.com/qFaw8tK.jpeg)

## 项目简介

Muspi 是一个运行在树莓派上的智能音乐娱乐系统，集成了多种音乐播放源和 AI 语音助手功能。

### 主要特性

- 🎵 **多音源支持**
  - Roon 音乐服务集成
  - AirPlay 2 无线音频流（通过 shairport-sync）
  - CD 播放支持（可选）
  - 流媒体播放

- 🤖 **AI 助手集成**
  - 小智语音助手支持
  - TTS（文本转语音）功能
  - MQTT 通信

- 🎮**内置小游戏**
  - 小恐龙（可选）
  - life游戏（可选）

## 硬件要求

### 基本硬件清单

**必需硬件**：
- **树莓派**：树莓派 3B+ 或更高版本（推荐树莓派 4/5）
- **显示屏**：[2.23inch OLED HAT](https://www.waveshare.net/shop/2.23inch-OLED-HAT.htm)（SSD1305 驱动）
- **输入设备**：键盘/按键（手柄未测试）
- **音频输出**：
  - 外接音响（3.5mm/HDMI/蓝牙）
  - 或连接 DAC + 功放 + 喇叭
- **USB 麦克风**：用于小智语音助手

**可选硬件**：
- **DAC 音频扩展板**：获得更好的音质
- **CD 驱动器**：用于 CD 播放功能
- **蓝牙适配器**：用于蓝牙音频输出或手柄连接

## 系统要求

- **操作系统**：树莓派 OS 64位 Lite（Debian Bookworm 或更高版本）
- **Python 版本**：Python 3.11+（已测试 Python 3.13）
- **硬件接口**：启用 SPI 接口
- **网络连接**：WiFi 或有线网络（用于语音助手、Roon、AirPlay）

## 安装步骤

### 1. 克隆项目

```bash
git clone https://github.com/puterjam/muspi.git
cd muspi
```

### 2. 运行安装脚本

```bash
chmod +x install.sh
./install.sh
```

安装脚本提供两种模式：
- **精简安装**：快速安装，基础功能（约 5 分钟）
- **完整安装**：包含所有功能（约 30-60 分钟，需编译）

> 注意：完整安装需要编译 shairport-sync 等组件，需要较长时间。

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

## 📚 文档导航

### 开发文档
- **[插件开发规范](docs/plugins.md)** - 插件开发完整指南、API 参考和示例
- **[按键映射配置](docs/keymap.md)** - 键盘/手柄按键配置说明和编程接口
- **[项目结构说明](docs/structure.md)** - 目录结构、核心模块和开发流程

### 使用文档
- **[更新日志](docs/changelog.md)** - 版本更新记录和未来计划
- **[故障排除](docs/troubleshooting.md)** - 常见问题解决方案和调试方法

## 插件开发

Muspi 支持插件化的显示系统，你可以开发自己的插件来扩展功能。

插件特性：🎨 绘图 API、⌨️ 按键处理、🔄 生命周期管理、📊 帧率控制

**快速开始**：查看 [插件开发规范](docs/plugins.md) 和示例插件代码。

## 更新日志

### 最近更新 (2025-11-21)

- ✅ CD 播放器优化（修复 socket 连接、播放状态管理）
- ✅ 音量条显示优化（Overlay 层帧率修复）
- ✅ 键盘映射系统（配置文件分离、自定义映射）
- ✅ 安装脚本改进（精简/完整模式、服务安装）
- ✅ 文档完善（插件开发、按键配置、故障排除）

更多更新历史请查看 [更新日志](docs/changelog.md)

## 许可证

MIT License

## 作者

PuterJam

---

**Enjoy your music with Muspi! 🎵**
