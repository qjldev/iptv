import subprocess
import datetime
import re
import json


CHANNELS = [
    {"name": "CCTV", "channel_url": "https://www.youtube.com/@CCTVDrama/streams"},
    {"name": "乐视", "channel_url": "https://www.youtube.com/@letvdramas/streams"},
    {"name": "百纳", "channel_url": "https://www.youtube.com/@BainationTVSeriesOfficial/streams"},
    {"name": "后宫甄嬛传", "channel_url": "https://www.youtube.com/@LegendofConcubineZhenHuan/streams"},
    {"name": "三立戏剧", "channel_url": "https://www.youtube.com/@SETdrama/streams"},
    {"name": "China Zone", "channel_url": "https://www.youtube.com/@ChinaZoneDrama/streams"},
    {"name": "台视时光机", "channel_url": "https://www.youtube.com/@TTVClassic/streams"},
    {"name": "华视戏剧频道", "channel_url": "https://www.youtube.com/@cts_drama/streams"},
    {"name": "酷看独播剧场", "channel_url": "https://www.youtube.com/@KukanDrama/streams"},
    {"name": "影视剧汇踪", "channel_url": "https://www.youtube.com/@影视剧汇踪/streams"}
]


def run_cmd(cmd):
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(
            result.stderr.strip() or result.stdout.strip()
        )

    return result.stdout.strip()


def get_live_video_info(channel_url):
    try:
        output = run_cmd([
            "yt-dlp",
            "--dump-single-json",
            "--playlist-items", "1",
            "--match-filter", "is_live",
            "--no-warnings",
            channel_url
        ])

    except Exception as e:
        print(f"获取直播信息失败: {channel_url}")
        print(e)
        return None, None

    if not output:
        return None, None

    try:
        data = json.loads(output)
    except Exception:
        return None, None

    entries = data.get("entries")

    if not entries:
        return None, None

    video = entries[0]

    webpage_url = video.get("webpage_url")
    title = video.get("title")

    if not webpage_url:
        return None, None

    return webpage_url, title


def get_best_stream(url):
    try:
        output = run_cmd([
            "yt-dlp",
            "-f", "best",
            "-g",
            "--user-agent",
            "Mozilla/5.0",
            "--no-warnings",
            url
        ])

        if not output:
            return None

        return output.splitlines()[0]

    except Exception as e:
        print(f"获取流失败: {url}")
        print(e)
        return None


def sanitize_title(title):
    if not title:
        return "未命名直播间"

    title = re.sub(r'[\\/:*?"<>|]', '_', title)
    title = re.sub(r"[\r\n]+", " ", title)

    return title.strip()


def git_push():
    try:
        subprocess.run(
            ["git", "add", "."],
            check=True
        )

        msg = f"update {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        commit = subprocess.run(
            ["git", "commit", "-m", msg],
            capture_output=True,
            text=True
        )

        if commit.returncode != 0:
            if (
                "nothing to commit" in commit.stdout
                or "nothing to commit" in commit.stderr
            ):
                print("没有变化，跳过 commit 和 push")
                return

            raise subprocess.CalledProcessError(
                commit.returncode,
                commit.args,
                commit.stdout,
                commit.stderr
            )

        subprocess.run(
            ["git", "push"],
            check=True
        )

        print("已推送到 Git 仓库")

    except subprocess.CalledProcessError as e:
        print("Git 操作失败:")
        print(e)


def generate_playlist():
    playlist = "#EXTM3U\n\n"

    for channel in CHANNELS:
        base_name = channel["name"]
        channel_url = channel["channel_url"]

        print(f"\n正在查找直播: {base_name}")

        live_video_url, live_title = get_live_video_info(channel_url)

        if not live_video_url:
            print(f"未找到直播: {base_name}")
            continue

        print(f"找到直播: {live_title}")

        stream_url = get_best_stream(live_video_url)

        if not stream_url:
            print(f"流解析失败: {base_name}")
            continue

        full_name = f"{base_name}-{sanitize_title(live_title)}"

        print(f"成功: {full_name}")

        playlist += (
            f'#EXTINF:-1 group-title="电视剧",{full_name}\n'
            f"{stream_url}\n\n"
        )

    with open("playlist.m3u8", "w", encoding="utf-8") as f:
        f.write(playlist)

    print("\n已生成 playlist.m3u8")

    git_push()


if __name__ == "__main__":
    generate_playlist()

