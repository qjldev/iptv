from streamlink import streams
import time

# 直播间列表
CHANNELS = [
{
        "name": "潜伏",
        "url": "https://www.youtube.com/watch?v=a-XpSWzP7JE"
    },
    {
        "name": "甄嬛传",
        "url": "https://www.youtube.com/watch?v=aZQG7ltunS0"
    },
    {
        "name": "后宫甄嬛传",
        "url": "https://www.youtube.com/watch?v=HmxuvOSB0OI"
    },
    {
        "name": "雍正王朝",
        "url": "https://www.youtube.com/watch?v=0z4IHU4g-1M"
    },
    {
        "name": "父母爱情",
        "url": "https://www.youtube.com/watch?v=Hou7uVklRxA"
    },  
    {
        "name": "汉武大帝",
        "url": "https://www.youtube.com/watch?v=JQdMw93ouv4"
    },
    {
        "name": "西游记",
        "url": "https://www.youtube.com/watch?v=z7kKvkBeepQ"
    },
    {
        "name": "三国演义",
        "url": "https://www.youtube.com/watch?v=XNO0vjTNhzo"
    },
    {
        "name": "康熙王朝",
        "url": "https://www.youtube.com/watch?v=iT7RicpCeic"
    },
    {
        "name": "红楼梦",
        "url": "https://www.youtube.com/watch?v=kWeO1gdM0Cg"
    },
    {
        "name": "武林外传",
        "url": "https://www.youtube.com/watch?v=9e7p4F7myy8"
    },
    {
        "name": "包青天",
        "url": "https://www.youtube.com/watch?v=Qq-uMi_1Rzk"
    },
    {
        "name": "雍正王朝China Zone俱乐部",
        "url": "https://www.youtube.com/watch?v=DbNDCtzTzxQ"
    },
    {
        "name": "琅琊榜",
        "url": "https://www.youtube.com/watch?v=5VHcY5Unh7M"
    }
]


def get_best_stream(url):
    try:
        s = streams(url)

        # best = 最高画质
        if "best" not in s:
            return None

        best_stream = s["best"]

        return best_stream.url

    except Exception as e:
        print(f"获取失败: {url}")
        print(e)

    return None


def generate_playlist():
    playlist = "#EXTM3U\n\n"

    for channel in CHANNELS:
        name = channel["name"]
        url = channel["url"]

        print(f"正在解析: {name}")

        stream_url = get_best_stream(url)

        if stream_url:
            print(f"成功: {name}")

            playlist += f"#EXTINF:-1,{name}\n"
            playlist += f"{stream_url}\n\n"

        else:
            print(f"失败: {name}")

    with open("playlist.m3u", "w", encoding="utf-8") as f:
        f.write(playlist)

    print("\n已生成 playlist.m3u")


generate_playlist()
