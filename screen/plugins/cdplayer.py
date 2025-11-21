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
CD_DEVICE = "/dev/sr0"
        
class cdplayer(DisplayPlugin):
    def __init__(self, manager, width, height):
        self.name = "cdplayer"
        super().__init__(manager, width, height)

        self.icon_drawer = None
        self.icon_drawer = IconDrawer(self.draw)
        self.media_player = MediaPlayer()
        self.last_play_time = 0
        self.pause_timout = 300 # 300 seconds = 5 minutes

        self.media_player.start_cd_monitor()
        self._is_in_longpress = False
        self.keymap = get_keymap()

    def render(self):    
        # get the canvas
        draw = self.canvas   
                
        # initialize the icon drawer
        if self.icon_drawer is None:
            self.icon_drawer = IconDrawer(draw)

        # draw the scrolling text
        offset = 28
        if self.media_player.is_running:
            if self.media_player.is_player_ready:
                draw_scroll_text(draw, self.media_player.current_title, (offset, 10), width=100, font=self.font10, align="center")
                draw_scroll_text(draw, self.media_player.current_artist + " - " + self.media_player.current_album, (offset, 24), width=100, font=self.font8, align="center")
                draw_scroll_text(draw, f"♪{self.media_player.current_track}/{self.media_player.current_track_length}", (offset, 0), width=100, font=self.font_status, align="center")
                # draw_scroll_text(draw, "♪" + self.client_name, (6+offset, 0), width=90, font=self.font_status, align="center")
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

        # draw the volume wave icon
        # self.icon_drawer.draw_volume_wave(x=86, y=0, level=volume)
                
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

        if evt.value == 2:  # long press
            # 长按 select 键 = 停止
            if self.keymap.is_key_match(evt.code, key_select) and not self._is_in_longpress:
                self.media_player.stop()
                self.media_player.cd.reset()
                self._is_in_longpress = True

            # 长按 cancel 键 = 弹出 CD
            if self.keymap.is_key_match(evt.code, key_cancel) and not self._is_in_longpress:
                self.media_player.eject()
                self._is_in_longpress = True

        if evt.value == 0:  # key up
            # 短按 select 键 = 播放/暂停/尝试播放
            if self.keymap.is_key_match(evt.code, key_select) and not self._is_in_longpress:
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
            if self.keymap.is_key_match(evt.code, key_cancel) and self.media_player.cd.is_inserted:
                self.media_player.next_track()

            self._is_in_longpress = False  

class MediaPlayer:
    def __init__(self):
        self.cd = CD()
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
            LOGGER.info("cd is already reading, please wait")
            return

        # If already running, just resume/unpause
        if self.is_running:
            LOGGER.info("player is already running")
            return

        def _callback(is_inserted):
            LOGGER.info(f"cd loaded: {is_inserted}")
            if is_inserted:
                self.play()
            else:
                if self.cd.read_status == "reading":
                    LOGGER.info("cd is reading")
                else:
                    LOGGER.info("cd not inserted")
                    self.cd.read_status = "nodisc"

        self.load_async(_callback) #try to load cd  

    def load_async(self, callback):
        def _run():
            result = self.cd.load()
            callback(result)

        threading.Thread(target=_run, daemon=True).start()
    
    def play(self):
        # Prevent duplicate play
        if self.is_running:
            LOGGER.warning('player is already running, ignoring play request')
            return

        # Check if CD is properly loaded
        if not self.cd.is_inserted or self.cd.disc is None:
            LOGGER.warning('CD not properly loaded, cannot play')
            return

        LOGGER.info('playing audio from CD')
        self._mpv = subprocess.Popen(self.MPV_COMMAND + ['cdda://'],
                                     bufsize=1,
                                     stdout=subprocess.PIPE,
                                     universal_newlines=True)
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
        for line in pipe:
            if not line:
                break
            LOGGER.info(f"\033[1m\033[32mmpv monitor\033[0m: {line.strip()}")

            if 'Exiting...' in line:
                self.stop()
                self.is_player_ready = False

            if '[cdda]' or '[alsa]' in line:
                self._set_current_track_info()
                self.is_player_ready = True

            if not self.is_running:
                break

    def stop(self):
        LOGGER.info('stopping audio from CD')
        if self.is_running:
            self._mpv.terminate()
            self._mpv = None
            self.is_player_ready = False
            self.read_mpv_thread = None
            self.read_meta_thread = None
            self.play_state = "stopped"

    def pause_or_play(self):
        if self.is_running and self.chapter is not None:
            if self.get_play_state() == 'pause':
                self._run_command('set', 'pause', 'no')
                self.play_state = "playing"
            else:
                self._run_command('set', 'pause', 'yes')
                self.play_state = "pause"
        self._set_current_track_info()
            
    def next_track(self):
        if self.is_running and self.chapter is not None:
            try:
                self.play_state = "pause"
                self._run_command('add', 'chapter', '1')
            except Exception:
                LOGGER.error("last track.")
        self._set_current_track_info()

    def prev_track(self):
        if self.is_running and self.chapter is not None:
            try:
                self.play_state = "pause"
                self._run_command('add', 'chapter', '-1')
            except Exception:
                LOGGER.error("first track.")
        self._set_current_track_info()

    def _set_current_track_info(self):
        if self.is_running and self.is_player_ready:
            if self.chapter is not None: # it meaning mpv is reader
                self.current_artist = self.cd.artist
                self.current_album = self.cd.album
                self.current_title = self.cd.tracks[self.chapter][0]
                self.current_track = self.chapter + 1
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
                    LOGGER.error(f"run command error: {e}")
                    return None
        except Exception:
            # Socket not ready yet, silently return None
            return None
            
    @property
    def is_running(self):
        '''
        check if the mpv is running
        '''
        return self._mpv is not None
    
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

            if 'sr0' in line and 'change' in line:
                LOGGER.info("cdrom content changed")
                try:
                    self.stop()
                    self.try_to_play()

                except Exception as e:
                    LOGGER.error(f"reload cd error: {e}")
                    self.stop()

        process.terminate()
        process.wait()

class CD:
    def __init__(self):
        self.disc = None
        self._cd_info = None
        self._is_cd_inserted = False
        self.artist = None
        self.album = None
        self.tracks = []
        self.track_length = 0
        self.read_status = "idle" # idle, nodisc, reading, readed, error

    def eject(self):
        LOGGER.info("eject cd")
        self.read_status = "ejecting"
        subprocess.Popen(['eject', CD_DEVICE], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self._is_cd_inserted = False
        self.disc = None
        self._cd_info = None
        self.artist = None
        self.album = None
        self.tracks = []
        self.track_length = 0

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

            # Use libdiscid to read disc
            self.disc = libdiscid.read(CD_DEVICE)

            if not self.disc or self.disc.toc == "":
                self._no_disc()
                return False

            self.read_status = "readed"
            LOGGER.info("CD readed.")
            LOGGER.info(f"disc id: {self.disc.id}")
            LOGGER.info(f"disc toc: {self.disc.toc}")

            #set default value
            _toc = self.disc.toc.split(' ')
            self.artist = "Unknown Artist"
            self.album = ""
            self.track_length = int(_toc[1])
            self.tracks = [[f"Track {i+1}", "Unknown"] for i in range(self.track_length)]
            self._is_cd_inserted = True

            #load cd info from file
            try:
                LOGGER.info(f"load cd info from config/cd/{self.disc.id}.json")
                _cd_info = open(f"config/cd/{self.disc.id}.json", "r").read()
                self._fix_info(json.loads(_cd_info))

                return True
            except FileNotFoundError as e:
                LOGGER.error(f"load file error: {e}")

            #if cd info is not found, get cd info from musicbrainz
            try:
                LOGGER.info("request info from musicbrainz")
                mb.set_useragent('muspi', '1.0', 'https://github.com/puterjam/muspi')
                _cd_info = mb.get_releases_by_discid(self.disc.id, includes=["recordings", "artists"], cdstubs=False)

                os.makedirs("config/cd", exist_ok=True)
                _cd_info = json.dumps(_cd_info)
                with open(f"config/cd/{self.disc.id}.json", "w") as f:
                    f.write(_cd_info)

                self._fix_info(json.loads(_cd_info))
            except mb.ResponseError as e:
                LOGGER.error(f"request from musicbrainz error: {e}")

            return True

        except Exception as e:
            LOGGER.error(f"load cd error: {e}")
            self._no_disc()
            return False
    
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

# if __name__ == "__main__":
#     mp = MediaPlayer()

#     # try:
#     #     is_loaded = mp.load()

#     #     if is_loaded:
#     #         mp.play()
#     #         # 启动CD监控
#     # except Exception as e:
#     #     print(f"play error: {e}")
#     #     print(f"error line: {traceback.extract_tb(e.__traceback__)[-1].lineno}")

#     mp.start_cd_monitor()
        
#     try:
#         # 保持程序运行
#         while True:
#             time.sleep(1)
#     except KeyboardInterrupt:
#         print("\n停止监控")
#         mp.stop()
#         mp.stop_cd_monitor()