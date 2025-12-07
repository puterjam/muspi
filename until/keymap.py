"""
全局按键映射管理器
统一管理所有功能按键，支持键盘、手柄等输入设备的改键映射
"""

import os
import json
from evdev import ecodes
from until.log import LOGGER

class KeyMap:
    """全局按键映射管理器类"""

    def __init__(self, config_path="/home/pi/workspace/muspi/config/keymap.json"):
        """
        初始化按键映射管理器

        Args:
            config_path: 按键配置文件路径
        """
        self.config_path = config_path
        self.config = {}
        self.keycode_cache = {}  # 缓存字符串到 keycode 的映射
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
                "longpress_threshold": 3.0
            },
            "keymap": {
                "navigation": {
                    "up": ["KEY_UP"],
                    "down": ["KEY_DOWN"],
                    "left": ["KEY_LEFT"],
                    "right": ["KEY_RIGHT"]
                },
                "action": {
                    "select": ["KEY_ENTER", "KEY_KP1"],
                    "cancel": ["KEY_ESC", "KEY_KP2"],
                    "menu": ["KEY_FORWARD", "KEY_M"]
                },
                "media": {
                    "play_pause": ["KEY_PLAYPAUSE", "KEY_KP1"],
                    "next": ["KEY_NEXTSONG", "KEY_KP2"],
                    "previous": ["KEY_PREVIOUSSONG"],
                    "stop": ["KEY_STOP"],
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

    def get_key(self, category, action):
        """
        获取指定类别和动作对应的按键代码列表

        Args:
            category: 按键类别 ("navigation", "action", "media")
            action: 动作名称 (如 "select", "menu", "play_pause")

        Returns:
            list[int]: 按键代码列表，如果不存在返回空列表
        """
        keymap = self.config.get("keymap", {})
        category_keys = keymap.get(category, {})
        key_names = category_keys.get(action)

        if key_names is None:
            return []

        if not isinstance(key_names, list):
            key_names = [key_names]

        keycodes = []
        for key_name in key_names:
            if not key_name.startswith("_"):  # 跳过注释字段
                keycode = self._keyname_to_code(key_name)
                if keycode is not None:
                    keycodes.append(keycode)

        return keycodes

    def match(self, *target_keys, keycode=None):
        """
        检查按键代码是否匹配目标按键列表

        Args:
            *target_keys: 一个或多个目标按键列表 (list[int])，支持传入多个列表进行检查
            keycode: 实际按下的按键代码 (int)，如果为 None 则自动从调用者的 self.key_code 获取

        Returns:
            bool: 是否匹配任意一个按键列表

        Examples:
            # 单个按键列表
            match(key_volume_up)

            # 多个按键列表 (匹配任意一个即返回 True)
            match(key_volume_up, key_nav_up)

            # 显式指定 keycode
            match(key_volume_up, key_nav_up, keycode=evt.code)

            # 兼容旧用法
            match(evt.code, key_volume_up)
        """
        # 兼容旧的调用方式: is_key_match(evt.code, key_list)
        # 如果第一个参数是 int 且 keycode 为 None，说明是旧用法
        if len(target_keys) == 2 and isinstance(target_keys[0], int) and keycode is None:
            keycode = target_keys[0]
            target_keys = (target_keys[1],)
        elif len(target_keys) == 1 and isinstance(target_keys[0], int) and isinstance(keycode, list):
            # is_key_match(evt.code, keycode=key_list) 的情况
            keycode, target_keys = target_keys[0], (keycode,)

        # 如果 keycode 为 None，尝试从调用者的 self.key_code 获取
        if keycode is None:
            import inspect
            frame = inspect.currentframe()
            try:
                caller_frame = frame.f_back
                caller_self = caller_frame.f_locals.get('self')
                if caller_self and hasattr(caller_self, 'key_code'):
                    keycode = caller_self.key_code
                else:
                    return False
            finally:
                del frame

        # 检查所有传入的按键列表
        for keys in target_keys:
            if keys and keycode in keys:
                return True

        return False

    def get_longpress_threshold(self):
        """
        获取长按阈值 (秒)

        Returns:
            float: 长按阈值
        """
        return self.config.get("settings", {}).get("longpress_threshold", 3.0)

    # ===== 便捷访问方法 =====

    # 导航键
    @property
    def nav_up(self):
        """获取上方向键"""
        return self.get_key("navigation", "up")
    
    @property
    def nav_down(self):
        """获取下方向键"""
        return self.get_key("navigation", "down")
    @property
    def nav_left(self):
        """获取左方向键"""
        return self.get_key("navigation", "left")

    @property
    def nav_right(self):
        """获取右方向键"""
        return self.get_key("navigation", "right")

    # 功能键
    @property
    def action_select(self):
        """获取确定键 (播放/暂停、确认、跳跃等)"""
        return self.get_key("action", "select")
    
    @property
    def action_cancel(self):
        """获取取消键 (下一曲、取消、切换等)"""
        return self.get_key("action", "cancel")
    
    @property
    def action_menu(self):
        """获取菜单键 (切换插件、菜单等)"""
        return self.get_key("action", "menu")
    
    @property
    def action_screenshot(self):
        """获取截图键"""
        return self.get_key("action", "screenshot")
    
    @property
    def action_next(self):
        """获取下一屏键"""
        return self.get_key("action", "next_screen")

    @property
    def action_previous(self):
        """获取上一屏键"""
        return self.get_key("action", "previous_screen")

    # 媒体键
    @property
    def media_play_pause(self):
        """获取播放/暂停键"""
        return self.get_key("media", "play_pause")
    
    @property
    def media_next(self):
        """获取下一曲键"""
        return self.get_key("media", "next")

    @property
    def media_previous(self):
        """获取上一曲键"""
        return self.get_key("media", "previous")
    
    @property
    def media_stop(self):
        """获取停止键"""
        return self.get_key("media", "stop")
    
    @property
    def media_volume_up(self):
        """获取音量增加键"""
        return self.get_key("media", "volume_up")
    
    @property
    def media_volume_down(self):
        """获取音量减少键"""
        return self.get_key("media", "volume_down")
    
    @property
    def media_volume_mute(self):
        """获取静音键"""
        return self.get_key("media", "mute")

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
