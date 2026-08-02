#!/usr/bin/env python3
"""
Generate one .m3u8 playlist file for each YouTube playlist URL.

Usage:
  1. Edit PLAYLIST_URLS below, then run:
     python youtube_playlists_to_m3u8.py

  2. Or pass URLs from the command line:
  python youtube_playlists_to_m3u8.py "https://www.youtube.com/playlist?list=..."
  python youtube_playlists_to_m3u8.py --input playlists.txt

Dependency:
  pip install yt-dlp

Notes:
  This writes the highest-quality single-file media URL that yt-dlp can find
  for each video. YouTube direct media URLs are often temporary and may stop
  working later; regenerate the .m3u8 file when that happens.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Iterable
from urllib.parse import parse_qs, urlparse


# Put your YouTube playlist links here.
# Add one string per playlist. The script will generate one .m3u8 file per link.
PLAYLIST_URLS = [
    "https://www.youtube.com/playlist?list=PLjlPO2gjIxr_PFiqz98AB0-j9xEYbCE9O",

    "https://www.youtube.com/playlist?list=PLCA_sYp__ahVnIoY4i4H4t1X5lripurpv",

    "https://www.youtube.com/playlist?list=PLSoZdFG148fbHBj8VE0vmn-TM5UZYRlM0",



]


# Highest-quality source that is still one playable URL with both video+audio.
# YouTube's absolute highest quality is often split into separate video/audio
# streams, which ordinary .m3u8 playlist entries cannot combine by themselves.
VIDEO_FORMAT = "best[acodec!=none][vcodec!=none]/best"


try:
    import yt_dlp
except ImportError:  # pragma: no cover
    print(
        "Missing dependency: yt-dlp\n"
        "Install it with:\n"
        "  pip install yt-dlp",
        file=sys.stderr,
    )
    raise SystemExit(1)


WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    "COM1",
    "COM2",
    "COM3",
    "COM4",
    "COM5",
    "COM6",
    "COM7",
    "COM8",
    "COM9",
    "LPT1",
    "LPT2",
    "LPT3",
    "LPT4",
    "LPT5",
    "LPT6",
    "LPT7",
    "LPT8",
    "LPT9",
}


def sanitize_filename(name: str, fallback: str = "youtube_playlist") -> str:
    """Return a filesystem-safe filename stem."""
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip()
    name = re.sub(r"\s+", " ", name).strip(" .")

    if not name:
        name = fallback

    if name.upper() in WINDOWS_RESERVED_NAMES:
        name = f"{name}_playlist"

    return name[:150]


def read_urls_from_file(path: Path) -> list[str]:
    """Read non-empty, non-comment URLs from a text file."""
    urls: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            urls.append(line)
    return urls


def get_playlist_id(url: str) -> str | None:
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    values = query.get("list")
    return values[0] if values else None


def video_watch_url(entry: dict) -> str | None:
    """Build a stable YouTube watch URL for a playlist entry."""
    webpage_url = entry.get("webpage_url")
    if isinstance(webpage_url, str) and webpage_url.startswith("http"):
        return webpage_url

    raw_url = entry.get("url")
    if isinstance(raw_url, str) and raw_url.startswith("http"):
        return raw_url

    video_id = entry.get("id") or raw_url
    if isinstance(video_id, str) and re.fullmatch(r"[\w-]{8,}", video_id):
        return f"https://www.youtube.com/watch?v={video_id}"

    return None


def extract_best_video_source(watch_url: str) -> tuple[str, int | None]:
    """Return the best single-file media URL and duration for one video."""
    ydl_opts = {
        "format": VIDEO_FORMAT,
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(watch_url, download=False)

    if not isinstance(info, dict):
        raise RuntimeError("yt-dlp did not return video metadata")

    media_url = info.get("url")
    if not isinstance(media_url, str) or not media_url.startswith("http"):
        raise RuntimeError("No direct media URL was found")

    duration = info.get("duration")
    duration_int = int(duration) if isinstance(duration, (int, float)) else None

    return media_url, duration_int


def m3u_escape(value: object) -> str:
    return str(value or "").replace("\r", " ").replace("\n", " ").strip()


def unique_path(path: Path) -> Path:
    """Avoid overwriting an existing file by adding -2, -3, ..."""
    if not path.exists():
        return path

    stem = path.stem
    suffix = path.suffix
    parent = path.parent

    for index in range(2, 1000):
        candidate = parent / f"{stem}-{index}{suffix}"
        if not candidate.exists():
            return candidate

    raise RuntimeError(f"Too many duplicate filenames for {path}")


def extract_playlist(url: str) -> dict:
    ydl_opts = {
        "extract_flat": "in_playlist",
        "ignoreerrors": True,
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    if not isinstance(info, dict):
        raise RuntimeError("yt-dlp did not return playlist metadata")

    return info


def write_m3u8(playlist_info: dict, source_url: str, output_dir: Path) -> Path:
    playlist_id = playlist_info.get("id") or get_playlist_id(source_url) or "playlist"
    playlist_title = playlist_info.get("title") or f"YouTube Playlist {playlist_id}"
    filename = sanitize_filename(str(playlist_title), fallback=str(playlist_id)) + ".m3u8"
    output_path = unique_path(output_dir / filename)

    entries = playlist_info.get("entries") or []
    lines = [
        "#EXTM3U",
        f"#PLAYLIST:{m3u_escape(playlist_title)}",
        f"#SOURCE:{m3u_escape(source_url)}",
    ]

    count = 0
    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            continue

        watch_url = video_watch_url(entry)
        if not watch_url:
            continue

        title = m3u_escape(entry.get("title") or f"Episode {index}")

        try:
            url, duration = extract_best_video_source(watch_url)
        except Exception as exc:
            print(f"  Skipped {title}: {exc}", file=sys.stderr)
            continue

        entry_duration = duration if duration is not None else entry.get("duration")
        duration_text = int(entry_duration) if isinstance(entry_duration, (int, float)) else -1

        lines.append(f'#EXTINF:{duration_text}, {title}')
        lines.append(url)
        count += 1

    if count == 0:
        raise RuntimeError("No playable playlist entries were found")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
    return output_path


def collect_urls(args: argparse.Namespace) -> list[str]:
    urls: list[str] = []

    if args.input:
        urls.extend(read_urls_from_file(args.input))

    urls.extend(args.urls)

    if not urls:
        urls.extend(PLAYLIST_URLS)

    seen: set[str] = set()
    unique_urls: list[str] = []
    for url in urls:
        if url not in seen:
            unique_urls.append(url)
            seen.add(url)

    return unique_urls


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate .m3u8 files from YouTube playlist links."
    )
    parser.add_argument(
        "urls",
        nargs="*",
        help="YouTube playlist URLs.",
    )
    parser.add_argument(
        "-i",
        "--input",
        type=Path,
        help="Text file containing one playlist URL per line.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Directory for generated .m3u8 files. Default: this script's directory",
    )
    return parser.parse_args(list(argv))


def main(argv: Iterable[str] = sys.argv[1:]) -> int:
    args = parse_args(argv)
    urls = collect_urls(args)

    if not urls:
        print(
            "Please provide at least one YouTube playlist URL.\n"
            'Example: python youtube_playlists_to_m3u8.py "https://www.youtube.com/playlist?list=..."',
            file=sys.stderr,
        )
        return 2

    output_dir = args.output or Path(__file__).resolve().parent
    output_dir.mkdir(parents=True, exist_ok=True)

    failures = 0
    for url in urls:
        print(f"Processing: {url}")
        try:
            playlist_info = extract_playlist(url)
            output_path = write_m3u8(playlist_info, url, output_dir)
        except Exception as exc:
            failures += 1
            print(f"  Failed: {exc}", file=sys.stderr)
            continue

        print(f"  Wrote: {output_path}")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
