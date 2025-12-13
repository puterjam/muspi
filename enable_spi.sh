#!/bin/bash
# 启用SPI接口脚本

echo "检查当前SPI配置..."
grep -q "^dtparam=spi=on" /boot/firmware/config.txt
if [ $? -eq 0 ]; then
    echo "SPI已经在config.txt中启用"
else
    echo "在config.txt中启用SPI..."
    echo "dtparam=spi=on" | sudo tee -a /boot/firmware/config.txt
    echo "已添加 dtparam=spi=on 到 /boot/firmware/config.txt"
fi

echo ""
echo "当前SPI设备:"
ls -l /dev/spi* 2>/dev/null || echo "未找到SPI设备"

echo ""
echo "引脚状态:"
pinctrl get 8,9,10,11

echo ""
echo "================================"
echo "请选择操作："
echo "1. 重启系统以应用SPI配置 (推荐)"
echo "2. 手动加载SPI模块 (临时方案)"
echo ""
read -p "请输入选项 (1 或 2): " choice

case $choice in
    1)
        echo "系统将在3秒后重启..."
        sleep 3
        sudo reboot
        ;;
    2)
        echo "尝试手动加载SPI模块..."
        sudo dtoverlay spi0-1cs
        echo "完成！请再次检查 /dev/spi* 设备"
        ;;
    *)
        echo "无效选项"
        ;;
esac
