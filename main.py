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
    检测显示设备并返回设备实例
    如果检测失败，从配置文件读取设置
    """
    config = load_config("display")
    
    driver = config.get('driver', 'ssd1309')
    width = config.get('width', 128)
    height = config.get('height', 64)
    rotate = config.get('rotate', 0)
    
    LOGGER.info(f"try init display device: {driver} ({width}x{height}, rotate={rotate})")

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