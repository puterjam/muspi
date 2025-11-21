#!/bin/bash
# Muspi 依赖安装脚本

set -e  # 遇到错误时退出

# 检查是否以 root 权限运行 apt 相关命令
if [ "$EUID" -ne 0 ]; then
    SUDO="sudo"
else
    SUDO=""
fi

# 定义颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 定义安装步骤函数
step_1_update_system() {
    echo -e "${GREEN}[1/10] 更新系统包列表...${NC}"
    $SUDO apt-get update
}

step_2_install_system_deps() {
    echo -e "${GREEN}[2/10] 安装系统级依赖...${NC}"
    $SUDO apt-get install -y \
        python3-venv \
        python3-dev \
        libopus0 \
        libopus-dev \
        libjpeg-dev \
        zlib1g-dev \
        libfreetype6-dev \
        liblcms2-dev \
        libwebp-dev \
        tcl8.6-dev \
        tk8.6-dev \
        build-essential \
        git \
        autoconf \
        automake \
        libtool \
        libpopt-dev \
        libconfig-dev \
        libasound2-dev \
        avahi-daemon \
        libavahi-client-dev \
        libssl-dev \
        libsoxr-dev \
        libplist-dev \
        libsodium-dev \
        libavutil-dev \
        libavcodec-dev \
        libavformat-dev \
        uuid-dev \
        libgcrypt-dev \
        xxd \
        swig \
        liblgpio-dev \
        liblgpio1 \
        libdiscid0 \
        libdiscid-dev \
        mpv \
        socat
}

step_3_setup_venv() {
    echo -e "${GREEN}[3/10] 检查虚拟环境...${NC}"
    if [ ! -d "venv" ]; then
        echo "创建 Python 虚拟环境..."
        python3 -m venv venv
    else
        echo "虚拟环境已存在"
    fi
}

step_4_install_python_deps() {
    echo -e "${GREEN}[4/10] 安装 Python 依赖...${NC}"
    ./venv/bin/pip install --upgrade pip
    ./venv/bin/pip install -r requirements.txt
}

step_5_install_nqptp() {
    echo -e "${GREEN}[5/10] 编译安装 nqptp（网络时间同步，AirPlay 2 所需）...${NC}"
    NQPTP_DIR="/tmp/nqptp"

    if ! command -v nqptp &> /dev/null; then
        echo "nqptp 未安装，开始编译..."

        # 克隆源码
        if [ -d "$NQPTP_DIR" ]; then
            rm -rf "$NQPTP_DIR"
        fi
        git clone https://github.com/mikebrady/nqptp.git "$NQPTP_DIR"
        cd "$NQPTP_DIR"

        # 编译
        echo "正在配置和编译 nqptp..."
        autoreconf -fi
        ./configure --with-systemd-startup
        make -j$(nproc)

        # 安装
        echo "正在安装 nqptp..."
        $SUDO make install

        # 启用服务
        echo "启用 nqptp 服务..."
        $SUDO systemctl daemon-reload
        $SUDO systemctl enable nqptp
        $SUDO systemctl start nqptp

        # 清理
        cd -
        rm -rf "$NQPTP_DIR"

        echo "nqptp 安装完成并已启动"
    else
        echo "nqptp 已安装"
        # 确保服务在运行
        if systemctl is-active --quiet nqptp; then
            echo "nqptp 服务已运行"
        else
            echo "启动 nqptp 服务..."
            $SUDO systemctl start nqptp
        fi
    fi
}

step_6_install_shairport() {
    echo -e "${GREEN}[6/10] 编译安装 shairport-sync（支持 AirPlay 2 和 metadata）...${NC}"
    SHAIRPORT_DIR="/tmp/shairport-sync"

    if ! command -v shairport-sync &> /dev/null; then
        echo "shairport-sync 未安装，开始编译..."

        # 克隆源码
        if [ -d "$SHAIRPORT_DIR" ]; then
            rm -rf "$SHAIRPORT_DIR"
        fi
        git clone https://github.com/mikebrady/shairport-sync.git "$SHAIRPORT_DIR"
        cd "$SHAIRPORT_DIR"

        # 编译
        echo "正在配置和编译 shairport-sync（启用 AirPlay 2 和 metadata）..."
        autoreconf -fi
        ./configure --sysconfdir=/etc \
            --with-alsa \
            --with-soxr \
            --with-avahi \
            --with-ssl=openssl \
            --with-systemd \
            --with-airplay-2 \
            --with-metadata
        make -j$(nproc)

        # 安装
        echo "正在安装 shairport-sync..."
        $SUDO make install

        # 清理
        cd -
        rm -rf "$SHAIRPORT_DIR"

        echo "shairport-sync 安装完成"
    else
        echo "shairport-sync 已安装"
    fi
}

step_7_install_metadata_reader() {
    echo -e "${GREEN}[7/10] 编译安装 shairport-sync-metadata-reader...${NC}"
    METADATA_READER_DIR="/tmp/shairport-sync-metadata-reader"

    if ! command -v shairport-sync-metadata-reader &> /dev/null; then
        echo "shairport-sync-metadata-reader 未安装，开始编译..."

        # 克隆源码
        if [ -d "$METADATA_READER_DIR" ]; then
            rm -rf "$METADATA_READER_DIR"
        fi
        git clone https://github.com/mikebrady/shairport-sync-metadata-reader.git "$METADATA_READER_DIR"
        cd "$METADATA_READER_DIR"

        # 编译
        echo "正在配置和编译 shairport-sync-metadata-reader..."
        autoreconf -i -f
        ./configure
        make -j$(nproc)

        # 安装
        echo "正在安装 shairport-sync-metadata-reader..."
        $SUDO make install

        # 清理
        cd -
        rm -rf "$METADATA_READER_DIR"

        echo "shairport-sync-metadata-reader 安装完成"
    else
        echo "shairport-sync-metadata-reader 已安装"
    fi
}

step_8_install_roonbridge() {
    echo -e "${GREEN}[8/10] 检查 RoonBridge 安装...${NC}"
    if ! command -v RoonBridge &> /dev/null; then
        echo "RoonBridge 未安装，开始安装..."
        echo "下载 RoonBridge 安装脚本（ARM64 版本）..."
        curl -O https://download.roonlabs.net/builds/roonbridge-installer-linuxarmv8.sh
        chmod +x roonbridge-installer-linuxarmv8.sh
        echo "运行 RoonBridge 安装脚本..."
        $SUDO ./roonbridge-installer-linuxarmv8.sh
        rm roonbridge-installer-linuxarmv8.sh
        echo "RoonBridge 安装完成"
    else
        echo "RoonBridge 已安装"
    fi
}

step_9_check_hardware() {
    echo -e "${GREEN}[9/10] 检查硬件接口配置...${NC}"
    if [ ! -e "/dev/spidev0.0" ]; then
        echo -e "${YELLOW}警告: SPI 接口未启用${NC}"
        echo "请运行 'sudo raspi-config' 并在 Interface Options 中启用 SPI"
        echo "启用后需要重启系统"
    else
        echo "SPI 接口已启用"
    fi

    if [ ! -e "/dev/i2c-1" ]; then
        echo -e "${YELLOW}警告: I2C 接口未启用${NC}"
        echo "请运行 'sudo raspi-config' 并在 Interface Options 中启用 I2C"
        echo "启用后需要重启系统"
    else
        echo "I2C 接口已启用"
    fi
}

step_10_wifi_optimization() {
    echo -e "${GREEN}[10/10] 配置 WiFi 优化（防掉线）...${NC}"

    # 禁用 WiFi 省电模式
    echo "禁用 WiFi 省电模式..."
    WIFI_INTERFACE=$(iw dev | awk '$1=="Interface"{print $2}' | head -n1)
    if [ -n "$WIFI_INTERFACE" ]; then
        # 立即禁用省电模式
        $SUDO iw dev $WIFI_INTERFACE set power_save off 2>/dev/null || true

        # 创建开机自动禁用省电模式的服务
        $SUDO tee /etc/systemd/system/wifi-powersave-off.service > /dev/null <<EOF
[Unit]
Description=Turn off WiFi power saving
After=network.target

[Service]
Type=oneshot
ExecStart=/sbin/iw dev $WIFI_INTERFACE set power_save off
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

        $SUDO systemctl daemon-reload
        $SUDO systemctl enable wifi-powersave-off.service 2>/dev/null || true
        echo "WiFi 省电模式已禁用（接口: $WIFI_INTERFACE）"
    else
        echo "警告: 未检测到 WiFi 接口，跳过省电模式配置"
    fi

    # 配置 WiFi 保活脚本
    echo "配置 WiFi 连接保活机制..."
    $SUDO tee /usr/local/bin/wifi-keepalive.sh > /dev/null <<'EOF'
#!/bin/bash
# WiFi 保活脚本 - 检测连接状态并自动重连

PING_TARGET="8.8.8.8"
MAX_RETRIES=3

# 检查网络连接
if ! ping -c 1 -W 2 $PING_TARGET > /dev/null 2>&1; then
    echo "[$(date)] WiFi 连接异常，尝试恢复..." >> /var/log/wifi-keepalive.log

    # 重启 WiFi 接口
    WIFI_INTERFACE=$(iw dev | awk '$1=="Interface"{print $2}' | head -n1)
    if [ -n "$WIFI_INTERFACE" ]; then
        ip link set $WIFI_INTERFACE down
        sleep 2
        ip link set $WIFI_INTERFACE up
        sleep 5

        # 禁用省电模式
        iw dev $WIFI_INTERFACE set power_save off

        echo "[$(date)] WiFi 接口已重启: $WIFI_INTERFACE" >> /var/log/wifi-keepalive.log
    fi
fi
EOF

    $SUDO chmod +x /usr/local/bin/wifi-keepalive.sh

    # 添加 cron 任务（每5分钟检查一次）
    CRON_JOB="*/5 * * * * /usr/local/bin/wifi-keepalive.sh"
    ($SUDO crontab -l 2>/dev/null | grep -v wifi-keepalive; echo "$CRON_JOB") | $SUDO crontab -

    # 创建日志文件
    $SUDO touch /var/log/wifi-keepalive.log
    $SUDO chmod 644 /var/log/wifi-keepalive.log

    echo "WiFi 保活机制已配置（每5分钟检查一次连接状态）"
    echo "日志文件: /var/log/wifi-keepalive.log"
}

# 显示步骤选择菜单
show_menu() {
    clear
    echo "================================"
    echo "Muspi 依赖安装脚本"
    echo "================================"
    echo ""
    echo "请选择要执行的安装步骤（可多选，用空格分隔）："
    echo ""
    echo "  [1]  更新系统包列表"
    echo "  [2]  安装系统级依赖"
    echo "  [3]  设置 Python 虚拟环境"
    echo "  [4]  安装 Python 依赖"
    echo "  [5]  编译安装 nqptp（AirPlay 2 时间同步）"
    echo "  [6]  编译安装 shairport-sync（AirPlay 2 支持）"
    echo "  [7]  编译安装 shairport-sync-metadata-reader"
    echo "  [8]  安装 RoonBridge"
    echo "  [9]  检查硬件接口（SPI/I2C）"
    echo "  [10] WiFi 优化配置"
    echo ""
    echo "  [a]  全部安装"
    echo "  [q]  退出"
    echo ""
    echo -n "请输入选项（例如：1 2 3 或 a）: "
}

# 执行选中的步骤
run_steps() {
    local steps=("$@")

    # 如果选择了全部安装
    if [[ " ${steps[@]} " =~ " a " ]] || [[ " ${steps[@]} " =~ " A " ]]; then
        steps=(1 2 3 4 5 6 7 8 9 10)
    fi

    echo ""
    echo "================================"
    echo "开始执行选中的安装步骤"
    echo "================================"
    echo ""

    for step in "${steps[@]}"; do
        case $step in
            1) step_1_update_system ;;
            2) step_2_install_system_deps ;;
            3) step_3_setup_venv ;;
            4) step_4_install_python_deps ;;
            5) step_5_install_nqptp ;;
            6) step_6_install_shairport ;;
            7) step_7_install_metadata_reader ;;
            8) step_8_install_roonbridge ;;
            9) step_9_check_hardware ;;
            10) step_10_wifi_optimization ;;
            *) echo -e "${YELLOW}警告: 未知步骤 $step，跳过${NC}" ;;
        esac
        echo ""
    done
}

# 显示安装完成信息
show_completion_message() {
    echo ""
    echo "================================"
    echo "依赖安装完成！"
    echo "================================"
    echo ""
    echo "注意事项："
    echo "1. 如果 SPI/I2C 接口未启用，请运行 'sudo raspi-config' 启用"
    echo "2. 启用硬件接口后需要重启系统"
    echo "3. nqptp 已安装并启动（AirPlay 2 网络时间同步）"
    echo "   - 查看状态: sudo systemctl status nqptp"
    echo "4. shairport-sync 已安装（支持 AirPlay 2 和 metadata）"
    echo "   - 配置文件: /etc/shairport-sync.conf"
    echo "   - 启动: sudo systemctl start shairport-sync"
    echo "   - 停止: sudo systemctl stop shairport-sync"
    echo "   - 查看状态: sudo systemctl status shairport-sync"
    echo "5. RoonBridge 安装后会作为系统服务运行"
    echo "   - 启动: sudo systemctl start roonbridge"
    echo "   - 停止: sudo systemctl stop roonbridge"
    echo "   - 查看状态: sudo systemctl status roonbridge"
    echo "6. WiFi 优化已配置："
    echo "   - WiFi 省电模式已禁用（防止连接断开）"
    echo "   - WiFi 保活检查每5分钟运行一次"
    echo "   - 查看保活日志: sudo tail -f /var/log/wifi-keepalive.log"
    echo "   - 检查省电状态: iw dev wlan0 get power_save"
    echo "7. 运行程序: ./venv/bin/python main.py"
    echo ""
}

# 主程序
main() {
    # 如果有命令行参数，直接执行指定步骤
    if [ $# -gt 0 ]; then
        if [ "$1" = "--all" ] || [ "$1" = "-a" ]; then
            run_steps a
        else
            run_steps "$@"
        fi
        show_completion_message
        exit 0
    fi

    # 交互式菜单
    while true; do
        show_menu
        read -r input

        # 将输入转为数组
        read -ra steps <<< "$input"

        # 检查是否退出
        if [[ " ${steps[@]} " =~ " q " ]] || [[ " ${steps[@]} " =~ " Q " ]]; then
            echo "已取消安装"
            exit 0
        fi

        # 检查是否有有效输入
        if [ ${#steps[@]} -eq 0 ]; then
            echo "请至少选择一个步骤"
            sleep 2
            continue
        fi

        # 执行选中的步骤
        run_steps "${steps[@]}"
        show_completion_message
        break
    done
}

# 运行主程序
main "$@"
