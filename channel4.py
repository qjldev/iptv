import datetime
import subprocess
import re
import requests

from streamlink import streams
from googleapiclient.discovery import build

# ========= 配置区 =========
YOUTUBE_API_KEY = "你的API密钥"  # 换成你自己的

CHANNELS = [
    {
        "name": "CCTV",
        "channel_url": "https://www.youtube.com/@CCTVDrama",
        "channel_id": "UC_xxx",  # 先用脚本或手动查好
    },
    {
        "name": "乐视",
        "channel_url": "https://www.youtube.com/@letvdramas",
        "channel_id": "UC_yyy",
    },
    # ……其它频道同理
]

# ========= 工具函数 =========

def get_channel_id_from_url(channel_url: str) -> str:
    """从频道页 URL 解析 channelId"""
    resp = requests.get(channel_url, timeout=10)
    resp.raise_for_status()
    html = resp.text

    m = re.search(r'<meta\s+itemprop="channelId"\s+content="([^"]+)"', html)
    if not m:
        raise ValueError(f"无法从 {channel_url} 解析 channelId")
    return m.group(1)


def get_live_streams_for_channel(channel_id: str):
    """返回该频道当前正在直播的列表：[{video_id, title, url}, ...]"""
    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

    request = youtube.liveBroadcasts().list(
        part="snippet,status",
        broadcastStatus="active",
        channelId=channel_id,
        maxResults=10,
    )
    response = request.execute()

    lives = []
    for item in response.get("items", []):
        vid = item["id"]
        title = item["snippet"]["title"]
        lives.append({
            "video_id": vid,
            "title": title,
            "url": f"https://www.youtube.com/watch?v={vid}",
        })
    return lives


def get_best_stream(url):
    """用 Streamlink 获取 best 流地址"""
    try:
        s = streams(url)
        if "best" not in s:
            return None
        return s["best"].url
    except Exception as e:
        print(f"获取失败: {url}")
        print(e)
        return None


def git_push():
    """git add/commit/push"""
    try:
        subprocess.run(["git", "add", "."], check=True)

        msg = f"update {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        subprocess.run(["git", "commit", "-m", msg], check=True)

        subprocess.run(["git", "push"], check=True)
        print("已推送到 Git 仓库")
    except subprocess.CalledProcessError as e:
        print("Git 操作失败:", e)


# ========= 主流程 =========

def generate_playlist():
    playlist = "#EXTM3U\n\n"

    for channel in CHANNELS:
        name = channel["name"]
        channel_id = channel.get("channel_id")

        # 如果没有 channel_id，先尝试从 channel_url 解析一次（建议提前跑好，不要每次都解析）
        if not channel_id:
            print(f"[{name}] 没有 channel_id，尝试从 {channel['channel_url']} 解析...")
            try:
                channel_id = get_channel_id_from_url(channel["channel_url"])
                channel["channel_id"] = channel_id  # 缓存到字典里，后续可用
                print(f"[{name}] 解析到 channelId: {channel_id}")
            except Exception as e:
                print(f"[{name}] 解析 channelId 失败，跳过该频道：{e}")
                continue

        print(f"[{name}] 查询当前直播...")

        try:
            live_streams = get_live_streams_for_channel(channel_id)
        except Exception as e:
            print(f"[{name}] 调用 YouTube API 失败，跳过：{e}")
            continue

        if not live_streams:
            print(f"[{name}] 当前没有直播")
            continue

        for stream in live_streams:
            video_url = stream["url"]
            stream_title = stream["title"]

            print(f"  正在解析: {name}-{stream_title}")

            stream_url = get_best_stream(video_url)

            if stream_url:
                display_name = f"{name}-{stream_title}"
                playlist += f"#EXTINF:-1,{display_name}\n{stream_url}\n\n"
                print(f"  成功: {display_name}")
            else:
                print(f"  失败: {name}-{stream_title}")

    with open("playlist.m3u", "w", encoding="utf-8") as f:
        f.write(playlist)

    print("\n已生成 playlist.m3u")

    # 自动推送到 Git
    git_push()


if __name__ == "__main__":
    generate_playlist()
