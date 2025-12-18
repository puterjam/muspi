import time
import sys
import signal

from pathlib import Path
from PIL import Image, ImageDraw
from until.device.input import KeyListener, ecodes
from until.device.volume import adjust_volume, detect_pcm_controls, toggle_mute, get_volume_percent
from until.log import LOGGER
from until.keymap import get_keymap
from until.resource import get_resource_path

from ui.fonts import Fonts
from ui.animation import Animation
from ui.overlays import OverlayManager


# contrast value
CONTRAST = 128
ANIMATION_DURATION = 0.3
FONTS = Fonts()

def _show_welcome(
    width, height, msg="Muspi", logo_name="logo.png", logo_size=(24, 24)
):
    """show welcome screen"""
    image = Image.new("1", (width, height))
    try:
        # 使用资源路径打开图片
        logo_path = get_resource_path("assets/icons/" + logo_name)

        logo = Image.open(logo_path)
        # 调整图片大小
        logo = logo.resize(logo_size)
        # 转换为单色模式
        logo = logo.convert("1")
    except Exception as e:
        LOGGER.error(f"can't load icon: {e}")
        logo = None

    draw = ImageDraw.Draw(image)

    # draw border
    draw.rectangle((0, 0, width - 1, height - 1), outline=255, width=1)

    # draw text
    draw.text((60, (height - 16) // 2), msg, font=FONTS.size_16, fill=255)

    # if logo loaded, draw logo
    if logo:
        x = (width - logo.width) // 5
        y = (height - logo.height) // 2
        image.paste(logo, (x, y))

    return image


class DisplayManager:
    def __init__(self, device=None):
        """Initialize the display manager"""
        # init display
        if device is None:
            LOGGER.error("display is not initialized")
            sys.exit(1)

        self.disp = device

        # init variables (必须在 turn_on_screen 之前初始化)
        self.key_listener = KeyListener()
        self.last_active = None
        self.active_id = 0
        self.last_screen_image = None
        self.main_screen = Image.new("1", (self.disp.width, self.disp.height), 0)
        self.anim = Animation(ANIMATION_DURATION)
        self.anim.reset("main_screen")
        self.anim_just_started = False  # 追踪动画是否刚开始

        # init keymap
        self.keymap = get_keymap()

        # init overlay manager
        self.overlay_manager = OverlayManager(self.disp.width, self.disp.height)

        # init sleep
        self.sleep = False

        # 初始化显示（在所有变量初始化之后）
        self.turn_on_screen()
        self.disp.contrast(CONTRAST)  # 128 is the default contrast value
        self.welcome()
        self.sleep_time = 3 * 60  # 3 minutes idle time
        self.sleep_count = time.time()
        
        self.is_muted = False  # 跟踪静音状态

        # initialize plugins
        self.plugins = []
        self.path = {
            "user": Path("~/.local/share/muspi"),
        }

        # register signal handler
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

    def set_path(self, key, path):
        p = Path(path).expanduser()
        self.path[key] = p
        self.path[key].mkdir(parents=True, exist_ok=True)
        LOGGER.info(f"set {key} path to {p}")
    
    def get_path(self, key):
        return self.path[key]
        
    def add_plugin(self, plugin, auto_hide=False):
        id = len(self.plugins)
        plugin_instance = plugin(self, self.disp.width, self.disp.height)
        plugin_instance.id = id

        plugin = {
            "plugin": plugin_instance,
            "auto_hide": auto_hide,
            "is_active": False,
            "id": id,
        }
        self.plugins.append(plugin)

    def active_next(self):
        """activate the next plugin"""
        if self.last_active:
            self.last_screen_image = self.last_active.get_image()
            self.anim.reset("main_screen")
            self.anim.direction = 1  # forward direction
            self.anim_just_started = True  # 标记动画刚开始
            self.last_active.set_active(False)

        next_id = (self.active_id + 1) % len(self.plugins)

        # check if the next plugin is a player and not playing
        while (
            self.plugins[next_id]["auto_hide"]
            and hasattr(self.plugins[next_id]["plugin"], "is_playing")
            and not self.plugins[next_id]["plugin"].is_playing()
        ):
            next_id = (next_id + 1) % len(self.plugins)

        self.plugins[next_id]["plugin"].set_active(True)

    def active_prev(self):
        """activate the previous plugin"""
        if self.last_active:
            self.last_screen_image = self.last_active.get_image()
            self.anim.reset("main_screen")
            self.anim.direction = -1  # reverse direction
            self.anim_just_started = True  # 标记动画刚开始
            self.last_active.set_active(False)

        prev_id = (self.active_id - 1) % len(self.plugins)

        # check if the previous plugin is a player and not playing
        while (
            self.plugins[prev_id]["auto_hide"]
            and hasattr(self.plugins[prev_id]["plugin"], "is_playing")
            and not self.plugins[prev_id]["plugin"].is_playing()
        ):
            prev_id = (prev_id - 1) % len(self.plugins)

        self.plugins[prev_id]["plugin"].set_active(True)

    def _adjust_volume_internal(self, direction):
        """Internal method to actually adjust the volume"""
        # 如果当前是静音状态，先取消静音
        if self.is_muted:
            self.is_muted = toggle_mute()
            LOGGER.info("Auto-unmuted due to volume adjustment")

        if hasattr(self.last_active, "adjust_volume"):
            self.last_active.adjust_volume(direction)
        else:
            volume = adjust_volume(direction)
            if volume is not None:
                self.overlay_manager.show_volume(volume)

    def adjust_volume(self, direction):
        """Directly adjust volume without any restrictions (for plugin use)

        This method can be called by plugins to adjust volume immediately,
        without the volume_adjusting flag or interval control.
        """
        self._adjust_volume_internal(direction)

    def _signal_handler(self, signum, frame):
        """handle the termination signal"""
        LOGGER.info(f"get signal {signum}, cleaning up...")
        self.cleanup()
        sys.exit(0)

    # 处理按键事件
    def key_callback(self, evt):
        """handle the key event"""
        km = self.keymap
        active_plugin = self.last_active
        
        exclusive_nav = bool(
            active_plugin and hasattr(active_plugin, "wants_exclusive_input")
            and active_plugin.wants_exclusive_input()
        )

        # 方向键在独占模式下不会触发全局操作
        allow_nav_for_screen = not exclusive_nav
           
        if self.sleep:
            self.turn_on_screen()
        else:
            # Screen switching: next_screen/previous_screen or left/right
            if km.down(km.action_next_screen) or (allow_nav_for_screen and km.down(km.nav_right)):
                self.active_next()

            if km.down(km.action_prev_screen) or (allow_nav_for_screen and km.down(km.nav_left)):
                self.active_prev()

            # Volume adjustment on initial press
            if km.down(km.media_volume_up):
                self.adjust_volume("up")

            if km.down(km.media_volume_down):
                self.adjust_volume("down")

            # Volume mute toggle
            if km.down(km.media_volume_mute):
                self.is_muted = toggle_mute()
                if self.is_muted is not None:
                    # 显示静音状态
                    if self.is_muted:
                        self.overlay_manager.show_volume(0)
                    else:
                        volume = get_volume_percent()
                        if volume is not None:
                            self.overlay_manager.show_volume(volume)

    def run(self):
        detect_pcm_controls()
        self.key_listener.start()
        self.key_listener.on(self.key_callback)

        try:
            while True:
                frame_start = time.time()
                self.sleep_check()

                for plugin in self.plugins:
                    plugin["plugin"].event_listener()

                if self.last_active is None:
                    self.plugins[0]["plugin"].set_active(
                        True
                    )  # set the first plugin as default active

                # 当屏幕锁定时，降低帧率并跳过渲染，防止烧屏和节省CPU
                if self.sleep:
                    time.sleep(0.5)  # 锁屏时每0.5秒检查一次
                    continue

                try:
                    # 动画开始前运行一次 update()
                    if self.anim.is_running("main_screen"):
                        if self.anim_just_started:
                            self.last_active.update()
                            self.anim_just_started = False
                    else:
                        # 动画未运行时正常更新插件
                        self.last_active.update()
                    
                    # 获取当前插件的图像
                    image = self.last_active.get_image()
                    screen_offset = 128

                    if self.last_screen_image is not None:
                        self.main_screen.paste(self.last_screen_image, (0, 0))

                    if self.anim.is_running("main_screen"):
                        screen_offset = round(
                            self.anim.run("main_screen", self.disp.width)
                        )
                        framerate = 1.0 / 120.0
                    else:
                        framerate = self.last_active.framerate
                        self.last_screen_image = None

                    # 计算图像粘贴位置，根据动画方向调整
                    if self.anim.direction == 1:  # 正向 (next)
                        paste_x = 128 - screen_offset
                    else:  # 反向 (previous)
                        paste_x = screen_offset - 128

                    self.main_screen.paste(image, (paste_x, 0))

                    # 更新覆盖层
                    self.overlay_manager.update()

                    # 如果有覆盖层，应用到主屏幕上
                    if self.overlay_manager.has_active_overlays():
                        self.main_screen = self.overlay_manager.render(self.main_screen)
                        # # 有覆盖层时保持高帧率
                        # if framerate > 1.0 / 60.0:
                        #     framerate = 1.0 / 60.0

                    # 使用 luma.oled 的 display() 方法直接显示图像
                    self.disp.display(self.main_screen)

                except Exception as e:
                    import traceback

                    LOGGER.error(f"错误堆栈: {traceback.format_exc()}")
                    # if error keep frame
                    LOGGER.error(f"error: {e}")
                    framerate = 0.1

                elapsed = time.time() - frame_start
                if elapsed < framerate:
                    time.sleep(framerate - elapsed)

        except KeyboardInterrupt:
            LOGGER.warning("received keyboard interrupt, cleaning up...")
            self.cleanup(False)
        except Exception as e:
            LOGGER.error(f"runtime error: {e}")
            self.cleanup(False)
        finally:
            self.cleanup(True)

    def welcome(self):
        welcome_image = _show_welcome(
            self.disp.width,
            self.disp.height,
            msg="Muspi",
            logo_name="heart.png",
            logo_size=(24, 24),
        )
        self.disp.display(welcome_image)
        # time.sleep(1)

    def reset_sleep_timer(self):
        self.sleep_count = time.time()

    def sleep_check(self):
        if time.time() - self.sleep_count > self.sleep_time:
            self.turn_off_screen()

    def turn_on_screen(self):
        LOGGER.info("\033[1m\033[37mTurn on screen\033[0m")
        self.reset_sleep_timer()
        # luma.oled 在初始化时已经完成了设置，这里只需要打开显示
        self.disp.show()  # 打开显示（0xAF命令）
        if hasattr(self, 'last_active') and self.last_active:
            self.last_active.on_disp_status_update("on")
        self.sleep = False

    def turn_off_screen(self):
        if not self.sleep:
            LOGGER.info("\033[1m\033[37mTurn off screen\033[0m")
            # 关闭显示（0xAE命令）
            self.disp.hide()
            if hasattr(self, 'last_active') and self.last_active:
                self.last_active.on_disp_status_update("off")
            self.sleep = True

    def cleanup(self, reset=True):
        # 清空显示
        self.disp.clear()
        if not reset:
            # 显示欢迎屏幕
            welcome_image = _show_welcome(self.disp.width, self.disp.height)
            self.disp.display(welcome_image)
        # luma.oled 的 clear() 方法已经包含了清空和显示，不需要额外的 reset
