# 项目结构

## 目录结构

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
│       ├── clock.py    # 时钟插件
│       ├── xiaozhi.py  # 小智 AI 插件
│       ├── roon.py     # Roon 音乐插件
│       ├── cdplayer.py # CD 播放器插件
│       ├── airplay.py  # AirPlay 插件
│       ├── dino.py     # 恐龙游戏插件
│       └── life.py     # 生命游戏插件
├── until/               # 工具模块
│   ├── device/         # 设备管理
│   │   ├── input.py    # 输入设备管理
│   │   └── volume.py   # 音量控制
│   ├── keymap.py       # 按键映射
│   └── log.py          # 日志工具
├── ui/                  # UI 组件
│   └── animation.py    # 动画效果
├── docs/                # 文档
│   ├── plugins.md      # 插件开发规范
│   ├── keymap.md       # 按键映射配置
│   ├── structure.md    # 项目结构说明（本文档）
│   ├── changelog.md    # 更新日志
│   └── troubleshooting.md # 故障排除
├── config/              # 配置文件
│   ├── keymap.json     # 按键配置
│   └── plugins.json    # 插件配置
├── example/             # 示例代码
│   ├── input_test.py   # 输入测试
│   └── py-xiaozhi.py   # 小智 AI 示例
├── requirements.txt     # Python 依赖
├── install.sh           # 安装脚本
└── install_service.sh   # 服务安装脚本
```

## 核心模块说明

### 主程序 (main.py)

程序入口，负责：
- 初始化硬件驱动（OLED 显示屏）
- 启动显示管理器
- 加载插件
- 处理程序生命周期

### 硬件驱动 (drive/)

**SSD1305.py**
- OLED 显示屏驱动
- 支持 SPI 接口通信
- 提供绘图 API（基于 PIL）

**config.py**
- 硬件配置参数
- GPIO 引脚定义
- SPI 配置

### 显示管理 (screen/)

**manager.py**
- 显示管理器核心
- 插件生命周期管理
- 帧率控制
- Overlay 层支持
- 输入事件分发

**plugin.py**
- 插件基类 `DisplayPlugin`
- 提供插件接口和工具方法
- 管理插件状态

**plugins/**
- 各种显示插件实现
- 每个插件继承 `DisplayPlugin`
- 独立的渲染和事件处理逻辑

### 工具模块 (until/)

**device/input.py**
- 输入设备管理
- 支持键盘、手柄热插拔
- 事件监听和分发

**device/volume.py**
- 系统音量控制
- ALSA 音量接口封装

**keymap.py**
- 按键映射管理
- 配置文件加载
- 按键匹配和查询 API

**log.py**
- 日志工具
- 统一的日志输出格式

### UI 组件 (ui/)

**animation.py**
- 动画效果实现
- 音量条、加载动画等

### 配置文件 (config/)

**keymap.json**
- 按键映射配置
- 定义各功能按键
- 支持多按键绑定

**plugins.json**
- 插件启用/禁用配置
- 插件加载顺序
- 插件特定配置

## 开发流程

### 添加新插件

1. 在 `screen/plugins/` 创建新的 Python 文件
2. 继承 `DisplayPlugin` 类
3. 实现 `update()` 方法（渲染逻辑）
4. 实现 `key_callback()` 方法（按键处理）
5. 在 `config/plugins.json` 中注册插件

详细说明参考 [插件开发规范](plugins.md)

### 修改按键映射

1. 编辑 `config/keymap.json`
2. 修改对应功能的按键代码
3. 重启程序或调用 `keymap.reload_config()` 热重载

详细说明参考 [按键映射配置](keymap.md)

### 添加新硬件支持

1. 在 `drive/` 目录添加驱动模块
2. 在 `until/device/` 添加设备管理模块
3. 在 `main.py` 中初始化硬件
4. 更新 `config.py` 配置

## 相关文档

- [插件开发规范](plugins.md)
- [按键映射配置](keymap.md)
- [更新日志](changelog.md)
- [故障排除](troubleshooting.md)
