# douyinDownloader

一个用于下载抖音视频的 Python 脚本。

> **2026-09-18 重大更新**：旧版依赖解析页面里的 `RENDER_DATA`，抖音改版后已彻底失效。
> 新版改用 **DrissionPage / Playwright 浏览器监听 `aweme/detail` 接口** 的方案，直接拿到接口返回的真实数据，
> 同时支持**普通视频**、**图文作品**、**实况图（Live Photo）**。旧版已归档到 `legacy/`。

## 功能

- [x] 支持抖音**分享短链**（`v.douyin.com/...`）、视频页链接（`douyin.com/video/xxx`）、用户主页 `modal_id` 链接
- [x] 普通视频下载（自动合并音频轨，无水印优先）
- [x] 图文作品：下载全部图片，调用 ffmpeg 合成为视频；有背景音乐时一并合成
- [x] 实况图（Live Photo）：图片 + 自带短视频合并
- [x] 批量下载，任务间随机间隔 1.5~3.5 秒降低风控概率
- [x] UA 轮换 + 失败重试，应对抖音 acrawler 风控挑战页

## 原理

抖音网页端把视频数据藏在 JS 撑起来的页面里，静态 HTML 里经常什么都拿不到（或者直接返回风控挑战页）。
所以新版做法是：**用真实浏览器打开视频页，在后台监听 XHR 响应里的 `aweme/detail`**，
拿到接口原始 JSON 后从中提取无水印播放地址、图片列表、音乐地址，再走 requests 下载。

## 环境要求

- Python 3.9+
- **ffmpeg 与 ffprobe**（合并音视频、图文转视频需要，且 ffmpeg 需带 drawtext 等常规能力）

## 安装

```bash
git clone git@github.com:aiaoxd/douyinDownloader.git
cd douyinDownloader

python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -r requirements.txt
playwright install chromium       # 浏览器监听方案必需
```

macOS 下若 `ffmpeg` 是精简版（缺 freetype/fontconfig），可用 Homebrew 安装完整版：

```bash
brew install ffmpeg
```

## 配置 Cookie（推荐，但非必需）

不配 Cookie 也能下载部分公开视频，但很容易撞上风控。配置方式二选一：

**方式一：环境变量**

```bash
export DOUYIN_COOKIE='ttwid=xxx; passport_csrf_token=xxx; ...'
```

**方式二：`cookies.json` 文件**

```bash
cp cookies.example.json cookies.json
# 然后编辑 cookies.json，把真实值填进 cookies 字段
```

获取 Cookie：Chrome 登录后打开 douyin.com → F12 → Network → 任选一条 `www.douyin.com` 请求 →
Request Headers → 复制 `cookie` 整行。

> ⚠️ **安全提醒**：本仓库源码不包含任何 Cookie，`cookies.json` 已被 `.gitignore` 排除。
> 请勿把 Cookie 写进代码或提交到 Git，也不要分享给他人 —— Cookie 相当于你的登录凭据。

## 运行

```bash
# 交互式：粘贴分享链接，一行一个，空行结束
python douyinDownloader.py

# 直接传链接
python douyinDownloader.py 'https://v.douyin.com/xxxxx/' 'https://www.douyin.com/video/7374xxxxx'

# 从文件读取（每行一个链接）
python douyinDownloader.py -f links.txt
```

下载的文件保存在 `downloads/<日期>/` 目录下（可用环境变量 `DOUYIN_DOWNLOAD_DIR` 自定义根目录）。
首次运行会自动启动一个 Chromium 窗口，这是浏览器监听方案需要的，请勿关闭。

## 目录结构

```
douyinDownloader.py     # 主程序
path_config.py          # 路径配置（全部基于脚本目录，无本机绝对路径）
util.py                 # 通用工具（视频时长解析等）
requirements.txt        # 依赖
cookies.example.json    # Cookie 配置模板
legacy/                 # 2024 年旧版实现（方案已失效，仅作留存）
```

## 常见问题

**Q：一直提示「未捕获到详情」/ 拿到 72914 字节的挑战页？**
抖音风控较强。先确认已配置有效 Cookie（Cookie 过期会导致命中率骤降），脚本内置了 UA 轮换和重试；仍然失败就等一段时间再试。

**Q：提示未安装 playwright？**
执行 `pip install playwright && playwright install chromium`。

**Q：报错 `No such filter: 'drawtext'`/ 音视频合并失败？**
检查 ffmpeg 是否完整安装，命令行直接跑 `ffmpeg -filters | grep drawtext` 确认。

## 视频教程

<https://www.bilibili.com/video/BV1X6kVY3EZj/>

## 免责声明

本项目仅供学习研究用途。下载的内容版权归原作者所有，请勿用于商业用途或二次分发，
因使用本项目产生的任何后果由使用者自行承担。
