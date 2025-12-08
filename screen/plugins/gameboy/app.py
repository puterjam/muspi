import json
import platform
import threading
import time
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image, ImageOps, ImageDraw

import dataclasses

from screen.base import DisplayPlugin
from until.keymap import get_keymap
from until.log import LOGGER
from ui.animation import Animation, Operator
from ui.component import draw_scroll_text


def _patch_dataclasses_for_libretro():
    """
    libretro.py 的 ctypes 结构没有文档字符串，dataclasses 会尝试读取
    inspect.signature 导致 ValueError。这里提前为这些结构补一个 docstring，
    让 dataclasses 跳过签名注入逻辑。
    """
    flag_name = "_libretro_doc_patch"
    if getattr(dataclasses, flag_name, False):
        return

    original = dataclasses._process_class  # type: ignore[attr-defined]

    def patched_process_class(cls, *args, **kwargs):
        module_name = getattr(cls, "__module__", "")
        if not getattr(cls, "__doc__", None) and module_name.startswith("libretro."):
            cls.__doc__ = f"{cls.__name__} structure"
        return original(cls, *args, **kwargs)

    dataclasses._process_class = patched_process_class  # type: ignore[assignment]
    setattr(dataclasses, flag_name, True)


_patch_dataclasses_for_libretro()

from pyarduboy.core import PyArduboy

try:
    from pyarduboy.drivers.audio.alsa import AlsaAudioDriver  # type: ignore
except Exception:  # pragma: no cover - ALSA 可能不可用
    AlsaAudioDriver = None

from pyarduboy.drivers.audio.null import NullAudioDriver


class gameboy(DisplayPlugin):
    """
    使用 PyArduboy 运行 Arduboy/Gearboy 游戏的 Muspi 插件

    - 游戏循环在独立线程中运行
    - 主渲染线程只负责把帧缓冲缩放到 OLED
    - 音频和输入都在工作线程中处理，保证 Muspi 主循环不卡顿
    """

    DEFAULT_CONFIG = {
        "rom": None,                      # None 表示显示 ROM 选择菜单
        "core": None,
        "core_name": None,
        "retro_path": None,               # None 表示使用插件目录下的 retro/
        "audio_driver": "auto",          # auto/alsa/pyaudio/null
        "pause_when_inactive": True,
        "threshold": 90,                  # 黑白阈值
        "frame_rate": 60.0,               # Muspi 渲染帧率
        "target_fps": 60,                 # 模拟器逻辑帧率
    }

    def __init__(self, manager, width, height):
        self.name = "gameboy"
        LOGGER.info("Gameboy 插件: 初始化插件")

        super().__init__(manager, width, height)
        # 运行参数
        self.keymap = get_keymap()
        self._config = self._load_config()
        self.framerate = float(self._config.get("frame_rate", 20.0))
        self._display_threshold = int(self._config.get("threshold", 90))
        self._pause_when_inactive = bool(self._config.get("pause_when_inactive", True))
        self._exclusive_input = False
        self._target_fps = max(1, int(self._config.get("target_fps", 60)))

        # ROM 列表和选择
        self._rom_list = self._load_rom_list()
        self._selected_rom_index = 0
        self._current_rom_path: Optional[Path] = None
        self._show_menu = True  # 是否显示菜单
        self._animation = Animation(0.28)
        self._menu_slide_offset = 0.0
        self._menu_prev_index: Optional[int] = None
        self._menu_slide_direction = 0
        self._thumbnail_cache: dict[Path, Image.Image] = {}
        self._scrollbar_hidden_offset = 4.0
        self._scrollbar_offset = self._scrollbar_hidden_offset
        self._scrollbar_last_move = 0.0
        self._scrollbar_hide_delay = 1.2
        self._scrollbar_visible = False
        self._scrollbar_thumb_progress = 0.0
        self._bottom_bar_height = 11

        # retro_path: 模拟器工作目录（存档、系统文件等）
        retro_path_config = self._config.get("retro_path")
        if retro_path_config:
            self._retro_path = Path(retro_path_config).expanduser()
        else:
            # 默认使用插件目录下的 retro/ 子目录
            self._retro_path = self.user_path / "retro"
        self._retro_path.mkdir(parents=True, exist_ok=True)

        # core_path: libretro 核心文件路径
        self._core_path = self._resolve_core_path(
            self._config.get("core"),
            self._config.get("core_name")
        )

        self._audio_backend = (self._config.get("audio_driver") or "auto").lower()

        # 状态
        self._status = "Loading Game..." if self._rom_list else "Put Game ROM to ./roms"
        self._last_frame_ts = 0.0
        self._emulator_ready = False
        self._thread_stop = threading.Event()
        self._loop_gate = threading.Event()
        if not self._pause_when_inactive:
            self._loop_gate.set()

        # 输入与输出
        self._frame_lock = threading.Lock()
        self._input_lock = threading.Lock()
        self._current_frame: Optional[np.ndarray] = None
        self._input_state = {
            "up": False,
            "down": False,
            "left": False,
            "right": False,
            "a": False,
            "b": False,
            "select": False,
            "start": False,
        }
        self._reset_request = threading.Event()

        # 游戏状态管理
        self._paused_game: Optional[Path] = None  # 当前暂停的游戏

        # 组合键状态追踪
        self._combo_keys_pressed = {
            "select": False,
            "cancel": False,
            "up": False,
            "down": False,
        }

        self.arduboy: Optional[PyArduboy] = None
        self._audio_driver = None
        self._worker: Optional[threading.Thread] = None

        # 如果配置文件指定了 ROM,直接启动
        rom_setting = self._config.get("rom")
        if rom_setting:
            self._current_rom_path = self._resolve_single_game_path(rom_setting)
            if self._current_rom_path:
                self._show_menu = False
                self._start_worker()
            else:
                LOGGER.error("Gameboy 插件: 配置的 ROM 不存在 -> %s", rom_setting)

    # ------------------------------------------------------------------ #
    # muspi生命周期

    def set_active(self, value):
        super().set_active(value)

        if value:
            self.manager.key_listener.on(self.key_callback)
            self._loop_gate.set()
        else:
            self.manager.key_listener.off(self.key_callback)
            if self._pause_when_inactive:
                self._loop_gate.clear()
            self._reset_inputs()

    def wants_exclusive_input(self) -> bool:
        # 菜单模式下不独占输入，允许系统切换
        if self._show_menu:
            return False
        return self._exclusive_input and self.is_active

    def event_listener(self):
        # 线程健康检查
        if self._worker and not self._worker.is_alive() and self._emulator_ready:
            self._status = "Quit Game Thread."
            self._emulator_ready = False

        # 只要有新帧就保持屏幕唤醒
        if self.is_active and (time.time() - self._last_frame_ts) < 0.5:
            self.manager.reset_sleep_timer()

    # ------------------------------------------------------------------ #
    # muspi渲染

    def render(self):
        self.clear()

        # 如果在菜单模式，显示游戏选择界面
        if self._show_menu:
            self._draw_menu()
            return

        # 游戏运行模式
        frame_img = None
        with self._frame_lock:
            if self._current_frame is not None:
                frame_img = self._convert_frame(self._current_frame)

        if frame_img:
            self.image.paste(frame_img)
            # 简单状态提示（运行中显示核心名称）
            if not self._emulator_ready:
                self._draw_status("wait for frames.")
        else:
            self._draw_status(self._status)

    # ------------------------------------------------------------------ #
    # muspi输入处理

    def key_callback(self, evt):
        pressed = evt.value != 0
        keycode = evt.code

        # 菜单模式下的按键处理
        if self._show_menu:
            self._handle_menu_key(keycode, pressed)
            return

        # 游戏模式下的按键处理
        # 检测 action_menu 按键快速返回选单
        if self.keymap.action_menu and keycode in self.keymap.action_menu and pressed:
            self._exit_to_menu()
            return

        # 更新组合键状态（备用退出方式）
        self._update_combo_key_state(keycode, pressed)

        # 检测组合键: action_select + action_cancel + nav_up（备用退出方式）
        if self._check_exit_combo():
            self._exit_to_menu()
            return
        if self._check_screenshot_combo():
            self._take_screenshot()

        mapping = (
            ("up", self.keymap.nav_up),
            ("down", self.keymap.nav_down),
            ("left", self.keymap.nav_left),
            ("right", self.keymap.nav_right),
            ("a", self.keymap.action_select),
            ("b", self.keymap.action_cancel),
            ("start", self.keymap.action_menu),
            ("select", self.keymap.media_play_pause),
        )

        for button, key_list in mapping:
            if key_list and keycode in key_list:
                self._set_button_state(button, pressed)

        # media_stop 作为快速复位
        if self.keymap.media_stop and keycode in self.keymap.media_stop and evt.value == 1:
            self._reset_request.set()

        # action_screenshot 截图
        if self.keymap.action_screenshot and keycode in self.keymap.action_screenshot and evt.value == 1:
            self._take_screenshot()

    # ------------------------------------------------------------------ #
    # 工作线程和模拟器相关

    def _start_worker(self):
        if self._worker and self._worker.is_alive():
            return

        self._worker = threading.Thread(target=self._game_loop, name="GameboyWorker", daemon=True)
        self._worker.start()

    def _game_loop(self):
        if not self._prepare_emulator():
            LOGGER.error("Emulator initialization failed, stopping thread.")
            return

        LOGGER.info("Emulator thread started.")
        frame_interval = 1.0 / self._target_fps

        while not self._thread_stop.is_set():
            if self._pause_when_inactive and not self._loop_gate.is_set():
                time.sleep(0.05)
                continue

            if not self.arduboy or not self.arduboy.bridge:
                break

            if not self.arduboy.bridge.is_running:
                self.arduboy.bridge.start()

            frame_start = time.perf_counter()

            try:
                # 输入处理
                self._apply_input_state()

                # 重置处理
                self._handle_pending_reset()
                
                # 运行帧
                self.arduboy.bridge.run_frame()
                
                # 捕获帧
                self._capture_frame()

                # 音频处理
                self._pump_audio()

            except Exception as exc:
                LOGGER.error("Running frame failed - %s", exc, exc_info=True)
                self._status = f"Running exception: {exc}"
                time.sleep(0.5)

            elapsed = time.perf_counter() - frame_start

            if elapsed < frame_interval:
                time.sleep(frame_interval - elapsed)

    def _prepare_emulator(self) -> bool:
        try:
            if not self._current_rom_path:
                self._status = "No game selected."
                return False

            kwargs = {
                "game_path": str(self._current_rom_path),
                "target_fps": self._target_fps,
                "retro_path": str(self._retro_path),
            }

            # 使用解析好的核心路径
            if self._core_path:
                kwargs["core_path"] = str(self._core_path)

            LOGGER.info("initialize emulator - %s", kwargs)
            self.arduboy = PyArduboy(**kwargs)

            if not self.arduboy.initialize():
                self._status = "initialize emulator failed."
                return False

            if not self.arduboy.bridge.start():
                self._status = "Launch emulator failed."
                return False

            self._audio_driver = self._init_audio_driver()
            self._emulator_ready = True
            self._status = "Game started."
            return True

        except FileNotFoundError as exc:
            self._status = f"File not found: {exc}"
            LOGGER.error("%s", exc)
        except Exception as exc:  # pragma: no cover
            self._status = f"Initialization exception: {exc}"
            LOGGER.error("Initialization failed", exc_info=True)

        return False

    def _init_audio_driver(self):
        sample_rate = 44100
        # if self.arduboy:
        #     sample_rate = self.arduboy.bridge.get_audio_sample_rate(default=sample_rate)
        #     LOGGER.info("Emulator sample rate: %d", sample_rate)

        backends = []
        if self._audio_backend == "auto":
            backends = ["alsa", "null"]
        else:
            backends = [self._audio_backend]

        for backend in backends:
            if backend == "alsa" and AlsaAudioDriver:
                try:
                    driver = AlsaAudioDriver()
                    if driver.init(sample_rate=sample_rate):
                        LOGGER.info("Using ALSA audio (%d Hz)", sample_rate)
                        return driver
                except Exception as exc:
                    LOGGER.warning("ALSA audio initialization failed - %s", exc)
                    continue
            if backend == "null":
                driver = NullAudioDriver()
                driver.init(sample_rate=sample_rate)
                LOGGER.info("Using null audio driver")
                return driver

        LOGGER.warning("No audio driver found, audio output disabled")
        return None

    def _apply_input_state(self):
        if not self.arduboy:
            return

        with self._input_lock:
            state = dict(self._input_state)

        self.arduboy.bridge.set_input_state(state)

    def _capture_frame(self):
        if not self.arduboy:
            return

        frame = self.arduboy.bridge.get_frame()
        if frame is None:
            return

        with self._frame_lock:
            self._current_frame = frame.copy()
            self._last_frame_ts = time.time()

    def _pump_audio(self):
        if not (self.arduboy and self._audio_driver):
            return

        samples = self.arduboy.bridge.get_audio_samples()
        if samples is None:
            return

        try:
            self._audio_driver.play_samples(samples)
        except Exception as exc:  # pragma: no cover
            LOGGER.warning("Audio playback failed - %s", exc)

    def _handle_pending_reset(self):
        if not (self.arduboy and self._reset_request.is_set()):
            return

        self._reset_request.clear()
        LOGGER.info("Resetting current game")
        try:
            self.arduboy.bridge.reset()
        except Exception as exc:
            LOGGER.error("Reset failed - %s", exc)

    # ------------------------------------------------------------------ #
    # 辅助工具

    def _load_config(self):
        config = dict(self.DEFAULT_CONFIG)
        config_path = Path("config/plugins.json")

        if not config_path.exists():
            return config

        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
            for plugin_conf in data.get("plugins", []):
                if plugin_conf.get("name") == self.name:
                    config.update(plugin_conf.get("config", {}))
                    break
        except Exception as exc:
            LOGGER.warning("load config failed - %s", exc)

        return config

    def _load_rom_list(self) -> list[Path]:
        """从 roms 目录加载所有可用的 ROM 文件"""
        roms_dir = self.user_path / "roms"
        if not roms_dir.exists():
            LOGGER.warning("ROM directory does not exist -> %s", roms_dir)
            return []

        rom_list = sorted(roms_dir.glob("*.hex"))
        LOGGER.info("Found %d ROM files", len(rom_list))
        return rom_list

    def _resolve_single_game_path(self, rom_setting: str) -> Optional[Path]:
        """解析单个游戏路径（用于配置文件指定的 ROM）"""
        candidate = Path(rom_setting).expanduser()
        if not candidate.is_absolute():
            candidate = self.user_path / candidate
        if candidate.exists():
            return candidate
        LOGGER.warning("Specified ROM does not exist -> %s", candidate)
        return None

    def _resolve_core_path(self, core_path_setting: Optional[str], core_name_setting: Optional[str]) -> Optional[Path]:
        """
        解析 libretro 核心文件路径

        优先级：
        1. 如果指定了 core_path，使用指定路径
        2. 如果指定了 core_name，在插件 core/ 目录查找对应核心
        3. 否则在插件 core/ 目录按优先级查找：arduous > ardens > gearboy
        """
        # 优先使用指定的核心路径
        if core_path_setting:
            candidate = Path(core_path_setting).expanduser()
            if candidate.exists():
                LOGGER.info("Using specified core -> %s", candidate)
                return candidate
            LOGGER.warning("Specified core does not exist -> %s", candidate)

        # 核心目录
        core_dir = self.work_path / "core"
        if not core_dir.exists():
            LOGGER.warning("Core directory does not exist -> %s", core_dir)
            return None

        # 确定要搜索的核心名称列表
        if core_name_setting:
            core_names = [core_name_setting]
        else:
            # 默认优先级：arduous > ardens > gearboy
            core_names = ["arduous", "ardens", "gearboy"]

        # 查找核心文件
        lib_ext = "so" if platform.system() == "Linux" else ("dylib" if platform.system() == "Darwin" else "dll")

        for core_name in core_names:
            core_file = core_dir / f"{core_name}_libretro.{lib_ext}"
            if core_file.exists():
                LOGGER.info("Using core %s -> %s", core_name, core_file)
                return core_file

        LOGGER.warning("Core file not found in %s", core_dir)
        return None

    def _set_button_state(self, button: str, pressed: bool):
        with self._input_lock:
            self._input_state[button] = pressed

    def _reset_inputs(self):
        with self._input_lock:
            for key in self._input_state:
                self._input_state[key] = False

    def _convert_frame(self, frame: np.ndarray) -> Optional[Image.Image]:
        if frame.dtype != np.uint8:
            frame = frame.astype(np.uint8)

        img = Image.fromarray(frame, mode="RGB")
        img = ImageOps.autocontrast(img.convert("L"), cutoff=2)

        scale = min(self.width / img.width, self.height / img.height)
        if scale <= 0:
            scale = 1

        new_size = (
            max(1, int(img.width * scale)),
            max(1, int(img.height * scale)),
        )

        resized = img.resize(new_size, Image.BILINEAR)
        mono = resized.point(lambda v, thr=self._display_threshold: 255 if v > thr else 0, mode="1")

        canvas = Image.new("1", (self.width, self.height), 0)
        offset = ((self.width - new_size[0]) // 2, (self.height - new_size[1]) // 2)
        canvas.paste(mono, offset)
        return canvas

    @staticmethod
    def _wrap_text(text: str, width: int):
        result = []
        current = ""
        for char in text:
            current += char
            if len(current) >= width:
                result.append(current)
                current = ""
        if current:
            result.append(current)
        return result


    # ------------------------------------------------------------------ #
    # UI&菜单相关功能

    def _draw_status(self, text: str):
        draw = self.canvas
        message = text or "Gameboy"
        lines = self._wrap_text(message, 16)
        y = (self.height - len(lines) * 10) // 2
        for idx, line in enumerate(lines):
            font = self.font10 if idx == 0 else self.font8
            # draw.text((4, max(0, y + idx * 11)), line, font=font, fill=255)
            draw_scroll_text(draw, line, (4, max(0, y + idx * 11)), width=self.width, font=font, align="center")
            
            
    def _draw_menu(self):
        draw = self.canvas
        
        """绘制游戏选择菜单"""
        if not self._rom_list:
            draw_scroll_text(draw, "☹ No Game found.", (0, self.height // 2 -6), width=self.width, font=self.font10, align="center")
            draw_scroll_text(draw, "Put Arduboy Game to ./roms ", (0, self.height // 2 +6), width=self.width, font=self.font8, align="center")
            # self.canvas.text((4, self.height // 2 - 5), "No games found", font=self.font10, fill=255)
            return

        self._animation.update()
        self._maybe_hide_scrollbar()

        active_rom = self._rom_list[self._selected_rom_index]
        has_transition = (
            self._menu_prev_index is not None and
            self._is_animation_running("menu_slide")
        )

        # 渲染卡片
        if has_transition and self._menu_prev_index is not None:
            slide_offset = self._menu_slide_offset
            direction = -1 if self._menu_slide_direction < 0 else 1
            previous_rom = self._rom_list[self._menu_prev_index]
            previous_offset = slide_offset - direction * self.height
            self._render_menu_card(previous_rom, previous_offset, self._menu_prev_index)
            self._render_menu_card(active_rom, slide_offset, self._selected_rom_index)
        else:
            self._menu_prev_index = None
            self._menu_slide_direction = 0
            self._menu_slide_offset = 0.0
            self._render_menu_card(active_rom, 0, self._selected_rom_index)

        # 绘制底部栏
        self._draw_bottom_bar()
        
        # 绘制滚动条
        self._draw_scrollbar()

    def _render_menu_card(self, rom: Path, y_offset: float, rom_index: int):
        """渲染全屏游戏卡片"""
        offset = int(round(y_offset))
        card = self._get_rom_visual(rom)
        if card:
            self.image.paste(card, (0, offset))

        # 额外状态（例如暂停）不在卡片上绘制，统一放在底部栏

    def _draw_bottom_bar(self):
        """绘制固定底部信息栏"""
        draw = self.canvas
        bar_height = self._bottom_bar_height
        bar_top = self.height - bar_height
        if bar_top <= 0:
            return
        draw.rectangle((0, bar_top - 1, self.width, bar_top), fill=255)
        draw.rectangle((0, bar_top, self.width, self.height), fill=0)

        if self._rom_list:

            current_rom = self._rom_list[self._selected_rom_index]
            if self._paused_game == current_rom:
                button = " Select  Restart"
                draw.text((4, bar_top + 2), button, font=self.font8, fill=255)
                paused_text = "Paused"
                paused_bbox = self.font8.getbbox(paused_text)
                paused_width = paused_bbox[2] - paused_bbox[0]
                draw.text((self.width - paused_width, bar_top + 2), paused_text, font=self.font8, fill=255)
            else:
                button = " Select  Start"
                draw.text((4, bar_top + 2), button, font=self.font8, fill=255)

    def _get_rom_visual(self, rom: Path) -> Image.Image:
        """获取 ROM 对应的封面或者文字卡片"""
        cached = self._thumbnail_cache.get(rom)
        if cached is not None:
            return cached

        cover = self._load_cover_image(rom)
        if cover is None:
            cover = self._create_text_card(rom)

        self._thumbnail_cache[rom] = cover
        return cover

    def _load_cover_image(self, rom: Path) -> Optional[Image.Image]:
        """加载游戏封面"""
        cover_path = self._retro_path / "thumbnails" / "arduboy" / "Snaps" / f"{rom.stem}.png"
        if not cover_path.exists():
            return None

        try:
            with Image.open(cover_path) as img:
                gray = img.convert("L")
                fitted = ImageOps.fit(gray, (self.width, self.height), Image.BILINEAR)
                contrasted = ImageOps.autocontrast(fitted, cutoff=2)
                mono = contrasted.point(lambda v: 255 if v > self._display_threshold else 0, mode="1")
                return mono
        except Exception as exc:
            LOGGER.warning("加载封面失败 -> %s: %s", cover_path, exc)
        return None

    def _create_text_card(self, rom: Path) -> Image.Image:
        """创建没有封面时的文字卡片"""
        card = Image.new("1", (self.width, self.height), 0)
        draw = ImageDraw.Draw(card)
        name = rom.stem or "No Title"
        lines = self._wrap_text(name, 12)
        metrics = []
        for line in lines:
            font = self._select_title_font(line)
            bbox = font.getbbox(line)
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
            metrics.append((line, font, width, height))

        total_height = sum(item[3] for item in metrics) + max(0, len(metrics) - 1) * 2
        y = (self.height - total_height) // 2 - 10 

        for line, font, text_width, text_height in metrics:
            x = (self.width - text_width) // 2
            draw.text((x, y), line, font=font, fill=255)
            y += text_height + 2

        return card

    def _select_title_font(self, text: str):
        if len(text) <= 8:
            return self.font16
        if len(text) <= 12:
            return self.font12
        return self.font10

    def _change_selection(self, delta: int):
        """基于方向调整选中游戏"""
        if not self._rom_list:
            return

        previous_index = self._selected_rom_index
        total = len(self._rom_list)
        self._selected_rom_index = (self._selected_rom_index + delta) % total

        if self._selected_rom_index == previous_index:
            return

        direction = 1 if delta > 0 else -1
        self._menu_prev_index = previous_index
        self._menu_slide_direction = direction
        self._menu_slide_offset = self.height * direction
        self._animation.start(
            "menu_slide",
            self,
            "_menu_slide_offset",
            0.0,
            duration=0.25,
            operator=Operator.ease_out_cubic,
        )
        self._scrollbar_last_move = time.time()
        self._show_scrollbar()
        self._animate_scrollbar_thumb()

    def _is_animation_running(self, anim_id: str) -> bool:
        return anim_id in self._animation.animation_list and self._animation.is_running(anim_id)

    def _show_scrollbar(self):
        """滚动条划入"""
        if self._scrollbar_offset <= 0.1 and self._scrollbar_visible:
            return
        self._scrollbar_visible = True
        self._animation.start(
            "scrollbar",
            self,
            "_scrollbar_offset",
            0.0,
            duration=0.2,
            operator=Operator.ease_out_cubic,
        )

    def _animate_scrollbar_thumb(self):
        """平滑滚动滑块"""
        if len(self._rom_list) <= 1:
            self._scrollbar_thumb_progress = 0.0
            return

        target = self._selected_rom_index / (len(self._rom_list) - 1)
        target = max(0.0, min(1.0, target))
        self._animation.start(
            "scrollbar_thumb",
            self,
            "_scrollbar_thumb_progress",
            target,
            duration=0.18,
            operator=Operator.ease_out_cubic,
        )

    def _maybe_hide_scrollbar(self):
        """自动隐藏滚动条"""
        if not self._scrollbar_visible:
            return

        if (time.time() - self._scrollbar_last_move) < self._scrollbar_hide_delay:
            return

        self._scrollbar_visible = False
        self._animation.start(
            "scrollbar",
            self,
            "_scrollbar_offset",
            self._scrollbar_hidden_offset,
            duration=0.2,
            operator=Operator.ease_in_out_quad,
        )

    def _draw_scrollbar(self):
        """绘制滚动条"""
        if not self._rom_list:
            return

        base_x = self.width - 3 + int(round(self._scrollbar_offset))
        right_x = base_x + 2
        if base_x >= self.width or right_x < 0:
            return

        track_top = 0
        track_bottom = self.height - self._bottom_bar_height - 2
        if track_bottom <= track_top:
            return

        draw = self.canvas
        # draw.line((base_x, track_top, base_x, track_bottom), fill=0, width=1)
        draw.line((base_x + 1, track_top, base_x + 1, track_bottom), fill=0, width=1)
        draw.line((base_x + 2, track_top, base_x + 2, track_bottom), fill=0, width=1)

        rom_count = len(self._rom_list)
        track_range = track_bottom - track_top
        if rom_count <= 1:
            slider_height = track_range
        else:
            slider_height = max(10, int(track_range / rom_count))
        slider_height = min(track_range, slider_height)

        if rom_count <= 1:
            slider_top = track_top
        else:
            progress = max(0.0, min(1.0, self._scrollbar_thumb_progress))
            max_offset = max(0, track_range - slider_height)
            slider_top = track_top + int(round(progress * max_offset))
        slider_bottom = min(track_bottom, slider_top + slider_height)
        draw.rectangle((base_x+2, slider_top, right_x, slider_bottom), fill=255)


    # ------------------------------------------------------------------ #
    # 用户交互功能
    
    def _handle_menu_key(self, keycode: int, pressed: bool):
        """处理菜单模式下的按键"""
        if not pressed:  # 只响应按下事件
            return

        if not self._rom_list:
            return

        # 上下导航
        if self.keymap.nav_up and keycode in self.keymap.nav_up:
            self._change_selection(-1)
        elif self.keymap.nav_down and keycode in self.keymap.nav_down:
            self._change_selection(1)

        # 选择游戏（action_select）
        elif self.keymap.action_select and keycode in self.keymap.action_select:
            self._load_selected_game()

    def _load_selected_game(self):
        """加载选中的游戏"""
        if not self._rom_list or self._selected_rom_index >= len(self._rom_list):
            return

        selected_rom = self._rom_list[self._selected_rom_index]

        # 检查是否是当前暂停的游戏
        if self._paused_game == selected_rom and self.arduboy:
            # 恢复游戏
            LOGGER.info("Resuming game -> %s", selected_rom.name)
            self._show_menu = False
            self._exclusive_input = True
            self._loop_gate.set()
        else:
            # 加载新游戏
            self._stop_current_game()
            self._current_rom_path = selected_rom
            self._paused_game = None
            self._show_menu = False
            self._exclusive_input = True
            # 确保游戏循环可以运行（新游戏需要立即启动）
            self._loop_gate.set()
            LOGGER.info("Loading game -> %s", selected_rom.name)
            self._start_worker()

    def _update_combo_key_state(self, keycode: int, pressed: bool):
        """更新组合键状态"""
        if self.keymap.action_select and keycode in self.keymap.action_select:
            self._combo_keys_pressed["select"] = pressed
        elif self.keymap.action_cancel and keycode in self.keymap.action_cancel:
            self._combo_keys_pressed["cancel"] = pressed
        elif self.keymap.nav_up and keycode in self.keymap.nav_up:
            self._combo_keys_pressed["up"] = pressed
        elif self.keymap.nav_down and keycode in self.keymap.nav_down:
            self._combo_keys_pressed["down"] = pressed

    def _check_exit_combo(self) -> bool:
        """检测退出组合键: action_select + action_cancel + nav_up 同时按下"""
        return (
            self._combo_keys_pressed["select"] and
            self._combo_keys_pressed["cancel"] and
            self._combo_keys_pressed["up"]
        )

    def _check_screenshot_combo(self) -> bool:
        """检测截图组合键: action_select + action_cancel + nav_down 同时按下"""
        return (
            self._combo_keys_pressed["select"] and
            self._combo_keys_pressed["cancel"] and
            self._combo_keys_pressed["down"]
        )
        
    def _exit_to_menu(self):
        """退出游戏回到选单"""
        LOGGER.info("Exiting game to menu")
        self._show_menu = True
        self._exclusive_input = False
        self._paused_game = self._current_rom_path
        self._loop_gate.clear()  # 暂停游戏循环
        self._reset_inputs()
        # 清空组合键状态
        for key in self._combo_keys_pressed:
            self._combo_keys_pressed[key] = False
        self._combo_screenshot_triggered = False

    def _stop_current_game(self):
        """停止当前游戏"""
        # 停止工作线程
        if self._worker and self._worker.is_alive():
            self._thread_stop.set()
            self._worker.join(timeout=2.0)

        # 无论线程是否存活，都要清除停止标志，为新线程做准备
        self._thread_stop.clear()

        # 关闭模拟器
        if self.arduboy:
            try:
                self.arduboy.shutdown()
            except Exception as exc:
                LOGGER.warning("Shutting down emulator failed - %s", exc)
            self.arduboy = None

        # 关闭音频驱动
        if self._audio_driver:
            try:
                self._audio_driver.close()
            except Exception as exc:
                LOGGER.warning("Closing audio driver failed - %s", exc)
            self._audio_driver = None

        # 重置状态
        self._emulator_ready = False
        self._current_frame = None
        self._worker = None

    def _take_screenshot(self):
        LOGGER.info("Taking screenshot.")
        """截取当前游戏帧并保存为 PNG 图片"""
        if not self._current_rom_path or self._show_menu:
            LOGGER.warning("Screenshot failed: not in game mode")
            return

        # 获取当前帧
        frame = None
        with self._frame_lock:
            if self._current_frame is not None:
                frame = self._current_frame.copy()

        if frame is None:
            LOGGER.warning("Screenshot failed: no frame available")
            return

        try:
            # 创建截图保存目录
            screenshot_dir = self._retro_path / "thumbnails" / "arduboy" / "Snaps"
            screenshot_dir.mkdir(parents=True, exist_ok=True)

            # 生成文件名: ROM 名字.png
            rom_name = self._current_rom_path.stem
            screenshot_path = screenshot_dir / f"{rom_name}.png"

            # 将帧转换为 RGB PIL Image
            if frame.dtype != np.uint8:
                frame = frame.astype(np.uint8)

            img = Image.fromarray(frame, mode="RGB")

            # 保存为 PNG
            img.save(screenshot_path, "PNG")
            LOGGER.info("Screenshot saved -> %s", screenshot_path)
            if self._current_rom_path:
                self._thumbnail_cache.pop(self._current_rom_path, None)

        except Exception as exc:
            LOGGER.error("Screenshot failed - %s", exc, exc_info=True)
