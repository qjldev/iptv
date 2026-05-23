import streamlink
import subprocess
import time
import datetime

# 【注意】这里的 URL 需要替换为频道的 /live 地址
# 例如：https://www.youtube.com/@ChinaZone/live




CHANNELS = [
    {"name": "CCTV", "url": "https://www.youtube.com/@CCTVDrama"},
    {"name": "乐视", "url": "https://www.youtube.com/@letvdramas"},
    {"name": "百纳", "url": "https://www.youtube.com/@BainationTVSeriesOfficial"},
    {"name": "后宫甄嬛传", "url": "https://www.youtube.com/@LegendofConcubineZhenHuan"},
    {"name": "三立化剧", "url": "https://www.youtube.com/@SETdrama"},
    {"name": "China Zone", "url": "https://www.youtube.com/@ChinaZoneDrama"},
    {"name": "台视时光机", "url": "https://www.youtube.com/@TTVClassic"},
    {"name": "华视戏剧频道", "url": "https://www.youtube.com/@cts_drama"},
    {"name": "酷看独播剧场", "url": "https://www.youtube.com/@KukanDrama"}

]







def get_stream_info(url):
    """
    解析直播源，返回 (直播间标题, m3u8链接)
    """
    try:
        # 创建 Streamlink 会话
        session = streamlink.Streamlink()
        # 解析网址获取对应的插件
        plugin = session.resolve_url(url)
        
        if not plugin:
            print(f"Streamlink 无法解析此网址: {url}")
            return None, None
            
        # 获取所有清晰度的流
        streams = plugin.streams()
        
        if "best" not in streams:
            return None, None
            
        # 提取直播间真实标题，如果获取失败则给个默认值
        title = plugin.get_title()
        if not title:
            title = "未知标题"
            
        return title, streams["best"].url
        
    except Exception as e:
        print(f"获取失败: {url}")
        print(e)
        return None, None

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

    for channel in CHANNELS:
        name = channel["name"]
        url = channel["url"]

        print(f"正在解析: {name} ...")

        # 解构返回的标题和链接
        title, stream_url = get_stream_info(url)

        if stream_url:
            print(f"成功: {name} - {title}")
            # 按照 "自定义name-直播间名" 格式拼接
            playlist += f"#EXTINF:-1,{name}-{title}\n{stream_url}\n\n"
        else:
            print(f"失败: {name}")

    with open("playlist.m3u", "w", encoding="utf-8") as f:
        f.write(playlist)

    print("\n已生成 playlist.m3u")

    # 自动推送到 Git
    git_push()

if __name__ == "__main__":
    generate_playlist()
