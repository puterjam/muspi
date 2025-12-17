from PIL import ImageFont
from until.resource import get_resource_path

class Fonts:
    def __init__(self):
        self.size_5 = ImageFont.truetype(get_resource_path("assets/fonts/QuinqueFive.ttf"), 5)
        self.size_8 = ImageFont.truetype(get_resource_path("assets/fonts/fusion-pixel-8px.ttf"), 8)
        self.size_10 = ImageFont.truetype(get_resource_path("assets/fonts/fusion-pixel-10px.ttf"), 10)
        self.size_12 = ImageFont.truetype(get_resource_path("assets/fonts/fusion-pixel-12px.ttf"), 12)
        self.size_16 = ImageFont.truetype(get_resource_path("assets/fonts/fusion-pixel-8px.ttf"), 16)