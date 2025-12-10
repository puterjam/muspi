#!/bin/bash
# Muspi 依赖安装脚本 - 支持精简安装和完整安装

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
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 安装类型（minimal 或 full）
INSTALL_TYPE=""

# 已安装的组件列表
INSTALLED_COMPONENTS=()

#==========================================
# 安装步骤函数
#==========================================

step_update_system() {
    echo -e "${GREEN}[1/7] 更新系统包列表...${NC}"
    $SUDO apt-get update
}

step_install_minimal_deps() {
    echo -e "${GREEN}[2/7] 安装基础系统依赖...${NC}"
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
        libdiscid-dev \
        liblgpio-dev \
        liblgpio1
}

step_init_submodules() {
    echo -e "${GREEN}[3/7] 初始化 Git 子模块...${NC}"

    # 检查是否有子模块
    if [ -f ".gitmodules" ]; then
        echo "正在初始化和更新 Git 子模块..."
        git submodule update --init --recursive
        echo "✓ Git 子模块初始化完成"
    else
        echo "未检测到 Git 子模块，跳过此步骤"
    fi
}

step_install_full_deps() {
    echo -e "${GREEN}[额外] 安装完整依赖（AirPlay/Roon/CD 支持）...${NC}"
    $SUDO apt-get install -y \
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
        libdiscid0 \
        libdiscid-dev \
        mpv \
        socat

    INSTALLED_COMPONENTS+=("mpv")
}

step_setup_venv() {
    echo -e "${GREEN}[4/7] 设置 Python 虚拟环境...${NC}"
    if [ ! -d "venv" ]; then
        echo "创建 Python 虚拟环境..."
        python3 -m venv venv
    else
        echo "虚拟环境已存在"
    fi
}

step_install_python_deps() {
    echo -e "${GREEN}[5/7] 安装 Python 依赖...${NC}"
    ./venv/bin/pip install --upgrade pip
    ./venv/bin/pip install -r requirements.txt
}

step_install_nqptp() {
    echo -e "${GREEN}[额外] 编译安装 nqptp（AirPlay 2 时间同步）...${NC}"
    NQPTP_DIR="/tmp/nqptp"

    if ! command -v nqptp &> /dev/null; then
        echo "nqptp 未安装，开始编译..."

        if [ -d "$NQPTP_DIR" ]; then
            rm -rf "$NQPTP_DIR"
        fi
        git clone https://github.com/mikebrady/nqptp.git "$NQPTP_DIR"
        cd "$NQPTP_DIR"

        autoreconf -fi
        ./configure --with-systemd-startup
        make -j$(nproc)
        $SUDO make install

        $SUDO systemctl daemon-reload
        $SUDO systemctl enable nqptp
        $SUDO systemctl start nqptp

        cd -
        rm -rf "$NQPTP_DIR"

        echo "nqptp 安装完成"
    else
        echo "nqptp 已安装"
        if ! systemctl is-active --quiet nqptp; then
            $SUDO systemctl start nqptp
        fi
    fi
}

step_install_shairport() {
    echo -e "${GREEN}[额外] 编译安装 shairport-sync（AirPlay 2）...${NC}"
    SHAIRPORT_DIR="/tmp/shairport-sync"

    if ! command -v shairport-sync &> /dev/null; then
        echo "shairport-sync 未安装，开始编译..."

        if [ -d "$SHAIRPORT_DIR" ]; then
            rm -rf "$SHAIRPORT_DIR"
        fi
        git clone https://github.com/mikebrady/shairport-sync.git "$SHAIRPORT_DIR"
        cd "$SHAIRPORT_DIR"

        echo "正在配置和编译 shairport-sync..."
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

        $SUDO make install

        cd -
        rm -rf "$SHAIRPORT_DIR"

        echo "shairport-sync 安装完成"
    else
        echo "shairport-sync 已安装"
    fi

    INSTALLED_COMPONENTS+=("shairport-sync")
}

step_install_metadata_reader() {
    echo -e "${GREEN}[额外] 编译安装 shairport-sync-metadata-reader...${NC}"
    METADATA_READER_DIR="/tmp/shairport-sync-metadata-reader"

    if ! command -v shairport-sync-metadata-reader &> /dev/null; then
        echo "shairport-sync-metadata-reader 未安装，开始编译..."

        if [ -d "$METADATA_READER_DIR" ]; then
            rm -rf "$METADATA_READER_DIR"
        fi
        git clone https://github.com/mikebrady/shairport-sync-metadata-reader.git "$METADATA_READER_DIR"
        cd "$METADATA_READER_DIR"

        autoreconf -i -f
        ./configure
        make -j$(nproc)
        $SUDO make install

        cd -
        rm -rf "$METADATA_READER_DIR"

        echo "shairport-sync-metadata-reader 安装完成"
    else
        echo "shairport-sync-metadata-reader 已安装"
    fi
}

step_install_roonbridge() {
    echo -e "${GREEN}[额外] 安装 RoonBridge...${NC}"
    if ! command -v RoonBridge &> /dev/null; then
        echo "RoonBridge 未安装，开始安装..."
        curl -O https://download.roonlabs.net/builds/roonbridge-installer-linuxarmv8.sh
        chmod +x roonbridge-installer-linuxarmv8.sh
        $SUDO ./roonbridge-installer-linuxarmv8.sh
        rm roonbridge-installer-linuxarmv8.sh
        echo "RoonBridge 安装完成"
    else
        echo "RoonBridge 已安装"
    fi

    INSTALLED_COMPONENTS+=("roonbridge")
}

step_check_hardware() {
    echo -e "${GREEN}[6/7] 检查硬件接口配置...${NC}"
    if [ ! -e "/dev/spidev0.0" ]; then
        echo -e "${YELLOW}警告: SPI 接口未启用${NC}"
        echo "请运行 'sudo raspi-config' 并在 Interface Options 中启用 SPI"
    else
        echo "✓ SPI 接口已启用"
    fi
}

step_wifi_optimization() {
    echo -e "${GREEN}[7/7] 配置 WiFi 优化...${NC}"

    WIFI_INTERFACE=$(iw dev 2>/dev/null | awk '$1=="Interface"{print $2}' | head -n1)
    if [ -z "$WIFI_INTERFACE" ]; then
        echo "未检测到 WiFi 接口，跳过 WiFi 优化"
        return
    fi

    # 禁用 WiFi 省电模式
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
    echo "✓ WiFi 省电模式已禁用"
}

#==========================================
# 主安装流程
#==========================================

install_minimal() {
    echo ""
    echo "================================"
    echo "精简安装模式"
    echo "================================"
    echo ""
    echo "将安装："
    echo "  ✓ 基础系统依赖"
    echo "  ✓ Git 子模块（pyarduboy 等）"
    echo "  ✓ Python 虚拟环境"
    echo "  ✓ Python 依赖包"
    echo "  ✓ 硬件接口检查"
    echo "  ✓ WiFi 优化"
    echo ""
    echo "不包括："
    echo "  ✗ shairport-sync (AirPlay 2)"
    echo "  ✗ RoonBridge (Roon)"
    echo "  ✗ mpv (CD 播放器)"
    echo ""

    INSTALL_TYPE="minimal"

    step_update_system
    step_install_minimal_deps
    step_init_submodules
    step_setup_venv
    step_install_python_deps
    step_check_hardware
    step_wifi_optimization

    echo -e "${GREEN}[8/7] 生成插件配置...${NC}"
    export INSTALL_TYPE
    export INSTALLED_COMPONENTS=$(IFS=,; echo "${INSTALLED_COMPONENTS[*]}")
}

install_full() {
    echo ""
    echo "================================"
    echo "完整安装模式"
    echo "================================"
    echo ""
    echo "将安装："
    echo "  ✓ 基础系统依赖"
    echo "  ✓ 完整系统依赖"
    echo "  ✓ Git 子模块（pyarduboy 等）"
    echo "  ✓ Python 虚拟环境"
    echo "  ✓ Python 依赖包"
    echo "  ✓ nqptp (AirPlay 2 时间同步)"
    echo "  ✓ shairport-sync (AirPlay 2)"
    echo "  ✓ shairport-sync-metadata-reader"
    echo "  ✓ RoonBridge (Roon 音乐服务)"
    echo "  ✓ mpv (CD 播放器)"
    echo "  ✓ 硬件接口检查"
    echo "  ✓ WiFi 优化"
    echo ""
    echo -e "${YELLOW}注意: 完整安装需要编译多个组件，可能需要较长时间${NC}"
    echo ""

    INSTALL_TYPE="full"

    step_update_system
    step_install_minimal_deps
    step_install_full_deps
    step_init_submodules
    step_setup_venv
    step_install_python_deps
    step_install_nqptp
    step_install_shairport
    step_install_metadata_reader
    step_install_roonbridge
    step_check_hardware
    step_wifi_optimization

    echo -e "${GREEN}[8/7] 生成插件配置...${NC}"
    export INSTALL_TYPE
    export INSTALLED_COMPONENTS=$(IFS=,; echo "${INSTALLED_COMPONENTS[*]}")
}

install_systemd_service() {
    echo ""
    echo "================================"
    echo "安装 Muspi 系统服务"
    echo "================================"
    echo ""

    if [ ! -f "install_service.sh" ]; then
        echo -e "${RED}错误: 未找到 install_service.sh 脚本${NC}"
        return 1
    fi

    chmod +x install_service.sh
    ./install_service.sh
}

show_completion_message() {
    echo ""
    echo "================================"
    echo "安装完成！"
    echo ""
    echo "使用 ./config.py 配置屏幕驱动和插件"
    echo "================================"
    echo ""

    if [ "$INSTALL_TYPE" = "minimal" ]; then
        echo "精简安装已完成"
        echo ""
        echo "如需启用 AirPlay/Roon/CD 功能，请运行完整安装"
    else
        echo "完整安装已完成，所有插件已启用"
        echo ""
        echo "服务管理："
        echo "  AirPlay 2:"
        echo "    - 启动: sudo systemctl start shairport-sync"
        echo "    - 状态: sudo systemctl status shairport-sync"
        echo "  Roon:"
        echo "    - 启动: sudo systemctl start roonbridge"
        echo "    - 状态: sudo systemctl status roonbridge"
    fi

    echo ""
    echo "注意事项："
    echo "  1. 使用 ./config.py 配置屏幕驱动和插件"
    echo "  2. 运行程序: ./muspi"
    echo ""

    # 询问是否安装系统服务
    echo -n "是否将 Muspi 安装为系统服务（开机自启）? [y/N] "
    read -r install_service

    if [[ "$install_service" =~ ^[Yy]$ ]]; then
        install_systemd_service
    else
        echo ""
        echo "跳过服务安装。如需稍后安装，请运行: ./install_service.sh"
        echo ""
    fi
}

#==========================================
# 主菜单
#==========================================

show_main_menu() {
    clear
    echo ""
    echo "$(tput setaf 2)          .~~.   .~~.$(tput sgr0)"
    echo "$(tput setaf 2)         '. \ ' ' / .'$(tput sgr0)"
    echo "$(tput setaf 1)          .~ .~~~..~.$(tput sgr0)          __  ___                     _"
    echo "$(tput setaf 1)         : .~.'~'.~. :$(tput sgr0)        /  |/  /__  __ _____ ____   (_)"
    echo "$(tput setaf 1)        ~ (   ) (   ) ~$(tput sgr0)      / /|_/ // / / // ___// __ \ / /"
    echo "$(tput setaf 1)       ( : '~'.~.'~' : )$(tput sgr0)    / /  / // /_/ /(__  )/ /_/ // /"
    echo "$(tput setaf 1)        ~ .~ (   ) ~. ~$(tput sgr0)    /_/  /_/ \__,_//____// .___//_/"
    echo "$(tput setaf 1)         (  : '~' :  )$(tput sgr0)                         /_/"
    echo "$(tput setaf 1)          '~ .~~~. ~'$(tput sgr0)      Created by PuterJam"
    echo "$(tput setaf 1)              '~'$(tput sgr0)"
    echo ""
    echo ""
    echo "请选择安装模式："
    echo ""
    echo "  [1] 精简安装（推荐新手）"
    echo "      - 快速安装，基础功能"
    echo "      - 支持：时钟、游戏、小智语音"
    echo "      - 安装时间：约 5 分钟"
    echo ""
    echo "  [2] 完整安装"
    echo "      - 包含所有功能"
    echo "      - 支持：AirPlay 2、Roon、CD 播放"
    echo "      - 安装时间：约 30-60 分钟（需编译）"
    echo ""
    echo "  [3] 仅安装系统服务"
    echo "      - 将 Muspi 配置为系统服务（开机自启）"
    echo "      - 需要已完成依赖安装"
    echo ""
    echo "  [q] 退出"
    echo ""
    echo -n "请选择 [1/2/3/q]: "
}

main() {
    # 命令行参数支持
    if [ $# -gt 0 ]; then
        case "$1" in
            --minimal|-m)
                install_minimal
                show_completion_message
                exit 0
                ;;
            --full|-f)
                install_full
                show_completion_message
                exit 0
                ;;
            --service|-s)
                echo ""
                echo "正在安装系统服务..."
                install_systemd_service
                echo ""
                echo "================================"
                echo "服务安装完成！"
                echo "================================"
                echo ""
                echo "服务管理命令："
                echo "  启动服务: sudo systemctl start muspi"
                echo "  停止服务: sudo systemctl stop muspi"
                echo "  查看状态: sudo systemctl status muspi"
                echo "  查看日志: sudo journalctl -u muspi -f"
                echo ""
                exit 0
                ;;
            *)
                echo "用法: $0 [--minimal|-m | --full|-f | --service|-s]"
                echo "  --minimal, -m  精简安装"
                echo "  --full, -f     完整安装"
                echo "  --service, -s  仅安装系统服务"
                exit 1
                ;;
        esac
    fi

    # 交互式菜单
    while true; do
        show_main_menu
        read -r choice

        case "$choice" in
            1)
                install_minimal
                show_completion_message
                break
                ;;
            2)
                install_full
                show_completion_message
                break
                ;;
            3)
                echo ""
                echo "正在安装系统服务..."
                install_systemd_service
                echo ""
                echo "================================"
                echo "服务安装完成！"
                echo "================================"
                echo ""
                echo "服务管理命令："
                echo "  启动服务: sudo systemctl start muspi"
                echo "  停止服务: sudo systemctl stop muspi"
                echo "  查看状态: sudo systemctl status muspi"
                echo "  查看日志: sudo journalctl -u muspi -f"
                echo ""
                break
                ;;
            q|Q)
                echo "已取消安装"
                exit 0
                ;;
            *)
                echo "无效选择，请重试"
                sleep 2
                ;;
        esac
    done
}

# 运行主程序
main "$@"
