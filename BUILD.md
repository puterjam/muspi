# Muspi PyInstaller 打包说明

本文档说明如何使用 PyInstaller 将 Muspi 项目打包成可执行文件。

本项目包含两个可执行程序：
- **muspi** - 主程序（OLED 显示娱乐系统）
- **muspi-config** - 配置管理工具（基于 curses 的交互式配置界面）

## 打包方法

### 方法一：使用打包脚本（推荐）

```bash
./build.sh
```

这个脚本会自动完成以下步骤：
1. 激活虚拟环境
2. 安装 PyInstaller（如果未安装）
3. 清理旧的构建文件
4. 打包主程序 (muspi.spec)
5. 打包配置工具 (config.spec)
6. 显示打包结果

### 方法二：手动打包

```bash
# 1. 激活虚拟环境
source venv/bin/activate

# 2. 安装 PyInstaller
pip install pyinstaller

# 3. 打包主程序
pyinstaller --clean muspi.spec

# 4. 打包配置工具
pyinstaller --clean config.spec

# 5. 查看结果
ls -lh dist/muspi/
ls -lh dist/muspi-config/
```

## 打包配置

本项目使用两个 spec 文件：
- [muspi.spec](muspi.spec) - 主程序打包配置
- [config.spec](config.spec) - 配置工具打包配置

### muspi.spec - 主程序配置

### 包含的资源文件
- `config/` - 配置文件（muspi.json, plugins.json, keymap.json）
- `assets/` - 资源文件（字体、图标）
- `screen/` - 屏幕插件模块
- `ui/` - UI 组件模块
- `until/` - 工具模块
- `drive/` - 驱动模块

### 隐藏导入
自动收集以下模块的子模块：
- luma（OLED 驱动）
- PIL（图像处理）
- evdev、gpiozero、lgpio（硬件接口）
- roonapi（Roon API）
- numpy、scipy（科学计算）
- 其他依赖模块

### config.spec - 配置工具配置

配置工具是独立的 curses 程序，包含：
- `config/` - 配置文件目录

## 打包结果

打包完成后，可执行文件位于：
```
dist/muspi/muspi              # 主程序
dist/muspi-config/muspi-config # 配置工具
```

完整的目录结构：
```
dist/
├── muspi/
│   ├── muspi          # 主程序可执行文件
│   ├── _internal/     # 依赖库和资源
│   ├── config/        # 配置文件
│   └── assets/        # 资源文件
└── muspi-config/
    ├── muspi-config   # 配置工具可执行文件
    ├── _internal/     # 依赖库
    └── config/        # 配置文件
```

## 测试打包结果

测试主程序：
```bash
cd dist/muspi
./muspi
```

测试配置工具：
```bash
cd dist/muspi-config
./muspi-config
```

## 创建发布包

创建包含两个程序的压缩包：

```bash
cd dist
tar -czf muspi-$(uname -m).tar.gz muspi/ muspi-config/
```

这会创建一个包含架构信息的压缩包，例如 `muspi-aarch64.tar.gz`

## 部署到目标机器

1. 将打包后的目录复制到目标机器
2. 确保目标机器安装了必要的系统依赖（SPI、I2C 驱动等）
3. 运行可执行文件

```bash
# 解压
tar -xzf muspi-aarch64.tar.gz

# 运行主程序
cd muspi
./muspi

# 或运行配置工具
cd ../muspi-config
./muspi-config
```

## 注意事项

### 硬件依赖
打包后的程序仍然依赖以下硬件和系统库：
- SPI 设备驱动（OLED 显示屏）
- I2C 设备驱动
- GPIO 库（lgpio、RPi.GPIO）
- 音频库（ALSA）
- 蓝牙库（pydbus）

### 系统兼容性
- 在树莓派上打包的程序只能在相同架构的 Linux 系统上运行
- 建议在目标系统相同的环境中打包
- ARM64 打包的程序不能在 x86_64 系统上运行，反之亦然

### 配置文件
打包后的程序会在运行时从以下位置读取配置：
1. 可执行文件同级的 `config/` 目录
2. `/var/lib/muspi/` 用户数据目录

首次运行前，可能需要调整配置文件中的路径设置。

## 调试问题

如果打包失败，可以：

1. 查看详细错误信息
```bash
pyinstaller --clean --log-level=DEBUG muspi.spec
```

2. 检查缺失的模块
```bash
# 运行打包后的程序，查看导入错误
cd dist/muspi
./muspi
```

3. 手动添加缺失的模块到 `muspi.spec` 的 `hiddenimports` 列表

4. 添加缺失的数据文件到 `muspi.spec` 的 `datas` 列表

## 优化建议

### 减小打包体积
编辑 [muspi.spec](muspi.spec)，在 `excludes` 列表中添加不需要的模块：

```python
excludes=['tkinter', 'matplotlib', 'test', 'unittest'],
```

### 启用 UPX 压缩
确保系统已安装 UPX：
```bash
sudo apt-get install upx-ucl
```

spec 文件中 `upx=True` 已启用。

### 单文件打包（不推荐）
如果需要单文件打包，修改 spec 文件：
```python
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,      # 添加
    a.datas,         # 添加
    [],
    name='muspi',
    debug=False,
    strip=False,
    upx=True,
    console=True,
    # 删除 exclude_binaries=True
)

# 删除 COLLECT 部分
```

注意：单文件打包会增加启动时间，且对于嵌入式设备不一定更好。
