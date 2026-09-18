import shutil
import subprocess
from datetime import datetime

import json
import os
import re
import sys
import requests
from urllib.parse import unquote
from tqdm import tqdm
import time
import random
from glob import glob
import ffmpeg
import util
import path_config

class DouyinDownloader:
    # 浏览器监听方案使用的桌面 UA
    UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
          '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')

    def __init__(self, share_link, download_folder='doyinVideo'):
        self.share_link = share_link

        # 使用统一路径配置
        self.current_date = datetime.now().strftime('%Y-%m-%d')
        self.today_path = path_config.get_video_dir(self.current_date)
        self.download_folder = self.today_path
        
        print(f"📁 视频下载目录: {self.download_folder}")
        self.headers = {
            'Referer': 'https://www.douyin.com/',
            'cookie': os.environ.get('DOUYIN_COOKIE', ''),
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        }
        # Cookie 一律从外部注入，源码里不保存任何凭据
        self._fallback_cookie = os.environ.get('DOUYIN_COOKIE', '')
        self.headers['cookie'] = self._load_cookie()
        # 风控时轮换 UA，提高重试成功率
        self.ua_pool = [
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        ]
        os.makedirs(self.download_folder, exist_ok=True)

        # 浏览器监听方案（Playwright 监听 aweme/detail）相关状态
        self.headless = False
        self._pw = None
        self._browser = None
        self._page = None
        self._captured = None

    def _load_cookie(self):
        """按优先级取 Cookie：环境变量 DOUYIN_COOKIE > cookies.json > 空字符串。

        出于安全考虑，本文件不内置任何 Cookie。
        """
        # 1) 环境变量（CI / 临时调试最方便）
        env_cookie = os.environ.get('DOUYIN_COOKIE', '').strip()
        if env_cookie:
            print("🍪 已加载环境变量 DOUYIN_COOKIE")
            return env_cookie

        # 2) cookies.json（见仓库内的 cookies.example.json）
        cookie_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cookies.json')
        try:
            if os.path.exists(cookie_file):
                with open(cookie_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                cookies = data.get('cookies', {})
                if cookies:
                    cookie_str = '; '.join(f'{k}={v}' for k, v in cookies.items())
                    ts = data.get('timestamp', 0)
                    age_days = (time.time() - ts) / 86400 if ts else 999
                    if age_days < 7:
                        print(f"🍪 已加载 cookies.json（{age_days:.1f} 天前更新）")
                        return cookie_str
                    print(f"⚠️ cookies.json 已过期（{age_days:.0f} 天前）")
        except Exception as e:
            print(f"⚠️ 读取 cookies.json 失败: {e}")

        # 3) 都没有：无 Cookie 运行（公开视频仍可能成功，受限视频会失败）
        print("⚠️ 未检测到 Cookie。请设置环境变量 DOUYIN_COOKIE 或放置 cookies.json；"
              "无 Cookie 时部分视频会因风控下载失败。")
        return ''

    def sanitize_filename(self, title):
        """替换非法字符和可能导致问题的特殊字符"""
        # 替换非法字符和特殊字符（#、@等可能在shell中引起问题）
        sanitized_title = re.sub(r'[<>:"/\\|?*\r\n\t#@]', '_', title)
        sanitized_title = sanitized_title.strip()
        sanitized_title = sanitized_title[:50]
        return sanitized_title

    # 合并视频文件
    def merge_videos(self, video_files, output_file):
        """
        将多个视频文件合并为一个视频，确保视频流参数一致。
        :param video_files: 视频文件列表
        :param output_file: 输出文件路径
        """
        # 如果目标文件已经存在，先删除
        if os.path.exists(output_file):
            os.remove(output_file)

        # 如果只有一个视频，直接复制
        if len(video_files) == 1:
            shutil.copy(video_files[0], output_file)
            return

        # 获取第一个视频的分辨率
        first_video_resolution = self.get_video_resolution(video_files[0])
        target_width, target_height = first_video_resolution

        input_files = []

        # 添加输入文件并确保视频流统一
        for file in video_files:
            input_files.append(ffmpeg.input(file))

        # 使用filter设置统一的分辨率和显示比例
        video_streams = [input_file.video.filter('scale', target_width, target_height).filter('setsar', 1) for
                         input_file in input_files]


        # 如果没有音频流，只有视频流
        ffmpeg.concat(*video_streams, v=1, a=0).output(output_file, y=None, loglevel='fatal').run()

        print(f"视频合并成功，输出文件: {output_file}")

    def get_media_duration(self,file):
        """
        获取视频或音频文件的时长（秒）。
        :param file_path: 媒体文件路径
        :return: 媒体文件时长（秒）
        """
        try:
            # 获取文件的时长信息
            probe = ffmpeg.probe(file, v='error', select_streams='v:0', show_entries='format=duration')
            duration = float(probe['format']['duration'])
            return duration
        except ffmpeg.Error as e:
            print(f"获取 {file} 时长失败: {e}")
            return 0

    def merge_video_audio(self, video_file, audio_file, output_file):
        """
        将视频文件和音频文件合并为一个文件，确保时长一致。
        :param video_file: 视频文件路径
        :param audio_file: 音频文件路径
        :param output_file: 输出文件路径
        """
        # 获取视频和音频文件的时长
        video_duration = self.get_media_duration(video_file)
        audio_duration = self.get_media_duration(audio_file)

        # 取短的时长
        shortest_duration = min(video_duration, audio_duration)

        # 判断并截取视频
        if video_duration > shortest_duration:
            video_input = ffmpeg.input(video_file, t=shortest_duration)  # 截取视频
        else:
            video_input = ffmpeg.input(video_file)

        # 判断并截取音频
        if audio_duration > shortest_duration:
            audio_input = ffmpeg.input(audio_file, t=shortest_duration)  # 截取音频
        else:
            audio_input = ffmpeg.input(audio_file)
        # 合并视频和音频
        ffmpeg.output(video_input, audio_input, output_file, vcodec='copy', acodec='aac', strict='experimental', y=None,
                      loglevel='fatal').run()

        print(f"视频和音频合并成功，输出文件: {output_file}")
    # 合并视频和音频
    # def merge_video_audio(self, video_file, audio_file, output_file):
    #     """
    #     将视频文件和音频文件合并为一个文件
    #     :param video_file: 视频文件路径
    #     :param audio_file: 音频文件路径
    #     :param output_file: 输出文件路径
    #     """
    #     video_input = ffmpeg.input(video_file)
    #     audio_input = ffmpeg.input(audio_file)
    #     ffmpeg.output(video_input, audio_input, output_file, vcodec='copy', acodec='aac', strict='experimental', y=None, loglevel='fatal').run()
    # 创建图片视频
    def create_photo_video(self, image_files, duration, output_file):
        """
        将所有图片合并为一个视频，图片展示时间为平分后的时长。

        :param image_files: 图片文件列表
        :param duration: 视频时长
        :param output_file: 输出文件路径
        """
        image_count = len(image_files)
        # 每张图片的展示时间（秒）
        display_time = duration / image_count
        if display_time > 10 :
            display_time = 5
        # # 随机选择一个图片文件作为测试
        ffmpeg.input(image_files[0], loop=1, framerate=30 / display_time).output(output_file, t=(display_time), y=None, loglevel='fatal').run()

    def get_video_resolution(self,file_path):
        """
        获取视频文件的分辨率。

        :param file_path: 视频文件路径
        :return: (width, height) 分辨率
        """
        # 获取视频文件的元数据
        probe = ffmpeg.probe(file_path, v='error', select_streams='v:0', show_entries='stream=width,height')
        # 提取宽度和高度
        width = probe['streams'][0]['width']
        height = probe['streams'][0]['height']
        return width, height

    def remove_temp_mp4(self,image_folder):
        removed_file = ['v_com.mp4', 'p_com.mp4', 'final.mp4', 'comb.mp4']
        removed_files = [os.path.join(image_folder, file) for file in removed_file]

        for file in removed_files:
            if os.path.exists(file):
                os.remove(file)

    def combine_live_photo(self, image_folder):

        #删除 v_com.mp4 p_com.mp4 如果存在的话
        self.remove_temp_mp4(image_folder)

        # 获取所有的mp4文件
        mp4_files = glob(os.path.join(image_folder, "*.mp4"))
        print(mp4_files)
        # 获取所有的jpg文件
        jpg_files = glob(os.path.join(image_folder, "*.jpg"))
        print(jpg_files)

        # 获取mp3文件 com.mp3
        mp3_files = glob(os.path.join(image_folder, "*.mp3"))
        print(mp3_files)

        # 将mp4视频合并为v_com.mp4 之后判断mp3的音频长度是否大于视频长度 如果大于 将大于的部分时间记录为photo_dur 并合并所有的图片为视频 每个图片出现的时间平分photo_dur时长 视频长度为photo_dur 命名为p_com.mp4
        mp3_file = mp3_files[0]  # 假设只有一个 mp3 文件
        video_file = mp4_files[0]  # 假设只有一个视频文件

        # 获取视频的时长
        video_info = ffmpeg.probe(video_file, v='error', select_streams='v:0', show_entries='stream=duration')
        video_duration = float(video_info['streams'][0]['duration'])
        print('视频时长',video_duration)
        # 获取音频的时长
        audio_info = ffmpeg.probe(mp3_file, v='error', select_streams='a:0', show_entries='stream=duration')
        audio_duration = float(audio_info['streams'][0]['duration'])
        print('音频时长', audio_duration)
        # 合并所有视频为一个视频 v_com.mp4
        v_com_file = os.path.join(image_folder, 'v_com.mp4')
        self.merge_videos(mp4_files, v_com_file)

        # 判断音频时长是否大于视频时长
        photo_dur = 0
        if audio_duration > video_duration and len(jpg_files) > 0:
            # 如果音频比视频长，生成照片视频
            photo_dur = audio_duration - video_duration
            p_com_file = os.path.join(image_folder, 'p_com.mp4')
            self.create_photo_video(jpg_files, photo_dur, p_com_file)

            # 合并 v_com.mp4 和 p_com.mp4 为 comb.mp4
            comb_file = os.path.join(image_folder, 'comb.mp4')
            self.merge_videos([v_com_file, p_com_file], comb_file)

        else:
            # 否则直接用 v_com.mp4
            comb_file = v_com_file

        # 将comb.mp4视频和com.mp3 合并为final.mp4
        final_file = os.path.join(image_folder, 'final.mp4')
        self.merge_video_audio(comb_file, mp3_file, final_file)

        print(f"最终视频保存为：{final_file}")
    def download_image(self, url,image_path):
        if os.path.exists(image_path): # 如果已经下完了
            print(f"Video already downloaded - {image_path} ")
        else:
            """下载图片"""
            response = requests.get(url, headers=self.headers, stream=True)
            print(f"HTTP Status Code: {response.status_code}")

            if response.status_code == 200:
                # 获取文件的总大小
                total_size = int(response.headers.get('Content-Length', 0))

                # 保存视频文件
                with open(image_path, 'wb') as f:
                    with tqdm(total=total_size, unit='B', unit_scale=True, desc="Downloading") as pbar:
                        for chunk in response.iter_content(chunk_size=1024):
                            if chunk:
                                f.write(chunk)
                                pbar.update(len(chunk))  # 更新进度条
                print(f"Video {image_path} downloaded successfully.")
                time.sleep(0.5)

            else:
                print("Failed to retrieve the image.")


    # 下载mp3
    def download_audio(self, url, audio_path):
        """下载视频"""
        response = requests.get(url, headers=self.headers, stream=True)
        print(f"HTTP Status Code: {response.status_code}")
        if response.status_code == 200:
            # 获取文件的总大小
            total_size = int(response.headers.get('Content-Length', 0))
            # 保存音频文件
            with open(audio_path, 'wb') as f:
                with tqdm(total=total_size, unit='B', unit_scale=True, desc="Downloading") as pbar:
                    for chunk in response.iter_content(chunk_size=1024):
                        if chunk:
                            f.write(chunk)
                            pbar.update(len(chunk))  # 更新进度条
            print(f"Video {audio_path} downloaded successfully.")
            time.sleep(0.5)

    def download_path_video(self, url, title,index,path):

        video_index = index
        video_path = path

        if os.path.exists(video_path): # 如果已经下完了
            print(f"Video already downloaded - {video_path} ")
        else: # 重新下
            """下载视频"""
            response = requests.get(url, headers=self.headers, stream=True)

            if response.status_code == 200:
                total_size = int(response.headers.get('Content-Length', 0))
                with open(video_path, 'wb') as f:
                    with tqdm(total=total_size, unit='B', unit_scale=True, desc="Downloading") as pbar:
                        for chunk in response.iter_content(chunk_size=1024):
                            if chunk:
                                f.write(chunk)
                                pbar.update(len(chunk))  # 更新进度条
                print(f"Video {video_path} downloaded successfully.")
            else:
                print(f"Failed to retrieve the video for {title}.")

    def download_video(self, url, title, index):

        video_index = index
        video_path = os.path.join(self.download_folder, f"{video_index}_{self.sanitize_filename(title)}.mp4")

        if os.path.exists(video_path): # 如果已经下完了
            print(f"Video already downloaded - {video_path} ")
        else: # 重新下
            """下载视频"""
            response = requests.get(url, headers=self.headers, stream=True)

            if response.status_code == 200:
                total_size = int(response.headers.get('Content-Length', 0))
                with open(video_path, 'wb') as f:
                    with tqdm(total=total_size, unit='B', unit_scale=True, desc="Downloading") as pbar:
                        for chunk in response.iter_content(chunk_size=1024):
                            if chunk:
                                f.write(chunk)
                                pbar.update(len(chunk))  # 更新进度条
                print(f"Video {video_path} downloaded successfully.")
            else:
                print(f"Failed to retrieve the video for {title}.")

    def combine_static_photo(self, img_folder):
        # 获取所有的jpg文件，匹配模式 foldername_1.jpg, foldername_2.jpg, ...
        jpg_files = glob(os.path.join(img_folder, "*_*.jpg"))
        print("JPG Files:", jpg_files)

        if not jpg_files:
            print("没有找到任何图片")
            return

        # 对图片排序，确保顺序正确
        jpg_files.sort()

        # 每张图片展示时间（秒）
        display_time = 3  # 例如，每张图片展示3秒
        frame_rate = 1 / display_time  # 设置帧率

        # 输出视频文件路径
        output_video = os.path.join(img_folder, "output_video.mp4")

        # 转换图片为统一格式和尺寸（确保 JPEG 格式和尺寸一致）
        for img_file in jpg_files:
            try:
                # 使用 PIL 将图片保存为标准 JPEG 格式，确保图片大小一致
                from PIL import Image
                img = Image.open(img_file)
                img = img.convert('RGB')  # 转换为RGB模式，避免一些图像处理库不能处理的问题
                img = img.resize((1080,1920))  # 将图片调整为固定大小，确保一致性
                img.save(img_file, 'JPEG')  # 保存为标准 JPEG 格式
            except Exception as e:
                print(f"处理图片 {img_file} 时出错: {e}")
                return

        # 通过 ffmpeg 将图片合成视频
        subprocess.run([
            'ffmpeg',
            '-framerate', str(frame_rate),  # 每秒多少帧
            '-pattern_type', 'glob',  # 使用 glob 模式匹配文件
            '-i', os.path.join(img_folder, '*_*.jpg'),  # 图片文件路径，假设文件名为 *_*.jpg
            '-s', '1080x1920',  # 设置视频的分辨率，例：1920x1080
            '-c:v', 'libx264',  # 使用 libx264 视频编码
            '-r', '30',  # 设置视频的帧率为 30
            '-pix_fmt', 'yuv420p',  # 设置视频的像素格式
            '-y', '-loglevel', 'error',  # 强制覆盖输出文件
            output_video  # 输出文件路径
        ])

        print(f"视频已生成并保存至: {output_video}")

        # 获取视频时长（秒）
        video_duration = util.get_video_duration(output_video)

        print(f"视频时长: {video_duration} 秒")

        # 获取 mp3 文件
        mp3_files = glob(os.path.join(img_folder, "*.mp3"))
        if not mp3_files:
            print("没有找到 MP3 文件")
            return

        mp3_file = mp3_files[0]
        print("MP3 文件:", mp3_file)

        # 获取音频时长（秒）
        audio_duration_cmd = ['ffmpeg', '-i', mp3_file]
        audio_duration_result = subprocess.run(audio_duration_cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE,
                                               text=True)
        audio_duration_output = audio_duration_result.stderr
        audio_duration = float(audio_duration_output.split("Duration: ")[1].split(",")[0].split(":")[2])

        print(f"音频时长: {audio_duration} 秒")

        # 如果音频比视频长，裁剪音频
        if audio_duration > video_duration:
            print("音频长于视频，裁剪音频...")
            trimmed_audio_file = os.path.join(img_folder, 'trimmed_audio.mp3')

            # 重新编码音频并裁剪，确保音频格式正确
            subprocess.run([
                'ffmpeg',
                '-i', mp3_file,  # 输入音频文件
                '-t', str(video_duration),  # 设置音频裁剪的时长为视频时长
                '-acodec', 'libmp3lame',  # 重新编码为 MP3 格式
                '-ar', '44100',  # 设置音频采样率
                '-ac', '2',  # 设置音频通道为立体声
                '-y',  # 强制覆盖输出文件
                trimmed_audio_file  # 输出裁剪后的音频文件
            ])
            mp3_file = trimmed_audio_file  # 使用裁剪后的音频文件

        # 合并视频和音频
        output_video_with_audio = os.path.join(img_folder, "final_output_video.mp4")
        subprocess.run([
            'ffmpeg',
            '-i', output_video,  # 输入视频文件
            '-i', mp3_file,  # 输入音频文件
            '-c:v', 'libx264',  # 视频编码
            '-c:a', 'aac',  # 音频编码
            '-shortest',  # 确保输出文件的时长与最短的流一致（这里是视频）
            '-y', '-loglevel', 'error', # 强制覆盖输出文件
            output_video_with_audio  # 输出文件路径
        ])

        print(f"最终视频已生成并保存至: {output_video_with_audio}")

    # ===================== 浏览器监听方案（接自 v2：Playwright 监听 aweme/detail） =====================
    @staticmethod
    def _find_chrome():
        """返回本机 Chrome 可执行文件路径，找不到返回 None"""
        candidates = [
            '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
            os.path.expanduser(
                '~/Library/Caches/ms-playwright/chromium-1234/chrome-mac-arm64/'
                'Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing'
            ),
        ]
        for p in candidates:
            if os.path.exists(p):
                return p
        return None

    def _on_response(self, resp):
        """Playwright 响应监听器：拦截 aweme/detail 的 JSON 响应"""
        if 'aweme/detail' in resp.url and self._captured is None:
            try:
                self._captured = resp.json()
            except Exception:
                pass  # 非 JSON（如挑战页）直接忽略

    def _ensure_browser(self):
        """懒启动浏览器（仅一次），之后在批量任务中复用"""
        if self._page is not None:
            return
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise RuntimeError(
                '未安装 playwright，无法使用浏览器监听下载。请在该项目的 Python 环境中执行：\n'
                '  pip install playwright\n'
                '  playwright install chromium'
            )
        chrome = self._find_chrome()
        if chrome is None:
            raise RuntimeError('未找到 Chrome，请安装 Google Chrome 后重试')
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(
            executable_path=chrome,
            headless=self.headless,
            args=['--no-first-run', '--window-position=3000,3000'],
        )
        ctx = self._browser.new_context(user_agent=self.UA, locale='zh-CN')
        self._page = ctx.new_page()
        self._page.on('response', self._on_response)
        print('✅ 浏览器已启动（监听 aweme/detail）')

    def close(self):
        """关闭浏览器，释放资源"""
        for closer in (self._browser.close if self._browser else None,
                       self._pw.stop if self._pw else None):
            if closer:
                try:
                    closer()
                except Exception:
                    pass
        self._pw = self._browser = self._page = None

    @staticmethod
    def get_video_id(link):
        """从分享链接 / 视频页 / 用户页中解析视频 ID"""
        if 'v.douyin.com' in link:
            try:
                r = requests.get(link, headers={'User-Agent': DouyinDownloader.UA},
                                 timeout=15, allow_redirects=True)
                link = r.url
            except Exception as e:
                print(f'⚠️ 短链解析失败: {e}')
                return None
        m = re.search(r'(?:video/|modal_id=)(\d+)', link)
        return m.group(1) if m else None

    def get_aweme_detail(self, video_id, wait_seconds=40, retries=2):
        """打开视频页并监听 aweme/detail，返回 aweme_detail 字典；失败返回 None。

        冷启动（浏览器刚启动后的首个导航）偶发需要更久才能触发详情请求，
        因此内置重试：每次重试重新打开页面再等待一次，第二次浏览器已 warm 几乎必成。
        """
        self._ensure_browser()
        url = f'https://www.douyin.com/video/{video_id}'
        data = None
        for attempt in range(1, retries + 1):
            self._captured = None
            try:
                self._page.goto(url, timeout=60000, wait_until='domcontentloaded')
            except Exception as e:
                print(f'⚠️ [{video_id}] 第{attempt}次打开页面异常: {e}')
            deadline = time.time() + wait_seconds
            while time.time() < deadline:
                if self._captured is not None:
                    break
                self._page.wait_for_timeout(500)
            data = self._captured
            if data is not None:
                break
            print(f'⚠️ [{video_id}] 第{attempt}/{retries}次 {wait_seconds}s 内未监听到 aweme/detail'
                  f'{"，重试中..." if attempt < retries else "，放弃"}')
        if data is None:
            print(f'❌ [{video_id}] 多次尝试仍未监听到 aweme/detail 请求')
            return None
        detail = data.get('aweme_detail')
        if not detail:
            fd = data.get('filter_detail') or {}
            msg = fd.get('detail_msg') or '未知原因（可能已删除/私密）'
            print(f'❌ [{video_id}] 视频不可用：{msg}')
            return None
        return detail

    @staticmethod
    def _pick_video_url(detail):
        """从 aweme_detail 中挑选最高码率的视频直链，过滤音乐 mp3 / 占位地址"""
        video = detail.get('video') or {}
        bit_rate = sorted(video.get('bit_rate') or [],
                          key=lambda g: g.get('bit_rate', 0), reverse=True)
        for gear in bit_rate:
            urls = ((gear.get('play_addr') or {}).get('url_list')) or []
            for u in urls:
                if 'douyinstatic' not in u and not u.endswith('.mp3'):
                    return u
        for u in (video.get('play_addr') or {}).get('url_list', []):
            if 'douyinstatic' not in u and not u.endswith('.mp3'):
                return u
        return None

    def get_video_url(self, url, video_index, wait_seconds=40):
        """通过浏览器监听 aweme/detail 获取播放地址 / 下载图文动图。

        返回 (play_url, title)：
          - 普通视频：play_url 为 http(s) 直链，由 download_video 负责下载
          - 图文 / 动图：已在内部下载并合并为 mp4，play_url 为本地文件路径
        失败返回 (None, None)。
        """
        video_id = self.get_video_id(url)
        if not video_id:
            print(f'❌ 无法从链接解析视频 ID: {url[:80]}')
            return None, None

        detail = self.get_aweme_detail(video_id, wait_seconds=wait_seconds)
        if detail is None:
            return None, None

        title = self.sanitize_filename(detail.get('desc', '') or video_id)
        media_type = detail.get('media_type')
        print(f'📹 [{video_id}] {detail.get("desc", "")}')

        # ---------- 图文作品（media_type == 2） ----------
        if media_type == 2:
            folder = os.path.join(self.download_folder, f'图文_{title}')
            os.makedirs(folder, exist_ok=True)
            for i, img in enumerate(detail.get('images', []), 1):
                urls = (img or {}).get('url_list', [])
                if urls:
                    self.download_image(urls[0], os.path.join(folder, f'{title}_{i}.jpg'))
            music = (detail.get('music') or {}).get('play_url') or {}
            for u in music.get('url_list', []):
                if u:
                    self.download_audio(u, os.path.join(folder, f'{title}.mp3'))
                    break
            self.combine_static_photo(folder)
            video_path = os.path.join(self.download_folder, f'{video_index}_{title}.mp4')
            final_file = os.path.join(folder, 'final_output_video.mp4')
            if os.path.exists(final_file):
                shutil.move(final_file, video_path)
                print('✅ 图文已下载并合并完成')
                return video_path, title
            print('❌ 图文合并失败（缺少图片或音频）')
            return None, title

        # ---------- 动图作品（media_type == 42） ----------
        if media_type == 42:
            folder = os.path.join(self.download_folder, f'动图_{title}')
            os.makedirs(folder, exist_ok=True)
            for i, img in enumerate(detail.get('images', []), 1):
                video_info = (img or {}).get('video')
                if video_info:
                    pa = video_info.get('play_addr') or {}
                    vurls = list(pa.get('url_list') or [])
                    if not vurls and video_info.get('playAddr'):
                        vurls = [x.get('src') for x in video_info.get('playAddr') if x.get('src')]
                    vurl = next((u for u in vurls if u and not u.endswith('.mp3')), None)
                    if vurl:
                        if not vurl.startswith('http'):
                            vurl = 'https:' + vurl
                        self.download_path_video(vurl, title, i, os.path.join(folder, f'{title}_{i}.mp4'))
                else:
                    urls = (img or {}).get('url_list', [])
                    if urls:
                        self.download_image(urls[0], os.path.join(folder, f'{title}_{i}.jpg'))
            music = (detail.get('music') or {}).get('play_url') or {}
            for u in music.get('url_list', []):
                if u:
                    self.download_audio(u, os.path.join(folder, f'{title}.mp3'))
                    break
            self.combine_live_photo(folder)
            video_path = os.path.join(self.download_folder, f'{video_index}_{title}.mp4')
            final_file = os.path.join(folder, 'final.mp4')
            if os.path.exists(final_file):
                shutil.move(final_file, video_path)
                print('✅ 动图已下载并合并完成')
                return video_path, title
            print('❌ 动图合并失败（缺少视频或音频）')
            return None, title

        # ---------- 普通视频 ----------
        play_url = self._pick_video_url(detail)
        if not play_url:
            print('  ❌ 未提取到可用的视频播放地址')
            return None, title
        if not play_url.startswith('http'):
            play_url = 'https:' + play_url
        return play_url, title

    def get_modalid_from_share_link(self):
        """从分享链接中提取 modal_id"""
        video_pattern = r'https://www\.douyin\.com/video/(\d+)'
        match = re.search(video_pattern, self.share_link)
        if match:
            modal_id = match.group(1)
            return modal_id
        return None
    def download_signle_with_modalid(self, modal_id, index=1):
        """下载单个视频（浏览器监听方案，结束后自动关闭浏览器）"""
        print(f"Downloading video {index} with id: {modal_id}")
        try:
            url = f'https://www.douyin.com/video/{modal_id}'
            play_url, title = self.get_video_url(url, index)
            if play_url and isinstance(play_url, str) and play_url.startswith('http'):
                self.download_video(play_url, title, index)
        finally:
            self.close()
        time.sleep(2)

    def start_download(self, links):
        """批量下载视频
        
        Args:
            links: 视频ID列表
            
        Returns:
            bool: 下载是否成功（至少下载一个视频返回True，否则返回False）
        """
        if not links:
            print("❌ 错误：视频ID列表为空，无法下载")
            return False
            
        success_count = 0
        fail_count = 0
        
        for index, modal_id in enumerate(links, start=1):
            print(f"Downloading video {index} with id: {modal_id}")
            try:
                # 直接用标准视频页地址，不依赖任何特定用户主页
                url = f'https://www.douyin.com/video/{modal_id}'
                play_url, title = self.get_video_url(url, index)
                if not play_url:
                    print(f"⚠️ 视频 {index} 获取播放地址失败")
                    fail_count += 1
                elif isinstance(play_url, str) and play_url.startswith('http'):
                    self.download_video(play_url, title, index)
                    success_count += 1
                elif os.path.exists(play_url):
                    success_count += 1
                else:
                    print(f"⚠️ 视频 {index} 下载结果异常")
                    fail_count += 1
            except Exception as e:
                print(f"❌ 下载视频 {index} 时出错: {e}")
                fail_count += 1
            # 间隔太短容易触发风控，随机化并放宽到 1.5~3.5 秒
            time.sleep(random.uniform(1.5, 3.5))
        
        print(f"\n📊 下载统计：成功 {success_count} 个，失败 {fail_count} 个")
        
        # 批量任务结束，关闭浏览器释放资源
        self.close()

        # 至少成功下载一个视频才算成功
        return success_count > 0


# ============================ 命令行入口 ============================
# 用法：
#   python douyinDownloader.py                 # 交互式：按提示粘贴分享链接，一行一个，回车两次开始
#   python douyinDownloader.py <链接1> <链接2>  # 直接传分享链接
#   python douyinDownloader.py -f links.txt    # 从文件读取（每行一个链接）
if __name__ == '__main__':
    args = sys.argv[1:]

    links = []
    if args and args[0] in ('-f', '--file'):
        if len(args) < 2:
            print("❌ 请用 -f <文件路径> 指定链接文件")
            sys.exit(1)
        with open(args[1], 'r', encoding='utf-8') as f:
            links = [ln.strip() for ln in f if ln.strip()]
    elif args:
        links = args
    else:
        print("请输入抖音分享链接（一行一个，直接回车结束输入）：")
        while True:
            try:
                line = input().strip()
            except EOFError:
                break
            if not line:
                break
            links.append(line)

    if not links:
        print("❌ 没有输入任何链接")
        sys.exit(1)

    downloader = DouyinDownloader('')
    try:
        # 统一先把「分享短链 / 视频页链接」解析成视频 ID，再批量下载
        video_ids = []
        for link in links:
            vid = DouyinDownloader.get_video_id(link)
            if vid:
                video_ids.append(vid)
            else:
                print(f"⚠️ 无法解析视频 ID，已跳过: {link[:80]}")

        if not video_ids:
            print("❌ 没有解析到任何有效的视频 ID")
            sys.exit(1)

        ok = downloader.start_download(video_ids)
        print("✅ 全部处理完成" if ok else "⚠️ 有部分视频未能下载，请检查上面的日志")
    finally:
        downloader.close()
