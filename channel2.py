from streamlink import streams
import subprocess
import datetime
import requests
from bs4 import BeautifulSoup
import re

CHANNELS = [
    {"name": "CCTV", "channel": "https://www.youtube.com/@CCTVDrama"},
    {"name": "乐视", "channel": "https://www.youtube.com/@letvdramas"},
    {"name": "百纳", "channel": "https://www.youtube.com/@BainationTVSeriesOfficial"},
    {"name": "后宫甄嬛传", "channel": "https://www.youtube.com/@LegendofConcubineZhenHuan"},
    {"name": "三立化剧", "channel": "https://www.youtube.com/@SETdrama"},
    {"name": "China Zone", "channel": "https://www.youtube.com/@ChinaZoneDrama"},
    {"name": "台视时光机", "channel": "https://www.youtube.com/@TTVClassic"},
    {"name": "华视戏剧频道", "channel": "https://www.youtube.com/@cts_drama"},
    {"name": "酷看独播剧场", "channel": "https://www.youtube.com/@KukanDrama"}

]


def get_live_info(channel_url):
    """
    从频道 /streams 中找正在直播的视频
    """
    try:
        ydl_opts = {
            "quiet": True,
            "skip_download": True,
            "extract_flat": True
        }

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(channel_url + "/streams", download=False)

            entries = info.get("entries", [])

            for e in entries:
                if not e:
                    continue

                # 关键：只要正在直播
                if e.get("is_live"):
                    url = e.get("url") or e.get("webpage_url")
                    title = e.get("title")
                    
                    # 有些返回是 video id
                    if url and "youtube.com" not in url:
                        url = f"https://www.youtube.com/watch?v={url}"

                    return url, title

        return None, None

    except Exception as e:
        print("获取直播失败:", channel_url)
        print(e)
        return None, None


def get_best_stream(url):
    """
    用 streamlink 获取真实播放源
    """
    try:
        s = streams(url)
        if "best" not in s:
            return None
        return s["best"].url

    except Exception as e:
        print("解析流失败:", url)
        print(e)
        return None


def git_push():
    try:
        subprocess.run(["git", "add", "."], check=True)

        msg = f"update {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        subprocess.run(["git", "commit", "-m", msg], check=True)
        subprocess.run(["git", "push"], check=True)

        print("已推送 Git")

    except subprocess.CalledProcessError as e:
        print("Git 失败:", e)


def generate_playlist():
    playlist = "#EXTM3U\n\n"

    for c in CHANNELS:
        name = c["name"]
        channel_url = c["channel"]

        print(f"\n检查频道: {name}")

        live_url, live_title = get_live_info(channel_url)

        if not live_url:
            print("没有直播")
            continue

        print("直播标题:", live_title)

        stream_url = get_best_stream(live_url)

        if not stream_url:
            print("无法解析流")
            continue

        final_name = f"{name}-{live_title}"

        playlist += f"#EXTINF:-1,{final_name}\n{stream_url}\n\n"

        print("添加成功:", final_name)

    with open("playlist.m3u", "w", encoding="utf-8") as f:
        f.write(playlist)

    print("\n已生成 playlist.m3u")

    git_push()


if __name__ == "__main__":
    generate_playlist()
