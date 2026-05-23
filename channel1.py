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
    {"name": "酷看独播剧场", "url": "https://www.youtube.com/@KukanDrama"},
    {"name": "影视剧汇踪", "url": "https://www.youtube.com/@影视剧汇踪"}

]







def get_stream_info(url):
    """
    解析直播源，返回 (直播间标题, m3u8链接)
    """
    try:
        session = streamlink.Streamlink()
        match = session.resolve_url(url)
        
        if not match:
            print(f"Streamlink 无法解析此网址: {url}")
            return None, None
            
        # 根据返回值的数量进行安全解包（兼容新老版本 Streamlink）
        if len(match) == 3:
            plugin_name, plugin_class, resolved_url = match
        elif len(match) == 2:
            plugin_class, resolved_url = match
        else:
            # 极限兜底：提取类和网址
            plugin_class = match[1]
            resolved_url = match[-1]
        
        # 实例化插件对象
        plugin = plugin_class(session, resolved_url)
        
        # 获取流
        streams = plugin.streams()
        
        if "best" not in streams:
            return None, None
            
        # 提取标题
        title = plugin.get_title()
        if not title:
            title = "未知标题"
            
        return title, streams["best"].url
        
    except streamlink.exceptions.NoPluginError:
        print(f"获取失败: 不支持的网址格式 {url}")
        return None, None
    except streamlink.exceptions.PluginError as e:
        # 这里专门捕获 YouTube 解析不到 videoId 的错误，通常是因为没开播
        if "Could not find videoId" in str(e):
            print(f"频道未开播或无法解析: {url}")
        else:
            print(f"插件解析错误: {e}")
        return None, None
    except Exception as e:
        print(f"未知错误: {url} -> {e}")
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
