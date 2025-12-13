import os
import threading
import time
from typing import List, Optional

import numpy as np

from screen.base import DisplayPlugin
from until.config import config as config_loader
from until.log import LOGGER
from ui.component import draw_scroll_text
from until.keymap import get_keymap

try:
    import alsaaudio

    ALSA_AVAILABLE = True
except ImportError:
    ALSA_AVAILABLE = False
    alsaaudio = None


class spectrum(DisplayPlugin):
    CONFIG_FILE = "config.json"
    DEFAULT_CONFIG = {
        "device": "", #音频设备，留空自动检测
        "sample_rate": 44100, #采样率，影响频域分辨率
        "chunk_size": 1024, #采样数据大小，影响频域分辨率
        "fft_size": 2048, #FFT窗口大小，影响频域分辨率
        "min_frequency": 40, #最小频率，影响频域显示范围
        "db_floor": -70.0, #dB.floor，影响频域显示范围
        "db_ceiling": -15.0, #dB.ceiling，影响频域显示范围
        "gain_db": 0.0, #dB.gain，影响频域显示范围
        "signal_threshold": 0.003, #峰值振幅，判断是否静音
        "bar_signal_threshold": 0.05, #频域最大条，判断是否静音
        "silence_hold": 0.25, #静音判断时间
        "bar_gamma": 0.5, #频域条高度指数
        "rise_smoothing": 0.35, #频域条高度上升平滑
        "decay_smoothing": 0.65, #频域条高度下降平滑
        "peak_decay": 0.02, #频域条高度衰减
    }
 
    # 音频设备循环检测列表
    LOOPBACK_CANDIDATES = [
        # "hw:Loopback,1",
        # "hw:Loopback,0",
        # "plughw:Loopback,1",
        # "plughw:Loopback,0",
        "Loopback",
        "default",
    ]

    def __init__(self, manager, width, height):
        self.name = "spectrum"
        super().__init__(manager, width, height)

        self.framerate = 60.0
        self.keymap = get_keymap()

        self._config = self._load_config()
        self.sample_rate = int(self._config.get("sample_rate", 44100))
        self.chunk_size = int(self._config.get("chunk_size", 1024))
        self.fft_size = int(self._config.get("fft_size", 2048))
        self.min_frequency = float(self._config.get("min_frequency", 40))
        self.channels = 2

        self._setup_bars()

        self._window = np.hanning(self.fft_size).astype(np.float32)
        self._freq_axis = np.fft.rfftfreq(self.fft_size, d=1.0 / self.sample_rate)
        self._bin_edges = self._build_frequency_bins()

        self._bars = np.zeros(self._bar_count, dtype=np.float32)
        self._peaks = np.zeros(self._bar_count, dtype=np.float32)
        self._bars_lock = threading.Lock()

        self._sample_buffer = np.zeros(0, dtype=np.float32)
        self._hop_size = max(1, self.fft_size // 2)
        self._db_floor = float(self._config.get("db_floor", -70.0))
        self._db_ceiling = float(self._config.get("db_ceiling", -15.0))
        self._gain_db = float(self._config.get("gain_db", 0.0))
        if self._db_ceiling <= self._db_floor:
            self._db_ceiling = self._db_floor + 10.0

        self._rise_smoothing = float(self._config.get("rise_smoothing", 0.35))
        self._decay_smoothing = float(self._config.get("decay_smoothing", 0.65))
        self._rise_smoothing = min(max(self._rise_smoothing, 0.01), 1.0)
        self._decay_smoothing = min(max(self._decay_smoothing, 0.01), 1.0)
        self._peak_decay = float(self._config.get("peak_decay", 0.05))
        self._peak_decay = min(max(self._peak_decay, 0.001), 1.0)

        self._capture_thread: Optional[threading.Thread] = None
        self._stop_event: Optional[threading.Event] = None
        self._device_label = None
        self._status_message = "Idle"
        self._error_message = None
        self._last_fft_ts = 0.0
        self._avg_level = 0.0

        env_device = os.environ.get("MUSPI_SPECTRUM_DEVICE", "").strip()
        configured = (self._config.get("device") or "").strip()
        self._device_hint = env_device or configured or None

        self._signal_threshold = float(self._config.get("signal_threshold", 0.003))
        self._bar_signal_threshold = float(self._config.get("bar_signal_threshold", 0.05))
        self._silence_hold = float(self._config.get("silence_hold", 0.75))
        self._last_signal_ts = time.time()
        self._bar_gamma = float(self._config.get("bar_gamma", 1.0))
        if self._bar_gamma <= 0:
            self._bar_gamma = 1.0

        if not ALSA_AVAILABLE:
            self._error_message = "Install pyalsaaudio"
            LOGGER.error("pyalsaaudio is not installed; spectrum plugin disabled")

    # 加载插件配置
    def _load_config(self):
        defaults = dict(self.DEFAULT_CONFIG)
        config_path = (self.user_path / self.CONFIG_FILE).expanduser()
        config_path.parent.mkdir(parents=True, exist_ok=True)

        if config_path.exists():
            data = config_loader.open(str(config_path)) or {}
            if isinstance(data, dict):
                for key, value in data.items():
                    if key in defaults:
                        defaults[key] = value
        else:
            config_loader.save(str(config_path), defaults)

        return defaults

    # 设置插件激活状态
    def set_active(self, active):
        was_active = self.is_active
        super().set_active(active)

        if active and not was_active:
            self._start_capture()
            self.manager.key_listener.on(self.key_callback)
        elif not active and was_active:
            self._stop_capture()
            self.manager.key_listener.off(self.key_callback)

    # 处理按键事件
    def key_callback(self, evt):
        # 获取全局功能按键和媒体按键
        key_nav_up = self.keymap.nav_up
        key_nav_down = self.keymap.nav_down

        if evt.value == 1:  # key down
            # volume up/down
            if self.keymap.match(key_nav_up):
                self.manager.adjust_volume("up")

            if self.keymap.match(key_nav_down):
                self.manager.adjust_volume("down")

    # 处理显示状态更新事件
    def on_disp_status_update(self, status: str):
        if status == "off":
            self._stop_capture()
        elif status == "on" and self.is_active:
            self._start_capture()

    # 计算频谱条的数量和间距
    def _setup_bars(self):
        self._bar_spacing = 1
        self._bar_width = 3 if self.width >= 96 else 2
        max_bars = max(8, self.width // (self._bar_width + self._bar_spacing))
        self._bar_count = min(32, max_bars)
        total_width = self._bar_count * self._bar_width + (self._bar_count - 1) * self._bar_spacing
        self._bars_offset = max(0, (self.width - total_width) // 2)

    # 构建频率分箱
    def _build_frequency_bins(self):
        nyquist = self.sample_rate / 2.0
        start_freq = max(10.0, min(self.min_frequency, nyquist))
        end_freq = max(start_freq + 10, nyquist)

        try:
            freq_edges = np.geomspace(start_freq, end_freq, self._bar_count + 1)
        except ValueError:
            freq_edges = np.linspace(start_freq, end_freq, self._bar_count + 1)

        freq_edges = np.clip(freq_edges, 0, nyquist)
        indices = np.searchsorted(self._freq_axis, freq_edges)
        indices = np.clip(indices, 0, len(self._freq_axis) - 1)

        edges: List[int] = indices.tolist()
        for i in range(1, len(edges)):
            if edges[i] <= edges[i - 1]:
                edges[i] = min(len(self._freq_axis) - 1, edges[i - 1] + 1)

        return edges

    # 启动捕获线程
    def _start_capture(self):
        if self._capture_thread and self._capture_thread.is_alive():
            return

        if not ALSA_AVAILABLE:
            self._error_message = "Install pyalsaaudio"
            return

        self._stop_event = threading.Event()
        self._capture_thread = threading.Thread(target=self._capture_loop, name="SpectrumLoopback", daemon=True)
        self._capture_thread.start()
        self._status_message = "Connecting..."
        self._error_message = None

    # 停止捕获线程
    def _stop_capture(self):
        if self._stop_event:
            self._stop_event.set()

        if self._capture_thread:
            self._capture_thread.join(timeout=1.0)

        self._capture_thread = None
        self._stop_event = None
        self._sample_buffer = np.zeros(0, dtype=np.float32)
        self._device_label = None

    # 捕获循环
    def _capture_loop(self):
        pcm = None

        try:
            pcm = self._open_capture_device()
            if pcm is None:
                return

            while self._stop_event and not self._stop_event.is_set():
                try:
                    length, data = pcm.read()
                except alsaaudio.ALSAAudioError as exc:  # type: ignore[attr-defined]
                    LOGGER.error(f"[spectrum] ALSA read error: {exc}")
                    self._error_message = "Loopback error"
                    time.sleep(0.5)
                    continue

                if length > 0:
                    self._consume_audio(data)
                else:
                    time.sleep(0.005)

        except Exception as exc:
            LOGGER.error(f"[spectrum] capture thread crashed: {exc}", exc_info=True)
            self._error_message = "Capture failed"
        finally:
            if pcm:
                try:
                    pcm.close()
                except Exception:
                    pass

    # 查找候选的音频设备
    def _candidate_devices(self):
        candidates = []

        def _add(dev):
            if dev and dev not in candidates:
                candidates.append(dev)

        if self._device_hint:
            _add(self._device_hint)

        for name in self.LOOPBACK_CANDIDATES:
            _add(name)

        try:
            card_names = alsaaudio.cards()
            LOGGER.debug(f"[spectrum] ALSA cards: {card_names}")
            for card_index, card_name in enumerate(card_names):
                base = f"hw:{card_index}"
                plug = f"plughw:{card_index}"
                _add(f"{base},0")
                _add(f"{plug},0")
                _add(f"{base},1")
                _add(f"{plug},1")
                if "loopback" in card_name.lower():
                    _add(card_name)
        except Exception as exc:
            LOGGER.warning(f"[spectrum] failed to enumerate ALSA cards: {exc}")

        try:
            pcm_names = alsaaudio.pcms(alsaaudio.PCM_CAPTURE)
            LOGGER.debug(f"[spectrum] ALSA capture PCMs: {pcm_names}")
            for pcm_name in pcm_names:
                _add(pcm_name)
        except Exception as exc:
            LOGGER.warning(f"[spectrum] failed to list capture PCMs: {exc}")

        return candidates

    # 打开音频捕获设备
    def _open_capture_device(self):
        for device in self._candidate_devices():
            try:
                pcm = alsaaudio.PCM(
                    type=alsaaudio.PCM_CAPTURE,
                    mode=alsaaudio.PCM_NONBLOCK,
                    device=device,
                )
                pcm.setchannels(self.channels)
                pcm.setrate(self.sample_rate)
                pcm.setformat(alsaaudio.PCM_FORMAT_S16_LE)
                pcm.setperiodsize(self.chunk_size)

                self._device_label = device
                # self._status_message = f"{device} {self.sample_rate // 1000}kHz"
                self._status_message = "Capturing"
                LOGGER.info(f"[spectrum] capturing loopback from {device}")
                return pcm
            except alsaaudio.ALSAAudioError as exc:  # type: ignore[attr-defined]
                LOGGER.warning(f"[spectrum] failed to open {device}: {exc}")
                continue

        self._error_message = "Loopback missing"
        LOGGER.error(
            "[spectrum] no loopback capture device available. "
            "Set MUSPI_SPECTRUM_DEVICE or edit plugins/spectrum/config.json"
        )
        return None

    # 处理捕获的音频数据
    def _consume_audio(self, raw_data: bytes):
        samples = np.frombuffer(raw_data, dtype=np.int16)

        if self.channels > 1:
            remainder = samples.size % self.channels
            if remainder:
                samples = samples[:-remainder]

            if samples.size == 0:
                return

            samples = samples.reshape(-1, self.channels).mean(axis=1)

        samples = samples.astype(np.float32) / 32768.0

        if self._sample_buffer.size == 0:
            self._sample_buffer = samples
        else:
            self._sample_buffer = np.concatenate((self._sample_buffer, samples))

        while self._sample_buffer.size >= self.fft_size:
            frame = self._sample_buffer[: self.fft_size]
            self._sample_buffer = self._sample_buffer[self._hop_size :]
            self._update_levels(frame)

    # 更新频谱级别
    def _update_levels(self, frame: np.ndarray):
        if frame.size != self.fft_size:
            return

        windowed = frame * self._window
        fft_result = np.fft.rfft(windowed)
        magnitude = np.abs(fft_result) / (self.fft_size / 2.0)
        magnitude = np.maximum(magnitude, 1e-7)
        spectrum_db = 20 * np.log10(magnitude) + self._gain_db

        bars = self._aggregate_bars(spectrum_db)

        peak_value = float(np.max(np.abs(frame)))
        bar_peak = float(np.max(bars)) if bars.size else 0.0
        
        # LOGGER.info(f"[spectrum] peak_value: {peak_value} bar_peak: {bar_peak}")
        now = time.time()
        silent = False

        if peak_value > self._signal_threshold or bar_peak > self._bar_signal_threshold:
            # LOGGER.info(f"[spectrum] peak_value: {peak_value} bar_peak: {bar_peak}")
            self.manager.reset_sleep_timer()  #when signal detected, reset sleep timer
            self._last_signal_ts = now
        else:
            if now - self._last_signal_ts > self._silence_hold:
                silent = True

        if silent:
            bars = np.zeros_like(bars)

        with self._bars_lock:
            current = self._bars
            diff = bars - current
            smoothing = np.where(diff >= 0, self._rise_smoothing, self._decay_smoothing)
            self._bars = current + smoothing * diff

            decayed = np.maximum(self._peaks - self._peak_decay, 0.0)
            self._peaks = np.maximum(bars, decayed)
            self._avg_level = float(np.mean(self._bars))
            self._last_fft_ts = time.time()

    # 聚合频谱数据到柱状图
    def _aggregate_bars(self, spectrum_db: np.ndarray):
        values = np.zeros(self._bar_count, dtype=np.float32)

        for idx in range(self._bar_count):
            start = self._bin_edges[idx]
            end = self._bin_edges[idx + 1]
            start = min(start, len(spectrum_db) - 1)
            end = min(max(end, start + 1), len(spectrum_db))

            segment = spectrum_db[start:end]
            if segment.size == 0:
                level = spectrum_db[start]
            else:
                level = float(np.max(segment))

            norm = (level - self._db_floor) / (self._db_ceiling - self._db_floor)
            values[idx] = np.clip(norm, 0.0, 1.0)

        return values

    # 获取当前状态文本
    def _get_status_text(self):
        if not ALSA_AVAILABLE:
            return "Install pyalsaaudio"

        if self._error_message:
            return self._error_message

        if self._capture_thread is None:
            return "Wait For Thread"

        if time.time() - self._last_signal_ts > 2.0:
            return "On Mute"

        return self._status_message or "Loopback"

    # 渲染频谱显示
    def render(self):
        draw = self.canvas

        status_text = self._get_status_text()
        
        draw_scroll_text(draw, "♫", (0, 0), font=self.font_status)
        draw_scroll_text(draw, status_text, (28, 0), width=90, font=self.font_status, align="center")
        # draw_scroll_text(draw, "R", (123, 0), font=self.font_status)
            
        top = min(self.height - 8, 7)
        baseline = self.height - 2
        max_height = max(4, baseline - top)

        with self._bars_lock:
            bars = self._bars.copy()
            peaks = self._peaks.copy()
            avg_level = self._avg_level

        gamma = self._bar_gamma
        apply_gamma = gamma != 1.0

        for idx, value in enumerate(bars):
            scaled_value = value**gamma if apply_gamma else value
            bar_height = int(scaled_value * max_height)
            left = self._bars_offset + idx * (self._bar_width + self._bar_spacing)
            right = left + self._bar_width - 1
            top_y = baseline - bar_height
            draw.rectangle((left, top_y, right, baseline), fill=255)

            scaled_peak = peaks[idx]**gamma if apply_gamma else peaks[idx]
            peak_height = int(scaled_peak * max_height)
            peak_y = max(top, baseline - peak_height)
            draw.line((left, peak_y, right, peak_y), fill=0 if peak_y == baseline else 255)

        draw.rectangle((2, self.height - 2, self.width, self.height - 2), fill=255)
        scaled_avg = avg_level**gamma if apply_gamma else avg_level
        level_width = int((self.width - 4) * np.clip(scaled_avg, 0.0, 1.0))
        
        if level_width > 0:
            draw.rectangle((2, self.height - 2, 2 + level_width, self.height - 1), fill=255)
    
    def __del__(self):
        self._stop_capture()
