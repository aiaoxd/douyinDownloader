#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
路径配置模块 - 统一管理所有文件路径
所有路径都基于脚本所在目录，不依赖任何本机绝对路径，换台机器直接可用。
"""

import os
from datetime import datetime

# 获取脚本所在目录的绝对路径
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 下载根目录（可用环境变量覆盖）
DOWNLOAD_ROOT = os.environ.get('DOUYIN_DOWNLOAD_DIR', os.path.join(SCRIPT_DIR, 'downloads'))


def get_base_dir():
    """获取基础目录（脚本所在目录）"""
    return SCRIPT_DIR


def get_download_root():
    """获取下载根目录"""
    os.makedirs(DOWNLOAD_ROOT, exist_ok=True)
    return DOWNLOAD_ROOT


def get_video_dir(date_str=None):
    """获取当天视频下载目录"""
    if date_str is None:
        date_str = datetime.now().strftime('%Y-%m-%d')
    video_dir = os.path.join(get_download_root(), date_str)
    os.makedirs(video_dir, exist_ok=True)
    return video_dir


def get_temp_dir():
    """获取临时文件目录"""
    temp_dir = os.path.join(SCRIPT_DIR, 'temp')
    os.makedirs(temp_dir, exist_ok=True)
    return temp_dir


def get_cookies_file():
    """获取 cookies.json 路径"""
    return os.path.join(SCRIPT_DIR, 'cookies.json')


def get_temp_file(filename):
    """获取临时文件的完整路径"""
    return os.path.join(get_temp_dir(), filename)


if __name__ == '__main__':
    print("脚本目录:", SCRIPT_DIR)
    print("下载根目录:", get_download_root())
    print("今日视频目录:", get_video_dir())
    print("临时目录:", get_temp_dir())
    print("Cookies 文件:", get_cookies_file())
