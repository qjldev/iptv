import yt_dlp
import json
from urllib.parse import urlparse, parse_qs

# 你的YouTube播放列表URL
playlist_urls = [
    "https://www.youtube.com/watch?v=qtKpNpn8blM&list=PLCA_sYp__ahVnIoY4i4H4t1X5lripurpv&index=1",
    "https://www.youtube.com/watch?v=Ldg2kZ7SSsY&list=PLIj4BzSwQ-_sOsjAiVEQNraRqbEKCwpIT&index=1",
    "https://www.youtube.com/watch?v=n3BWhGVJa7c&list=PLBsq7Qi22k-dc2SVTZNGblius-fEiPY3e&index=1"
]

def extract_playlist_info(url):
    """提取播放列表信息"""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # 获取播放列表标题
            playlist_title = info.get('title', '未知电视剧')
            
            # 获取所有视频
            entries = info.get('entries', [])
            
            videos = []
            for idx, entry in enumerate(entries, 1):
                video_id = entry.get('id')
                title = entry.get('title', f'第{idx}集')
                duration = entry.get('duration', 0)
                
                # 格式化时长
                minutes = duration // 60
                seconds = duration % 60
                duration_str = f"{minutes:02d}:{seconds:02d}" if duration > 0 else "00:00"
                
                videos.append({
                    'number': idx,
                    'title': title,
                    'id': video_id,
                    'duration': duration_str,
                    'url': f"https://www.youtube.com/watch?v={video_id}"
                })
            
            return {
                'title': playlist_title,
                'videos': videos
            }
    except Exception as e:
        print(f"错误: {e}")
        return None

def generate_m3u(playlists, output_file='tv.m3u'):
    """生成M3U文件"""
    with open(output_file, 'w', encoding='utf-8') as f:
        # 写入M3U头
        f.write('#EXTM3U\n')
        
        for playlist in playlists:
            if not playlist:
                continue
                
            title = playlist['title']
            videos = playlist['videos']
            
            print(f"\n📺 电视剧: {title}")
            print(f"   共 {len(videos)} 集")
            
            for video in videos:
                # 写入扩展信息
                f.write(f'#EXTINF:-1 tvg-id="" tvg-name="{video["title"]}" tvg-logo="" group-title="{title}",{video["title"]}\n')
                # 写入URL
                f.write(f'{video["url"]}\n')
                
                print(f"   ✅ {video['title']}")
        
        print(f"\n✅ M3U文件已生成: {output_file}")

def main():
    print("🎬 开始获取电视剧信息...\n")
    
    all_playlists = []
    
    for url in playlist_urls:
        print(f"📥 正在处理: {url}")
        info = extract_playlist_info(url)
        if info:
            all_playlists.append(info)
    
    if all_playlists:
        generate_m3u(all_playlists)
    else:
        print("❌ 未能获取任何播放列表信息")

if __name__ == '__main__':
    main()
