import time
import sys
import signal

from pathlib import Path
from PIL import Image, ImageDraw
from until.device.input import KeyListener, ecodes
from until.device.volume import adjust_volume, detect_pcm_controls, toggle_mute, get_volume_percent
from until.log import LOGGER
from until.keymap import get_keymap

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
        # 使用绝对路径打开图片
        logo_path = Path("assets/icons/" + logo_name).resolve()

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
        self.turn_on_screen()
        self.disp.contrast(CONTRAST)  # 128 is the default contrast value
        self.welcome()

        # init variables
        self.key_listener = KeyListener()
        self.last_active = None
        self.active_id = 0
        self.last_screen_image = None
        self.main_screen = Image.new("1", (self.disp.width, self.disp.height), 0)
        self.anim = Animation(ANIMATION_DURATION)
        self.anim.reset("main_screen")

        # init keymap
        self.keymap = get_keymap()

        # init overlay manager
        self.overlay_manager = OverlayManager(self.disp.width, self.disp.height)

        # init sleep
        self.sleep = False
        self.sleep_time = 10 * 60  # 10 minutes idle time
        self.sleep_count = time.time()

        # init volume long press
        self.volume_adjust_interval = 0.03  # 30ms interval for comfortable volume adjustment
        self.last_volume_adjust_time = 0
        self.volume_adjusting = False
        self.is_muted = False  # 跟踪静音状态

        # initialize plugins
        self.plugins = []

        # register signal handler
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

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

    def _adjust_volume_with_interval(self, direction):
        """Adjust volume with interval control for comfortable long press"""
        if not self.volume_adjusting:
            return  # Don't adjust if not currently pressing

        current_time = time.time()
        if current_time - self.last_volume_adjust_time >= self.volume_adjust_interval:
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
            self.last_volume_adjust_time = current_time

    def _signal_handler(self, signum, frame):
        """handle the termination signal"""
        LOGGER.info(f"get signal {signum}, cleaning up...")
        self.cleanup()
        sys.exit(0)

    # 处理按键事件
    def key_callback(self, evt):
        """handle the key event"""
        
        # 获取全局按键
        key_next_screen = self.keymap.action_next
        key_previous_screen = self.keymap.action_previous
        key_volume_up = self.keymap.media_volume_up
        key_volume_down = self.keymap.media_volume_down
        key_volume_mute = self.keymap.media_volume_mute

        # 获取导航键
        key_nav_left = self.keymap.nav_left
        key_nav_right = self.keymap.nav_right
        key_nav_up = self.keymap.nav_up
        key_nav_down = self.keymap.nav_down

        keycode = evt.code
        active_plugin = self.last_active
        exclusive_nav = bool(
            active_plugin and hasattr(active_plugin, "wants_exclusive_input")
            and active_plugin.wants_exclusive_input()
        )

        # 判断按键类别
        nav_left = keycode in key_nav_left
        nav_right = keycode in key_nav_right
        nav_up = keycode in key_nav_up
        nav_down = keycode in key_nav_down
        next_screen_key = keycode in key_next_screen
        prev_screen_key = keycode in key_previous_screen
        volume_up_key = keycode in key_volume_up
        volume_down_key = keycode in key_volume_down
        is_volume_mute = keycode in key_volume_mute

        # 方向键在独占模式下不会触发全局操作
        allow_nav_for_screen = not exclusive_nav
        allow_nav_for_volume = not exclusive_nav

        is_volume_up = volume_up_key or (allow_nav_for_volume and nav_up)
        is_volume_down = volume_down_key or (allow_nav_for_volume and nav_down)

        if evt.value == 1:  # key down
            if self.sleep:
                self.turn_on_screen()
            else:
                # Screen switching: next_screen/previous_screen or left/right
                if next_screen_key or (allow_nav_for_screen and nav_right):
                    self.active_next()

                if prev_screen_key or (allow_nav_for_screen and nav_left):
                    self.active_prev()

                # Volume adjustment on initial press
                if is_volume_up:
                    self.volume_adjusting = True
                    self._adjust_volume_with_interval("up")

                if is_volume_down:
                    self.volume_adjusting = True
                    self._adjust_volume_with_interval("down")

                # Volume mute toggle
                if is_volume_mute:
                    self.is_muted = toggle_mute()
                    if self.is_muted is not None:
                        # 显示静音状态
                        if self.is_muted:
                            self.overlay_manager.show_volume(0)
                        else:
                            volume = get_volume_percent()
                            if volume is not None:
                                self.overlay_manager.show_volume(volume)

        elif evt.value == 2:  # key repeat (long press)
            if not self.sleep:
                # Continue volume adjustment during long press
                if is_volume_up:
                    self._adjust_volume_with_interval("up")

                if is_volume_down:
                    self._adjust_volume_with_interval("down")

        elif evt.value == 0:  # key release
            # Reset volume adjusting flag and timer
            if is_volume_up or is_volume_down:
                self.volume_adjusting = False
                self.last_volume_adjust_time = 0

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

                try:
                    self.last_active.update()
                    image = self.last_active.get_image()
                    screen_offset = 128

                    if self.last_screen_image is not None:
                        self.main_screen.paste(self.last_screen_image, (0, 0))

                    if self.anim.is_running("main_screen"):
                        screen_offset = round(
                            self.anim.run("main_screen", self.disp.width)
                        )
                        framerate = 1.0 / 60.0
                    else:
                        framerate = self.last_active.framerate
                        self.last_screen_image = None

                    # Calculate offset based on animation direction
                    if self.anim.direction == 1:  # forward (next)
                        paste_x = 128 - screen_offset
                    else:  # backward (previous)
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
        time.sleep(1)

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
        self.sleep = False

    def turn_off_screen(self):
        if not self.sleep:
            LOGGER.info("\033[1m\033[37mTurn off screen\033[0m")
            # 关闭显示（0xAE命令）
            self.disp.hide()
            self.sleep = True

    def cleanup(self, reset=True):
        # 清空显示
        self.disp.clear()
        if not reset:
            # 显示欢迎屏幕
            welcome_image = _show_welcome(self.disp.width, self.disp.height)
            self.disp.display(welcome_image)
        # luma.oled 的 clear() 方法已经包含了清空和显示，不需要额外的 reset
