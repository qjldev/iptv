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


def get_live_videos(channel_url):
    try:
        output = run_cmd([
            "yt-dlp",
            "--dump-single-json",
            "--flat-playlist",
            "--no-warnings",
            channel_url
        ])

    except Exception as e:
        print(f"获取频道失败: {channel_url}")
        print(e)
        return []

    if not output:
        return []

    try:
        data = json.loads(output)
    except Exception:
        return []

    entries = data.get("entries", [])

    live_videos = []

    for entry in entries:
        video_id = entry.get("id")
        title = entry.get("title", "")

        if not video_id:
            continue

        video_url = f"https://www.youtube.com/watch?v={video_id}"

        try:
            info_output = run_cmd([
                "yt-dlp",
                "--dump-single-json",
                "--no-warnings",
                video_url
            ])

            info = json.loads(info_output)

            # 一旦遇到非直播，后面通常也不是直播
            if not info.get("is_live"):
                print("检测到非直播，停止扫描")
                break

            live_videos.append({
                "url": video_url,
                "title": title
            })

        except Exception:
            print("解析视频失败，停止扫描")
            break

    return live_videos


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

        print(f"\n正在扫描频道: {base_name}")

        live_videos = get_live_videos(channel_url)

        if not live_videos:
            print("当前没有直播")
            continue

        print(f"发现 {len(live_videos)} 个直播")

        for video in live_videos:
            live_title = video["title"]
            live_video_url = video["url"]

            print(f"正在解析: {live_title}")

            stream_url = get_best_stream(live_video_url)

            if not stream_url:
                print("流解析失败")
                continue

            full_name = f"{base_name}-{sanitize_title(live_title)}"

            print(f"成功: {full_name}")

            playlist += (
                f'#EXTINF:-1 group-title="电视剧",{full_name}\n'
                f"{stream_url}\n\n"
            )

    with open("playlist.m3u", "w", encoding="utf-8") as f:
        f.write(playlist)

    print("\n已生成 playlist.m3u")

    git_push()


if __name__ == "__main__":
    generate_playlist()
