from streamlink.session import Streamlink
import subprocess
import datetime
import re
import json

# 清理了不合法/无法访问的频道
CHANNELS = [
    {"name": "CCTV", "channel_url": "https://www.youtube.com/@CCTVDrama"},
    {"name": "乐视", "channel_url": "https://www.youtube.com/@letvdramas"},
    {"name": "百纳", "channel_url": "https://www.youtube.com/@BainationTVSeriesOfficial"},
    {"name": "后宫甄嬛传", "channel_url": "https://www.youtube.com/@LegendofConcubineZhenHuan"},
    {"name": "三立化剧", "channel_url": "https://www.youtube.com/@SETdrama"},
    {"name": "ChinaZone", "channel_url": "https://www.youtube.com/@ChinaZoneDrama"},
    {"name": "台视时光机", "channel_url": "https://www.youtube.com/@TTVClassic"},
    {"name": "华视戏剧", "channel_url": "https://www.youtube.com/@cts_drama"},
    {"name": "酷看独播", "channel_url": "https://www.youtube.com/@KukanDrama"},
]

def run_cmd(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return result.stdout.strip()

def get_live_video_info(channel_url):
    live_url = channel_url.rstrip("/") + "/live"
    try:
        output = run_cmd([
            "yt-dlp",
            "--dump-single-json",
            "--no-warnings",
            "--cookies-from-browser=edge",  # 自动读取浏览器 Cookie，解决 403
            live_url
        ])
    except Exception as e:
        print(f"获取直播信息失败: {channel_url}")
        return None, None

    if not output:
        return None, None

    data = json.loads(output)
    webpage_url = data.get("webpage_url") or data.get("original_url")
    title = data.get("title")

    if not webpage_url or "watch?v=" not in webpage_url:
        return None, None

    return webpage_url, title

def get_best_stream(url):
    try:
        session = Streamlink()
        streams = session.streams(url)
        if "best" not in streams:
            return None
        return streams["best"].url
    except Exception as e:
        print(f"获取流失败: {url}")
        return None

def git_push():
    try:
        subprocess.run(["git", "add", "."], check=True)
        msg = f"update {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        commit = subprocess.run(
            ["git", "commit", "-m", msg],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )

        if commit.returncode != 0:
            if "nothing to commit" in commit.stdout or "nothing to commit" in commit.stderr:
                print("没有变化，跳过 commit 和 push")
                return
            raise subprocess.CalledProcessError(commit.returncode, commit.args)

        subprocess.run(["git", "push"], check=True)
        print("已推送到 Git 仓库")
    except subprocess.CalledProcessError:
        print("Git 操作失败（无变化或网络问题）")

def sanitize_title(title):
    if not title:
        return "未命名直播间"
    return re.sub(r'[\\/*?:"<>|\r\n]', " ", title).strip()

def generate_playlist():
    playlist = "#EXTM3U\n\n"
    for channel in CHANNELS:
        name = channel["name"]
        url = channel["channel_url"]
        print(f"正在检测: {name}")

        live_url, title = get_live_video_info(url)
        if not live_url:
            print(f"未开播: {name}")
            continue

        stream = get_best_stream(live_url)
        if stream:
            clean_title = sanitize_title(title)
            full_name = f"{name} - {clean_title}"
            print(f"成功获取: {full_name}")
            playlist += f"#EXTINF:-1,{full_name}\n{stream}\n\n"
        else:
            print(f"流获取失败: {name}")

    with open("playlist.m3u", "w", encoding="utf-8") as f:
        f.write(playlist)
    print("\n✅ 已生成 playlist.m3u")
    git_push()

if __name__ == "__main__":
    generate_playlist()
