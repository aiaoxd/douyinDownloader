import json
import os
import re
from urllib.parse import unquote
from tqdm import tqdm
import requests

def sanitize_filename(title):
    # 替换非法字符（例如 Windows 系统中的非法字符）
    sanitized_title = re.sub(r'[<>:"/\\|?*]', '_', title)  # 将非法字符替换为 '_'
    sanitized_title = sanitized_title.strip()  # 去除两端的空格
    return sanitized_title
def download_video(url):
    headers = {
        'Referer': 'https://www.douyin.com/',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    }

    # 发起请求，获取视频内容
    response = requests.get(url, headers=headers, stream=True)
    print(f"HTTP Status Code: {response.status_code}")

    # 如果没有video文件夹就创建
    if not os.path.exists('video'):
        os.makedirs('video')

    # 如果响应成功
    if response.status_code == 200:
        # 获取文件的总大小
        total_size = int(response.headers.get('Content-Length', 0))
        limit_title = title[:50]
        video_path = f'video/{sanitize_filename(limit_title)}.mp4'

        full_path = os.path.join(os.getcwd(),video_path)
        # 以二进制流的方式保存文件，带进度条
        with open(full_path, 'wb') as f:
            # 使用 tqdm 显示进度条
            with tqdm(total=total_size, unit='B', unit_scale=True, desc="Downloading") as pbar:
                for chunk in response.iter_content(chunk_size=1024):
                    # 写入文件
                    if chunk:
                        f.write(chunk)
                        pbar.update(len(chunk))  # 更新进度条
        print(f"video {full_path}已下载完成")

    else:
        print("Failed to retrieve the video.")


def get_video_url(url):
    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'cookie': '',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    }
    response = requests.get(url,headers=headers)
    content = re.findall('</div><script id="RENDER_DATA" type="application/json">(.*?)</script>', response.text)
    content = unquote(content[0])
    content = json.loads(content)
    part_url = content["app"]["videoDetail"]["video"]["bitRateList"][0]['playAddr'][0]['src']
    global title
    title = content["app"]["videoDetail"]["desc"]
    print(f'{title}')
    print("https://"+part_url)

    return "https:"+part_url


def get_modalid_from_share_link(share_link):
    """从分享链接中提取 modal_id"""

    # 先尝试从 URL 中直接提取 modal_id 参数
    modal_id_pattern = r'[?&]modal_id=(\d+)'
    match = re.search(modal_id_pattern, share_link)
    if match:
        modal_id = match.group(1)
        print(f"Extracted modal_id from direct modal_id= parameter: {modal_id}")
        return modal_id

    # 匹配视频链接，提取视频的 modal_id
    video_pattern = r'https://www\.douyin\.com/video/(\d+)'
    match = re.search(video_pattern, share_link)
    if match:
        modal_id = match.group(1)
        print(f"Extracted modal_id from video link: {modal_id}")
        return modal_id

    # 匹配带有 modal_id 参数的用户链接
    user_pattern = r'https://www\.douyin\.com/user/.+?modal_id=(\d+)'

    # 匹配带有 modal_id 参数的 discover 链接
    discover_pattern = r'https://www\.douyin\.com/discover\?modal_id=(\d+)'

    # 尝试匹配带有 modal_id 参数的用户链接
    match = re.search(user_pattern, share_link)
    if match:
        modal_id = match.group(1)
        print(f"Extracted modal_id from user link: {modal_id}")
        return modal_id

    # 尝试匹配 discover 链接中的 modal_id
    match = re.search(discover_pattern, share_link)
    if match:
        modal_id = match.group(1)
        print(f"Extracted modal_id from discover link: {modal_id}")
        return modal_id

    # 如果没有找到，继续处理分享链接
    pattern = r'https://v\.douyin\.com/[a-zA-Z0-9]+/?'
    try:
        # 提取分享链接中的 URL 部分
        url = re.findall(pattern, share_link)[0]
    except Exception as e:
        print('Invalid URL')
        return None

    print(f"Extracted URL: {url}")

    # 重试机制，最多重试5次
    max_retries = 5
    retries = 0
    while retries < max_retries:
        try:
            # 使用线程来进行请求
            response = make_request(url)

            # 检查是否成功获取最终重定向 URL
            if response.url:
                print(f"Final Redirect URL: {response.url}")
                print(response.url)
                # 提取 video modal_id
                pattern = r'https://www\.douyin\.com/video/(\d+)'
                match = re.search(pattern, response.url)

                if match:
                    modal_id = match.group(1)
                    print(f"Extracted modal_id: {modal_id}")
                    return modal_id
                else:
                    print("No modal_id found in final URL.")
                    retries += 1
                    time.sleep(2)  # 等待 2 秒再尝试
                    print(f"Retrying... ({retries}/{max_retries})")
            else:
                print("Invalid response URL. Retrying...")
                retries += 1
                time.sleep(2)  # 等待 2 秒再尝试
                print(f"Retrying... ({retries}/{max_retries})")

        except requests.exceptions.RequestException as e:
            retries += 1
            print(f"Request error: {e}. Retrying... ({retries}/{max_retries})")
            time.sleep(2)  # 等待 2 秒再尝试

    print("Max retries reached. Could not retrieve the modal_id.")
    return None

def make_request( url):
    """处理请求的函数，包含超时设置"""
    try:
        response = requests.get(url, headers=headers, allow_redirects=True, timeout=10)
        return response
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
        raise
if __name__ == '__main__':
    title = ''

    while True:
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'cookie': '',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        }

        shark = input("请输入抖音视频分享链接: ")
        modal_id = get_modalid_from_share_link(shark)
        if not modal_id:
            print("无效的分享链接")
        else:
            url = f'https://www.douyin.com/user/MS4wLjABAAAAf7i8sK5OxbSctQ45rmH2dDIFYNPmlqHRtnGucIQSRSGuQUiiYEoxdc2QpBIu5XmS?from_tab_name=main&modal_id={modal_id}'
            play_url = get_video_url(url)
            download_video(play_url)


