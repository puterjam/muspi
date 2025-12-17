"""
资源路径处理模块
用于处理开发环境和 PyInstaller 打包后的资源路径
"""
import os
import sys


def get_resource_path(relative_path):
    """
    获取资源文件的绝对路径
    在开发环境和 PyInstaller 打包后都能正确工作

    Args:
        relative_path: 相对于项目根目录的路径，例如 "assets/fonts/font.ttf"

    Returns:
        资源文件的绝对路径
    """
    # PyInstaller 会设置 sys._MEIPASS 指向临时解压目录
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # 打包后的环境
        base_path = sys._MEIPASS
    else:
        # 开发环境，使用项目根目录
        # 假设此文件在 until/ 目录下
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    return os.path.join(base_path, relative_path)


def get_project_root():
    """
    获取项目根目录

    Returns:
        项目根目录的绝对路径
    """
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return sys._MEIPASS
    else:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
