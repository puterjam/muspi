import importlib
from pathlib import Path
from until.log import LOGGER
from screen.manager import DisplayManager
from until.config import config

# config path
CONFIG_PATH = "config/plugins.json"  # 系统插件配置模板


class PluginManager:
    def __init__(self, manager: DisplayManager):
        self.manager = manager
        self.plugin_classes = {}
        self.plugin_modules = {}  # 缓存已加载的模块
        self.plugin_paths = {}  # 缓存插件路径
        self.user_path = Path(manager.get_path("user"))
        self.user_config_path = self.user_path / "plugins.json"
        self._init_user_config()
        self.config = config.open(str(self.user_config_path))

    def _init_user_config(self):
        """
        初始化用户插件配置文件

        如果用户配置不存在,复制系统配置到用户目录
        如果用户配置存在,同步系统新增或删除的插件
        """
        import shutil

        # 确保用户目录存在
        self.user_path.mkdir(parents=True, exist_ok=True)

        # 加载系统配置
        system_config = config.open(CONFIG_PATH)
        if not system_config:
            LOGGER.error(f"Failed to load system plugin config: {CONFIG_PATH}")
            return

        # 如果用户配置不存在,复制系统配置
        if not self.user_config_path.exists():
            LOGGER.info(f"User plugin config not found, copying from system config...")
            try:
                shutil.copy2(CONFIG_PATH, self.user_config_path)
                LOGGER.info(f"User plugin config created: {self.user_config_path}")
            except Exception as e:
                LOGGER.error(f"Failed to create user plugin config: {e}")
            return

        # 加载用户配置
        user_config = config.open(str(self.user_config_path))
        if not user_config:
            LOGGER.error(f"Failed to load user plugin config: {self.user_config_path}")
            return

        # 同步系统配置的插件列表
        system_plugins = system_config.get("plugins", [])
        user_plugins = user_config.get("plugins", [])

        # 创建插件名称到插件对象的映射
        user_plugin_dict = {p["name"]: p for p in user_plugins}
        system_plugin_dict = {p["name"]: p for p in system_plugins}

        updated = False

        # 检查系统新增的插件
        for plugin_name, system_plugin in system_plugin_dict.items():
            if plugin_name not in user_plugin_dict:
                LOGGER.info(f"New plugin detected: {plugin_name}, adding to user config")
                user_plugins.append(system_plugin.copy())
                updated = True

        # 检查用户配置中已删除的插件
        plugins_to_remove = []
        for plugin_name in user_plugin_dict.keys():
            if plugin_name not in system_plugin_dict:
                LOGGER.info(f"Plugin removed from system: {plugin_name}, removing from user config")
                plugins_to_remove.append(plugin_name)
                updated = True

        # 删除已移除的插件
        if plugins_to_remove:
            user_plugins = [p for p in user_plugins if p["name"] not in plugins_to_remove]

        # 保存更新后的用户配置
        if updated:
            user_config["plugins"] = user_plugins
            config.save(str(self.user_config_path), user_config)
            LOGGER.info(f"User plugin config synchronized")

    def _load_plugin_module(self, plugin_name):
        """
        动态加载插件模块

        :param plugin_name: 插件名称（如 'xiaozhi'）
        :return: (module, work_path) 元组
        """
        # 如果已经加载过，直接返回缓存
        if plugin_name in self.plugin_modules:
            return self.plugin_modules[plugin_name], self.plugin_paths[plugin_name]

        try:
            # 构建模块路径
            module_path = f"screen.plugins.{plugin_name.lower()}.app"

            # 构建工作路径
            work_path = f"screen/plugins/{plugin_name.lower()}"

            # 动态导入模块
            LOGGER.info(f"Loading plugin module: \033[94m{module_path.replace('screen.plugins.', '')}\033[0m")
            module = importlib.import_module(module_path)

            # 缓存模块和路径
            self.plugin_modules[plugin_name] = module
            self.plugin_paths[plugin_name] = work_path

            return module, work_path

        except ImportError as e:
            LOGGER.error(f"Failed to import plugin module '{module_path}': {e}")
            return None, None
        except Exception as e:
            LOGGER.error(f"Unexpected error loading plugin '{plugin_name}': {e}")
            return None, None

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
                module, work_path = self._load_plugin_module(plugin_name)
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
        self._init_user_config()
        self.config = config.open(str(self.user_config_path))
        LOGGER.info("Configuration reloaded")

    def get_loaded_plugins(self):
        """
        获取已加载的插件列表

        :return: 插件名称列表
        """
        return list(self.plugin_classes.keys())
                