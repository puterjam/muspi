#!/bin/bash
# Muspi 打包脚本

set -e  # 遇到错误时退出

echo "========================================="
echo "  Muspi PyInstaller 打包工具"
echo "========================================="
echo ""

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "错误: 未找到虚拟环境 venv/"
    echo "请先创建虚拟环境: python3 -m venv venv --system-site-packages"
    exit 1
fi

# 激活虚拟环境
echo "激活虚拟环境..."
source venv/bin/activate

# 检查 PyInstaller
if ! command -v pyinstaller &> /dev/null; then
    echo "安装 PyInstaller..."
    pip install pyinstaller
fi

# 清理旧的构建文件
echo ""
echo "清理旧的构建文件..."
rm -rf build/
rm -rf dist/

# 执行打包
echo ""
echo "开始打包主程序 (muspi)..."
pyinstaller --clean muspi.spec

echo ""
echo "开始打包配置工具 (muspi-config)..."
pyinstaller --clean config.spec

# 检查打包结果
if [ -d "dist/muspi" ] && [ -d "dist/muspi-config" ]; then
    echo ""
    echo "========================================="
    echo "  打包成功！"
    echo "========================================="
    echo ""
    echo "可执行文件位置:"
    echo "  主程序:   dist/muspi/muspi"
    echo "  配置工具: dist/muspi-config/muspi-config"
    echo ""
    echo "测试运行:"
    echo "  主程序:   cd dist/muspi && ./muspi"
    echo "  配置工具: cd dist/muspi-config && ./muspi-config"
    echo ""
    echo "创建发布包:"
    echo "  cd dist && tar -czf muspi-$(uname -m).tar.gz muspi/ muspi-config/"
    echo ""
else
    echo ""
    echo "打包失败！请检查错误信息。"
    [ ! -d "dist/muspi" ] && echo "  - muspi 主程序打包失败"
    [ ! -d "dist/muspi-config" ] && echo "  - muspi-config 配置工具打包失败"
    exit 1
fi
