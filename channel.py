import re
import time
import datetime
import subprocess

import yt_dlp
from streamlink import streams


# 这里只需要填写 @ 后面的部分
# 例如：
# CCTVDrama
# ChinaZoneDrama
# @ 不需要写
# /streams 不需要写

CHANNELS = [
    "CCTVDrama",                    #CCTV
    "letvdramas",                   #乐视
    "BainationTVSeriesOfficial",    #百纳
    "LegendofConcubineZhenHuan",    #后宫甄嬛传
    "SETdrama",                     #三立化剧
    "ChinaZoneDrama",               #China Zone
    "TTVClassic",                   #台视时光机
    "cts_drama",                    #华视戏剧频道
    "KukanDrama",                   #酷看独播剧场
    "影视剧汇踪",                    #影视剧汇踪


    
]






def build_live_url(channel_id):

    return f"https://www.youtube.com/@{channel_id}/live"


def extract_drama_name(title):

    patterns = [
        r'【(.*?)】',
        r'《(.*?)》',
        r'（(.*?)）',
        r'\((.*?)\)'
    ]

    for pattern in patterns:

        match = re.search(pattern, title)

        if match:
            return match.group(1).strip()

    return title.strip()


def get_live_info(channel_id):

    live_url = build_live_url(channel_id)

    ydl_opts = {
        "quiet": True,
        "skip_download": True
    }

    try:

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:

            info = ydl.extract_info(
                live_url,
                download=False
            )

            # 没开播
            if not info:
                return None

            channel_name = (
                info.get("channel")
                or info.get("uploader")
                or channel_id
            )

            live_title = info.get("title", "")

            video_url = info.get("webpage_url")

            return {
                "channel_name": channel_name,
                "live_title": live_title,
                "video_url": video_url
            }

    except Exception as e:

        print(f"{channel_id} 当前未开播")
        print(e)

    return None


def get_best_stream(video_url):

    try:

        s = streams(video_url)

        if not s:
            return None

        if "best" not in s:
            return None

        return s["best"].url

    except Exception as e:

        print("获取直播源失败:")
        print(e)

    return None


def git_push():

    try:

        subprocess.run(
            ["git", "add", "."],
            check=True
        )

        msg = (
            f"update "
            f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        subprocess.run(
            ["git", "commit", "-m", msg],
            check=True
        )

        subprocess.run(
            ["git", "push"],
            check=True
        )

        print("已推送 Git")

    except subprocess.CalledProcessError as e:

        print("Git 推送失败:")
        print(e)


def generate_playlist():

    playlist = "#EXTM3U\n\n"

    for channel_id in CHANNELS:

        print(f"正在检查频道: {channel_id}")

        live_info = get_live_info(channel_id)

        if not live_info:

            print("当前没有直播")
            continue

        channel_name = live_info["channel_name"]
        live_title = live_info["live_title"]
        video_url = live_info["video_url"]

        drama_name = extract_drama_name(live_title)

        final_name = f"{channel_name} - {drama_name}"

        print(f"正在获取直播源: {final_name}")

        stream_url = get_best_stream(video_url)

        if not stream_url:

            print("直播源获取失败")
            continue

        playlist += f"#EXTINF:-1,{final_name}\n"
        playlist += f"{stream_url}\n\n"

        print(f"成功: {final_name}")

    with open("playlist.m3u", "w", encoding="utf-8") as f:

        f.write(playlist)

    print("\n已生成 playlist.m3u")

    git_push()


if __name__ == "__main__":

    while True:

        print("\n========== 开始刷新 ==========\n")

        generate_playlist()

        print("\n========== 5分钟后再次刷新 ==========\n")

        time.sleep(300)
