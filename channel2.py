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

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def get_live_url_and_title(channel_url):
    try:
        url = channel_url.rstrip("/") + "/streams"

        r = requests.get(url, headers=HEADERS, timeout=15)

        html = r.text

        # 找直播链接
        live_match = re.search(r'"/watch\?v=([^"]+)"', html)

        # 找标题
        title_match = re.search(r'"title":{"runs":\[\{"text":"([^"]+)"', html)

        if not live_match:
            return None, None

        video_id = live_match.group(1)
        title = title_match.group(1) if title_match else "直播"

        live_url = f"https://www.youtube.com/watch?v={video_id}"

        return live_url, title

    except Exception as e:
        print("获取直播失败:", channel_url)
        print(e)
        return None, None


def get_best_stream(url):
    try:
        s = streams(url)

        if "best" not in s:
            return None

        return s["best"].url

    except Exception as e:
        print(f"解析失败: {url}")
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
        print("Git 操作失败:", e)


def generate_playlist():
    playlist = "#EXTM3U\n\n"

    for channel in CHANNELS:

        custom_name = channel["name"]
        channel_url = channel["channel"]

        print(f"检查频道: {custom_name}")

        live_url, live_title = get_live_url_and_title(channel_url)

        if not live_url:
            print("当前没有直播")
            continue

        print("直播间:", live_title)

        stream_url = get_best_stream(live_url)

        if not stream_url:
            print("解析直播流失败")
            continue

        final_name = f"{custom_name}-{live_title}"

        playlist += f"#EXTINF:-1,{final_name}\n{stream_url}\n\n"

        print("成功添加:", final_name)

    with open("playlist.m3u", "w", encoding="utf-8") as f:
        f.write(playlist)

    print("\n已生成 playlist.m3u")

    git_push()


if __name__ == "__main__":
    generate_playlist()
