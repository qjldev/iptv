#!/usr/bin/env python3
"""
YouTube Playlist to M3U Generator
将YouTube播放列表转换成支持分组（电视剧）和剧集（第N集）的M3U播放列表。
"""

import os
import re
import json
import subprocess
import sys

# --- 配置区 -------------------------------------------------
# 在这里填写你的YouTube播放列表链接
PLAYLIST_URLS = [
    "https://www.youtube.com/playlist?list=PLwEZ9TU8jLG8qEHivbNNjYS4GwL82ebgV",
    "https://www.youtube.com/playlist?list=PLCA_sYp__ahVnIoY4i4H4t1X5lripurpv",
    "https://www.youtube.com/playlist?list=PLG7s6E3b-GiPyoChletK0XK_r7IqbNuLF",
    "https://www.youtube.com/playlist?list=PLIj4BzSwQ-_sOsjAiVEQNraRqbEKCwpIT",
    "https://www.youtube.com/playlist?list=PLBsq7Qi22k-dc2SVTZNGblius-fEiPY3e",
]
# 输出文件名
OUTPUT_FILE = "youtube_playlists.m3u"

# --- 核心函数 ------------------------------------------------
def get_playlist_info(playlist_url):
    """
    使用yt-dlp获取播放列表的标题和其中每个视频的原始信息
    """
    print(f"🔄 正在解析播放列表: {playlist_url}")
    cmd = [
        "yt-dlp",
        "--flat-playlist",  # 只获取列表信息，不深入视频详情，速度快
        "--dump-json",      # 以JSON格式输出
        playlist_url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')

    if result.returncode != 0:
        print(f"❌ 解析播放列表失败: {result.stderr}")
        return None

    # yt-dlp对于每个条目输出一行JSON
    playlist_title = None
    entries = []
    for line in result.stdout.strip().split('\n'):
        if not line:
            continue
        try:
            info = json.loads(line)
            # 播放列表的标题通常在第一条信息中
            if playlist_title is None and 'playlist_title' in info:
                playlist_title = info['playlist_title']
            # 提取视频的必要信息
            if 'id' in info and 'title' in info:
                entries.append({
                    'video_id': info['id'],
                    'title': info['title'],
                    'webpage_url': f"https://www.youtube.com/watch?v={info['id']}",
                })
        except json.JSONDecodeError:
            continue

    return {
        'playlist_title': playlist_title or "未命名播放列表",
        'entries': entries,
    }

def get_video_stream_url(video_info):
    """
    获取单个视频的最佳流媒体地址
    """
    video_url = video_info['webpage_url']
    title = video_info['title']
    print(f"   🔗 正在获取地址: {title[:50]}...")

    # 使用 -g 参数让yt-dlp直接输出最佳质量的流媒体URL
    cmd = ["yt-dlp", "-g", "-f", "best", video_url]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"   ⚠️ 无法获取流地址: {title[:30]}... 错误: {result.stderr.strip()}")
        return None
    # yt-dlp可能会输出多个URL（比如视频和音频分开），这里只取第一个（通常是视频）
    stream_url = result.stdout.strip().split('\n')[0]
    return stream_url

def sanitize_filename(filename):
    """清理文件名中的非法字符"""
    return re.sub(r'[\\/*?:"<>|]', "_", filename)

def generate_m3u_file(all_playlists_data, output_filename):
    """
    将收集到的数据生成标准M3U文件
    """
    print(f"\n📝 正在生成播放列表文件: {output_filename}")
    with open(output_filename, 'w', encoding='utf-8') as f:
        # 写入M3U文件头
        f.write('#EXTM3U\n')
        f.write('# 由 YouTube Playlist to M3U Generator 生成\n\n')

        for playlist_data in all_playlists_data:
            playlist_title = playlist_data['playlist_title']
            entries = playlist_data['entries']

            if not entries:
                print(f"⚠️ 跳过空播放列表: {playlist_title}")
                continue

            # 写入分组（电视剧）信息
            # 标准M3U分组标记 #EXTGRP
            f.write(f'#EXTGRP:{playlist_title}\n')
            # 为每个剧集添加一个注释行，方便在某些播放器中显示
            f.write(f'# 电视剧: {playlist_title}\n')

            print(f"  📂 正在写入剧集: {playlist_title} (共 {len(entries)} 集)")
            for idx, entry in enumerate(entries, start=1):
                # 获取视频的真实流地址（在运行时动态获取）
                stream_url = get_video_stream_url(entry)
                if not stream_url:
                    # 如果无法获取流地址，则使用其原始YouTube网页地址作为备用
                    stream_url = entry['webpage_url']
                    print(f"     ⚠️ 第{idx}集 '{entry['title'][:40]}...' 无法获取流地址，将使用网页地址作为备用")

                # 写入单集（条目）信息
                # 格式: #EXTINF:时长(可选，这里用-1代替),显示名称
                # 显示名称格式为: "第1集 - 原标题"
                display_name = f"第{idx}集 - {entry['title']}"
                f.write(f'#EXTINF:-1,{display_name}\n')
                f.write(f'{stream_url}\n')
                print(f"     ✅ 第{idx}集 '{entry['title'][:40]}...' 已添加")

                # 可选：为避免请求过快导致被封，可以增加一个小延时
                # import time; time.sleep(0.5)
            f.write('\n')  # 在每个播放列表后添加一个空行，增加可读性

    print(f"\n🎉 完成！播放列表已保存为: {output_filename}")

# --- 主程序 -------------------------------------------------
def main():
    print("🎬 YouTube 播放列表转 M3U 播放列表生成器")
    print("=" * 40)

    if not PLAYLIST_URLS:
        print("❌ 错误: 没有提供任何播放列表URL，请检查脚本开头的 PLAYLIST_URLS 列表。")
        sys.exit(1)

    all_playlists_data = []
    for url in PLAYLIST_URLS:
        playlist_info = get_playlist_info(url)
        if playlist_info and playlist_info['entries']:
            all_playlists_data.append(playlist_info)
        else:
            print(f"⚠️ 未能从 {url} 获取有效数据，已跳过。")

    if not all_playlists_data:
        print("❌ 错误: 未能从任何播放列表获取有效数据。")
        sys.exit(1)

    generate_m3u_file(all_playlists_data, OUTPUT_FILE)


if __name__ == "__main__":
    main()
