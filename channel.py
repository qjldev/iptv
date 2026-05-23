import re
import time
import datetime
import subprocess

import yt_dlp
from streamlink import streams


# 这里只填写频道 ID
# 例如：
# @CCTVDrama
# @ChinaZoneDrama
# @XXX

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


def build_channel_url(channel_id):

    return f"https://www.youtube.com/@{channel_id}/streams"


def extract_drama_name(title):
    """
    提取电视剧名称
    优先：
    【xxx】
    《xxx》
    """

    patterns = [
        r'【(.*?)】',
        r'《(.*?)》'
    ]

    for pattern in patterns:

        match = re.search(pattern, title)

        if match:
            return match.group(1)

    return title


def get_live_info(channel_url):

    ydl_opts = {
        "quiet": True,
        "extract_flat": True,
        "skip_download": True
    }

    try:

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:

            info = ydl.extract_info(
                channel_url,
                download=False
            )

            # 自动获取频道名
            channel_name = (
                info.get("channel")
                or info.get("uploader")
                or "Unknown"
            )

            entries = info.get("entries", [])

            for entry in entries:

                # 找正在直播的
                if entry.get("live_status") == "is_live":

                    live_title = entry.get("title", "")

                    video_url = (
                        f"https://www.youtube.com/watch?v={entry['id']}"
                    )

                    return {
                        "channel_name": channel_name,
                        "live_title": live_title,
                        "video_url": video_url
                    }

    except Exception as e:

        print("获取直播信息失败:")
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

        if not channel_id:
            continue

        channel_url = build_channel_url(channel_id)

        print(f"正在检查频道: {channel_id}")

        live_info = get_live_info(channel_url)

        if not live_info:

            print("当前没有直播")
            continue

        channel_name = live_info["channel_name"]

        live_title = live_info["live_title"]

        video_url = live_info["video_url"]

        drama_name = extract_drama_name(live_title)

        final_name = (
            f"{channel_name} - {drama_name}"
        )

        print(f"正在获取直播源: {final_name}")

        stream_url = get_best_stream(video_url)

        if not stream_url:

            print("直播源获取失败")
            continue

        playlist += (
            f"#EXTINF:-1,{final_name}\n"
        )

        playlist += (
            f"{stream_url}\n\n"
        )

        print(f"成功: {final_name}")

    with open(
        "playlist.m3u",
        "w",
        encoding="utf-8"
    ) as f:

        f.write(playlist)

    print("\n已生成 playlist.m3u")

    git_push()


if __name__ == "__main__":

    while True:

        print("\n========== 开始刷新 ==========\n")

        generate_playlist()

        print(
            "\n========== "
            "5分钟后再次刷新 "
            "==========\n"
        )

        # 5分钟刷新一次
        time.sleep(300)
