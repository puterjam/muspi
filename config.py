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
        input("\n按 Enter 键返回菜单...")

        # 重新初始化 curses
        self.stdscr = curses.initscr()
        curses.noecho()
        curses.cbreak()
        self.stdscr.keypad(True)
        curses.curs_set(0)

    def service_control_menu(self):
        """服务控制菜单"""
        installed = self.is_service_installed()

        while True:
            if installed:
                items = [
                    "启动服务",
                    "停止服务",
                    "重启服务",
                    "查看服务状态",
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

            if choice == -1 or (installed and choice == 6) or (not installed and choice == 1):
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
                elif choice == 3:
                    self.show_service_status()
                elif choice == 4:
                    self.show_service_logs()
                elif choice == 5:
                    if self.uninstall_service():
                        installed = self.is_service_installed()

    def run(self):
        """运行主程序"""
        while True:
            items = [
                "设置显示驱动",
                "插件管理",
                "Muspi 服务管理",
                "退出"
            ]

            choice = self.show_menu("Muspi 配置中心", items)

            if choice == -1 or choice == 3:
                break
            elif choice == 0:
                self.select_display_driver()
            elif choice == 1:
                self.manage_plugins()
            elif choice == 2:
                self.service_control_menu()


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
