"""
全局按键映射管理器
统一管理所有功能按键，支持键盘、手柄等输入设备的改键映射
"""

import os
import json
from evdev import ecodes
from until.log import LOGGER
from until.resource import get_resource_path

class KeyMap:
    """全局按键映射管理器类"""

    def __init__(self, config_path=None):
        """
        初始化按键映射管理器

        Args:
            config_path: 按键配置文件路径
        """
        if config_path is None:
            config_path = get_resource_path("config/keymap.json")
        self.config_path = config_path
        self.config = {}
        self.keycode_cache = {}  # 缓存字符串到 keycode 的映射
        self.axis_bindings = {}  # 缓存轴事件绑定 {(code, value): [(category, action), ...]}
        self._key_press_times = {}  # 记录按键按下的时间戳 {keycode: timestamp}
        self._longpress_triggered = {}  # 记录长按是否已触发 {keycode: bool}
        self._last_repeat_times = {}  # 记录上次重复触发的时间戳 {keycode: timestamp}
        self.load_config()

    def load_config(self):
        """加载按键配置文件"""
        try:
            if not os.path.exists(self.config_path):
                LOGGER.error(f"keymap config file not found: {self.config_path}")
                self.config = self._get_default_config()
                return

            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)

            LOGGER.info(f"keymap config loaded: {self.config_path}")

        except Exception as e:
            LOGGER.error(f"load keymap config failed: {e}")
            self.config = self._get_default_config()

    def reload_config(self):
        """重新加载配置文件 (支持热更新)"""
        LOGGER.info("reload keymap config...")
        self.keycode_cache.clear()
        self.axis_bindings.clear()
        self.load_config()

    def save_config(self):
        """保存当前配置到文件"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=4)
            LOGGER.info(f"keymap config saved: {self.config_path}")
        except Exception as e:
            LOGGER.error(f"save keymap config failed: {e}")

    def _get_default_config(self):
        """获取默认配置 (如果配置文件不存在)"""
        return {
            "settings": {
                "longpress_threshold": 0.5
            },
            "keymap": {
                "navigation": {
                    "up": ["KEY_UP", {"type": "ABS", "code": "ABS_HAT0Y", "value": -1}],
                    "down": ["KEY_DOWN", {"type": "ABS", "code": "ABS_HAT0Y", "value": 1}],
                    "left": ["KEY_LEFT", {"type": "ABS", "code": "ABS_HAT0X", "value": -1}],
                    "right": ["KEY_RIGHT", {"type": "ABS", "code": "ABS_HAT0X", "value": 1}]
                },
                "action": {
                    "select": ["KEY_Z", "BTN_EAST"],
                    "cancel": ["KEY_X", "BTN_SOUTH"],
                    "next_screen": ["KEY_PAGEDOWN", "BTN_TR"],
                    "previous_screen": ["KEY_PAGEUP", "BTN_TL"],
                    "menu": ["KEY_M", "BTN_MODE"],
                    "screenshot": ["KEY_F12", "BTN_Z"]
                },
                "media": {
                    "play_pause": ["KEY_PLAYPAUSE"],
                    "next": ["KEY_NEXTSONG"],
                    "previous": ["KEY_PREVIOUSSONG"],
                    "stop": ["KEY_STOPCD"],
                    "volume_up": ["KEY_VOLUMEUP"],
                    "volume_down": ["KEY_VOLUMEDOWN"],
                    "mute": ["KEY_MUTE"]
                }
            }
        }

    def _keyname_to_code(self, key_name):
        """
        将按键名称转换为 evdev keycode

        Args:
            key_name: 按键名称字符串 (如 "KEY_KP1")

        Returns:
            int: evdev keycode，如果不存在返回 None
        """
        if key_name in self.keycode_cache:
            return self.keycode_cache[key_name]

        try:
            keycode = getattr(ecodes, key_name)
            self.keycode_cache[key_name] = keycode
            return keycode
        except AttributeError:
            LOGGER.error(f"未知的按键名称: {key_name}")
            return None

    def _get_key(self, category, action):
        """
        获取指定类别和动作对应的按键代码列表

        Args:
            category: 按键类别 ("navigation", "action", "media", "gamepad")
            action: 动作名称 (如 "select", "menu", "play_pause", "up")

        Returns:
            list[int]: 按键代码列表，如果不存在返回空列表

        Note:
            此方法只返回按钮事件(KEY_*, BTN_*)的代码
            轴事件(ABS_*)需要使用 match_axis() 方法
        """
        keymap = self.config.get("keymap", {})
        category_keys = keymap.get(category, {})
        key_names = category_keys.get(action)

        if key_names is None:
            return []

        if not isinstance(key_names, list):
            key_names = [key_names]

        keycodes = []
        for key_item in key_names:
            # 跳过注释字段
            if isinstance(key_item, str) and key_item.startswith("_"):
                continue

            # 处理字符串格式的按键名称
            if isinstance(key_item, str):
                keycode = self._keyname_to_code(key_item)
                if keycode is not None:
                    keycodes.append(keycode)

            # 处理字典格式的轴事件 - 缓存到 axis_bindings
            elif isinstance(key_item, dict):
                axis_type = key_item.get("type")
                axis_code_name = key_item.get("code")
                axis_value = key_item.get("value")

                if axis_type == "ABS" and axis_code_name and axis_value is not None:
                    axis_code = self._keyname_to_code(axis_code_name)
                    if axis_code is not None:
                        # 缓存轴事件绑定 (按下时的值和释放/回中值)
                        for value in (axis_value, 0):
                            key = (axis_code, value)
                            if key not in self.axis_bindings:
                                self.axis_bindings[key] = []
                            # 避免重复添加
                            if (category, action) not in self.axis_bindings[key]:
                                self.axis_bindings[key].append((category, action))

        return keycodes

    def _get_event_from_context(self, evt):
        """
        从调用栈上下文中获取事件对象

        Args:
            evt: 传入的事件对象,如果不为 None 则直接返回

        Returns:
            InputEvent | None: 事件对象,如果找不到则返回 None
        """
        if evt is not None:
            return evt

        import inspect
        frame = inspect.currentframe()
        try:
            # 获取调用者的调用者的栈帧 (跳过当前方法)
            caller_frame = frame.f_back.f_back
            # 优先从调用者的局部变量中获取 evt
            evt = caller_frame.f_locals.get('evt')
            # 如果局部变量没有，尝试从 self.evt 获取
            if evt is None:
                caller_self = caller_frame.f_locals.get('self')
                if caller_self:
                    evt = getattr(caller_self, 'evt', None)
        finally:
            del frame

        return evt

    def down(self, *args, evt=None):
        """
        处理按键按下事件
        自动记录按键按下时间,用于长按检测

        Args:
            *args: 可变参数,传递给 match()
            evt: evdev.InputEvent 对象

        Returns:
            bool: 是否匹配按键
        """
        evt = self._get_event_from_context(evt)
        if evt is None:
            return False

        if abs(evt.value) == 1:  # 按下 (value=1 或 -1,兼容手柄)
            import time
            # 仅在首次按下时记录时间戳和初始化状态
            if evt.code not in self._key_press_times:
                self._key_press_times[evt.code] = time.time()
                self._longpress_triggered[evt.code] = False
                self._last_repeat_times[evt.code] = 0

            return self.match(*args, evt=evt) if args else True

        return False

    def up(self, *args, evt=None):
        """
        处理按键释放事件
        自动清理按键按下时间记录

        Args:
            *args: 可变参数,传递给 match()
            evt: evdev.InputEvent 对象

        Returns:
            bool: 是否匹配按键
        """
        evt = self._get_event_from_context(evt)
        if evt is None:
            return False

        if evt.value == 0:  # 释放
            # 清理所有与该按键相关的状态
            if evt.code in self._key_press_times:
                del self._key_press_times[evt.code]
            if evt.code in self._longpress_triggered:
                del self._longpress_triggered[evt.code]
            if evt.code in self._last_repeat_times:
                del self._last_repeat_times[evt.code]

            return self.match(*args, evt=evt) if args else True

        return False

    def longpress(self, *args, evt=None, threshold=None, repeat=False, repeat_interval=0.06):
        """
        检测按键是否达到长按阈值
        需要配合 down() 使用,或者在 evt.value == 2 (持续按住) 时调用

        Args:
            *args: 可变参数,传递给 match()
            evt: evdev.InputEvent 对象
            threshold: 长按阈值(秒),如果不提供则使用配置文件中的默认值
            repeat: 是否启用重复触发模式
                    - False: 长按达到阈值后只返回一次 True
                    - True: 长按后每隔 repeat_interval 秒重复返回 True
            repeat_interval: 重复触发间隔(秒),默认 0.06 秒 (60ms)

        Returns:
            bool: 如果按键达到长按阈值则返回 True,否则返回 False

        Examples:
            # 不重复模式 - 只触发一次
            if keymap.longpress('action', 'select'):
                print("长按 select 键")

            # 重复模式 - 持续触发
            if keymap.longpress('navigation', 'up', repeat=True, repeat_interval=0.1):
                # 每 100ms 触发一次
                scroll_up()
        """
        import time

        evt = self._get_event_from_context(evt)
        if evt is None:
            return False

        # 获取长按阈值
        if threshold is None:
            threshold = self._get_longpress_threshold()

        # 如果是首次按下事件,记录时间戳并初始化状态
        if evt.value != 0 and evt.code not in self._key_press_times:
            self._key_press_times[evt.code] = time.time()
            self._longpress_triggered[evt.code] = False
            return False

        # 如果是持续按住 (value == 2) 或其他非零值,检查是否达到阈值
        if evt.value != 0 and evt.code in self._key_press_times:
            press_duration = time.time() - self._key_press_times[evt.code]

            # 达到长按阈值
            if press_duration >= threshold:
                # 检查按键是否匹配
                matched = True
                if args:
                    matched = self.match(*args, evt=evt)

                if not matched:
                    return False

                # 非重复模式：只触发一次
                if not repeat:
                    if not self._longpress_triggered.get(evt.code, False):
                        self._longpress_triggered[evt.code] = True
                        return True
                    return False

                # 重复模式：检查是否到了下次触发时间
                current_time = time.time()
                last_repeat_time = self._last_repeat_times.get(evt.code, 0)

                # 首次触发或距离上次触发超过 repeat_interval
                if current_time - last_repeat_time >= repeat_interval:
                    self._last_repeat_times[evt.code] = current_time
                    return True

        return False
            
    def match(self, *args, evt=None):
        """
        统一匹配输入事件是否对应目标按键或虚拟功能键
        支持两种调用方式:
        1. match(key_list1, key_list2, ...) - 传统模式,匹配按键代码列表
        2. match(category, action) - 虚拟功能键模式,支持 EV_KEY 和 EV_ABS

        Args:
            *args: 可变参数
                   - 如果是 list: 按键代码列表 (传统模式)
                   - 如果是 2 个 str: (category, action) 虚拟功能键模式
            evt: evdev.InputEvent 对象,如果不提供则从调用栈中获取 self.evt

        Returns:
            bool: 是否匹配

        Examples:
            # 传统模式 - 匹配按键代码列表
            if keymap.match(key_nav_up, key_select):
                ...

            # 虚拟功能键模式 - 统一匹配按钮和轴事件
            if keymap.match('navigation', 'up'):
                # 匹配 KEY_UP 或 ABS_HAT0Y=-1
                ...
        """
        from evdev import ecodes

        evt = self._get_event_from_context(evt)
        if evt is None:
            return False

        # 模式 1: 虚拟功能键模式 - match(category, action)
        if len(args) == 2 and isinstance(args[0], str) and isinstance(args[1], str):
            category, action = args

            # 处理按钮事件 (EV_KEY)
            if evt.type == ecodes.EV_KEY:
                key_buttons = self._get_key(category, action)
                return evt.code in key_buttons

            # 处理轴事件 (EV_ABS)
            elif evt.type == ecodes.EV_ABS:
                return self.match_axis(evt.code, evt.value, category, action)

            return False

        # 模式 2: 传统模式 - match(key_list1, key_list2, ...)
        else:
            # 检查按钮事件 (EV_KEY)
            if evt.type == ecodes.EV_KEY:
                for key_list in args:
                    if key_list and evt.code in key_list:
                        return True
                return False

            # 检查轴事件 (EV_ABS)
            elif evt.type == ecodes.EV_ABS:
                # 获取所有轴事件绑定的动作
                actions = self.get_axis_action(evt.code, evt.value)
                # LOGGER.info(f"Axis {evt.code} value {evt.value} actions: {actions}")
                for category, action in actions:
                    action_keys = self._get_key(category, action)
                    # 检查是否匹配任意一个传入的 key_list
                    for key_list in args:
                        if action_keys == key_list:
                            return True
                return False

            return False

    def match_axis(self, axis_code, axis_value, category, action):
        """
        检查轴事件是否匹配指定的类别和动作

        Args:
            axis_code: 轴代码 (如 ecodes.ABS_HAT0Y)
            axis_value: 轴值 (如 -1, 0, 1)
            category: 按键类别 ("navigation", "gamepad" 等)
            action: 动作名称 (如 "up", "down", "left", "right")

        Returns:
            bool: 是否匹配

        Example:
            # 检查 ABS_HAT0Y = -1 是否对应 navigation.up
            if keymap.match_axis(evt.code, evt.value, "navigation", "up"):
                handle_up()
        """
        # 确保轴绑定已加载
        if not self.axis_bindings:
            # 触发一次 _get_key 来构建缓存
            keymap = self.config.get("keymap", {})
            for cat in keymap:
                if not cat.startswith("_"):
                    for act in keymap[cat]:
                        if not act.startswith("_"):
                            self._get_key(cat, act)

        # 检查是否匹配
        key = (axis_code, axis_value)
        bindings = self.axis_bindings.get(key, [])
        return (category, action) in bindings

    def get_axis_action(self, axis_code, axis_value):
        """
        根据轴事件获取对应的动作

        Args:
            axis_code: 轴代码 (如 ecodes.ABS_HAT0Y)
            axis_value: 轴值 (如 -1, 0, 1)

        Returns:
            list: [(category, action), ...] 所有匹配的动作列表

        Example:
            actions = keymap.get_axis_action(evt.code, evt.value)
            # 返回: [("navigation", "up"), ("gamepad", "up")]
        """
        # 确保轴绑定已加载
        if not self.axis_bindings:
            keymap = self.config.get("keymap", {})
            for cat in keymap:
                if not cat.startswith("_"):
                    for act in keymap[cat]:
                        if not act.startswith("_"):
                            self._get_key(cat, act)

        key = (axis_code, axis_value)
        return self.axis_bindings.get(key, [])

    def _get_longpress_threshold(self):
        """
        获取长按阈值 (秒)

        Returns:
            float: 长按阈值
        """
        return self.config.get("settings", {}).get("longpress_threshold", 0.5)

    # ===== 便捷访问方法 =====

    # 导航键
    @property
    def nav_up(self):
        """获取上方向键"""
        return self._get_key("navigation", "up")
    
    @property
    def nav_down(self):
        """获取下方向键"""
        return self._get_key("navigation", "down")
    @property
    def nav_left(self):
        """获取左方向键"""
        return self._get_key("navigation", "left")

    @property
    def nav_right(self):
        """获取右方向键"""
        return self._get_key("navigation", "right")

    # 功能键
    @property
    def action_select(self):
        """获取确定键 (播放/暂停、确认、跳跃等)"""
        return self._get_key("action", "select")
    
    @property
    def action_cancel(self):
        """获取取消键 (下一曲、取消、切换等)"""
        return self._get_key("action", "cancel")
    
    @property
    def action_menu(self):
        """获取菜单键 (切换插件、菜单等)"""
        return self._get_key("action", "menu")
    
    @property
    def action_screenshot(self):
        """获取截图键"""
        return self._get_key("action", "screenshot")
    
    @property
    def action_next_screen(self):
        """获取下一屏键"""
        return self._get_key("action", "next_screen")

    @property
    def action_prev_screen(self):
        """获取上一屏键"""
        return self._get_key("action", "previous_screen")

    # 媒体键
    @property
    def media_play_pause(self):
        """获取播放/暂停键"""
        return self._get_key("media", "play_pause")
    
    @property
    def media_next(self):
        """获取下一曲键"""
        return self._get_key("media", "next")

    @property
    def media_previous(self):
        """获取上一曲键"""
        return self._get_key("media", "previous")
    
    @property
    def media_stop(self):
        """获取停止键"""
        return self._get_key("media", "stop")
    
    @property
    def media_volume_up(self):
        """获取音量增加键"""
        return self._get_key("media", "volume_up")
    
    @property
    def media_volume_down(self):
        """获取音量减少键"""
        return self._get_key("media", "volume_down")
    
    @property
    def media_volume_mute(self):
        """获取静音键"""
        return self._get_key("media", "mute")

    # 手柄按键
    @property
    def gamepad_up(self):
        """获取手柄上方向键"""
        return self._get_key("gamepad", "up")

    @property
    def gamepad_down(self):
        """获取手柄下方向键"""
        return self._get_key("gamepad", "down")

    @property
    def gamepad_left(self):
        """获取手柄左方向键"""
        return self._get_key("gamepad", "left")

    @property
    def gamepad_right(self):
        """获取手柄右方向键"""
        return self._get_key("gamepad", "right")

    @property
    def gamepad_a(self):
        """获取手柄A键"""
        return self._get_key("gamepad", "a")

    @property
    def gamepad_b(self):
        """获取手柄B键"""
        return self._get_key("gamepad", "b")

    @property
    def gamepad_x(self):
        """获取手柄X键"""
        return self._get_key("gamepad", "x")

    @property
    def gamepad_y(self):
        """获取手柄Y键"""
        return self._get_key("gamepad", "y")

    @property
    def gamepad_tl(self):
        """获取手柄TL键（左扳机上键）"""
        return self._get_key("gamepad", "tl")

    @property
    def gamepad_tr(self):
        """获取手柄TR键（右扳机上键）"""
        return self._get_key("gamepad", "tr")

    @property
    def gamepad_lb(self):
        """获取手柄LB键（左肩键）"""
        return self._get_key("gamepad", "lb")

    @property
    def gamepad_rb(self):
        """获取手柄RB键（右肩键）"""
        return self._get_key("gamepad", "rb")

    @property
    def gamepad_thumb(self):
        """获取手柄摇杆按键"""
        return self._get_key("gamepad", "thumb")

    @property
    def gamepad_select(self):
        """获取手柄SELECT键"""
        return self._get_key("gamepad", "select")

    @property
    def gamepad_start(self):
        """获取手柄START键"""
        return self._get_key("gamepad", "start")

    @property
    def gamepad_screenshot(self):
        """获取手柄截图键"""
        return self._get_key("gamepad", "screenshot")

    @property
    def gamepad_mode(self):
        """获取手柄MODE键"""
        return self._get_key("gamepad", "mode")

    # def print_current_mapping(self):
    #     """打印当前按键映射 (调试用)"""
    #     LOGGER.info("=== 当前全局按键映射 ===")

    #     keymap = self.config.get("keymap", {})

    #     for category, actions in keymap.items():
    #         if category.startswith("_"):
    #             continue
    #         LOGGER.info(f"\n[{category}]")
    #         for action, key_names in actions.items():
    #             if not action.startswith("_"):
    #                 LOGGER.info(f"  {action}: {key_names}")


# 全局单例实例
_keymap_instance = None


def get_keymap():
    """
    获取全局按键映射单例

    Returns:
        KeyMap: 按键映射管理器实例
    """
    global _keymap_instance
    if _keymap_instance is None:
        _keymap_instance = KeyMap()
    return _keymap_instance


if __name__ == "__main__":
    # 测试代码
    km = get_keymap()
    km.print_current_mapping()

    LOGGER.info("\n=== 测试查询 ===")
    LOGGER.info(f"确定键 (select): {km.get_action_select()}")
    LOGGER.info(f"取消键 (cancel): {km.get_action_cancel()}")
    LOGGER.info(f"菜单键 (menu): {km.get_action_menu()}")
    LOGGER.info(f"播放/暂停键: {km.get_media_play_pause()}")
    LOGGER.info(f"音量增加键: {km.get_media_volume_up()}")

    LOGGER.info("\n=== 测试匹配 ===")
    test_keycode = ecodes.KEY_KP1
    LOGGER.info(f"按键 {test_keycode} (KEY_KP1) 是否匹配确定键: {km.is_key_match(test_keycode, km.get_action_select())}")
    LOGGER.info(f"按键 {test_keycode} (KEY_KP1) 是否匹配取消键: {km.is_key_match(test_keycode, km.get_action_cancel())}")
