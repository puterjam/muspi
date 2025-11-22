import musicbrainzngs as mb
import libdiscid
import json
import os
import subprocess
import threading
import time

from screen.base import DisplayPlugin
from ui.component import draw_scroll_text, draw_vu
from assets.icons import IconDrawer

from until.log import LOGGER
from until.keymap import get_keymap

MPV_SOCKET_PATH = "/tmp/mpv_socket"

# 光盘播放器插件类 for Muspi
class cdplayer(DisplayPlugin):
    def __init__(self, manager, width, height):
        self.name = "cdplayer"
        super().__init__(manager, width, height)

        self.icon_drawer = IconDrawer(self.draw)
        self.media_player = MediaPlayer()
        self.last_play_time = 0
        self.pause_timout = 300 # 300 seconds = 5 minutes

        self.media_player.start_cd_monitor()
        self._is_in_longpress = False
        self._key_press_start_time = {}  # Track when each key was pressed
        self._longpress_duration = 2.0  # 2 seconds for long press
        self.keymap = get_keymap()

    def render(self):
        # get the canvas
        draw = self.canvas

        # draw the scrolling text
        offset = 28
        if self.media_player.is_running:
            if self.media_player.is_player_ready:
                draw_scroll_text(draw, self.media_player.current_title, (offset, 10), width=100, font=self.font10, align="center")
                draw_scroll_text(draw, self.media_player.current_artist + " - " + self.media_player.current_album, (offset, 24), width=100, font=self.font8, align="center")
                draw_scroll_text(draw, f"♪{self.media_player.current_track}/{self.media_player.current_track_length}", (offset, 0), width=100, font=self.font_status, align="center")
            else:
                draw_scroll_text(draw, "即将开始播放.", (offset, 10), width=100, font=self.font10, align="center")
        else:
            if self.media_player.cd.read_status == "reading":
                draw_scroll_text(draw, "CD读取中...", (offset, 10), width=100, font=self.font10, align="center")
            elif self.media_player.cd.read_status == "nodisc":
                draw_scroll_text(draw, "放入CD开始播放", (offset, 10), width=100, font=self.font10, align="center")
            elif self.media_player.cd.read_status == "idle":
                draw_scroll_text(draw, "Muspi CD Player", (offset, 10), width=100, font=self.font10, align="center")
            elif self.media_player.cd.read_status == "readed":
                draw_scroll_text(draw, "读取曲目信息...", (offset, 10), width=100, font=self.font10, align="center")
            elif self.media_player.cd.read_status == "ejecting":
                draw_scroll_text(draw, "CD弹出中...", (offset, 10), width=100, font=self.font10, align="center")
            else:
                draw_scroll_text(draw, self.media_player.cd.read_status, (offset, 10), width=100, font=self.font10, align="center")

        draw_scroll_text(draw, "CD", (89+offset, 0), font=self.font_status)

        # draw the VU table
        if self.media_player.play_state == "playing" and self.media_player.is_player_ready:
            draw_vu(draw, volume_level=0.5) 
            if self.manager.sleep:
                self.manager.turn_on_screen()
            draw_scroll_text(draw, "⏵", (offset, 0), font=self.font_status)
        elif self.media_player.play_state == "pause":
            draw_vu(draw, volume_level=0.0)
            draw_scroll_text(draw, "⏸", (offset, 0), font=self.font_status)
        else:
            draw_vu(draw, volume_level=0.0)
            draw_scroll_text(draw, "⏹", (offset, 0), font=self.font_status)
                
    def is_playing(self):
        return self.media_player.play_state == "playing"

    def set_active(self, value):
        super().set_active(value)
        if value:
            self.last_play_time = time.time()
            self.manager.key_listener.on(self.key_callback)
        else:
            self.manager.key_listener.off(self.key_callback)
    
    def event_listener(self):
        if self.media_player.cd.read_status == "reading":
            self.set_active(True)
        
        if self.media_player.is_running:
            self.manager.reset_sleep_timer() # reset the sleep timer

        # check if the pause state has been more than 5 minutes
        if not self.media_player.is_running and time.time() - self.last_play_time > self.pause_timout:  # 300 seconds = 5 minutes
            self.set_active(False)

    def key_callback(self, device_name, evt):
        # 获取全局功能按键
        key_select = self.keymap.get_action_select()  # 播放/暂停/停止
        key_cancel = self.keymap.get_action_cancel()  # 下一曲/弹出
        
        key_prev = self.keymap.get_media_previous()  # 上一曲
        key_next = self.keymap.get_media_next()  # 下一曲
        key_stop = self.keymap.get_media_stop()  # 停止播放
        key_play_pause = self.keymap.get_media_play_pause()  # 播放/暂停

        if evt.value == 1:  # key down - record press start time
            self._key_press_start_time[evt.code] = time.time()
            self._is_in_longpress = False

        elif evt.value == 2:  # key hold (repeated event)
            # Check if key has been held long enough (3 seconds)
            if evt.code in self._key_press_start_time and not self._is_in_longpress:
                press_duration = time.time() - self._key_press_start_time[evt.code]

                if press_duration >= self._longpress_duration:
                    # 长按 select 键 = 停止
                    if self.keymap.is_key_match(evt.code, key_select):
                        self.media_player.stop()
                        self.media_player.cd.reset()
                        self._is_in_longpress = True

                    # 长按 cancel 键 = 弹出 CD
                    elif self.keymap.is_key_match(evt.code, key_cancel):
                        self.media_player.eject()
                        self._is_in_longpress = True

        elif evt.value == 0:  # key up
            # Check if it was a long press or short press
            if evt.code in self._key_press_start_time:
                press_duration = time.time() - self._key_press_start_time[evt.code]

                # Only handle short press if not already handled as long press
                if not self._is_in_longpress and press_duration < self._longpress_duration:
                    # 短按 select 键 = 播放/暂停/尝试播放
                    if self.keymap.is_key_match(evt.code, key_select):
                        if self.media_player.is_running:
                            # 正在播放，则暂停/恢复
                            self.media_player.pause_or_play()
                        elif self.media_player.cd.is_inserted and self.media_player.cd.read_status != "reading":
                            # CD已插入且读取完成，直接播放
                            self.media_player.play()
                        else:
                            # CD未插入或正在读取，尝试加载并播放
                            self.media_player.try_to_play()

                    # 短按 cancel 键 = 下一曲
                    elif self.keymap.is_key_match(evt.code, key_cancel) and self.media_player.cd.is_inserted:
                        self.media_player.next_track()

                    # 上一曲
                    elif self.keymap.is_key_match(evt.code, key_prev) and self.media_player.cd.is_inserted:
                        self.media_player.prev_track()

                    # 下一曲
                    elif self.keymap.is_key_match(evt.code, key_next) and self.media_player.cd.is_inserted:
                        self.media_player.next_track()

                    # 停止播放
                    elif self.keymap.is_key_match(evt.code, key_stop):
                        self.media_player.stop()
                        self.media_player.cd.reset()

                    # 播放/暂停
                    elif self.keymap.is_key_match(evt.code, key_play_pause):
                        if self.media_player.is_running:
                            # 正在播放，则暂停/恢复
                            self.media_player.pause_or_play()
                        elif self.media_player.cd.is_inserted and self.media_player.cd.read_status != "reading":
                            # CD已插入且读取完成，直接播放
                            self.media_player.play()
                        else:
                            # CD未插入或正在读取，尝试加载并播放
                            self.media_player.try_to_play()

                # Clean up
                del self._key_press_start_time[evt.code]
                self._is_in_longpress = False  

# 媒体播放器类
class MediaPlayer:
    def __init__(self):
        self.cd = CDDevice()
        self._mpv = None
        self._monitor_thread = None
        self._stop_cd_monitor = False
        self.MPV_COMMAND = ["mpv", "--quiet", "--vo=null",
                            "--no-audio-display",
                            "--cache=auto",
                            "--audio-device=alsa",
                            "--input-ipc-server=" + MPV_SOCKET_PATH]
        
        self.current_artist = "Unknown"
        self.current_album = "Unknown album"
        self.current_title = "Unknown"
        self.current_track = 1
        self.current_track_length = 0
        self.play_state = "stopped"
        self.is_player_ready = False

        self.read_meta_thread = None
        self.read_mpv_thread = None
    
    def try_to_play(self):
        # If already reading, don't trigger another read
        if self.cd.read_status == "reading":
            LOGGER.info("CD is already, please wait")
            return

        # If already running, just resume/unpause
        if self.is_running:
            LOGGER.info("MPV is running")
            return

        def _callback(is_inserted):
            LOGGER.info(f"CD loaded: {is_inserted}")
            if is_inserted:
                self.play()
            else:
                if self.cd.read_status == "reading":
                    LOGGER.info("CD is reading")
                else:
                    LOGGER.info("CD not inserted")
                    self.cd.read_status = "nodisc"

        self.load_async(_callback) #try to load cd  

    def load_async(self, callback):
        def _run():
            result = self.cd.load()
            callback(result)

        threading.Thread(target=_run, daemon=True).start()
    
    def _kill_all_mpv_processes(self):
        """
        强制杀死所有mpv进程,防止重音问题
        """
        try:
            # 使用pkill杀死所有CD相关的mpv进程(包括cdda和普通文件播放)
            result = subprocess.run(['pkill', '-9', '-f', 'mpv.*--input-ipc-server=/tmp/mpv_socket'],
                                   capture_output=True,
                                   text=True,
                                   timeout=3)
            if result.returncode == 0:
                LOGGER.info('Killed existing MPV processes')
                time.sleep(0.3)  # 等待进程完全退出
            else:
                LOGGER.info('No existing MPV processes found')
        except subprocess.TimeoutExpired:
            LOGGER.warning('pkill command timed out')
        except Exception as e:
            LOGGER.error(f'Error killing MPV processes: {e}')

    def play(self):
        # Prevent duplicate play
        if self.is_running:
            LOGGER.warning('MPV is running, ignoring play request')
            return

        # Check if CD is properly loaded
        if not self.cd.is_inserted or self.cd.disc is None:
            LOGGER.warning('CD not properly loaded, cannot play')
            return

        # 强制清理所有可能存在的MPV进程
        self._kill_all_mpv_processes()

        # Clean up socket file before starting new process
        try:
            if os.path.exists(MPV_SOCKET_PATH):
                os.remove(MPV_SOCKET_PATH)
                LOGGER.info('Cleaned up old mpv socket before starting')
        except Exception as e:
            LOGGER.error(f'Error cleaning up socket before play: {e}')

        # 根据CD类型选择播放方式
        if self.cd.type == "cdda":
            LOGGER.info('Play audio from CDDA')
            self._mpv = subprocess.Popen(self.MPV_COMMAND + ['cdda://'],
                                         bufsize=1,
                                         stdout=subprocess.PIPE,
                                         universal_newlines=True,
                                         encoding='utf-8',
                                         errors='replace')
        else:
            # Data CD - play audio files as playlist
            LOGGER.info(f'Play {len(self.cd.audio_files)} audio files from data CD')
            self._mpv = subprocess.Popen(self.MPV_COMMAND + self.cd.audio_files,
                                         bufsize=1,
                                         stdout=subprocess.PIPE,
                                         universal_newlines=True,
                                         encoding='utf-8',
                                         errors='replace')

        # 启动监听线程
        self.read_mpv_thread = threading.Thread(target=self._monitor_mpv_output,
                        args=(self._mpv.stdout,),
                        daemon=True)
        self.read_mpv_thread.start()

        self.read_meta_thread = threading.Thread(target=self._read_meta, daemon=True)
        self.read_meta_thread.start() 

    def _read_meta(self):
        while self.is_running:
            time.sleep(1)
            self._set_current_track_info()
            self.get_play_state()

    def _monitor_mpv_output(self, pipe):
        """
        监听 mpv 进程输出
        """
        try:
            for line in pipe:
                if not line:
                    break

                try:
                    LOGGER.info(f"\033[1m\033[32mMPV monitor\033[0m: {line.strip()}")
                except Exception as e:
                    LOGGER.warning(f"Error logging MPV output: {e}")
                    continue

                if 'Exiting...' in line:
                    self.stop()
                    self.cd.read_status = "idle"
                    self.is_player_ready = False

                if '[cdda]' or '[alsa]' in line:
                    self._set_current_track_info()
                    self.is_player_ready = True

                if not self.is_running:
                    break
        except Exception as e:
            LOGGER.error(f"Error in MPV monitor thread: {e}")
        finally:
            LOGGER.info("MPV monitor thread exited")

    def stop(self):
        LOGGER.info('Stopping audio from CD')
        if self._mpv is not None:
            try:
                # First try graceful termination
                self._mpv.terminate()

                # Wait up to 2 seconds for process to end
                try:
                    self._mpv.wait(timeout=2)
                    LOGGER.info('MPV process terminated gracefully')
                except subprocess.TimeoutExpired:
                    # If still running, force kill
                    LOGGER.warning('MPV process did not terminate, force killing')
                    self._mpv.kill()
                    self._mpv.wait()  # Wait for kill to complete

            except Exception as e:
                LOGGER.error(f'Error stopping MPV: {e}')
                # Force kill as last resort
                try:
                    self._mpv.kill()
                    self._mpv.wait()
                except:
                    pass
            finally:
                self._mpv = None
                self.is_player_ready = False
                self.read_mpv_thread = None
                self.read_meta_thread = None
                self.play_state = "stopped"

                # Clean up socket file if it exists
                try:
                    if os.path.exists(MPV_SOCKET_PATH):
                        os.remove(MPV_SOCKET_PATH)
                        LOGGER.info('Cleaned up mpv socket')
                except Exception as e:
                    LOGGER.error(f'Error cleaning up socket: {e}')

    def pause_or_play(self):
        if self.is_running:
            if self.get_play_state() == 'pause':
                self._run_command('set', 'pause', 'no')
                self.play_state = "playing"
            else:
                self._run_command('set', 'pause', 'yes')
                self.play_state = "pause"
        self._set_current_track_info()
            
    def next_track(self):
        if self.is_running:
            try:
                self.play_state = "pause"
                LOGGER.info("Next track.")
                if self.cd.type == "cdda":
                    # CDDA使用chapter切换
                    self._run_command('add', 'chapter', '1')
                else:
                    # Data CD使用playlist切换
                    self._run_command('playlist-next')
            except Exception:
                LOGGER.error("Last track.")
        self._set_current_track_info()

    def prev_track(self):
        if self.is_running:
            try:
                self.play_state = "pause"
                LOGGER.info("Previous track.")
                if self.cd.type == "cdda":
                    # CDDA使用chapter切换
                    self._run_command('add', 'chapter', '-1')
                else:
                    # Data CD使用playlist切换
                    self._run_command('playlist-prev')
            except Exception:
                LOGGER.error("First track.")
        self._set_current_track_info()

    def _set_current_track_info(self):
        if self.is_running and self.is_player_ready:
            if self.cd.type == "cdda":
                # CDDA: 使用chapter信息
                chapter = self.chapter
                if chapter is not None and isinstance(chapter, int) and 0 <= chapter < len(self.cd.tracks):
                    self.current_artist = self.cd.artist
                    self.current_album = self.cd.album
                    self.current_title = self.cd.tracks[chapter][0]
                    self.current_track = chapter + 1
                    self.current_track_length = self.cd.track_length
            else:
                # Data CD: 使用playlist-pos信息
                playlist_pos = self._run_command('get_property', 'playlist-pos')
                if playlist_pos is not None and isinstance(playlist_pos, int) and 0 <= playlist_pos < len(self.cd.tracks):
                    self.current_title = self.cd.tracks[playlist_pos][0]  # 文件名
                    self.current_artist = "DATA CD"
                    ext = self.cd.tracks[playlist_pos][1]  # 扩展名
                    self.current_album = ext[1:] if ext.startswith('.') else ext  # 去掉开头的点
                    self.current_track = playlist_pos + 1
                    self.current_track_length = self.cd.track_length

    def eject(self):
        self.stop()
        time.sleep(0.1)
        self.cd.eject()

    def _run_command(self, *command):
        # LOGGER.info(f"run command: {command}")
        # Check if socket exists before trying to connect
        if not os.path.exists(MPV_SOCKET_PATH):
            return None

        command_dict = {
            "command": command
        }
        command_json = json.dumps(command_dict) + '\n'
        try:
            socat = subprocess.Popen(['socat', '-', MPV_SOCKET_PATH], stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            socat_output = socat.communicate(command_json.encode('utf-8'))
            
            
            if socat_output[0] is not None and \
                            len(socat_output[0]) != 0:
                try:
                    data = json.loads(socat_output[0].decode())
                    if 'data' in data:
                        return data['data']
                    else:
                        return None
                except Exception as e:
                    LOGGER.error(f"Run command error: {e}")
                    return None
        except Exception:
            # Socket not ready yet, silently return None
            return None
            
    @property
    def is_running(self):
        '''
        check if the mpv is running
        '''
        if self._mpv is None:
            return False

        # Check if process is actually alive
        if self._mpv.poll() is not None:
            # Process has terminated
            LOGGER.warning('MPV process terminated unexpectedly')
            self._mpv = None
            self.is_player_ready = False
            self.play_state = "stopped"
            return False

        return True
    
    @property
    def chapter(self):
        if self.is_running:
            try:
                chapter = self._run_command('get_property', 'chapter')
                chapters = self._run_command('get_property', 'chapters')

                self.cd.track_length = int(chapters) #fix track length, because the track length is not correct
                if len(self.cd.tracks) != self.cd.track_length:
                    LOGGER.info(f"fix track length: {self.cd.track_length}")
                    self.cd.tracks = [[f"Track {i+1}", "Unknown"] for i in range(self.cd.track_length)]
                    
                return chapter
            except:
                return 0
        else:
            return None
    
    def get_play_state(self):
        '''
        check if the mpv is paused
        '''
        if self.is_running:
            self.play_state = self._run_command('get_property', 'pause')
            self.play_state = 'pause' if self.play_state else 'playing'
        else:
            self.play_state = 'stopped'
        
        return self.play_state

    def start_cd_monitor(self):
        """
        开始监控CD设备变化
        """
        if self._monitor_thread is not None:
            return

        self._stop_cd_monitor = False
        self._monitor_thread = threading.Thread(target=self._monitor_cd)
        self._monitor_thread.daemon = True
        self._monitor_thread.start()

    def stop_cd_monitor(self):
        """
        停止监控CD设备变化
        """
        self._stop_cd_monitor = True
        if self._monitor_thread is not None:
            self._monitor_thread.join()
            self._monitor_thread = None

    def _monitor_cd(self):
        """
        监控CD设备变化的内部方法
        """
        cmd = ['udevadm', 'monitor', '--kernel', '--subsystem-match=block']
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        while not self._stop_cd_monitor:
            line = process.stdout.readline()
            if not line:
                break

            # Monitor all sr devices (sr0, sr1, sr2, etc.)
            if any(f'sr{i}' in line for i in range(10)):
                if 'change' in line or 'remove' in line:
                    try:
                        # Stop current playback and force kill any remaining processes
                        self.stop()
                        self._kill_all_mpv_processes()

                        # Handle different event types
                        if 'change' in line:
                            LOGGER.info("CD-ROM content changed.")
                            self.try_to_play()
                        elif 'remove' in line:
                            LOGGER.warning("USB CD-ROM device removed.")
                            self.cd.reset()

                    except Exception as e:
                        LOGGER.error(f"Handle CD event error: {e}")
                        self.stop()

        process.terminate()
        process.wait()

# 定义 CD 设备类
class CDDevice:
    def __init__(self):
        self.disc = None
        self._cd_info = None
        self._is_cd_inserted = False
        self.artist = None
        self.album = None
        self.tracks = []
        self.track_length = 0
        self.read_status = "idle" # idle, nodisc, reading, readed, error
        self._cd_device = None  # Current CD device path
        self.type = "cdda"  # cdda or data
        self.audio_files = []  # For data CDs
        self.mount_point = "/media/cdrom"  # Mount point for data CDs

    def _find_cd_device(self):
        """
        查找可用的 CD-ROM 设备
        返回第一个找到的 /dev/sr* 设备路径
        """
        import glob
        devices = glob.glob('/dev/sr*')
        if devices:
            # 过滤掉非块设备
            for device in sorted(devices):
                if os.path.exists(device):
                    LOGGER.info(f"Found CD device: {device}")
                    return device

        # 尝试使用 /dev/cdrom 作为备选
        if os.path.exists('/dev/cdrom'):
            LOGGER.info("Using fallback device: /dev/cdrom")
            return '/dev/cdrom'

        LOGGER.warning("No CD device found")
        return None

    def _scan_audio_files(self):
        """
        扫描挂载点的音频文件
        """
        audio_extensions = ['.mp3', '.flac', '.wav', '.ogg', '.m4a', '.wma', '.ape', '.aac']
        audio_files = []

        try:
            if not os.path.exists(self.mount_point):
                return []

            for root, _, files in os.walk(self.mount_point):
                for file in sorted(files):
                    ext = os.path.splitext(file)[1].lower()
                    if ext in audio_extensions:
                        full_path = os.path.join(root, file)
                        audio_files.append(full_path)

            LOGGER.info(f"Found {len(audio_files)} audio files on data CD")
            return audio_files
        except Exception as e:
            LOGGER.error(f"Error scanning audio files: {e}")
            return []

    def _mount_cd(self):
        """
        挂载CD到mount_point
        """
        try:
            LOGGER.info(f"Mounting CD-ROM: {self._cd_device} to {self.mount_point}")

            # 创建挂载点(如果不存在)
            if not os.path.exists(self.mount_point):
                mkdir_result = subprocess.run(['sudo', 'mkdir', '-p', self.mount_point],
                                             capture_output=True, text=True, timeout=10)
                if mkdir_result.returncode != 0:
                    LOGGER.error(f"Failed to create mount point: {mkdir_result.stderr}")
                    return False

            # 尝试挂载 (增加超时时间到30秒,CD挂载可能较慢)
            result = subprocess.run(['sudo', 'mount', self._cd_device, self.mount_point],
                                   capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                LOGGER.info(f"CD mounted successfully at {self.mount_point}")
                return True
            else:
                LOGGER.warning(f"Mount failed: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            # 超时但可能已经挂载成功,检查挂载状态
            LOGGER.warning(f"Mount command timed out, checking if mounted anyway")
            if os.path.ismount(self.mount_point):
                LOGGER.info(f"CD is mounted at {self.mount_point} (despite timeout)")
                return True
            else:
                LOGGER.error(f"Mount timed out and CD is not mounted")
                return False
        except Exception as e:
            LOGGER.error(f"Error mounting CD: {e}")
            return False

    def _unmount_cd(self):
        """
        卸载CD
        """
        try:
            subprocess.run(['sudo', 'umount', self.mount_point],
                          capture_output=True, text=True, timeout=5)
            LOGGER.info("CD unmounted")
        except Exception as e:
            LOGGER.error(f"Error unmounting CD: {e}")

    def eject(self):
        LOGGER.info("Eject CD")
        self.read_status = "ejecting"

        # 先卸载数据CD
        if self.type == "data":
            self._unmount_cd()

        # 使用当前设备或查找设备
        device = self._cd_device or self._find_cd_device()
        if device:
            subprocess.Popen(['sudo','eject', device], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        self._is_cd_inserted = False
        self.disc = None
        self._cd_info = None
        self.artist = None
        self.album = None
        self.tracks = []
        self.track_length = 0
        self._cd_device = None
        self.type = "cdda"
        self.audio_files = []

        threading.Timer(
            5,
            lambda: self.reset()
        ).start()

    @property
    def is_inserted(self):
        return self._is_cd_inserted
    
    def reset(self):
        self._is_cd_inserted = False
        self.read_status = "idle"
    
    def load(self):
        '''
        加载CD
        '''
        try:
            # Prevent duplicate loading
            if self.read_status == "reading":
                LOGGER.warning("CD is already being read")
                return False

            LOGGER.info("Read CD")
            self.read_status = "reading"

            # Find available CD device
            self._cd_device = self._find_cd_device()
            if not self._cd_device:
                LOGGER.error("No CD device available")
                self._no_disc()
                return False

            # Try to read as CDDA first
            try:
                LOGGER.info(f"Reading from device: {self._cd_device}")
                self.disc = libdiscid.read(self._cd_device)

                if self.disc and self.disc.toc != "":
                    # This is a CDDA
                    self.type = "cdda"
                    self.read_status = "readed"
                    LOGGER.info("CDDA detected")
                    LOGGER.info(f"disc id: {self.disc.id}")
                    LOGGER.info(f"disc toc: {self.disc.toc}")

                    #set default value
                    _toc = self.disc.toc.split(' ')
                    self.artist = "Unknown Artist"
                    self.album = ""
                    self.track_length = int(_toc[1])
                    self.tracks = [[f"Track {i+1}", "Unknown"] for i in range(self.track_length)]
                    self._is_cd_inserted = True

                    # Try to load CDDA metadata
                    return self._load_cdda_metadata()
                else:
                    raise Exception("Not a CDDA, try data CD")

            except Exception as e:
                # Not a CDDA, try as data CD
                LOGGER.info(f"Not CDDA: {e}, trying data CD")

                # Try to mount as data CD
                if self._mount_cd():
                    # Scan for audio files
                    self.audio_files = self._scan_audio_files()

                    if len(self.audio_files) > 0:
                        # Data CD with audio files
                        self.type = "data"
                        self.read_status = "readed"
                        self.track_length = len(self.audio_files)

                        # Build tracks list with filename info
                        self.tracks = []
                        for audio_file in self.audio_files:
                            filename = os.path.basename(audio_file)
                            name_without_ext = os.path.splitext(filename)[0]
                            ext = os.path.splitext(filename)[1]
                            self.tracks.append([name_without_ext, ext])

                        self.artist = ""
                        self.album = ""
                        self._is_cd_inserted = True
                        self.disc = True  # Mark as valid disc

                        LOGGER.info(f"Data CD detected with {self.track_length} audio files")
                        return True
                    else:
                        # No audio files found
                        self._unmount_cd()
                        self._no_disc()
                        return False
                else:
                    # Mount failed
                    self._no_disc()
                    return False

        except Exception as e:
            LOGGER.error(f"Load CD error: {e}")
            self._no_disc()
            return False

    def _load_cdda_metadata(self):
        """
        加载CDDA元数据
        """
        #load cd info from file
        try:
            LOGGER.info(f"Load CD info from config/cd/{self.disc.id}.json")
            _cd_info = open(f"config/cd/{self.disc.id}.json", "r").read()
            self._fix_info(json.loads(_cd_info))

            return True
        except FileNotFoundError as e:
            LOGGER.error(f"Load file error: {e}")

        #if cd info is not found, get cd info from musicbrainz
        try:
            LOGGER.info("Request info from musicbrainz")
            mb.set_useragent('muspi', '1.0', 'https://github.com/puterjam/muspi')
            _cd_info = mb.get_releases_by_discid(self.disc.id, includes=["recordings", "artists"], cdstubs=False)

            os.makedirs("config/cd", exist_ok=True)
            _cd_info = json.dumps(_cd_info)
            with open(f"config/cd/{self.disc.id}.json", "w") as f:
                f.write(_cd_info)

            self._fix_info(json.loads(_cd_info))
        except mb.ResponseError as e:
            LOGGER.error(f"Request from musicbrainz error: {e}")

        return True
    
    def _no_disc(self):
        self._is_cd_inserted = False
        self.read_status = "nodisc"
        # Reset status after a delay to allow retry
        threading.Timer(
            15,
            lambda: self.reset() if self.read_status == "nodisc" else None
        ).start()

    def _fix_info(self, cd_info):
        self._cd_info = cd_info

        # Handle response from get_releases_by_discid
        if 'disc' in cd_info and 'release-list' in cd_info['disc']:
            release = cd_info['disc']['release-list'][0]
            self.artist = release.get('artist-credit-phrase', 'Unknown Artist')
            self.album = release.get('title', 'Unknown Album')

            medium_list = release.get('medium-list', [])
            for medium in medium_list:
                if 'disc-list' in medium:
                    for disc in medium['disc-list']:
                        if disc['id'] == self.disc.id:
                            self.track_length = medium['track-count']
                            self.tracks = [[track['recording']['title'],
                                          track['recording']['artist-credit'][0]["artist"]["name"]]
                                          for track in medium['track-list']]
                            LOGGER.info(f"find cd info: {self.artist} - {self.album}")
                            return True

        # Fallback: try old format for cached files
        if 'release-list' in cd_info:
            for release in cd_info['release-list']:
                artist = release['artist-credit-phrase']
                album = release['title']
                medium_list = release['medium-list']
                medium_count = release['medium-count']
                LOGGER.info(f"artist: {artist}, album: {album}")

                for disc_count in range(medium_count):
                    count = disc_count - 1
                    if medium_list[count]["format"] == "CD" and len(medium_list[count]['disc-list']) > 0:
                        offset = ' '.join(str(x) for x in medium_list[count]['disc-list'][0]['offset-list'])

                        if offset in self.disc.toc:
                            LOGGER.info(f"find cd info: {offset}")
                            self.artist = artist
                            self.album = album
                            self.track_length = medium_list[count]['track-count']
                            self.tracks = [[track['recording']['title'], track['recording']['artist-credit'][0]["artist"]["name"]]
                                            for track in medium_list[count]['track-list']]

                            return True #use cd info

        return False #use unknown info
