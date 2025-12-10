#!/bin/bash

# select_display.sh - 选择显示屏幕并更新配置文件

CONFIG_FILE="config/muspi.json"

# 检查配置文件是否存在
if [ ! -f "$CONFIG_FILE" ]; then
    echo "错误: 配置文件 $CONFIG_FILE 不存在"
    exit 1
fi

# 检查是否安装了 jq
if ! command -v jq &> /dev/null; then
    echo "错误: 需要安装 jq 工具"
    echo "请运行: sudo apt-get install jq"
    exit 1
fi

# 获取当前配置的显示驱动
current_driver=$(jq -r '.display.driver' "$CONFIG_FILE")
echo "当前使用的显示驱动: $current_driver"
echo ""

# 获取所有可用的显示驱动
echo "可用的显示驱动:"
drivers=($(jq -r '.drivers | keys[]' "$CONFIG_FILE"))

# 显示驱动列表
for i in "${!drivers[@]}"; do
    driver="${drivers[$i]}"
    width=$(jq -r ".drivers.\"$driver\".width" "$CONFIG_FILE")
    height=$(jq -r ".drivers.\"$driver\".height" "$CONFIG_FILE")
    driver_type=$(jq -r ".drivers.\"$driver\".driver" "$CONFIG_FILE")

    marker=""
    if [ "$driver" = "$current_driver" ]; then
        marker=" (当前)"
    fi

    echo "  $((i+1)). $driver - ${driver_type} (${width}x${height})${marker}"
done

echo ""
read -p "请选择要使用的显示驱动 [1-${#drivers[@]}]: " choice

# 验证输入
if ! [[ "$choice" =~ ^[0-9]+$ ]] || [ "$choice" -lt 1 ] || [ "$choice" -gt "${#drivers[@]}" ]; then
    echo "错误: 无效的选择"
    exit 1
fi

# 获取选择的驱动
selected_driver="${drivers[$((choice-1))]}"

# 如果选择的驱动与当前相同，则无需更新
if [ "$selected_driver" = "$current_driver" ]; then
    echo "已经在使用 $selected_driver，无需更改"
    exit 0
fi

# 更新配置文件
echo "正在更新配置文件..."
jq ".display.driver = \"$selected_driver\"" "$CONFIG_FILE" > "${CONFIG_FILE}.tmp"

# 检查 jq 是否执行成功
if [ $? -eq 0 ]; then
    mv "${CONFIG_FILE}.tmp" "$CONFIG_FILE"
    echo "成功更新显示驱动为: $selected_driver"
else
    echo "错误: 更新配置文件失败"
    rm -f "${CONFIG_FILE}.tmp"
    exit 1
fi
