import sys
import time
from pydbus import SystemBus
from gi.repository import GLib

# 替换为你要配对的设备的 MAC 地址
DEVICE_MAC_ADDRESS = "B3:D0:0A:54:2C:F5"
# BlueZ Agent Manager 和 Agent 路径
BLUEZ_SERVICE = "org.bluez"
AGENT_MANAGER_PATH = "/org/bluez"
AGENT_PATH = "/com/muspi/agent" # 你的 Agent 路径

# Agent 接口定义
AGENT_INTERFACE = """
<node>
  <interface name="org.bluez.Agent1">
    <method name="Release"/>
    <method name="RequestPinCode">
      <arg direction="in" type="o"/>
      <arg direction="out" type="s"/>
    </method>
    <method name="DisplayPinCode">
      <arg direction="in" type="o"/>
      <arg direction="in" type="s"/>
    </method>
    <method name="RequestPasskey">
      <arg direction="in" type="o"/>
      <arg direction="out" type="u"/>
    </method>
    <method name="DisplayPasskey">
      <arg direction="in" type="o"/>
      <arg direction="in" type="u"/>
      <arg direction="in" type="q"/>
    </method>
    <method name="RequestConfirmation">
      <arg direction="in" type="o"/>
      <arg direction="in" type="u"/>
    </method>
    <method name="RequestAuthorization">
      <arg direction="in" type="o"/>
    </method>
    <method name="AuthorizeService">
      <arg direction="in" type="o"/>
      <arg direction="in" type="s"/>
    </method>
    <method name="Cancel"/>
  </interface>
</node>
"""

class SimpleAgent:
    """一个简单的 Agent，硬编码了 Pin Code 和 Passkey 确认逻辑"""
    def __init__(self, bus):
        self.bus = bus
        self.loop = GLib.MainLoop()
        
    def path_to_mac(self, path):
        """将 D-Bus 对象路径转换为 MAC 地址"""
        return path.split("/")[-1].replace("dev_", "").replace("_", ":")

    def Release(self):
        print("Agent: Released")

    def RequestPinCode(self, device_path):
        mac = self.path_to_mac(device_path)
        print(f"\nAgent: 收到设备 {mac} 的 Pin Code 请求。")
        # --- 在这里可以实现用户输入逻辑 ---
        # 示例：假设您知道设备需要 Pin Code 1234
        pin = input(f"请输入 {mac} 的 Pin Code (或直接回车使用 0000): ") or "0000"
        return pin

    def RequestPasskey(self, device_path):
        mac = self.path_to_mac(device_path)
        print(f"\nAgent: 收到设备 {mac} 的 Passkey 请求。")
        # --- 在这里可以实现用户输入逻辑 ---
        # 示例：假设您需要用户输入一个 Passkey
        passkey_str = input(f"请输入 {mac} 的 Passkey: ")
        return int(passkey_str)

    def RequestConfirmation(self, device_path, passkey):
        mac = self.path_to_mac(device_path)
        print(f"\nAgent: 设备 {mac} 请求确认 Passkey: {passkey}")
        # --- 默认自动确认 'yes'，或者让用户输入 ---
        confirm = input("请在设备上确认 Passkey 是否显示一致 (yes/no): ").lower().strip()
        if confirm == 'yes':
            print("Agent: 确认成功。")
            return
        raise Exception("Rejected by user")

    def DisplayPinCode(self, device_path, pincode):
        mac = self.path_to_mac(device_path)
        print(f"\nAgent: 设备 {mac} 显示 Pin Code: {pincode}")

    def DisplayPasskey(self, device_path, passkey, entered):
        mac = self.path_to_mac(device_path)
        print(f"\nAgent: 设备 {mac} 显示 Passkey: {passkey}, 已输入: {entered}")

    def RequestAuthorization(self, device_path):
        mac = self.path_to_mac(device_path)
        print(f"\nAgent: 设备 {mac} 请求授权。")
        # --- 默认授权通过 ---
        return

    def AuthorizeService(self, device_path, uuid):
        mac = self.path_to_mac(device_path)
        print(f"\nAgent: 设备 {mac} 请求授权服务 UUID: {uuid}")
        # --- 默认授权通过 ---
        return

    def Cancel(self):
        print("Agent: Cancelled")
        
def find_device_path(bus, adapter_path, mac_address):
    """在 bus 中查找设备的对象路径"""
    candidate_path = adapter_path + "/dev_" + mac_address.replace(":", "_")
    try:
        object_manager = bus.get(BLUEZ_SERVICE, "/")["org.freedesktop.DBus.ObjectManager"]
        managed_objects = object_manager.GetManagedObjects()
    except GLib.Error as e:
        print(f"错误：无法获取 BlueZ 对象列表: {e}")
        return None

    if candidate_path in managed_objects:
        return candidate_path

    for path, interfaces in managed_objects.items():
        if not path.startswith(adapter_path + "/dev_"):
            continue
        device_props = interfaces.get("org.bluez.Device1", {})
        address = device_props.get("Address")
        if address and address.upper() == mac_address.upper():
            return path

    return None


def pair_device(mac_address):
    """查找设备对象并调用 Pair 方法"""
    bus = SystemBus()
    
    # 查找 Adapter
    # 通常适配器路径是 /org/bluez/hci0
    adapter_path = "/org/bluez/hci0" 
    try:
        adapter = bus.get(BLUEZ_SERVICE, adapter_path)
    except GLib.Error as e:
        print(f"错误：无法获取蓝牙适配器。请确保蓝牙已开启: {e}")
        return

    # 注册 Agent
    agent = SimpleAgent(bus)
    agent_registration = None
    agent_manager = None
    try:
        agent_registration = bus.register_object(AGENT_PATH, agent, AGENT_INTERFACE)
    except Exception as e:
        print(f"错误：无法在总线上注册 Agent 对象: {e}")
        return
    
    # 获取 AgentManager 接口并注册 Agent
    try:
        agent_manager = bus.get(BLUEZ_SERVICE, AGENT_MANAGER_PATH)['org.bluez.AgentManager1']
        agent_manager.RegisterAgent(AGENT_PATH, "KeyboardDisplay") # 注册为 KeyboardDisplay 模式
        print(f"Agent 已成功注册到 {AGENT_PATH}。")
    except GLib.Error as e:
        print(f"错误：无法注册 Agent。可能已存在或 BlueZ 未运行: {e}")
        if agent_registration:
            agent_registration.unregister()
        return

    # 获取 Device 对象路径
    # 路径通常是 /org/bluez/hci0/dev_MAC_ADDRESS_...
    # 我们需要先通过 Adapter 接口找到它，或者直接构造路径
    
    device_path = find_device_path(bus, adapter_path, mac_address)
    if not device_path:
        print(f"未在 {adapter_path} 下找到设备 {mac_address}，尝试开启扫描刷新缓存...")
        try:
            adapter.StartDiscovery()
            time.sleep(5)
        except GLib.Error as e:
            print(f"无法开启扫描: {e}")
        finally:
            try:
                adapter.StopDiscovery()
            except GLib.Error:
                pass
        device_path = find_device_path(bus, adapter_path, mac_address)
        if not device_path:
            print(f"错误：仍然找不到设备 {mac_address}。请确保设备处于配对/可发现状态并已被扫描到。")
            return
    
    try:
        device = bus.get(BLUEZ_SERVICE, device_path)
        print(f"找到设备 {mac_address}。尝试配对...")
        
        # 尝试配对，此调用会触发 Agent 的方法
        # BlueZ 会连接设备并调用 Agent 进行身份验证
        try:
            device.Pair()
        except GLib.Error as pair_error:
            if "org.bluez.Error.ConnectionAttemptFailed" in str(pair_error):
                print(f"\n❌ 无法连接到 {mac_address} (ConnectionAttemptFailed)。请确保设备靠近、已进入配对模式并未连接到其他主机，然后重试。")
            else:
                print(f"\n❌ 调用 Pair 失败: {pair_error}")
            return
        print("配对调用完成。等待 Agent 交互...")
        
        # 简单等待，让配对过程完成（实际项目中可能需要更复杂的事件循环）
        time.sleep(5) 
        
        # 检查配对结果
        device_props = bus.get(BLUEZ_SERVICE, device_path)['org.freedesktop.DBus.Properties']
        paired_status = device_props.Get("org.bluez.Device1", "Paired")
        
        if paired_status:
            print(f"\n🎉 设备 {mac_address} 配对成功！")
            try:
                device_props.Set("org.bluez.Device1", "Trusted", GLib.Variant("b", True))
                print("设备已设置为 Trusted。")
            except Exception as trust_error:
                print(f"警告：无法将设备标记为 Trusted: {trust_error}")
        else:
            print(f"\n❌ 设备 {mac_address} 配对失败。")
            
    except GLib.Error as e:
        print(f"\n❌ 配对过程中发生错误: {e}")
    finally:
        # 取消注册 Agent
        try:
            agent_manager.UnregisterAgent(AGENT_PATH)
        except Exception:
            pass
        finally:
            if agent_registration:
                agent_registration.unregister()
            print("Agent 已取消注册。")

if __name__ == "__main__":
    mac_address = DEVICE_MAC_ADDRESS
    if len(sys.argv) > 1:
        mac_address = sys.argv[1].strip()

    if mac_address == "B3:D0:0A:54:2C:F5":
        print("请提供要配对的设备 MAC 地址，例如: python bluetooth_agent.py AA:BB:CC:DD:EE:FF")
        sys.exit(1)
        
    # 必须确保设备是可发现的 (Discoverable) 且在范围内
    # 在运行此脚本之前，最好先在 bluetoothctl 中使用 'scan on' 找到设备，确保它存在于 BlueZ 的缓存中。
    pair_device(mac_address)
