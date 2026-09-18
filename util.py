#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用工具函数（下载器用到的部分）

这里只保留 douyinDownloader.py 实际依赖的函数：get_video_duration。
"""

import json
import subprocess


def get_video_duration(video_path):
    """获取视频时长（秒），使用 ffprobe 解析视频元数据"""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "json",
        video_path,
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    if result.returncode == 0:
        duration_data = json.loads(result.stdout)
        return float(duration_data['format']['duration'])

    print(f"获取视频时长失败: {result.stderr}")
    return 0


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        print(get_video_duration(sys.argv[1]), "秒")
