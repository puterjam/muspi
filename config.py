#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Muspi Configuration Manager (使用 curses 实现)
使用 Python 标准库 curses，无需额外安装

特点:
- 支持鼠标点击选择
- 支持键盘方向键导航
- 使用标准库，无需安装依赖
"""

import json
import os
import sys
import subprocess
import curses
import re
import time
import select
from pathlib import Path


class ConfigManager:
    """配置管理器 (curses 版本)"""

    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.base_path = Path(__file__).parent
        self.muspi_config_path = self.base_path / "config" / "muspi.json"
        self.service_file = self.base_path / "muspi.service"
        self.service_name = "muspi.service"

        # 读取 user_path 配置
        self.user_path = self._get_user_path()
        self.plugins_config_path = self.user_path / "plugins.json"

        # 初始化颜色
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_CYAN, -1)     # 标题
        curses.init_pair(2, curses.COLOR_GREEN, -1)    # 选中/成功
        curses.init_pair(3, curses.COLOR_YELLOW, -1)   # 警告
        curses.init_pair(4, curses.COLOR_RED, -1)      # 错误
        curses.init_pair(5, curses.COLOR_BLUE, -1)     # 子标题
        curses.init_pair(6, curses.COLOR_WHITE, curses.COLOR_BLUE)  # 高亮选中

        # 启用鼠标
        curses.mousemask(curses.ALL_MOUSE_EVENTS | curses.REPORT_MOUSE_POSITION)

        # 设置
        self.stdscr.keypad(True)
        curses.curs_set(0)  # 隐藏光标

    def _get_user_path(self):
        """获取用户数据路径"""
        try:
            muspi_config = self.load_json(self.muspi_config_path)
            if muspi_config:
                user_path = muspi_config.get("path", {}).get("user", "~/.local/share/muspi")
                # 展开 ~ 为用户主目录
                expanded_path = Path(user_path).expanduser()
                return expanded_path
        except Exception as e:
            pass
        # 默认路径
        return Path("~/.local/share/muspi").expanduser()

    def load_json(self, path):
        """加载 JSON 配置文件"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            return None

    def save_json(self, path, data):
        """保存 JSON 配置文件"""
        try:
            with open(path, 'w', encoding='utf-8') as f:
                # 使用 sort_keys=False 保持字段顺序
                json.dump(data, f, ensure_ascii=False, indent=4, sort_keys=False)
            return True
        except Exception as e:
            # 调试信息
            print(f"保存失败: {e}")
            return False

    def is_service_installed(self):
        """检查服务是否已安装"""
        try:
            result = subprocess.run(
                ["systemctl", "list-unit-files", self.service_name],
                capture_output=True,
                text=True
            )
            return self.service_name in result.stdout
        except Exception:
            return False

    def show_message(self, title, message, color=0):
        """显示消息框"""
        self.stdscr.clear()
        h, w = self.stdscr.getmaxyx()

        # 显示标题
        self.stdscr.addstr(2, 2, title, curses.color_pair(5) | curses.A_BOLD)

        # 显示消息
        lines = message.split('\n')
        for i, line in enumerate(lines):
            if i + 4 < h:
                self.stdscr.addstr(i + 4, 4, line, curses.color_pair(color))

        # 提示
        self.stdscr.addstr(h - 2, 2, "按任意键继续...", curses.A_DIM)

        self.stdscr.refresh()
        self.stdscr.getch()

    def wait_any_key(self, message="\n按任意键返回菜单..."):
        """等待用户按任意键(在非curses模式下使用)"""
        print(message)
        import sys, tty, termios
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    def show_menu(self, title, items, selected=0, show_numbers=True, show_logo=True):
        """显示菜单并返回选择

        Args:
            title: 菜单标题
            items: 菜单项列表 ["选项1", "选项2", ...]
            selected: 初始选中项
            show_numbers: 是否显示序号
            show_logo: 是否显示 ASCII art logo

        Returns:
            选中的索引，或 -1 表示取消
        """
        current = selected

        while True:
            self.stdscr.clear()
            h, w = self.stdscr.getmaxyx()

            current_y = 1
# 显示 ASCII art logo（仅主菜单）
            if show_logo:
                logo_lines = [
                    ("   .~~.   .~~.", curses.color_pair(2)),
                    ("  '. \\ ' ' / .'", curses.color_pair(2)),
                    ("   .~ .~~~..~.          __  ___                     _", curses.color_pair(4)),
                    ("  : .~.'~'.~. :        /  |/  /__  __ _____ ____   (_)", curses.color_pair(4)),
                    (" ~ (   ) (   ) ~      / /|_/ // / / // ___// __ \\ / /", curses.color_pair(4)),
                    ("( : '~'.~.'~' : )    / /  / // /_/ /(__  )/ /_/ // /", curses.color_pair(4)),
                    (" ~ .~ (   ) ~. ~    /_/  /_/ \\__,_//____// .___//_/", curses.color_pair(4)),
                    ("  (  : '~' :  )                         /_/", curses.color_pair(4)),
                    ("   '~ .~~~. ~'      Created by PuterJam", curses.color_pair(4)),
                    ("       '~'", curses.color_pair(4)),
                ]

                try:
                    for line, color in logo_lines:
                        if current_y < h - 2:
                            # 居中显示
                            x = 2
                            self.stdscr.addstr(current_y, x, line, color)
                            current_y += 1
                except curses.error:
                    pass

                current_y += 1  # 额外空行
                
            # 显示标题
            self.stdscr.addstr(current_y, 2, title,
                             curses.color_pair(1) | curses.A_BOLD)
            current_y += 2

            # 显示菜单项
            start_y = current_y + 1
            item_positions = [None] * len(items)
            y = start_y
            for idx, item in enumerate(items):
                is_last_item = idx == len(items) - 1
                if is_last_item and show_numbers and len(items) > 1:
                    # 为 0 选项单独留空行
                    y += 1

                if y >= h - 2:
                    break

                item_positions[idx] = y

                # 添加序号
                if show_numbers:
                    number = f"{idx + 1}. " if idx < len(items) - 1 else "0. "
                else:
                    number = ""

                if idx == current:
                    # 高亮选中项
                    self.stdscr.addstr(y, 4, f" {number}{item} ",
                                     curses.color_pair(6) | curses.A_BOLD)
                else:
                    self.stdscr.addstr(y, 4, f"  {number}{item}  ")

                y += 1

            # 显示提示
            if show_numbers:
                hint = "↑↓ 方向键 | 数字快选 | Enter 确认 | q 退出 | r 快速重启"
            else:
                hint = "↑↓ 方向键 | Enter 确认 | q 退出 | r 快速重启"
            self.stdscr.addstr(h - 2, 2, hint, curses.A_DIM)

            self.stdscr.refresh()

            # 获取输入
            try:
                key = self.stdscr.getch()

                if key == curses.KEY_UP and current > 0:
                    current -= 1
                elif key == curses.KEY_DOWN and current < len(items) - 1:
                    current += 1
                elif key in [curses.KEY_ENTER, ord('\n'), ord('\r')]:
                    return current
                elif key == ord('q') or key == 27:  # q 或 ESC
                    return -1
                elif show_numbers and ord('0') <= key <= ord('9'):
                    # 数字快速选择
                    num = key - ord('0')
                    if num == 0:
                        # 0 对应最后一项
                        return len(items) - 1
                    elif 1 <= num < len(items):
                        return num - 1
                elif key in (ord('r'), ord('R')):
                    self.control_service("restart")
                elif key == curses.KEY_MOUSE:
                    # 处理鼠标事件
                    try:
                        _, mx, my, _, _ = curses.getmouse()
                        # 检查点击是否在菜单项上
                        for idx, item_y in enumerate(item_positions):
                            if item_y is not None and my == item_y and 4 <= mx < w - 4:
                                return idx
                    except:
                        pass
            except KeyboardInterrupt:
                return -1

    def select_display_driver(self):
        """选择显示驱动"""
        config = self.load_json(self.muspi_config_path)
        if not config:
            self.show_message("错误", "无法读取配置文件", 4)
            return

        current_driver = config.get("display", {}).get("driver", "unknown")
        drivers = config.get("drivers", {})

        if not drivers:
            self.show_message("错误", "配置文件中没有可用的驱动", 4)
            return

        # 构建菜单项
        driver_list = list(drivers.keys())
        items = []
        for driver_name in driver_list:
            driver_info = drivers[driver_name]
            driver_type = driver_info.get("driver", "unknown")
            width = driver_info.get("width", 0)
            height = driver_info.get("height", 0)
            marker = " (当前)" if driver_name == current_driver else ""
            items.append(f"{driver_name} - {driver_type} ({width}x{height}){marker}")

        items.append("返回主菜单")

        # 显示菜单
        choice = self.show_menu("显示驱动设置", items)

        if choice == -1 or choice == len(items) - 1:
            return

        selected_driver = driver_list[choice]

        # 更新配置
        if selected_driver == current_driver:
            self.show_message("提示", f"已经在使用 {selected_driver}，无需更改", 3)
            return

        config["display"]["driver"] = selected_driver
        if self.save_json(self.muspi_config_path, config):
            self.show_message("成功",
                            f"✓ 成功更新显示驱动为: {selected_driver}\n\n提示: 请重启 Muspi 服务以使更改生效",
                            2)
        else:
            self.show_message("错误", "保存配置文件失败", 4)

    def manage_plugins(self):
        """管理插件开关"""
        config = self.load_json(self.plugins_config_path)
        if not config:
            self.show_message("错误", "无法读取配置文件，请先启动一次 Muspi", 4)
            return

        plugins = config.get("plugins", [])
        if not plugins:
            self.show_message("错误", "配置文件中没有可用的插件", 4)
            return

        current = 0
        while True:
            self.stdscr.clear()
            h, w = self.stdscr.getmaxyx()

            # 显示标题
            title = f"插件管理 - {self.plugins_config_path}"
            self.stdscr.addstr(1, 2, title,
                             curses.color_pair(1) | curses.A_BOLD)

            # 显示插件列表
            start_y = 4
            # 计算最大显示名称长度（中文按2个字符宽度计算）
            max_display_width = 0
            for plugin in plugins:
                name = plugin.get("name", "unknown")
                display_name = plugin.get("description", name)
                # 计算显示宽度（中文字符占2个位置）
                width = sum(2 if ord(c) > 127 else 1 for c in display_name)
                max_display_width = max(max_display_width, width)

            # 设置固定宽度（至少20个字符位置）
            fixed_width = max(20, max_display_width)

            for idx, plugin in enumerate(plugins):
                y = start_y + idx
                if y >= h - 6:
                    break

                name = plugin.get("name", "unknown")
                # 优先显示 description，如果没有则显示 name
                display_name = plugin.get("description", name)
                enabled = plugin.get("enabled", False)
                auto_hide = plugin.get("auto_hide", False)

                # 计算当前名称的显示宽度
                current_width = sum(2 if ord(c) > 127 else 1 for c in display_name)
                # 计算需要填充的空格数
                padding = fixed_width - current_width
                padded_name = display_name + " " * padding

                # 状态用颜色区分
                status_color = curses.color_pair(2) if enabled else curses.color_pair(4)
                status = "[启用]" if enabled else "[禁用]"
                auto_hide_text = " (auto_hide)" if auto_hide else ""

                number = f"{idx + 1}. "

                try:
                    if idx == current:
                        # 高亮选中项
                        self.stdscr.addstr(y, 4, f" {number}{padded_name} ",
                                         curses.color_pair(6) | curses.A_BOLD)
                        self.stdscr.addstr(f"{status}", status_color | curses.A_BOLD)
                        self.stdscr.addstr(f"{auto_hide_text} ", curses.color_pair(6) | curses.A_BOLD)
                    else:
                        self.stdscr.addstr(y, 4, f"  {number}{padded_name} ")
                        self.stdscr.addstr(f"{status}", status_color)
                        self.stdscr.addstr(f"{auto_hide_text}  ")
                except curses.error:
                    # 如果写入失败（比如超出屏幕范围），跳过
                    pass

            # 显示操作选项
            sep_y = start_y + len(plugins)
            self.stdscr.addstr(sep_y + 1, 4, f"  0. 返回主菜单  ")

            # 显示提示
            hint = "↑↓ 方向键 | 数字快选 | Enter 切换 | q 退出 | r 快速重启"
            self.stdscr.addstr(h - 2, 2, hint, curses.A_DIM)

            self.stdscr.refresh()

            # 获取输入
            try:
                key = self.stdscr.getch()

                if key == curses.KEY_UP and current > 0:
                    current -= 1
                elif key == curses.KEY_DOWN and current < len(plugins) - 1:
                    current += 1
                elif key in [curses.KEY_ENTER, ord('\n'), ord('\r'), ord(' ')]:
                    # Enter 或空格切换选中插件的状态
                    if current < len(plugins):
                        plugin = plugins[current]
                        plugin["enabled"] = not plugin["enabled"]
                        self.save_json(self.plugins_config_path, config)
                        # 继续显示，不退出
                elif key == ord('q') or key == 27:  # q 或 ESC
                    break
                elif ord('0') <= key <= ord('9'):
                    # 数字快速选择
                    num = key - ord('0')
                    if num == 0:
                        # 0 返回
                        break
                    elif 1 <= num <= len(plugins):
                        # 直接切换对应插件
                        plugin = plugins[num - 1]
                        plugin["enabled"] = not plugin["enabled"]
                        self.save_json(self.plugins_config_path, config)
                        current = num - 1
                elif key in (ord('r'), ord('R')):
                    self.control_service("restart")
                elif key == curses.KEY_MOUSE:
                    # 处理鼠标事件
                    try:
                        _, mx, my, _, _ = curses.getmouse()
                        # 检查点击是否在插件项上
                        for idx in range(len(plugins)):
                            item_y = start_y + idx
                            if my == item_y and 4 <= mx < w - 4:
                                plugin = plugins[idx]
                                plugin["enabled"] = not plugin["enabled"]
                                self.save_json(self.plugins_config_path, config)
                                current = idx
                                break
                        # 检查点击是否在"返回主菜单"上
                        exit_y = sep_y + 1
                        if my == exit_y and 4 <= mx < w - 4:
                            break
                    except:
                        pass
            except KeyboardInterrupt:
                break

    def _run_bluetoothctl(self, *args):
        """执行 bluetoothctl 命令并返回结果"""
        try:
            return subprocess.run(
                ["bluetoothctl", *args],
                capture_output=True,
                text=True
            )
        except FileNotFoundError:
            self.show_message("错误", "bluetoothctl 未安装，请先安装 bluez-tools", 4)
        except Exception as e:
            self.show_message("错误", f"执行 bluetoothctl 失败:\n{e}", 4)
        return None

    def _parse_bluetooth_devices(self, text):
        devices = {}
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            match = re.search(r"Device\s+([0-9A-Fa-f:]{17})\s+(.+)$", line)
            if not match:
                continue

            mac = match.group(1).upper()
            name = match.group(2).strip() or mac
            devices[mac] = {"mac": mac, "name": name}

        return list(devices.values())

    def scan_bluetooth_devices(self, timeout=30):
        """扫描附近蓝牙设备 - 使用非交互模式(简化可靠版)"""
        # 先获取已有设备列表作为基准
        existing_result = subprocess.run(
            ["bluetoothctl", "devices"],
            capture_output=True,
            text=True,
            timeout=2
        )
        existing_macs = set()
        for line in existing_result.stdout.splitlines():
            parts = line.split(maxsplit=2)
            if len(parts) >= 2 and parts[0] == "Device":
                existing_macs.add(parts[1].upper())

        # 调用扫描，但只显示新发现的设备
        return self.scan_bluetooth_devices_simple(timeout, existing_macs)

    def scan_bluetooth_devices_simple(self, timeout=30, existing_macs=None):
        """简化版蓝牙扫描 - 使用非交互模式"""
        # 设置非阻塞输入
        self.stdscr.nodelay(True)

        # 用于存储发现的设备
        devices = {}
        if existing_macs is None:
            existing_macs = set()

        # 创建日志文件
        log_file_path = self.base_path / "bluetooth_scan.log"
        log_file = open(log_file_path, 'w', encoding='utf-8')
        log_file.write(f"=== 蓝牙扫描日志 (简化版) {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n\n")
        log_file.write(f"扫描前已有设备数: {len(existing_macs)}\n")
        log_file.write(f"已有设备: {existing_macs}\n\n")

        # 启动后台扫描进程
        scan_proc = subprocess.Popen(
            ["bluetoothctl", "--", "scan", "on"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        log_file.write(">>> 启动后台扫描: bluetoothctl scan on\n")
        log_file.flush()

        # 启动监控进程获取设备列表
        start_time = time.time()
        user_stopped = False
        poll_count = 0

        try:
            while True:
                # 检查用户输入
                try:
                    key = self.stdscr.getch()
                    if key in (ord('q'), ord('Q'), 27):
                        user_stopped = True
                        log_file.write(f"\n>>> 用户停止扫描 (耗时: {time.time() - start_time:.1f}秒)\n")
                        log_file.flush()
                        break
                except:
                    pass

                # 获取当前设备列表
                poll_count += 1
                log_file.write(f"\n--- 第 {poll_count} 次轮询 (时间: {time.time() - start_time:.1f}秒) ---\n")
                log_file.flush()

                result = subprocess.run(
                    ["bluetoothctl", "devices"],
                    capture_output=True,
                    text=True,
                    timeout=2
                )

                log_file.write(f"[STDOUT]\n{result.stdout}\n")
                log_file.flush()

                # 解析设备
                new_devices = {}
                for line in result.stdout.splitlines():
                    log_file.write(f"[PARSE] 解析行: {line}\n")

                    # 格式: Device MAC_ADDRESS Name
                    parts = line.split(maxsplit=2)
                    if len(parts) >= 2 and parts[0] == "Device":
                        mac = parts[1].upper()
                        name = parts[2] if len(parts) > 2 else None

                        log_file.write(f"[INFO] MAC={mac}, Name={name}\n")

                        # 检查是否是有效名称
                        if name:
                            # 排除 MAC 格式的名称
                            mac_pattern = re.match(r'^[0-9A-Fa-f]{2}[-:][0-9A-Fa-f]{2}[-:][0-9A-Fa-f]{2}[-:][0-9A-Fa-f]{2}[-:][0-9A-Fa-f]{2}[-:][0-9A-Fa-f]{2}$', name)
                            if not mac_pattern:
                                # 判断设备状态
                                if mac in existing_macs:
                                    # 已配对的设备
                                    status = "PAIRED"
                                    log_file.write(f"[INFO] 已配对设备: {name} ({mac})\n")
                                else:
                                    # 新发现的设备
                                    status = "NEW" if mac not in devices else "CHG"
                                    log_file.write(f"[ACTION] 新发现设备: {name} ({mac}) - {status}\n")

                                new_devices[mac] = {"name": name, "status": status, "mac": mac}
                            else:
                                log_file.write(f"[SKIP] MAC格式名称: {name}\n")
                        else:
                            log_file.write(f"[SKIP] 无名称设备: {mac}\n")

                    log_file.flush()

                # 更新设备列表
                devices.update(new_devices)
                log_file.write(f"[SUMMARY] 当前设备总数: {len(devices)}\n")
                log_file.flush()

                # 实时显示
                self._display_scanning_ui(devices, user_stopped)

                # 超时检查
                if timeout > 0 and time.time() - start_time >= timeout:
                    log_file.write(f"\n>>> 扫描超时 (timeout={timeout}秒)\n")
                    log_file.flush()
                    break

                time.sleep(0.5)

        finally:
            # 停止扫描
            log_file.write("\n>>> 停止扫描: bluetoothctl scan off\n")
            log_file.flush()
            scan_proc.terminate()
            subprocess.run(["bluetoothctl", "--", "scan", "off"], capture_output=True)
            self.stdscr.nodelay(False)

            # 记录最终结果
            log_file.write(f"\n=== 扫描结束,共发现 {len(devices)} 个设备 ===\n")
            for mac, info in devices.items():
                log_file.write(f"  - {info['name']} ({mac}) [{info['status']}]\n")
            log_file.close()

        return list(devices.values())

    def scan_bluetooth_devices_raw(self, timeout=30):
        """扫描附近蓝牙设备 - 使用原始 bluetoothctl 输出(备用方案)"""
        # 设置非阻塞输入
        self.stdscr.nodelay(True)

        # 用于存储发现的设备 {mac: {"name": str, "status": str}}
        devices = {}

        # 创建日志文件
        log_file_path = self.base_path / "bluetooth_scan.log"
        log_file = open(log_file_path, 'w', encoding='utf-8')
        log_file.write(f"=== 蓝牙扫描日志 {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n\n")

        try:
            # 启动 bluetoothctl 进程
            proc = subprocess.Popen(
                ["bluetoothctl"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )

            # 开始扫描
            proc.stdin.write("scan on\n")
            proc.stdin.flush()
            log_file.write(">>> 发送命令: scan on\n")
            log_file.flush()

            start_time = time.time()
            user_stopped = False

            # 实时读取和显示
            while True:
                # 检查用户输入
                try:
                    key = self.stdscr.getch()
                    if key in (ord('q'), ord('Q'), 27):  # q 或 ESC
                        user_stopped = True
                        log_file.write(f"\n>>> 用户停止扫描 (耗时: {time.time() - start_time:.1f}秒)\n")
                        log_file.flush()
                        break
                except:
                    pass

                # 使用 select 检查是否有输出可读
                readable, _, _ = select.select([proc.stdout], [], [], 0.1)

                if readable:
                    line = proc.stdout.readline()
                    if not line:
                        break

                    # 记录原始输出
                    log_file.write(f"[RAW] {line}")
                    log_file.flush()

                    # 移除 ANSI 转义序列（颜色代码等）
                    # 更精确地移除转义序列，避免误删 [NEW]、[CHG]、[DEL]
                    clean_line = re.sub(r'\x1b\[[0-9;]*m', '', line)  # 移除颜色代码 ESC[...m
                    clean_line = re.sub(r'\x1b\[[0-9;]*[A-Z]', '', clean_line)  # 移除其他 ESC 序列
                    clean_line = re.sub(r'\[[0-9]+[A-Z]', '', clean_line)  # 移除 [22P 这样的序列
                    clean_line = re.sub(r'\[K', '', clean_line)  # 移除清屏代码
                    clean_line = re.sub(r'\[bluetooth\]#', '', clean_line)  # 移除提示符
                    clean_line = clean_line.strip()  # 移除首尾空白

                    log_file.write(f"[CLEAN] {clean_line}\n")
                    log_file.flush()

                    # 跳过空行
                    if not clean_line:
                        continue

                    # 解析蓝牙设备信息
                    # 格式示例: [NEW] Device 54:4F:79:05:89:D1 AAAA舜子
                    #          [CHG] Device 14:D1:9E:30:5B:14 Aeolus
                    #          [DEL] Device AA:BB:CC:DD:EE:FF
                    match = re.search(r"\[(NEW|CHG|DEL)\]\s+Device\s+([0-9A-Fa-f:]{17})(?:\s+(.+))?", clean_line)

                    # 调试:记录是否匹配
                    if "[NEW]" in clean_line or "[CHG]" in clean_line or "[DEL]" in clean_line:
                        if "Device" in clean_line:
                            if match:
                                log_file.write(f"[DEBUG] 正则匹配成功!\n")
                            else:
                                log_file.write(f"[DEBUG] 正则匹配失败! 行内容: {repr(clean_line)}\n")
                            log_file.flush()

                    if match:
                        status = match.group(1)
                        mac = match.group(2).upper()
                        name = match.group(3).strip() if match.group(3) else None

                        log_file.write(f"[PARSE] 状态={status}, MAC={mac}, 名称={name}\n")
                        log_file.flush()

                        # 检查是否是有效的设备名称
                        # 排除：1) 无名称  2) 名称就是 MAC 地址的变体
                        is_valid_name = False
                        if name:
                            # 检查名称是否只是 MAC 地址的另一种格式（用-分隔）
                            mac_pattern = re.match(r'^[0-9A-Fa-f]{2}[-:][0-9A-Fa-f]{2}[-:][0-9A-Fa-f]{2}[-:][0-9A-Fa-f]{2}[-:][0-9A-Fa-f]{2}[-:][0-9A-Fa-f]{2}$', name)
                            if not mac_pattern:
                                is_valid_name = True

                        # 只处理有有效名称的设备
                        if is_valid_name:
                            if status == "DEL":
                                # 删除设备
                                devices.pop(mac, None)
                                log_file.write(f"[ACTION] 删除设备: {mac}\n")
                            else:
                                # 添加或更新设备
                                devices[mac] = {"name": name, "status": status, "mac": mac}
                                log_file.write(f"[ACTION] 添加/更新设备: {name} ({mac})\n")
                            log_file.flush()
                        else:
                            if name:
                                log_file.write(f"[SKIP] 跳过MAC格式名称设备: {name} ({mac})\n")
                            else:
                                log_file.write(f"[SKIP] 跳过无名称设备: {mac}\n")
                            log_file.flush()

                    # 实时显示界面
                    self._display_scanning_ui(devices, user_stopped)

                # 超时检查 (如果设置了 timeout)
                if timeout > 0 and time.time() - start_time >= timeout:
                    log_file.write(f"\n>>> 扫描超时 (timeout={timeout}秒)\n")
                    log_file.flush()
                    break

                # 短暂休眠避免 CPU 占用过高
                time.sleep(0.05)

        except Exception as e:
            log_file.write(f"\n!!! 异常: {e}\n")
            log_file.flush()

        finally:
            # 停止扫描
            log_file.write("\n>>> 发送命令: scan off\n")
            log_file.flush()
            self._run_bluetoothctl("scan", "off")

            # 退出 bluetoothctl
            try:
                proc.stdin.write("quit\n")
                proc.stdin.flush()
            except:
                pass

            proc.terminate()
            proc.wait(timeout=2)

            # 恢复阻塞输入
            self.stdscr.nodelay(False)

            # 记录最终结果
            log_file.write(f"\n=== 扫描结束,共发现 {len(devices)} 个设备 ===\n")
            for mac, info in devices.items():
                log_file.write(f"  - {info['name']} ({mac}) [{info['status']}]\n")
            log_file.close()

        # 返回设备列表
        return list(devices.values())

    def _display_scanning_ui(self, devices, user_stopped=False):
        """显示扫描界面"""
        try:
            self.stdscr.clear()
            h, w = self.stdscr.getmaxyx()

            # 标题
            if user_stopped:
                title = "蓝牙设备扫描 - 已停止"
                color = curses.color_pair(3)
            else:
                title = "蓝牙设备扫描中..."
                color = curses.color_pair(5) | curses.A_BOLD

            self.stdscr.addstr(1, 2, title, color)
            self.stdscr.addstr(2, 2, "按 q 或 ESC 停止扫描", curses.A_DIM)
            self.stdscr.addstr(3, 2, "-" * (w - 4))

            # 显示设备列表
            y = 5
            device_count = 0

            if devices:
                for mac, info in sorted(devices.items(), key=lambda x: x[1]["name"]):
                    if y >= h - 3:
                        break

                    name = info["name"]
                    status = info["status"]

                    # 显示设备信息
                    # self.stdscr.addstr(y, 4, status_text, status_color | curses.A_BOLD)
                    self.stdscr.addstr(y, 4, f"{name}", curses.A_BOLD)
                    self.stdscr.addstr(y, 4 + len(name) + 2, f"({mac})", curses.A_DIM)

                    y += 1
                    device_count += 1
            else:
                self.stdscr.addstr(y, 4, "暂无设备...", curses.A_DIM)

            # 底部状态栏
            status_text = f"已发现 {device_count} 个设备"
            self.stdscr.addstr(h - 2, 2, status_text, curses.color_pair(5))

            self.stdscr.refresh()

        except curses.error:
            # 忽略屏幕绘制错误
            pass

    def get_paired_bluetooth_devices(self):
        result = self._run_bluetoothctl("devices", "Paired")
        if not result:
            return None
        devices = self._parse_bluetooth_devices(f"{result.stdout}\n{result.stderr}")
        if devices:
            return devices
        if result.returncode != 0:
            self.show_message("错误", f"读取已配对设备失败:\n{result.stderr or result.stdout}", 4)
            return None
        return []

    def select_bluetooth_device(self, devices, title):
        if not devices:
            return None

        items = []
        for device in devices:
            name = device.get("name") or "未知设备"
            items.append(f"{name} ({device['mac']})")
        items.append("返回上一级")

        choice = self.show_menu(title, items, show_logo=False)
        if choice == -1 or choice == len(items) - 1:
            return None
        return devices[choice]

    def pair_and_connect_device(self, device):
        mac = device.get("mac")
        name = device.get("name") or mac

        agent_script = self.base_path / "until/device/bluetooth_agent.py"
        if not agent_script.exists():
            self.show_message("错误",
                              f"未找到 until/device/bluetooth_agent.py，无法配对 {name}。",
                              4)
            return False

        try:
            result = subprocess.run(
                [sys.executable, str(agent_script), mac],
                capture_output=True,
                text=True,
                cwd=self.base_path
            )
        except Exception as e:
            self.show_message("错误",
                              f"执行 until/device/bluetooth_agent.py 失败:\n{e}",
                              4)
            return False

        stdout = (result.stdout or "").strip()
        stderr = (result.stderr or "").strip()
        combined_output = "\n".join(filter(None, [stdout, stderr]))

        if result.returncode == 0:
            message = f"✓ 已通过 Agent 配对 {name}\nMAC: {mac}"
            if combined_output:
                message += f"\n\n{combined_output}"
            self.show_message("成功", message, 2)
            return True

        self.show_message("蓝牙操作失败",
                          f"使用 until/device/bluetooth_agent.py 配对 {name} 失败:\n{combined_output or '未知错误'}",
                          4)
        return False

    def connect_paired_device(self, device):
        mac = device.get("mac")
        name = device.get("name") or mac
        result = self._run_bluetoothctl("connect", mac)
        if not result:
            return

        if result.returncode == 0:
            self.show_message("成功", f"✓ 已连接 {name}", 2)
        else:
            self.show_message("蓝牙操作失败",
                              f"连接 {name} 失败:\n{result.stderr or result.stdout}",
                              4)

    def remove_paired_device(self):
        devices = self.get_paired_bluetooth_devices()
        if devices is None:
            return
        if not devices:
            self.show_message("提示", "当前没有已配对的设备可以移除", 3)
            return

        device = self.select_bluetooth_device(devices, "选择要取消配对的设备")
        if not device:
            return

        mac = device.get("mac")
        name = device.get("name") or mac
        result = self._run_bluetoothctl("remove", mac)
        if not result:
            return

        if result.returncode == 0:
            self.show_message("成功", f"✓ 已移除 {name}\nMAC: {mac}", 2)
        else:
            self.show_message("蓝牙操作失败",
                              f"移除 {name} 失败:\n{result.stderr or result.stdout}",
                              4)

    def scan_and_connect_menu(self):
        devices = self.scan_bluetooth_devices()
        if devices is None:
            return
        if not devices:
            self.show_message("提示", "未发现可用的蓝牙设备", 3)
            return

        device = self.select_bluetooth_device(devices, "附近蓝牙设备")
        if device:
            self.pair_and_connect_device(device)

    def paired_devices_menu(self):
        devices = self.get_paired_bluetooth_devices()
        if devices is None:
            return
        if not devices:
            self.show_message("提示", "当前没有已配对的设备", 3)
            return

        device = self.select_bluetooth_device(devices, "已配对设备")
        if device:
            self.connect_paired_device(device)

    def bluetooth_menu(self):
        while True:
            items = [
                "扫描附近设备 (配对并连接)",
                "查看已配对设备 (重新连接)",
                "取消配对 (移除设备)",
                "返回主菜单"
            ]

            choice = self.show_menu("蓝牙配置", items, show_logo=False)

            if choice == -1 or choice == 3:
                break
            elif choice == 0:
                self.scan_and_connect_menu()
            elif choice == 1:
                self.paired_devices_menu()
            elif choice == 2:
                self.remove_paired_device()

    def install_service(self):
        """安装 Muspi 服务"""
        if not self.service_file.exists():
            self.show_message("错误", f"服务文件 {self.service_file} 不存在", 4)
            return False

        try:
            # 检查服务是否已安装
            if self.is_service_installed():
                self.show_message("提示", "服务已安装，将重新安装", 3)

            # 复制服务文件到 systemd 目录
            result = subprocess.run(
                ["sudo", "cp", str(self.service_file), f"/etc/systemd/system/{self.service_name}"],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                self.show_message("错误", f"复制服务文件失败:\n{result.stderr}", 4)
                return False

            # 重新加载 systemd
            result = subprocess.run(
                ["sudo", "systemctl", "daemon-reload"],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                self.show_message("错误", f"重新加载 systemd 失败:\n{result.stderr}", 4)
                return False

            # 启用服务
            result = subprocess.run(
                ["sudo", "systemctl", "enable", self.service_name],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                self.show_message("错误", f"启用服务失败:\n{result.stderr}", 4)
                return False

            self.show_message("成功",
                            "✓ Muspi 服务安装成功\n\n提示: 使用 '启动服务' 选项来启动服务",
                            2)
            return True

        except Exception as e:
            self.show_message("错误", f"安装服务时发生错误:\n{e}", 4)
            return False

    def control_service(self, action):
        """控制服务（启动/停止/重启）"""
        action_map = {
            "start": "启动",
            "stop": "停止",
            "restart": "重启"
        }

        action_name = action_map.get(action, action)

        try:
            result = subprocess.run(
                ["sudo", "systemctl", action, self.service_name],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                self.show_message("成功", f"✓ 服务{action_name}成功", 2)
                return True
            else:
                self.show_message("错误", f"服务{action_name}失败:\n{result.stderr}", 4)
                return False

        except Exception as e:
            self.show_message("错误", f"{action_name}服务时发生错误:\n{e}", 4)
            return False

    def show_service_status(self):
        """显示服务状态"""
        try:
            result = subprocess.run(
                ["systemctl", "status", self.service_name],
                capture_output=True,
                text=True
            )

            # 提取关键信息
            status_lines = result.stdout.split('\n')
            display_lines = []

            for line in status_lines[:15]:  # 只显示前15行
                display_lines.append(line)

            if "could not be found" in result.stderr:
                self.show_message("服务状态", "服务未安装", 3)
            else:
                self.show_message("服务状态", '\n'.join(display_lines), 0)

        except Exception as e:
            self.show_message("错误", f"查看服务状态时发生错误:\n{e}", 4)

    def uninstall_service(self):
        """卸载 Muspi 服务"""
        if not self.is_service_installed():
            self.show_message("提示", "服务未安装", 3)
            return False

        # 确认对话框
        self.stdscr.clear()
        h, w = self.stdscr.getmaxyx()

        self.stdscr.addstr(h // 2 - 2, 4, "警告: 即将卸载 Muspi 服务",
                          curses.color_pair(3) | curses.A_BOLD)
        self.stdscr.addstr(h // 2, 4, "确认卸载? (y/N): ", curses.color_pair(3))
        self.stdscr.refresh()

        curses.echo()
        curses.curs_set(1)
        confirm = self.stdscr.getstr(h // 2, 23, 10).decode('utf-8').strip().lower()
        curses.noecho()
        curses.curs_set(0)

        if confirm != 'y':
            self.show_message("提示", "操作已取消", 3)
            return False

        try:
            # 停止服务
            subprocess.run(
                ["sudo", "systemctl", "stop", self.service_name],
                capture_output=True,
                text=True
            )

            # 禁用服务
            result = subprocess.run(
                ["sudo", "systemctl", "disable", self.service_name],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                self.show_message("错误", f"禁用服务失败:\n{result.stderr}", 4)
                return False

            # 删除服务文件
            result = subprocess.run(
                ["sudo", "rm", f"/etc/systemd/system/{self.service_name}"],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                self.show_message("错误", f"删除服务文件失败:\n{result.stderr}", 4)
                return False

            # 重新加载 systemd
            result = subprocess.run(
                ["sudo", "systemctl", "daemon-reload"],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                self.show_message("错误", f"重新加载 systemd 失败:\n{result.stderr}", 4)
                return False

            self.show_message("成功", "✓ Muspi 服务卸载成功", 2)
            return True

        except Exception as e:
            self.show_message("错误", f"卸载服务时发生错误:\n{e}", 4)
            return False

    def show_service_logs(self):
        """实时显示服务日志"""
        # 退出 curses 模式，进入终端模式显示日志
        curses.endwin()

        try:
            print("\n" + "=" * 60)
            print("Muspi 服务日志 (按 Ctrl+C 退出)")
            print("=" * 60 + "\n")

            # 使用 journalctl 实时查看日志
            subprocess.run(
                ["journalctl", "-u", self.service_name, "-f", "--output=cat"],
                check=False
            )
        except KeyboardInterrupt:
            print("\n\n日志查看已停止")
        except Exception as e:
            print(f"\n查看日志时出错: {e}")

        # 提示用户按键继续
        self.wait_any_key()

        # 重新初始化 curses
        self.stdscr = curses.initscr()
        curses.noecho()
        curses.cbreak()
        self.stdscr.keypad(True)
        curses.curs_set(0)

    def restart_shairport_sync(self):
        """重启 shairport-sync 服务"""
        try:
            result = subprocess.run(
                ["sudo", "systemctl", "restart", "shairport-sync"],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                self.show_message("成功", "✓ shairport-sync 服务重启成功", 2)
                return True
            else:
                self.show_message("错误", f"shairport-sync 服务重启失败:\n{result.stderr}", 4)
                return False

        except Exception as e:
            self.show_message("错误", f"重启 shairport-sync 服务时发生错误:\n{e}", 4)
            return False

    def show_shairport_sync_logs(self):
        """实时显示 shairport-sync 服务日志"""
        # 退出 curses 模式，进入终端模式显示日志
        curses.endwin()

        try:
            print("\n" + "=" * 60)
            print("shairport-sync 服务日志 (按 Ctrl+C 退出)")
            print("=" * 60 + "\n")

            # 使用 journalctl 实时查看日志
            subprocess.run(
                ["journalctl", "-u", "shairport-sync", "-f", "--output=cat"],
                check=False
            )
        except KeyboardInterrupt:
            print("\n\n日志查看已停止")
        except Exception as e:
            print(f"\n查看日志时出错: {e}")

        # 提示用户按键继续
        self.wait_any_key()

        # 重新初始化 curses
        self.stdscr = curses.initscr()
        curses.noecho()
        curses.cbreak()
        self.stdscr.keypad(True)
        curses.curs_set(0)

    def other_tools_menu(self):
        """其他工具菜单"""
        while True:
            items = [
                "重启 shairport-sync 服务",
                "查看 shairport-sync 日志",
                "返回主菜单"
            ]

            choice = self.show_menu("其他工具", items, show_logo=False)

            if choice == -1 or choice == 2:
                break
            elif choice == 0:
                self.restart_shairport_sync()
            elif choice == 1:
                self.show_shairport_sync_logs()

    def service_control_menu(self):
        """服务控制菜单"""
        installed = self.is_service_installed()

        while True:
            if installed:
                items = [
                    "启动服务",
                    "停止服务",
                    "重启服务",
                    "查看插件日志",
                    "卸载服务",
                    "返回主菜单"
                ]
                title = "Muspi 服务管理 [已安装]"
            else:
                items = [
                    "安装 Muspi 服务",
                    "返回主菜单"
                ]
                title = "Muspi 服务管理 [未安装]"

            choice = self.show_menu(title, items)

            if choice == -1 or (installed and choice == 5) or (not installed and choice == 1):
                break

            # 执行操作
            if not installed and choice == 0:
                if self.install_service():
                    installed = self.is_service_installed()
            elif installed:
                if choice == 0:
                    self.control_service("start")
                elif choice == 1:
                    self.control_service("stop")
                elif choice == 2:
                    self.control_service("restart")
                # elif choice == 3:
                #     self.show_service_status()
                elif choice == 3:
                    self.show_service_logs()
                elif choice == 4:
                    if self.uninstall_service():
                        installed = self.is_service_installed()

    def run(self):
        """运行主程序"""
        while True:
            items = [
                "设置显示驱动",
                "插件管理",
                "Muspi 服务管理",
                "蓝牙设备配置",
                "其他",
                "退出"
            ]

            choice = self.show_menu("Muspi 配置中心", items)

            if choice == -1 or choice == 5:
                break
            elif choice == 0:
                self.select_display_driver()
            elif choice == 1:
                self.manage_plugins()
            elif choice == 2:
                self.service_control_menu()
            elif choice == 3:
                self.bluetooth_menu()
            elif choice == 4:
                self.other_tools_menu()


def main(stdscr):
    """主入口（curses 包装）"""
    manager = ConfigManager(stdscr)
    manager.run()


if __name__ == "__main__":
    # 检查是否在正确的目录
    if not Path("config/muspi.json").exists():
        print("错误: 请在 muspi 项目根目录下运行此脚本")
        sys.exit(1)

    # 检查 TERM 环境变量
    if not os.environ.get('TERM'):
        print("警告: TERM 环境变量未设置，自动设置为 xterm-256color")
        os.environ['TERM'] = 'xterm-256color'

    # 检查 locale 设置
    current_lang = os.environ.get('LANG', '')
    if not current_lang or current_lang == 'C':
        print("警告: LANG 环境变量未正确设置，自动设置为 en_US.UTF-8")
        os.environ['LANG'] = 'en_US.UTF-8'
        os.environ['LC_ALL'] = 'en_US.UTF-8'

    # 运行 curses 应用
    try:
        curses.wrapper(main)
        print("\n感谢使用 Muspi Configuration Manager！\n")
    except KeyboardInterrupt:
        print("\n\n感谢使用 Muspi Configuration Manager！\n")
    except curses.error as e:
        print(f"\n终端错误: {e}")
        print("提示: 请确保在支持 curses 的终端中运行此程序")
        print("建议: 尝试设置环境变量 export TERM=xterm-256color")
        sys.exit(1)
    except Exception as e:
        print(f"\n发生错误: {e}\n")
        import traceback
        traceback.print_exc()
