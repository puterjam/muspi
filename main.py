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

# add Display Manager
from screen.manager import DisplayManager

# add screen plugins
from screen.plugin import PluginManager


def main():
    device = ssd1305(rotate=2)
    
    # init manager
    manager = DisplayManager(device=device)

    # create plugin manager
    plugin = PluginManager(manager)
    
    # load plugins
    plugin.load()
    
    # start main loop
    manager.run()


if __name__ == "__main__":
    main()