# /*****************************************************************************
# * | File        :	  main.py
# * | Author      :   PuterJam
# * | Function    :   Muspi Entertainment with AI Agent
# * | Info        :
# *----------------
# * | This version:   V1.0
# * | Date        :   2025-05-07
# * | Info        :   
# ******************************************************************************/
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documnetation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to  whom the Software is
# furished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS OR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
# 
#           .~~.   .~~.
#          '. \ ' ' / .'   
#           .~ .~~~..~.          __  ___                     _ 
#          : .~.'~'.~. :        /  |/  /__  __ _____ ____   (_)
#         ~ (   ) (   ) ~      / /|_/ // / / // ___// __ \ / / 
#        ( : '~'.~.'~' : )    / /  / // /_/ /(__  )/ /_/ // /  
#         ~ .~ (   ) ~. ~    /_/  /_/ \__,_//____// .___//_/   
#          (  : '~' :  )                         /_/           
#           '~ .~~~. ~'      Created by PuterJam               
#               '~'        

# add oled driver (luma.oled based)
from drive.luma.ssd1305 import ssd1305
from drive.luma.ssd1309 import ssd1309

# add Display Manager
from screen.manager import DisplayManager
from until.log import LOGGER
# add screen plugins
from screen.plugin import PluginManager


import json
import os


def load_config(key,default={}):
    """加载配置"""
    config_path = os.path.join(os.path.dirname(__file__), 'config', 'muspi.json')

    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            return config.get(key, default)

    # 默认配置
    return default


def detect_display():
    """
    从配置文件读取显示设备设置并返回设备实例
    注意：由于 ssd1305 和 ssd1309 都基于 ssd1306，无法通过自动检测区分，必须手动配置
    """
    display_config = load_config("display", {"driver": "waveshare-1309"})
    drivers_config = load_config("drivers", {})

    # 获取选择的驱动名称
    driver_name = display_config.get('driver', 'waveshare-1309')

    # 获取驱动的详细配置
    driver_config = drivers_config.get(driver_name)
    if not driver_config:
        raise ValueError(f"driver config not found: {driver_name}")

    driver = driver_config.get('driver', 'ssd1309')
    width = driver_config.get('width', 128)
    height = driver_config.get('height', 64)
    rotate = driver_config.get('rotate', 0)

    LOGGER.info(f"try init display device: {driver_name} -> {driver} ({width}x{height}, rotate={rotate})")

    try:
        if driver == 'ssd1309':
            device = ssd1309(width=width, height=height, rotate=rotate)
        elif driver == 'ssd1305':
            device = ssd1305(width=width, height=height, rotate=rotate)
        else:
            raise ValueError(f"unsupported driver: {driver}")

        LOGGER.info(f"✓ display device init success: {device.width}x{device.height}")
        return device

    except Exception as e:
        LOGGER.error(f"✗ display device init failed: {e}")
        raise


def main():
    # 加载配置
    config = load_config("path",{})
    
    user_path = config.get('user','/var/lib/muspi')

    # 检测并初始化显示设备
    device = detect_display()

    # init manager
    manager = DisplayManager(device=device)
    manager.set_path("user", user_path)
    
    # create plugin manager
    plugin = PluginManager(manager)
    
    # load plugins
    plugin.load()
    
    # start main loop
    manager.run()


if __name__ == "__main__":
    main()