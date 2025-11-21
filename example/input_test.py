#!/home/pi/workspace/muspi/venv/bin/python
"""
键盘和手柄输入检测测试脚本
实时显示所有输入设备的按键事件
"""

import sys
import time

try:
    from evdev import InputDevice, list_devices, categorize, ecodes
except ImportError:
    print("错误: 未找到 evdev 模块")
    print("请运行以下命令安装:")
    print("  pip install evdev")
    print("或使用虚拟环境:")
    print("  ./venv/bin/pip install evdev")
    sys.exit(1)

def get_key_name(code):
    """获取按键名称"""
    for name, value in ecodes.ecodes.items():
        if value == code:
            return name
    return f"UNKNOWN({code})"

def get_event_type_name(type_code):
    """获取事件类型名称"""
    event_types = {
        ecodes.EV_KEY: "KEY",
        ecodes.EV_REL: "REL",
        ecodes.EV_ABS: "ABS",
        ecodes.EV_MSC: "MSC",
        ecodes.EV_SW: "SW",
        ecodes.EV_LED: "LED",
        ecodes.EV_SND: "SND",
        ecodes.EV_REP: "REP",
        ecodes.EV_FF: "FF",
        ecodes.EV_PWR: "PWR",
        ecodes.EV_FF_STATUS: "FF_STATUS",
        ecodes.EV_SYN: "SYN"
    }
    return event_types.get(type_code, f"TYPE_{type_code}")

def get_value_description(value):
    """获取事件值描述"""
    if value == 0:
        return "RELEASE"
    elif value == 1:
        return "PRESS"
    elif value == 2:
        return "REPEAT"
    else:
        return str(value)

def list_input_devices():
    """列出所有输入设备"""
    devices = []
    print("=" * 80)
    print("检测到的输入设备:")
    print("=" * 80)

    for path in list_devices():
        try:
            device = InputDevice(path)
            devices.append(device)

            # 显示设备信息
            print(f"\n设备 #{len(devices)}:")
            print(f"  路径: {device.path}")
            print(f"  名称: {device.name}")
            print(f"  物理地址: {device.phys}")

            # 显示支持的事件类型
            capabilities = device.capabilities(verbose=True)
            if capabilities:
                print(f"  支持的事件类型:")
                for event_type, codes in capabilities.items():
                    if event_type[0] == 'EV_SYN':
                        continue
                    print(f"    - {event_type[0]}: {len(codes)} 个输入")

        except Exception as e:
            print(f"  错误: 无法打开设备 {path}: {e}")

    print("\n" + "=" * 80)
    print(f"总共找到 {len(devices)} 个输入设备")
    print("=" * 80)
    print()

    return devices

def monitor_inputs(devices):
    """监控所有输入设备的事件"""
    if not devices:
        print("错误: 没有可用的输入设备")
        return

    print("开始监控输入事件... (按 Ctrl+C 退出)")
    print("=" * 80)
    print()

    # 创建设备字典，方便查找
    device_map = {dev.fd: dev for dev in devices}

    try:
        while True:
            # 使用 select 等待任何设备的事件
            from select import select

            r, w, x = select(device_map, [], [], 0.1)

            for fd in r:
                device = device_map[fd]

                # 读取事件
                for event in device.read():
                    # 跳过同步事件
                    if event.type == ecodes.EV_SYN:
                        continue

                    # 格式化输出
                    timestamp = time.strftime("%H:%M:%S", time.localtime(event.sec))
                    device_name = device.name[:30].ljust(30)
                    event_type = get_event_type_name(event.type).ljust(8)

                    if event.type == ecodes.EV_KEY:
                        # 按键事件
                        key_name = get_key_name(event.code).ljust(20)
                        value_desc = get_value_description(event.value).ljust(10)

                        print(f"[{timestamp}] {device_name} | {event_type} | "
                              f"{key_name} | {value_desc} | code={event.code}")

                    elif event.type == ecodes.EV_ABS:
                        # 绝对坐标事件（摇杆、触摸板等）
                        axis_name = get_key_name(event.code).ljust(20)

                        print(f"[{timestamp}] {device_name} | {event_type} | "
                              f"{axis_name} | value={event.value:6d} | code={event.code}")

                    elif event.type == ecodes.EV_REL:
                        # 相对坐标事件（鼠标等）
                        axis_name = get_key_name(event.code).ljust(20)

                        print(f"[{timestamp}] {device_name} | {event_type} | "
                              f"{axis_name} | delta={event.value:6d} | code={event.code}")

                    else:
                        # 其他事件
                        print(f"[{timestamp}] {device_name} | {event_type} | "
                              f"code={event.code:4d} | value={event.value:6d}")

    except KeyboardInterrupt:
        print("\n\n监控已停止")
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()

def main():
    """主函数"""
    print("\n" + "=" * 80)
    print(" " * 20 + "键盘和手柄输入检测工具")
    print("=" * 80)
    print()

    # 列出所有设备
    devices = list_input_devices()

    if not devices:
        print("\n未找到任何输入设备!")
        print("提示: 请确保以 root 权限运行此脚本，或者将用户添加到 input 组")
        print("      sudo usermod -a -G input $USER")
        sys.exit(1)

    # 监控输入
    monitor_inputs(devices)

if __name__ == "__main__":
    main()
