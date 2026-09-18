# douyinDownloader

一个用于下载抖音视频的 Python 脚本。支持**普通视频**、**图文作品**、**实况图（Live Photo）**。

> **2026-09-18 更新**
> 1. 新增 **协议模式**：纯 HTTP 取数，**不需要浏览器**（默认走这条）。
> 2. 修复 `requirements.txt` 漏掉 `Pillow` 导致的「图文合并失败」误报。
> 3. 拆分依赖：浏览器相关依赖移到可选的 `requirements-browser.txt`。

## 两种取数模式

脚本内置两条取数路径，用环境变量 `DOUYIN_FETCH_MODE` 切换：

| 模式 | 做法 | 依赖 | 画质 | 速度 |
|---|---|---|---|---|
| `protocol` | 纯 HTTP 请求分享页，解析页面内嵌的 `_ROUTER_DATA` | 只要 requests | 无水印 **1080p** h264 | 约 1~2 秒/条 |
| `browser` | 用 Chromium 打开视频页，监听 `aweme/detail` 接口 | 需 playwright + Chrome | 无水印 **最高 4K**（HEVC） | 约 10~40 秒/条 |
| `auto`（默认） | 先协议；被风控自动回退浏览器 | 装了 playwright 才有回退能力 | 视情况 | 视情况 |

```bash
export DOUYIN_FETCH_MODE=protocol    # 只用协议（不装 playwright 也能跑）
export DOUYIN_FETCH_MODE=auto        # 默认，协议优先 + 浏览器兜底
export DOUYIN_FETCH_MODE=browser     # 只用浏览器（旧行为）
```

> **怎么选**：日常下载用默认的 `auto` 就够了。服务器 / 容器里没有图形界面、或者不想装 Chromium，用 `protocol`。对个别视频的画质有要求（4K），用 `browser`。

## 功能

- [x] 支持抖音**分享短链**（`v.douyin.com/...`）、视频页链接（`douyin.com/video/xxx`）、用户主页 `modal_id` 链接
- [x] 普通视频下载（协议模式拿到的是**无水印、已含音轨的单文件**，不需要额外合并）
- [x] 图文作品：下载全部图片（抖音给的是 webp，脚本自动转 JPEG），与背景音乐合成为视频
- [x] 实况图（Live Photo）：图片 + 自带短视频合并
- [x] 批量下载，任务间随机间隔 1.5~3.5 秒降低风控概率
- [x] 协议模式连续被风控时自动熔断并回退浏览器，不会一直空等

## 原理

### 协议模式（默认优先）

抖音在 **移动端** 渲染分享页 `https://www.douyin.com/share/video/<视频ID>/` 时，
会把作品数据以 JSON 形式内嵌在页面里：`window._ROUTER_DATA = {...}`，
其中 `loaderData."video_(id)/page".videoInfoRes.item_list[0]` 就是作品对象。
所以只要一次 `requests.get` + 一次 JSON 解析就能拿到全部数据。

几个关键处理：

1. **分享页给的是带水印的 720p `playwm` 地址**，把接口换成 `/aweme/v1/play/` 并显式指定
   `ratio=1080p`，即可拿到**无水印 1080p**（实测 `ratio=4k` / `origin` 都会回落到 1080p）。
2. **图文 / 实况图的背景音乐没有独立字段**，它被伪装成一个 video 挂在
   `video.play_addr.url_list` 里（`video_id=` 后面其实是个 `.mp3` 直链），脚本会把它挖出来直接用。
3. **图文作品的图片是 webp**，脚本用 Pillow 统一转成 JPEG 再交给 ffmpeg 合成。

### 浏览器模式（回退）

用真实浏览器内核打开视频页，在后台监听 XHR 响应里的 `aweme/detail` 接口，
直接取抖音前端自己请求的原始 JSON。这条路拿到的清晰度更高（可到 4K HEVC），
代价是要装 Chromium、要等页面加载与接口返回。

## 环境要求

- Python 3.9+
- **ffmpeg 与 ffprobe**（图文 / 实况图合成需要）
- Python 包依赖见 `requirements.txt`，其中 **Pillow** 用于图文作品的图片规格化，
  缺了会导致「图文作品」下载成功但合并失败

## 安装

```bash
git clone git@github.com:aiaoxd/douyinDownloader.git
cd douyinDownloader

python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# 核心依赖（协议模式只需这些）
pip install -r requirements.txt

# 可选：想要浏览器回退能力，再装这个
pip install -r requirements-browser.txt
playwright install chromium       # 本机已有 Google Chrome 的话可以跳过
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
**协议模式全程无窗口**；浏览器模式首次运行会启动一个 Chromium 窗口，请勿关闭。

### 可调环境变量

| 变量 | 默认 | 说明 |
|---|---|---|
| `DOUYIN_FETCH_MODE` | `auto` | 取数方式：`auto` / `protocol` / `browser` |
| `DOUYIN_PROTOCOL_RATIO` | `1080p` | 协议模式请求的清晰度（实测上限 1080p） |
| `DOUYIN_COOKIE` | 空 | Cookie 字符串，优先级高于 `cookies.json` |
| `DOUYIN_DOWNLOAD_DIR` | `./downloads` | 下载根目录 |

## 已知限制

- **协议模式的清晰度上限是 1080p**。要 4K 请用 `browser` 模式。
- **分享页有频率风控**。请求过密（实测连续几十次快速请求）会返回一个约 2.5KB 的
  argus 挑战页（页面里没有 `_ROUTER_DATA`）。脚本已内置失败识别与回退，
  日常批量下载建议保留任务间 1.5~3.5 秒的随机间隔。
- **`iesdouyin.com` 的分享页在带登录 Cookie 时会被挑战**，`www.douyin.com` 正常，
  所以脚本优先用后者（`SHARE_HOSTS` 里可调整顺序）。
- **网页端接口 `/aweme/v1/web/aweme/detail/` 已不可直接用**（返回
  `Blocked by ArgusSecurityPlugin Uifid Not Found`），故不采用该路线。

## 目录结构

```
douyinDownloader.py         # 主程序（协议 + 浏览器两种取数方式）
path_config.py              # 路径配置（全部基于脚本目录，无本机绝对路径）
util.py                     # 通用工具（视频时长解析等）
requirements.txt            # 核心依赖（协议模式只需这些）
requirements-browser.txt    # 可选依赖（浏览器回退模式）
cookies.example.json        # Cookie 配置模板
legacy/                     # 2024 年旧版实现（方案已失效，仅作留存）
```

## 常见问题

**Q：一直提示「未捕获到详情」/ 拿到 72914 字节的挑战页？**
抖音风控较强。先确认已配置有效 Cookie（Cookie 过期会导致命中率骤降），脚本内置了 UA 轮换和重试；仍然失败就等一段时间再试。

**Q：协议模式提示「命中风控挑战页」怎么办？**
说明这一波请求被限速了。等几分钟再跑，或者把 `DOUYIN_FETCH_MODE` 设为 `auto`/`browser` 让它走浏览器。默认的 `auto` 模式在连续失败 3 次后会把本批任务整体切到浏览器，不会逐条空等。

**Q：提示未安装 playwright？**
说明当前是 `auto` 或 `browser` 模式且需要走浏览器。执行 `pip install -r requirements-browser.txt && playwright install chromium`；
或者直接 `export DOUYIN_FETCH_MODE=protocol` 用纯协议模式。

**Q：下载图文作品时报「图文合并失败」？**
先看紧跟其后的原因。如果是 **缺少 Pillow 依赖**，执行 `pip install Pillow`（或 `pip install -r requirements.txt`）即可 ——
图片和音频已经下好了，报错信息里会给出保存目录，装完可直接重跑，不用重新下载。
老版本这条路径的报错是「图文合并失败（缺少图片或音频）」，原因是 `ImportError` 被内部的 `except Exception` 吞掉了，
容易误判成风控问题（已在 2026-09-18 修正为明确提示）。

**Q：报错 `No such filter: 'drawtext'`/ 音视频合并失败？**
检查 ffmpeg 是否完整安装，命令行直接跑 `ffmpeg -filters | grep drawtext` 确认。

## 视频教程

<https://www.bilibili.com/video/BV1X6kVY3EZj/>

## 免责声明

本项目仅供学习研究用途。下载的内容版权归原作者所有，请勿用于商业用途或二次分发，
因使用本项目产生的任何后果由使用者自行承担。
