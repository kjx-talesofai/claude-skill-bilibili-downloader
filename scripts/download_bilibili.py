#!/usr/bin/env python3
"""
Standalone Bilibili video downloader.
Downloads video + audio streams (DASH format) and merges them with ffmpeg.

Usage:
    python download_bilibili.py <bilibili_url> [--output-dir <dir>]

Example:
    python download_bilibili.py "https://www.bilibili.com/video/BV1Z4dPB1E8e"
    python download_bilibili.py BV1Z4dPB1E8e --output-dir ~/Movies
"""

import argparse
import hashlib
import httpx
import os
import re
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path

REFERER = "https://www.bilibili.com/"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"

mixinKeyEncTab = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
    33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
    61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
    36, 20, 34, 44, 52
]


def get_mixin_key(orig: str) -> str:
    return "".join(orig[i] for i in mixinKeyEncTab)[:32]


def enc_wbi(params: dict, img_key: str, sub_key: str) -> str:
    mixin_key = get_mixin_key(img_key + sub_key)
    params["wts"] = round(time.time())
    params = dict(sorted(params.items()))
    params = {k: "".join(c for c in str(v) if c not in "!'()*") for k, v in params.items()}
    query = urllib.parse.urlencode(params)
    wbi_sign = hashlib.md5((query + mixin_key).encode()).hexdigest()
    params["w_rid"] = wbi_sign
    return urllib.parse.urlencode(params)


def get_wbi_keys(client: httpx.Client) -> tuple[str, str]:
    resp = client.get("https://api.bilibili.com/x/web-interface/nav").json()
    img_url = resp["data"]["wbi_img"]["img_url"]
    sub_url = resp["data"]["wbi_img"]["sub_url"]
    img_key = img_url.split("/")[-1].split(".")[0]
    sub_key = sub_url.split("/")[-1].split(".")[0]
    return img_key, sub_key


def extract_bvid(url_or_bvid: str) -> str:
    url_or_bvid = url_or_bvid.strip()
    if url_or_bvid.startswith("BV"):
        return url_or_bvid
    match = re.search(r"BV\w+", url_or_bvid)
    if match:
        return match.group(0)
    raise ValueError(f"Cannot extract BV ID from: {url_or_bvid}")


def get_video_info(client: httpx.Client, bvid: str, img_key: str, sub_key: str) -> dict:
    params = {"bvid": bvid}
    query = enc_wbi(params, img_key, sub_key)
    url = f"https://api.bilibili.com/x/web-interface/wbi/view?{query}"
    resp = client.get(url).json()
    if resp.get("code") != 0:
        raise Exception(f"Failed to get video info: {resp.get('message')}")
    return resp["data"]


def get_playurl(client: httpx.Client, bvid: str, cid: int, img_key: str, sub_key: str) -> dict:
    params = {
        "bvid": bvid,
        "cid": cid,
        "qn": 80,
        "fnver": 0,
        "fnval": 4048,
        "fourk": 1,
    }
    query = enc_wbi(params, img_key, sub_key)
    url = f"https://api.bilibili.com/x/player/playurl?{query}"
    resp = client.get(url).json()
    if resp.get("code") != 0:
        raise Exception(f"Failed to get playurl: {resp.get('message')}")
    return resp["data"]


def download_file(client: httpx.Client, url: str, output_path: Path, desc: str):
    headers = {"Referer": REFERER}
    with client.stream("GET", url, headers=headers, follow_redirects=True) as response:
        response.raise_for_status()
        total = int(response.headers.get("content-length", 0))
        downloaded = 0
        with open(output_path, "wb") as f:
            for chunk in response.iter_bytes(chunk_size=8192):
                f.write(chunk)
                downloaded += len(chunk)
                if total > 0:
                    pct = downloaded / total * 100
                    print(f"\r  {desc}: {pct:.1f}%", end="", flush=True)
    print()


def merge_with_ffmpeg(video_path: Path, audio_path: Path, output_path: Path):
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-i", str(audio_path),
        "-c", "copy",
        str(output_path)
    ]
    print(f"  Merging with ffmpeg -> {output_path.name}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"ffmpeg merge failed: {result.stderr}")


def sanitize_filename(name: str) -> str:
    return "".join(c for c in name if c.isalnum() or c in " _-").strip() or "bilibili_video"


def download_video(url_or_bvid: str, output_dir: Path | None = None) -> Path:
    if output_dir is None:
        output_dir = Path.home() / "Downloads" / "bilibili_videos"
    output_dir.mkdir(parents=True, exist_ok=True)

    bvid = extract_bvid(url_or_bvid)
    print(f"Target video: {bvid}")

    headers = {"Referer": REFERER, "User-Agent": USER_AGENT}
    with httpx.Client(headers=headers, timeout=60, follow_redirects=True) as client:
        print("Fetching WBI keys...")
        img_key, sub_key = get_wbi_keys(client)

        print("Fetching video info...")
        info = get_video_info(client, bvid, img_key, sub_key)
        title = info["title"]
        cid = info["cid"]
        print(f"Title: {title}")

        print("Fetching stream URLs...")
        playurl = get_playurl(client, bvid, cid, img_key, sub_key)

        dash = playurl.get("dash")
        if not dash:
            raise Exception("No DASH streams available")

        video_streams = dash.get("video", [])
        audio_streams = dash.get("audio", [])
        if not video_streams or not audio_streams:
            raise Exception("No video/audio streams found")

        video_streams.sort(key=lambda x: x.get("bandwidth", 0), reverse=True)
        audio_streams.sort(key=lambda x: x.get("bandwidth", 0), reverse=True)

        best_video = video_streams[0]
        best_audio = audio_streams[0]
        video_url = best_video.get("baseUrl") or best_video.get("base_url")
        audio_url = best_audio.get("baseUrl") or best_audio.get("base_url")
        print(f"Video quality: {best_video.get('id')} | Audio quality: {best_audio.get('id')}")

        safe_title = sanitize_filename(title)
        video_path = output_dir / f"{safe_title}_video.m4s"
        audio_path = output_dir / f"{safe_title}_audio.m4s"
        output_path = output_dir / f"{safe_title}.mp4"

        print(f"\nDownloading video stream...")
        download_file(client, video_url, video_path, "Video")

        print(f"Downloading audio stream...")
        download_file(client, audio_url, audio_path, "Audio")

    print()
    merge_with_ffmpeg(video_path, audio_path, output_path)

    video_path.unlink()
    audio_path.unlink()

    print(f"\nDone! Saved to: {output_path}")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Download Bilibili videos")
    parser.add_argument("url", help="Bilibili video URL or BV ID")
    parser.add_argument("--output-dir", "-o", type=Path, default=None, help="Output directory")
    args = parser.parse_args()

    try:
        download_video(args.url, args.output_dir)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
