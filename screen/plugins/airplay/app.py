import time
import subprocess
import threading
import queue

from until.log import LOGGER
from screen.base import DisplayPlugin
from ui.component import draw_scroll_text, draw_vu
from assets.icons import IconDrawer

class airplay(DisplayPlugin):
    def __init__(self, manager, width, height):
        self.name = "airplay"
        super().__init__(manager, width, height)
        
        self.icon_drawer = None
        self.current_title = "play next"
        self.current_artist = "show info"
        self.current_album = ""
        self.play_state = "pause"
        self.client_name = ""
        self.stream_volume = None
        self.last_play_time = time.time()  # record the last play time
        self.metadata_queue = queue.Queue()
        self.pause_timout = 30
        self._start_metadata_reader()
        
    
    def _start_metadata_reader(self):
        def metadata_reader_thread():
            process = subprocess.Popen(
                "shairport-sync-metadata-reader < /tmp/shairport-sync-metadata",
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=False
            )
            
            while True:
                try:
                    line = process.stdout.readline()
                    if line:
                        decoded_line = line.decode('utf-8', errors='replace').strip()
                        if "Artist" in decoded_line:
                            try:
                                artist = decoded_line.split('"')[1]
                                self.metadata_queue.put(("artist", artist))
                            except IndexError:
                                pass
                        elif "Album" in decoded_line:
                            try:
                                album = decoded_line.split('"')[1]
                                self.metadata_queue.put(("album", album))
                            except IndexError:
                                pass
                        elif "Title" in decoded_line:
                            try:
                                title = decoded_line.split('"')[1]
                                self.metadata_queue.put(("title", title))
                            except IndexError:
                                pass
                        elif "Volume" in decoded_line:
                            try:
                                volume = decoded_line.split('"')[1].strip()
                                self.metadata_queue.put(("volume", volume))
                            except IndexError:
                                pass
                        elif "Play Session End." in decoded_line:
                            self.metadata_queue.put(("session_state", False))
                        elif "Play Session Begin." in decoded_line:
                            self.metadata_queue.put(("session_state", True))
                        elif "Resume." in decoded_line:
                            self.metadata_queue.put(("session_state", True))
                            self.metadata_queue.put(("play_state", "play"))
                        elif "Pause." in decoded_line:
                            self.metadata_queue.put(("play_state", "pause"))
                        elif "The name of the AirPlay client is" in decoded_line:
                            try:
                                client_name = decoded_line.split('"')[1].strip()
                                self.metadata_queue.put(("client_name", client_name))
                            except IndexError:
                                pass
                    else:
                        time.sleep(0.1)
                except Exception as e:
                    LOGGER.error(f"read metadata error: {e}")
                    time.sleep(1)
        
        # start metadata reader thread
        self.metadata_thread = threading.Thread(target=metadata_reader_thread, daemon=True)
        self.metadata_thread.start()
    
    def _read_metadata(self):
        try:
            while not self.metadata_queue.empty():
                metadata_type, value = self.metadata_queue.get_nowait()
                if metadata_type == "title":
                    self.current_title = value
                elif metadata_type == "artist":
                    self.current_artist = value
                elif metadata_type == "album":
                    self.current_album = value
                elif metadata_type == "session_state":
                    self.set_active(value)
                    if value:  # if start playing, update the last play time
                        self.last_play_time = time.time()
                elif metadata_type == "play_state":
                    if self.play_state != value:  # if play state changed
                        self.last_play_time = time.time()  # update the last play time
                    self.play_state = value
                elif metadata_type == "volume":
                    self.stream_volume = value
                elif metadata_type == "client_name":
                    self.client_name = value
        except queue.Empty:
            pass
    
    def render(self):
        # get the canvas
        draw = self.canvas
        
        # initialize the icon drawer
        if self.icon_drawer is None:
            self.icon_drawer = IconDrawer(draw)
        
        if self.stream_volume is None:
            volume = 0.5
        else:
            left_db, right_db, _, _ = map(float, self.stream_volume.split(','))
            volume = max(0, (min(left_db, right_db) + 100) / 100)  # convert the range of -144 to 0 to 0 to 1

        # self.icon_drawer.draw_airplay(x=24, y=0) 
        
        # draw the scrolling text
        offset = 28
        if self.current_title and self.current_artist:
            draw_scroll_text(draw, self.current_title, (offset, 10), width=100, font=self.font10, align="center")
            draw_scroll_text(draw, self.current_artist + " - " + self.current_album, (offset, 24), width=100, font=self.font8, align="center")
            #draw_scroll_text(draw, "♪" + self.client_name, (58+offset, 0), font=self.font_status)
            draw_scroll_text(draw, "♪" + self.client_name, (6+offset, 0), width=90, font=self.font_status, align="center")
            draw_scroll_text(draw, "A", (95+offset, 0), font=self.font_status)

        # draw the VU table
        if self.play_state == "play":
            draw_vu(draw, volume_level=volume) 
            if self.manager.sleep:
                self.manager.turn_on_screen()
            draw_scroll_text(draw, "⏵", (offset, 0), font=self.font_status)
        else:
            draw_vu(draw, volume_level=0.0)
            draw_scroll_text(draw, "⏸", (offset, 0), font=self.font_status)
        
        # draw the volume wave icon
        # self.icon_drawer.draw_volume_wave(x=86, y=0, level=volume)
        
        if self.play_state == "play":
            self.manager.reset_sleep_timer() # reset the sleep timer
            
    def is_playing(self):
        return self.play_state == "play"

    def set_active(self, value):
        super().set_active(value)
        if value:
            self.last_play_time = time.time()
    
    def event_listener(self):
        self._read_metadata()

        # check if the pause state has been more than 5 minutes
        if self.play_state == "pause" and time.time() - self.last_play_time > self.pause_timout:  # 300 seconds = 5 minutes
            self.set_active(False)
