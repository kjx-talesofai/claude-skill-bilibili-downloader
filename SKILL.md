---
name: bilibili-downloader
description: Download Bilibili videos to local MP4. Triggers on bilibili.com URLs, BV IDs, or phrases like "download bilibili video" / "下载哔哩哔哩视频" / "B站下载".
---

# Bilibili Video Downloader

Download Bilibili videos directly without needing the Bili23-Downloader GUI.

## How to Use

1. Extract the BV ID from the user's URL (e.g., `BV1Z4dPB1E8e` from `https://www.bilibili.com/video/BV1Z4dPB1E8e`)
2. Run the bundled script: `python scripts/download_bilibili.py <URL_or_BVID>`
3. The script downloads to `~/Downloads/bilibili_videos/` by default

## Script Interface

```bash
# Download by full URL
python scripts/download_bilibili.py "https://www.bilibili.com/video/BV1Z4dPB1E8e"

# Download by BV ID directly
python scripts/download_bilibili.py BV1Z4dPB1E8e

# Custom output directory
python scripts/download_bilibili.py BV1Z4dPB1E8e --output-dir ~/Movies
```

## Python API

```python
from scripts.download_bilibili import download_video
from pathlib import Path

# Returns the Path to the downloaded MP4 file
output = download_video("https://www.bilibili.com/video/BV1Z4dPB1E8e")
# or
output = download_video("BV1Z4dPB1E8e", output_dir=Path.home() / "Videos")
```

## What It Does

1. **Fetch WBI keys** from Bilibili's nav API (required for API signatures)
2. **Get video metadata** (title, CID, pages) via `/x/web-interface/wbi/view`
3. **Get stream URLs** via `/x/player/playurl` (DASH format: separate video + audio)
4. **Download both streams** with progress output
5. **Merge with ffmpeg** into a single MP4 file
6. **Clean up** temporary `.m4s` files

## Limitations

- **Quality**: Without login cookies, max quality is 480P. Bilibili restricts higher qualities (1080P, 4K) to logged-in users.
- **Dependencies**: Requires `httpx` and `ffmpeg` installed on the system.
- **No subtitles/danmaku**: This is a lightweight downloader. For subtitles, danmaku, or 4K downloads, use the full Bili23-Downloader GUI with login.
