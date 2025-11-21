import importlib
from until.log import LOGGER
from screen.manager import DisplayManager
from until.config import config

# config path
CONFIG_PATH = "config/plugins.json"


class PluginManager:
    def __init__(self, manager: DisplayManager):
        self.manager = manager
        self.plugin_classes = {}
        self.plugin_modules = {}  # 缓存已加载的模块
        self.config = config.open(CONFIG_PATH)

    def _load_plugin_module(self, plugin_name):
        """
        动态加载插件模块

        :param plugin_name: 插件名称（如 'xiaozhi'）
        :return: 加载的模块对象
        """
        # 如果已经加载过，直接返回缓存
        if plugin_name in self.plugin_modules:
            return self.plugin_modules[plugin_name]

        try:
            # 构建模块路径
            module_path = f"screen.plugins.{plugin_name.lower()}"

            # 动态导入模块
            LOGGER.info(f"Loading plugin module: {module_path}")
            module = importlib.import_module(module_path)

            # 缓存模块
            self.plugin_modules[plugin_name] = module

            return module

        except ImportError as e:
            LOGGER.error(f"Failed to import plugin module '{module_path}': {e}")
            return None
        except Exception as e:
            LOGGER.error(f"Unexpected error loading plugin '{plugin_name}': {e}")
            return None

    def load(self):
        """
        根据 JSON 配置动态加载插件

        优点:
        - 完全由 JSON 控制加载哪些插件
        - 按需加载，不需要预先导入所有模块
        - 支持运行时重新加载配置
        """
        LOGGER.info("Loading plugins from config...")

        loaded_count = 0
        skipped_count = 0
        failed_count = 0

        for plugin_info in self.config["plugins"]:
            plugin_name = plugin_info["name"]

            # 检查是否启用
            if not plugin_info["enabled"]:
                LOGGER.info(f"Plugin '{plugin_name}' is disabled, skipping")
                skipped_count += 1
                continue

            try:
                # 动态加载模块
                module = self._load_plugin_module(plugin_name)
                if module is None:
                    failed_count += 1
                    continue

                # 获取插件类
                class_name = plugin_info.get("class_name", plugin_name)

                if not hasattr(module, class_name):
                    LOGGER.error(f"Plugin class '{class_name}' not found in module '{plugin_name}'")
                    failed_count += 1
                    continue

                plugin_class = getattr(module, class_name)

                # 缓存插件类
                self.plugin_classes[plugin_name] = plugin_class

                # 添加到 DisplayManager
                auto_hide = plugin_info.get("auto_hide", False)
                self.manager.add_plugin(plugin_class, auto_hide=auto_hide)

                LOGGER.info(f"✓ Loaded plugin: {plugin_name} (auto_hide={auto_hide})")
                loaded_count += 1

            except Exception as e:
                LOGGER.error(f"Failed to load plugin '{plugin_name}': {e}")
                import traceback
                LOGGER.error(traceback.format_exc())
                failed_count += 1

        # 输出加载总结
        LOGGER.info(f"Plugin loading complete: \033[2m{loaded_count} loaded, {skipped_count} skipped, {failed_count} failed\033[0m")

    def reload_config(self):
        """
        重新加载配置文件
        注意：这不会卸载已加载的插件，只会更新配置
        """
        LOGGER.info("Reloading plugin configuration...")
        self.config = config.open(CONFIG_PATH)
        LOGGER.info("Configuration reloaded")

    def get_loaded_plugins(self):
        """
        获取已加载的插件列表

        :return: 插件名称列表
        """
        return list(self.plugin_classes.keys())
                