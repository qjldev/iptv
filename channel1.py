from streamlink import streams
import subprocess
import time
import datetime
import yt_dlp

# 这里改成【频道主页链接】，不是单个视频链接
CHANNELS = [
    {"name": "CCTV", "url": "https://www.youtube.com/@CCTVDrama"},
    {"name": "乐视", "url": "https://www.youtube.com/@letvdramas"},
    {"name": "百纳", "url": "https://www.youtube.com/@BainationTVSeriesOfficial"},
    {"name": "后宫甄嬛传", "url": "https://www.youtube.com/@LegendofConcubineZhenHuan"},
    {"name": "三立化剧", "url": "https://www.youtube.com/@SETdrama"},
    {"name": "China Zone", "url": "https://www.youtube.com/@ChinaZoneDrama"},
    {"name": "台视时光机", "url": "https://www.youtube.com/@TTVClassic"},
    {"name": "华视戏剧频道", "url": "https://www.youtube.com/@cts_drama"},
    {"name": "酷看独播剧场", "url": "https://www.youtube.com/@KukanDrama"},

]

def get_channel_lives(channel_url):
    """
    输入频道主页URL，返回该频道当前所有正在直播的 (title, video_url) 列表
    """
    live_list = []
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'force_generic_extractor': False
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # 先拿频道所有视频
            info = ydl.extract_info(channel_url, download=False)
            if 'entries' not in info:
                return live_list
            for entry in info['entries']:
                if not entry:
                    continue
                # 判断是否正在直播
                if entry.get('live_status') == 'is_live' or entry.get('is_live'):
                    title = entry.get('title', '未知直播')
                    video_url = f"https://www.youtube.com/watch?v={entry['id']}"
                    live_list.append((title, video_url))
    except Exception as e:
        print(f"获取频道直播失败: {channel_url}")
        print(e)
    return live_list

def get_best_stream(url):
    try:
        s = streams(url)
        if "best" not in s:
            return None
        return s["best"].url
    except Exception as e:
        print(f"获取流失败: {url}")
        print(e)
        return None

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

    for ch in CHANNELS:
        ch_name = ch["name"]
        ch_url = ch["url"]
        print(f"\n===== 正在处理频道: {ch_name} =====")

        # 1. 拿到该频道所有正在直播
        lives = get_channel_lives(ch_url)
        if not lives:
            print(f"[-] {ch_name} 当前无直播")
            continue

        # 2. 逐个解析直播流
        for live_title, live_url in lives:
            print(f"解析直播: {live_title}")
            stream_url = get_best_stream(live_url)
            if stream_url:
                # 命名：频道名-直播间名
                full_name = f"{ch_name}-{live_title}"
                playlist += f"#EXTINF:-1,{full_name}\n{stream_url}\n\n"
                print(f"[+] 成功: {full_name}")
            else:
                print(f"[-] 失败: {live_title}")

    with open("playlist.m3u", "w", encoding="utf-8") as f:
        f.write(playlist)
    print("\n✅ 已生成 playlist.m3u")

    # 自动推送到 Git
    git_push()

if __name__ == "__main__":
    generate_playlist()
