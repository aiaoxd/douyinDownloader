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
        video_path = f'video/{sanitize_filename(title)}.mp4'

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
        'cookie': 'douyin.com; device_web_cpu_core=10; device_web_memory_size=8; __ac_nonce=06760391f00b9b51264ae; __ac_signature=_02B4Z6wo00f019a5ceAAAIDAhEZR-X3jjWfWmXVAAJLXd4; ttwid=1%7C7MTKBSMsP4eOv9h5NAh8p0E-NYIud09ftNmB0mjLpWc%7C1734359327%7C8794abeabbd47447e1f56e5abc726be089f2a0344d6343b5f75f23e7b0f0028f; UIFID_TEMP=0de8750d2b188f4235dbfd208e44abbb976428f0720eb983255afefa45d39c0c6532e1d4768dd8587bf919f866ff1396912bcb2af71efee56a14a2a9f37b74010d0a0413795262f6d4afe02a032ac7ab; s_v_web_id=verify_m4r4ribr_c7krmY1z_WoeI_43po_ATpO_I4o8U1bex2D7; hevc_supported=true; home_can_add_dy_2_desktop=%220%22; dy_swidth=2560; dy_sheight=1440; stream_recommend_feed_params=%22%7B%5C%22cookie_enabled%5C%22%3Atrue%2C%5C%22screen_width%5C%22%3A2560%2C%5C%22screen_height%5C%22%3A1440%2C%5C%22browser_online%5C%22%3Atrue%2C%5C%22cpu_core_num%5C%22%3A10%2C%5C%22device_memory%5C%22%3A8%2C%5C%22downlink%5C%22%3A10%2C%5C%22effective_type%5C%22%3A%5C%224g%5C%22%2C%5C%22round_trip_time%5C%22%3A50%7D%22; strategyABtestKey=%221734359328.577%22; csrf_session_id=2f53aed9aa6974e83aa9a1014180c3a4; fpk1=U2FsdGVkX1/IpBh0qdmlKAVhGyYHgur4/VtL9AReZoeSxadXn4juKvsakahRGqjxOPytHWspYoBogyhS/V6QSw==; fpk2=0845b309c7b9b957afd9ecf775a4c21f; passport_csrf_token=d80e0c5b2fa2328219856be5ba7e671e; passport_csrf_token_default=d80e0c5b2fa2328219856be5ba7e671e; odin_tt=3c891091d2eb0f4718c1d5645bc4a0017032d4d5aa989decb729e9da2ad570918cbe5e9133dc6b145fa8c758de98efe32ff1f81aa0d611e838cc73ab08ef7d3f6adf66ab4d10e8372ddd628f94f16b8e; volume_info=%7B%22isUserMute%22%3Afalse%2C%22isMute%22%3Afalse%2C%22volume%22%3A0.5%7D; bd_ticket_guard_client_web_domain=2; FORCE_LOGIN=%7B%22videoConsumedRemainSeconds%22%3A180%7D; UIFID=0de8750d2b188f4235dbfd208e44abbb976428f0720eb983255afefa45d39c0c6532e1d4768dd8587bf919f866ff139655a3c2b735923234f371c699560c657923fd3d6c5b63ab7bb9b83423b6cb4787e2ce66a7fbc4ecb24c8570f520fe6de068bbb95115023c0c6c1b6ee31b49fb7e3996fb8349f43a3fd8b7a61cd9e18e8fe65eb6a7c13de4c0960d84e344b644725db3eb2fa6b7caf821de1b50527979f2; is_dash_user=1; biz_trace_id=b57a241f; bd_ticket_guard_client_data=eyJiZC10aWNrZXQtZ3VhcmQtdmVyc2lvbiI6MiwiYmQtdGlja2V0LWd1YXJkLWl0ZXJhdGlvbi12ZXJzaW9uIjoxLCJiZC10aWNrZXQtZ3VhcmQtcmVlLXB1YmxpYy1rZXkiOiJCTEo2R0lDalVoWW1XcHpGOFdrN0Vrc0dXcCtaUzNKY1g4NGNGY2k0TTl1TEowNjdUb21mbFU5aDdvWVBGamhNRWNRQWtKdnN1MnM3RmpTWnlJQXpHMjA9IiwiYmQtdGlja2V0LWd1YXJkLXdlYi12ZXJzaW9uIjoyfQ%3D%3D; download_guide=%221%2F20241216%2F0%22; sdk_source_info=7e276470716a68645a606960273f276364697660272927676c715a6d6069756077273f276364697660272927666d776a68605a607d71606b766c6a6b5a7666776c7571273f275e58272927666a6b766a69605a696c6061273f27636469766027292762696a6764695a7364776c6467696076273f275e5827292771273f273d33323131333c3036313632342778; bit_env=RiOY4jzzpxZoVCl6zdVSVhVRjdwHRTxqcqWdqMBZLPGjMdB4Tax1kAELHNTVAAh72KuhumewE4Lq6f0-VJ2UpJrkrhSxoPw9LUb3zQrq1OSwbeSPHkRlRgRQvO89sItdGUyq1oFr0XyRCnMYG87KSeWyc4x0czGR0o50hTDoDLG5rJVoRcdQOLvjiAegsqyytKF59sPX_QM9qffK2SqYsg0hCggURc_AI6kguDDE5DvG0bnyz1utw4z1eEnIoLrkGDqzqBZj4dOAr0BVU6ofbsS-pOQ2u2PM1dLP9FlBVBlVaqYVgHJeSLsR5k76BRTddUjTb4zEilVIEwAMJWGN4I1BxVt6fC9B5tBQpuT0lj3n3eKXCKXZsd8FrEs5_pbfDsxV-e_WMiXI2ff4qxiTC0U73sfo9OpicKICtZjdq8qsHxJuu6wVR36zvXeL2Wch5C6MzprNvkivv0l8nbh2mSgy1nabZr3dmU6NcR-Bg3Q3xTWUlR9aAUmpopC-cNuXjgLpT-Lw1AYGilSUnCvosth1Gfypq-b0MpgmdSDgTrQ%3D; gulu_source_res=eyJwX2luIjoiMDhjOGQ3ZTJiODQyNjZkZWI5Y2VkMGJiODNlNmY1ZWY0ZjMyNTE2ZmYyZjAzNDMzZjI0OWU1Y2Q1NTczNTk5NyJ9; passport_auth_mix_state=hp9bc3dgb1tm5wd8p82zawus27g0e3ue; IsDouyinActive=false',
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
    # 正则表达式
    pattern = r'https://v\.douyin\.com/[a-zA-Z0-9]+/?'

    # 查找所有匹配的 URL
    try:
        url = re.findall(pattern, share_link)[0]
    except Exception as e:
        print('未找到链接')
        return None

    print(url)
    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'cookie': 'ttwid=1%7C7MTKBSMsP4eOv9h5NAh8p0E-NYIud09ftNmB0mjLpWc%7C1734359327%7C8794abeabbd47447e1f56e5abc726be089f2a0344d6343b5f75f23e7b0f0028f; UIFID_TEMP=0de8750d2b188f4235dbfd208e44abbb976428f0720eb983255afefa45d39c0c6532e1d4768dd8587bf919f866ff1396912bcb2af71efee56a14a2a9f37b74010d0a0413795262f6d4afe02a032ac7ab; hevc_supported=true; home_can_add_dy_2_desktop=%220%22; stream_recommend_feed_params=%22%7B%5C%22cookie_enabled%5C%22%3Atrue%2C%5C%22screen_width%5C%22%3A2560%2C%5C%22screen_height%5C%22%3A1440%2C%5C%22browser_online%5C%22%3Atrue%2C%5C%22cpu_core_num%5C%22%3A10%2C%5C%22device_memory%5C%22%3A8%2C%5C%22downlink%5C%22%3A10%2C%5C%22effective_type%5C%22%3A%5C%224g%5C%22%2C%5C%22round_trip_time%5C%22%3A50%7D%22; strategyABtestKey=%221734359328.577%22; passport_csrf_token=d80e0c5b2fa2328219856be5ba7e671e; passport_csrf_token_default=d80e0c5b2fa2328219856be5ba7e671e; odin_tt=3c891091d2eb0f4718c1d5645bc4a0017032d4d5aa989decb729e9da2ad570918cbe5e9133dc6b145fa8c758de98efe32ff1f81aa0d611e838cc73ab08ef7d3f6adf66ab4d10e8372ddd628f94f16b8e; volume_info=%7B%22isUserMute%22%3Afalse%2C%22isMute%22%3Afalse%2C%22volume%22%3A0.5%7D; bd_ticket_guard_client_web_domain=2; FORCE_LOGIN=%7B%22videoConsumedRemainSeconds%22%3A180%7D; is_dash_user=1; download_guide=%223%2F20241216%2F0%22; sdk_source_info=7e276470716a68645a606960273f276364697660272927676c715a6d6069756077273f276364697660272927666d776a68605a607d71606b766c6a6b5a7666776c7571273f275e58272927666a6b766a69605a696c6061273f27636469766027292762696a6764695a7364776c6467696076273f275e5827292771273f2730323d353430373336313632342778; bit_env=dVEnjgYiHnjRcSaHQt77E3Gi73m6t_cr2dXBkCgzp7guLYwwskTiT-1NfWYmF8QAQq3NZPHzcLlMXL40wKkpKqZvE7dkiCsyB8yRNOysITpY_A92X6aHGH1B0AcTsQcNFzjesZ3DvAFdGPtgSL2ZeBbAo2nKVs7APROctwxB-CD6AGd1XtncW59qG4y6uKhvg21mW3t8sTqwUHSvGJOZDJLoDTJ81hWeBqvW9ODcJ9jwbbQxZtbMDeVhYoTUc1VrWAiwDndhJuf9Vj37OMBQ9mYKYgVw7oy-2Z2EEfjE_Yl6qCQeNfnqNsELTdfWrahpPMuEFj8KWi7_82N-4Dwa2DUrG4XTPR6n-ojBNkZ1iUVdXYha6A5GD6KU4-feUtkSnysfH9umwFKXSVHrFhvaof2jxynXqzaJfzaq2xjqIRyq_YuKeJXJzAO_DJQQTk8oY6MBNSCIHXIF4Tf_Ws2-pJwlaueNjLULldQami4OccBMrGn66c6e9ig6QyehGKG4-wrK6Xp9IngvVRKukBiMNTP19TJdF7GkbRDTvUo6j_M%3D; gulu_source_res=eyJwX2luIjoiMDhjOGQ3ZTJiODQyNjZkZWI5Y2VkMGJiODNlNmY1ZWY0ZjMyNTE2ZmYyZjAzNDMzZjI0OWU1Y2Q1NTczNTk5NyJ9; passport_auth_mix_state=loaefj8z3n6mcyg4yqnccouvwiuwams5; vdg_s=1; stream_player_status_params=%22%7B%5C%22is_auto_play%5C%22%3A0%2C%5C%22is_full_screen%5C%22%3A0%2C%5C%22is_full_webscreen%5C%22%3A0%2C%5C%22is_mute%5C%22%3A0%2C%5C%22is_speed%5C%22%3A1%2C%5C%22is_visible%5C%22%3A0%7D%22; bd_ticket_guard_client_data=eyJiZC10aWNrZXQtZ3VhcmQtdmVyc2lvbiI6MiwiYmQtdGlja2V0LWd1YXJkLWl0ZXJhdGlvbi12ZXJzaW9uIjoxLCJiZC10aWNrZXQtZ3VhcmQtcmVlLXB1YmxpYy1rZXkiOiJCTEo2R0lDalVoWW1XcHpGOFdrN0Vrc0dXcCtaUzNKY1g4NGNGY2k0TTl1TEowNjdUb21mbFU5aDdvWVBGamhNRWNRQWtKdnN1MnM3RmpTWnlJQXpHMjA9IiwiYmQtdGlja2V0LWd1YXJkLXdlYi12ZXJzaW9uIjoyfQ%3D%3D; biz_trace_id=7c90c95a; IsDouyinActive=false',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    }

    try:
        # 发起 GET 请求，设置超时时间防止卡住
        response = requests.get(url, headers=headers,allow_redirects=True)

        # 如果响应 URL 存在
        if response.url:
            print(f"Final Redirect URL: {response.url}")

            # 使用正则表达式查找视频 ID
            pattern = r'https://www\.douyin\.com/video/(\d+)'
            match = re.search(pattern, response.url)

            if match:
                # 提取视频 ID
                modal_id = match.group(1)
                print(f"提取的 modal_id: {modal_id}")
                return modal_id
            else:
                print("没有找到 modal_id")
                return None
        else:
            print("未找到有效的响应 URL")
            return None

    except requests.exceptions.Timeout:
        print("请求超时")
        return None
    except requests.exceptions.RequestException as e:
        print(f"请求发生错误: {e}")
        return None


if __name__ == '__main__':
    title = ''

    while True:
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'cookie': 'douyin.com; device_web_cpu_core=10; device_web_memory_size=8; __ac_nonce=06760391f00b9b51264ae; __ac_signature=_02B4Z6wo00f019a5ceAAAIDAhEZR-X3jjWfWmXVAAJLXd4; ttwid=1%7C7MTKBSMsP4eOv9h5NAh8p0E-NYIud09ftNmB0mjLpWc%7C1734359327%7C8794abeabbd47447e1f56e5abc726be089f2a0344d6343b5f75f23e7b0f0028f; UIFID_TEMP=0de8750d2b188f4235dbfd208e44abbb976428f0720eb983255afefa45d39c0c6532e1d4768dd8587bf919f866ff1396912bcb2af71efee56a14a2a9f37b74010d0a0413795262f6d4afe02a032ac7ab; s_v_web_id=verify_m4r4ribr_c7krmY1z_WoeI_43po_ATpO_I4o8U1bex2D7; hevc_supported=true; home_can_add_dy_2_desktop=%220%22; dy_swidth=2560; dy_sheight=1440; stream_recommend_feed_params=%22%7B%5C%22cookie_enabled%5C%22%3Atrue%2C%5C%22screen_width%5C%22%3A2560%2C%5C%22screen_height%5C%22%3A1440%2C%5C%22browser_online%5C%22%3Atrue%2C%5C%22cpu_core_num%5C%22%3A10%2C%5C%22device_memory%5C%22%3A8%2C%5C%22downlink%5C%22%3A10%2C%5C%22effective_type%5C%22%3A%5C%224g%5C%22%2C%5C%22round_trip_time%5C%22%3A50%7D%22; strategyABtestKey=%221734359328.577%22; csrf_session_id=2f53aed9aa6974e83aa9a1014180c3a4; fpk1=U2FsdGVkX1/IpBh0qdmlKAVhGyYHgur4/VtL9AReZoeSxadXn4juKvsakahRGqjxOPytHWspYoBogyhS/V6QSw==; fpk2=0845b309c7b9b957afd9ecf775a4c21f; passport_csrf_token=d80e0c5b2fa2328219856be5ba7e671e; passport_csrf_token_default=d80e0c5b2fa2328219856be5ba7e671e; odin_tt=3c891091d2eb0f4718c1d5645bc4a0017032d4d5aa989decb729e9da2ad570918cbe5e9133dc6b145fa8c758de98efe32ff1f81aa0d611e838cc73ab08ef7d3f6adf66ab4d10e8372ddd628f94f16b8e; volume_info=%7B%22isUserMute%22%3Afalse%2C%22isMute%22%3Afalse%2C%22volume%22%3A0.5%7D; bd_ticket_guard_client_web_domain=2; FORCE_LOGIN=%7B%22videoConsumedRemainSeconds%22%3A180%7D; UIFID=0de8750d2b188f4235dbfd208e44abbb976428f0720eb983255afefa45d39c0c6532e1d4768dd8587bf919f866ff139655a3c2b735923234f371c699560c657923fd3d6c5b63ab7bb9b83423b6cb4787e2ce66a7fbc4ecb24c8570f520fe6de068bbb95115023c0c6c1b6ee31b49fb7e3996fb8349f43a3fd8b7a61cd9e18e8fe65eb6a7c13de4c0960d84e344b644725db3eb2fa6b7caf821de1b50527979f2; is_dash_user=1; biz_trace_id=b57a241f; bd_ticket_guard_client_data=eyJiZC10aWNrZXQtZ3VhcmQtdmVyc2lvbiI6MiwiYmQtdGlja2V0LWd1YXJkLWl0ZXJhdGlvbi12ZXJzaW9uIjoxLCJiZC10aWNrZXQtZ3VhcmQtcmVlLXB1YmxpYy1rZXkiOiJCTEo2R0lDalVoWW1XcHpGOFdrN0Vrc0dXcCtaUzNKY1g4NGNGY2k0TTl1TEowNjdUb21mbFU5aDdvWVBGamhNRWNRQWtKdnN1MnM3RmpTWnlJQXpHMjA9IiwiYmQtdGlja2V0LWd1YXJkLXdlYi12ZXJzaW9uIjoyfQ%3D%3D; download_guide=%221%2F20241216%2F0%22; sdk_source_info=7e276470716a68645a606960273f276364697660272927676c715a6d6069756077273f276364697660272927666d776a68605a607d71606b766c6a6b5a7666776c7571273f275e58272927666a6b766a69605a696c6061273f27636469766027292762696a6764695a7364776c6467696076273f275e5827292771273f273d33323131333c3036313632342778; bit_env=RiOY4jzzpxZoVCl6zdVSVhVRjdwHRTxqcqWdqMBZLPGjMdB4Tax1kAELHNTVAAh72KuhumewE4Lq6f0-VJ2UpJrkrhSxoPw9LUb3zQrq1OSwbeSPHkRlRgRQvO89sItdGUyq1oFr0XyRCnMYG87KSeWyc4x0czGR0o50hTDoDLG5rJVoRcdQOLvjiAegsqyytKF59sPX_QM9qffK2SqYsg0hCggURc_AI6kguDDE5DvG0bnyz1utw4z1eEnIoLrkGDqzqBZj4dOAr0BVU6ofbsS-pOQ2u2PM1dLP9FlBVBlVaqYVgHJeSLsR5k76BRTddUjTb4zEilVIEwAMJWGN4I1BxVt6fC9B5tBQpuT0lj3n3eKXCKXZsd8FrEs5_pbfDsxV-e_WMiXI2ff4qxiTC0U73sfo9OpicKICtZjdq8qsHxJuu6wVR36zvXeL2Wch5C6MzprNvkivv0l8nbh2mSgy1nabZr3dmU6NcR-Bg3Q3xTWUlR9aAUmpopC-cNuXjgLpT-Lw1AYGilSUnCvosth1Gfypq-b0MpgmdSDgTrQ%3D; gulu_source_res=eyJwX2luIjoiMDhjOGQ3ZTJiODQyNjZkZWI5Y2VkMGJiODNlNmY1ZWY0ZjMyNTE2ZmYyZjAzNDMzZjI0OWU1Y2Q1NTczNTk5NyJ9; passport_auth_mix_state=hp9bc3dgb1tm5wd8p82zawus27g0e3ue; IsDouyinActive=false',
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


