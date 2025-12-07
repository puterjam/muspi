from abc import ABC, abstractmethod
from pathlib import Path
from PIL import Image, ImageDraw
from until.log import LOGGER
from screen.manager import FONTS

DEFAULT_FPS = 8.0

class DisplayPlugin(ABC):
    """Base class for display plugins"""

    def __init__(self, manager, width, height):
        """Initialize the display plugin

        Args:
            manager: DisplayManager instance
            width: Display width
            height: Display height
        """
        # Manager
        self.manager = manager
        self.width = width
        self.height = height


        # ID
        self.name = self.name or "base"

        # Work path - plugin's directory path (calculated from plugin name)
        # e.g., for clock plugin: Path("screen/plugins/clock")
        self.work_path = Path(f"screen/plugins/{self.name}")
        
        # Image Buffer
        self.image = Image.new('1', (width, height))
        self.draw = ImageDraw.Draw(self.image)
        
        # Fonts
        self.font_status = FONTS.size_5
        self.font8 = FONTS.size_8
        self.font10 = FONTS.size_10
        self.font12 = FONTS.size_12
        self.font16 = FONTS.size_16

        
        # Parameters
        self.is_active = False # whether the plugin is active
        self._fps = DEFAULT_FPS
        
        LOGGER.info(f"[\033[1m{self.name}\033[0m] initialized.")

    def update(self):
        self.clear() #default clear the canvas
        self.render()
    
    @abstractmethod
    def render(self):
        """render canvas in display"""
        pass
    
    # @abstractmethod
    def event_listener(self):
        """listen to the metadata"""
        pass

    def is_playing(self):
        """check if the plugin is playing"""
        pass

    def wants_exclusive_input(self) -> bool:
        """
        是否需要独占输入（例如游戏插件需要方向键）

        返回 True 时，DisplayManager 不会用导航键处理全局功能
        """
        return False

    def get_active(self):
        """check if the plugin should be activated"""
        return self.is_active
    
    def set_active(self, active):
        """set the active state of the plugin"""
        if self.manager.last_active != self and active:
            if self.manager.last_active:
                self.manager.last_active.set_active(False)
            self.manager.last_active = self
            LOGGER.info(f"[\033[1m\033[37m{self.name}\033[0m] set active. register id: {self.id}")
            self.manager.active_id = self.id
            if self.manager.sleep:
                self.manager.turn_on_screen()

        if self.manager.last_active == self and not active:
            self.manager.last_active = None

        self.is_active = active
    
    def get_image(self):
        """get the current image"""
        return self.image
    
    def clear(self):
        """clear the display"""
        self.draw.rectangle((0, 0, self.width, self.height), fill=0) 
    
    @property
    def canvas(self):
        """get the canvas draw object"""
        return self.draw
    
    @property
    def framerate(self):
        """get the current framerate"""
        return 1.0 / self._fps
    
    @framerate.setter
    def framerate(self, value):
        """set the current framerate"""
        self._fps = value
