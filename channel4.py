from streamlink import streams
import subprocess
import datetime
import yt_dlp

CHANNELS = [
    {"name": "CCTV", "channel_url": "https://www.youtube.com/@CCTVDrama"},
    {"name": "乐视", "channel_url": "https://www.youtube.com/@letvdramas"},
    {"name": "百纳", "channel_url": "https://www.youtube.com/@BainationTVSeriesOfficial"},
    {"name": "后宫甄嬛传", "channel_url": "https://www.youtube.com/@LegendofConcubineZhenHuan"},
    {"name": "三立化剧", "channel_url": "https://www.youtube.com/@SETdrama"},
    {"name": "China Zone", "channel_url": "https://www.youtube.com/@ChinaZoneDrama"},
    {"name": "台视时光机", "channel_url": "https://www.youtube.com/@TTVClassic"},
    {"name": "华视戏剧频道", "channel_url": "https://www.youtube.com/@cts_drama"},
    {"name": "酷看独播剧场", "channel_url": "https://www.youtube.com/@KukanDrama"},
    {"name": "影视剧汇踪", "channel_url": "https://www.youtube.com/@影视剧汇踪"}
]


def is_currently_live(video_url):
    """
    用 yt-dlp 检查该视频是否【正在直播】。
    防止频道 /live 页面把"直播回放"或"预告"也列出来。
    """
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            # is_live=True 或 live_status=='is_live' 都表示正在直播
            return info.get('is_live') or info.get('live_status') == 'is_live'
    except Exception:
        return False


def get_channel_live_streams(channel_url):
    """
    访问频道的 /live 页面，提取当前所有候选直播，
    并过滤掉未在直播的视频。
    """
    live_url = channel_url.rstrip('/') + '/live'
    ydl_opts = {
        'extract_flat': True,      # 只提取列表，不深入每个视频，速度快
        'quiet': True,
        'no_warnings': True,
        'playlistend': 5,          # 每个频道最多检查前 5 个，防止意外爆炸
    }

    candidates = []
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(live_url, download=False)

            if not result:
                return []

            # 情况 A：/live 直接重定向到单个直播视频
            if result.get('_type') != 'playlist' and 'id' in result:
                candidates.append({
                    'title': result.get('title', 'Unknown'),
                    'url': result.get('webpage_url') or result.get('url') or f"https://www.youtube.com/watch?v={result['id']}"
                })
            # 情况 B：/live 是一个播放列表页面
            elif 'entries' in result:
                for entry in result['entries']:
                    if not entry or not entry.get('id'):
                        continue
                    candidates.append({
                        'title': entry.get('title', 'Unknown'),
                        'url': entry.get('url') or f"https://www.youtube.com/watch?v={entry['id']}"
                    })
    except Exception as e:
        print(f"  解析频道页面失败: {e}")
        return []

    # 二次校验：确保视频真的在直播
    live_streams = []
    for cand in candidates:
        short_title = cand['title'][:50]
        print(f"  检查直播状态: {short_title}...")
        if is_currently_live(cand['url']):
            live_streams.append(cand)
        else:
            print(f"    -> 未在直播，跳过")

    return live_streams


def get_best_stream(url):
    try:
        s = streams(url)
        if "best" not in s:
            return None
        return s["best"].url
    except Exception as e:
        print(f"  获取直播源失败: {e}")
        return None


def sanitize_title(title):
    """清理 M3U 标题里的换行符等危险字符"""
    return title.replace('\n', ' ').replace('\r', '').strip()


def git_push():
    try:
        subprocess.run(["git", "add", "."], check=True)
        msg = f"update {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        subprocess.run(["git", "commit", "-m", msg], check=True)
        subprocess.run(["git", "push"], check=True)
        print("已推送到 Git 仓库")
    except subprocess.CalledProcessError as e:
        print("Git 操作失败:", e)


def generate_playlist():
    playlist = "#EXTM3U\n\n"
    total = 0

    for channel in CHANNELS:
        name = channel["name"]
        url = channel["channel_url"]

        print(f"\n[{name}] 正在解析频道...")

        live_streams = get_channel_live_streams(url)

        if not live_streams:
            print(f"[{name}] 未找到正在直播的内容")
            continue

        for live in live_streams:
            live_title = sanitize_title(live['title'])
            display_name = f"{name}-{live_title}"

            print(f"[{name}] 获取直播源: {live_title[:40]}")
            stream_url = get_best_stream(live['url'])

            if stream_url:
                print(f"[{name}] 成功")
                playlist += f"#EXTINF:-1,{display_name}\n{stream_url}\n\n"
                total += 1
            else:
                print(f"[{name}] 失败: 无法提取直播源")

    with open("playlist.m3u", "w", encoding="utf-8") as f:
        f.write(playlist)

    print(f"\n已生成 playlist.m3u，共 {total} 个直播源")
    git_push()


if __name__ == "__main__":
    generate_playlist()
